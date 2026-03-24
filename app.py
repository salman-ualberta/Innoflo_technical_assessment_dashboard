import streamlit as st
import pandas as pd
from utility import get_week_label
from Q1 import top_card, total_consumed_volume_per_product, per_product_consumption_trend
from Q2 import top_10_eqipment_categories, top_5_equipment_groups, top_50_equipment_items

# 1. Setup Page
st.set_page_config(page_title="Fuel Analytics Dashboard", layout="wide")

# 2. Data Loading Function
@st.cache_data # since the data is static, the data will be loaded once and cached.
def load_and_merge_data():
    # Load all 5 files
    df_trans = pd.read_csv('./data/Site_1_dispensing_transactions_2026-03-17T10_48_09-06_00.csv')
    df_equip = pd.read_csv('./data/Site_1_equipment_items_2026-03-17T10_45_45-06_00.csv')
    df_cats = pd.read_csv('./data/Site_1_equipment_categories_2026-03-17T10_45_16-06_00.csv')
    df_groups = pd.read_csv('./data/Site_1_equipment_groups_2026-03-17T10_45_12-06_00.csv')
    df_prod = pd.read_csv('./data/Site_1_products_2026-03-17T10_24_50-06_00.csv')

    # Convert string to actual Python datetime objects
    df_trans['Date'] = pd.to_datetime(df_trans['Date'], dayfirst=True, errors='coerce')
    df_trans = df_trans.dropna(subset=['Date']) # Remove rows with empty dates

    # Remove unwanted space from the data
    df_trans['Equipment ID'] = df_trans['Equipment ID'].str.strip()
    df_equip['Equipment ID'] = df_equip['Equipment ID'].str.strip()
    df_equip['Equipment Category'] = df_equip['Equipment Category'].str.strip()
    df_equip['Equipment Group'] = df_equip['Equipment Group'].str.strip()
    df_cats['Equipment Category ID'] = df_cats['Equipment Category ID'].str.strip()
    df_groups['Equipment Group ID'] = df_groups['Equipment Group ID'].str.strip()

    # Remove transactions with Equipment IDs that are not present in the Equipment Item table but keep the empty ones
    valid_ids = df_equip['Equipment ID'].unique()
    mask = df_trans['Equipment ID'].isin(valid_ids) | df_trans['Equipment ID'].isna()
    df_trans = df_trans[mask]
        


    # Covert volume to numeric data
    df_trans['Volume'] = pd.to_numeric(df_trans['Volume'], errors='coerce').fillna(0)

    # The Master Merge
    # 1. Join Transactions to Equipment Items
    df_merged = df_trans.merge(
        df_equip[['Equipment ID', 'Equipment Group', 'Equipment Category', 'Description']].rename(columns={'Description': 'Equip_Desc'}),
        on='Equipment ID',
        how='left'
    )
    
    # 2. Join to get Category Names
    df_merged = df_merged.merge(
        df_cats[['Equipment Category ID', 'Description']].rename(columns={'Description': 'Equipment_Category_Name'}),
        left_on='Equipment Category',
        right_on='Equipment Category ID',
        how='left'
    )

    # 3. Join to get Group Names
    df_merged = df_merged.merge(
        df_groups[['Equipment Group ID', 'Description']].rename(columns={'Description': 'Equipment_Group_Name'}),
        left_on='Equipment Group',
        right_on='Equipment Group ID',
        how='left'
    )

    # 4. Join to get Product Names
    df_merged = df_merged.merge(
        df_prod[['Product ID', 'Description']].rename(columns={'Description': 'Product Name'}),
        left_on='Product',
        right_on='Product ID',
        how='left'
    )

 
    # Final Polish: Fill empty equipment information with "No Recorded Equipment" and "Unassigned" for category and group.
    df_merged['Equipment ID'] = df_merged['Equipment ID'].fillna('No Recorded Equipment ID')
    df_merged['Equip_Desc'] = df_merged['Equip_Desc'].fillna('No Recorded Equipment Description')
    df_merged['Equipment_Category_Name'] = df_merged['Equipment_Category_Name'].fillna('Unassigned Category')
    df_merged['Equipment_Group_Name'] = df_merged['Equipment_Group_Name'].fillna('Unassigned Group')
    df_merged['Product'] = df_merged['Product'].fillna('Unknown Product')
    df_merged['Product Name'] = df_merged['Product Name'].fillna(df_merged['Product']) # Fallback to ID if no name
    
    #Add extra columns to help data filtering
    df_merged['Year'] = df_merged['Date'].dt.year
    df_merged['Month_Name'] = df_merged['Date'].dt.strftime('%B')
    df_merged['Week_Number'] = df_merged['Date'].dt.isocalendar().week
    df_merged['Day_Date'] = df_merged['Date'].dt.date
    df_merged['Custom_Week_Label'] = df_merged.apply(get_week_label, axis=1)

    return df_merged

def sidebar_filters(df):
    st.sidebar.header("Report Configuration")

    # Step 1: Select Report Type
    report_type = st.sidebar.selectbox(
        "1. Select Report Type", 
        # ["Monthly", "Weekly", "Daily", "Custom Range"]
        ["Over the past 3 months","Monthly", "Weekly", "Daily", "Custom Date Range"]
    )

    # Initialize the filtered dataframe
    df_filtered = df.copy()

    # Step 2: Show Dynamic Sub-Filters based on Report Type
    if report_type == "Monthly":
        
        # i. Select Year
        available_years = sorted(df['Year'].unique())
        sel_year = st.sidebar.selectbox("2. Select Year", available_years)
        
        # ii. Filter by year to only show months that actually have data for that year
        df_year = df[df['Year'] == sel_year]
        months = sorted(df_year['Month_Name'].unique(), 
                        key=lambda x: pd.to_datetime(x, format='%B').month)
        sel_month = st.sidebar.selectbox("3. Select Month", months)
        
        # Filter original data based on the selected filters
        df_filtered = df_year[df_year['Month_Name'] == sel_month]

    elif report_type == "Weekly":
        # i. Select Year
        years = sorted(df['Year'].unique())
        sel_year = st.sidebar.selectbox("2. Select Year", years)
        df_year = df[df['Year'] == sel_year]
        
        # ii. Select Month
        months = sorted(df_year['Month_Name'].unique(), 
                        key=lambda x: pd.to_datetime(x, format='%B').month)
        sel_month = st.sidebar.selectbox("3. Select Month", months)
        df_month = df_year[df_year['Month_Name'] == sel_month]
        
        # iii. Select Week (DYNAMIC: Only shows weeks that have data)
        available_weeks = sorted(df_month['Custom_Week_Label'].unique())
        sel_week = st.sidebar.selectbox("4. Select Week", available_weeks)
        
        # Filter original data based on the selected filters
        df_filtered = df_month[df_month['Custom_Week_Label'] == sel_week]

    elif report_type == "Daily":
        # i. Select Year
        available_years = sorted(df['Year'].unique())
        sel_year = st.sidebar.selectbox("2. Select Year", available_years)
               
        # ii. Handle data availability based on the selected year
        # Find the actual first/last day of data within that year
        df_year = df[df['Year'] == sel_year]
        data_min = df_year['Day_Date'].min()
        data_max = df_year['Day_Date'].max()

        # The Calendar Widget
        # value: what the calendar opens to
        # min_value/max_value: what the user is ALLOWED to click
        sel_day = st.sidebar.date_input(
            "3. Select Date",
            value=data_min,
            min_value=data_min,
            max_value=data_max
        )
        
        # Filter original data based on the selected filters
        df_filtered = df[df['Day_Date'] == sel_day]

    elif report_type == "Custom Date Range":
        start_year = st.sidebar.selectbox("2. Select Start Year", sorted(df['Year'].unique()), key="start_yr")
        df_start_yr = df[df['Year'] == start_year]
        
        start_date = st.sidebar.date_input(
            "3. Select Start Date",
            value=df_start_yr['Day_Date'].min(),
            min_value=df_start_yr['Day_Date'].min(),
            max_value=df_start_yr['Day_Date'].max(),
            key="start_dt"
        )

        if start_date:
            end_year = st.sidebar.selectbox(
                "4. Select End Year", 
                sorted([y for y in df['Year'].unique() if y >= start_year]), 
                key="end_yr"
            )
            
            df_end_yr = df[df['Year'] == end_year]
            
            # The absolute minimum for End Date is the Start Date
            # The absolute maximum is the end of the data in that year
            abs_max_data = df_end_yr['Day_Date'].max()
            
            # Ensure the calendar min_value is never before the start_date
            calendar_min = max(start_date, df_end_yr['Day_Date'].min())

            end_date = st.sidebar.date_input(
                "5. Select End Date",
                value=abs_max_data,
                min_value=calendar_min,
                max_value=abs_max_data,
                key="end_dt"
            )
            
            # Filter original data based on the selected filters
            df_filtered = df[(df['Day_Date'] >= start_date) & (df['Day_Date'] <= end_date)]
        else:
            # Fallback if somehow start_date is cleared
            st.sidebar.warning("Please select a start date first.")
            df_filtered = df.iloc[0:0]

    # Products filter
    # Create a list of products from the filtered data
    all_prods = sorted(df_filtered['Product Name'].unique().tolist())

    # i. Create the "Dropdown" using a Popover
    with st.sidebar.popover("Select Products"):
        st.markdown("Select one or more products:")
        
        selected_prods = []
        
        # ii. Create a checkbox for every product
        for prod in all_prods:
            # value=True makes it checked by default
            if st.checkbox(prod, value=True, key=f"filter_{prod}"):
                selected_prods.append(prod)

    # Check if no product has been selected
    if not selected_prods:
        st.warning("Please select at least one product to display data.")
        # Show an empty dataframe to avoid chart errors
        df_filtered = df_filtered.iloc[0:0] 
    else:
        # Filter tje actual data based on the selected products
        df_filtered = df_filtered[df_filtered['Product Name'].isin(selected_prods)]

    return df_filtered, report_type

def q1_visualizations(df_filtered, report_type):
    st.header("Product Consumption Over Time")
    top_card(df_filtered)
    total_consumed_volume_per_product(df_filtered)
    per_product_consumption_trend(df_filtered, report_type)
    st.markdown("---")

def q2_visualizations(df_filtered):
    st.header("Largest Consumers Analysis")
    col1, col2 = st.columns(2)
    with col1:
        top_10_eqipment_categories(df_filtered)
    with col2:
        top_5_equipment_groups(df_filtered)

    top_50_equipment_items(df_filtered)
        


# --- MAIN Function ---
def main():
    try:
        df = load_and_merge_data()
    except Exception as e:
        st.error(f"Failed to load data: {e}")
        return

    # Get Filtered Data
    df_filtered, report_type = sidebar_filters(df)
    
    st.markdown("<h1 style='text-align: center;'>Fuel Analytics Dashboard</h1>", unsafe_allow_html=True)
    
    # Check if we have data to show
    if df_filtered.empty:
        st.warning("No data matches the selected filters.")
        return
    
    try:
        q1_visualizations(df_filtered, report_type)
    except Exception as e:
        st.error(f"Error loading Product Consumption charts: {e}")

    try:
        q2_visualizations(df_filtered)
    except Exception as e:
        st.error(f"Error loading Consumer Analysis charts: {e}")


if __name__ == "__main__":
    main()

    