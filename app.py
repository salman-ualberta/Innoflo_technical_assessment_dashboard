import streamlit as st
import pandas as pd
from utility import get_week_label, PRODUCT_COLORS, PRODUCT_LABEL_COLORS
import plotly.express as px

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
        ["Monthly", "Weekly", "Daily"]
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

        # 4. The Calendar Widget
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


def top_card(df_filtered):
    # Calculate metrics
    total_vol = df_filtered['Volume'].sum()
    avg_daily = total_vol / df_filtered['Day_Date'].nunique()
    top_prod = df_filtered.groupby('Product Name')['Volume'].sum().idxmax()
    top_prod_vol = df_filtered.groupby('Product Name')['Volume'].sum().max()

    # Display in columns
    kpi1, kpi2, kpi3 = st.columns(3)
    kpi1.metric("Total Dispensed", f"{total_vol:,.0f} L")
    kpi2.metric("Top Product", top_prod, f"{top_prod_vol:,.0f} L")
    kpi3.metric("Avg Daily Consumption", f"{avg_daily:,.0f} L")
    st.markdown("---")

def total_consumed_volume_per_product(df_filtered):
    df_totals = df_filtered.groupby('Product Name')['Volume'].sum().reset_index()
    total_volume_overall = df_totals['Volume'].sum()
    df_totals['percent'] = (df_totals['Volume'] / total_volume_overall) * 100
    df_totals = df_totals.sort_values('Volume', ascending=True)

    fig = px.bar(
        df_totals, 
        x='Volume', 
        y='Product Name', 
        orientation='h',
        log_x=True, # log_x scaling, so small products are actually visible next to Diesel
        title="<b>Total Consumed Volume per Product Type</b>",
        color='Product Name',
        color_discrete_map=PRODUCT_COLORS,
        custom_data=['percent'],
        text='Volume',
        template='plotly_white'
    )

    # Fix data label colors. Black for light colored bar abd white for dark colored bar
    fig.for_each_trace(lambda t: t.update(
        textfont=dict(
            color=PRODUCT_LABEL_COLORS.get(t.name, "white"), 
            size=12
        )
    ))

    # CUSTOMIZATION FOR VISIBILITY
    fig.update_traces(
        hovertemplate=(
            "<b>%{y}</b><br>" +
            "Volume: %{x:.1f} L<br>" +
            "Percentage: %{customdata[0]:.1f}%" +
            "<extra></extra>"
        ),
        texttemplate='%{text:,.0f} L', 
        textposition='inside',        
        insidetextanchor='start',
        marker_line_color='rgb(8,48,107)',
        marker_line_width=1.5,
        opacity=0.8
    )

    fig.update_layout(
        height=500,                    
        margin=dict(l=20, r=20, t=60, b=20),
        hoverlabel=dict(
            bgcolor="white",     
            font_size=13,        
            font_color="black",  
            font_family="Arial"
        ),
        xaxis=dict(
            title="Total Volume",
            title_font=dict(color="black"),
            tickfont=dict(color="black", size=12)
        ),
        yaxis=dict(
            title=None,
            tickfont=dict(color="black", size=12)
        ),
        showlegend=True              
    )

    st.plotly_chart(fig, use_container_width=True)


def per_product_consumption_trend(df_filtered, report_type):
    # Set the grouping column based on report type. For daily report, X axis will show hours.
    if report_type == "Daily":
        df_filtered['Time_Pivot'] = df_filtered['Date'].dt.hour
        x_label = "Hour of Day (24h)"
    else:
        # Use Day_Date for Monthly/Weekly
        df_filtered['Time_Pivot'] = df_filtered['Day_Date']
        x_label = "Date"

    # AGGREGATE: Sum the volume
    df_plot = df_filtered.groupby(['Time_Pivot', 'Product Name'])['Volume'].sum().reset_index()

    # This creates a row for every date/product combo and fills missing ones with 0
    df_pivot = df_plot.pivot(index='Time_Pivot', columns='Product Name', values='Volume').fillna(0)
    
    # Calculate % change compared to previous time period (Delta)
    df_pct = df_pivot.pct_change().replace([float('inf'), float('-inf')], 1.0)
    df_pct = (df_pct.fillna(0) * 100).round(1)

    
    # UNPIVOT (Melt) both Volume and Delta to merge them
    df_volume_melted = df_pivot.reset_index().melt(id_vars='Time_Pivot', var_name='Product Name', value_name='Volume')
    df_delta_melted = df_pct.reset_index().melt(id_vars='Time_Pivot', var_name='Product Name', value_name='Delta')
    df_delta_melted['Delta'] = df_delta_melted['Delta'].astype(float)
    
    # Merge them back so each row has Volume and Delta
    df_plot = pd.merge(df_volume_melted, df_delta_melted, on=['Time_Pivot', 'Product Name'])
    df_plot = df_plot.sort_values(by='Time_Pivot')

    st.markdown("### **Product Consumption Trend View Type:**") 

    view_mode = st.radio(
        label="View Type:",
        options=["Show Product Trends with Volume Distribution", "Show Product Trends"], 
        horizontal=True,
        label_visibility="collapsed"
    )

    # Common parameters for both chart types
    chart_args = {
        "data_frame": df_plot,
        "x": 'Time_Pivot',
        "y": 'Volume',
        "color": 'Product Name',
        "color_discrete_map": PRODUCT_COLORS,
        "labels": {'Volume': 'Total Litres', 'Time_Pivot': x_label},
        "template": 'plotly_white',
        "custom_data": ['Delta'],
        "markers": True    
    }

    if view_mode == "Show Product Trends":
        fig = px.line(
            **chart_args,
            title=f"<b>Product Consumption Trend ({report_type})</b>"
        )
    else:
        fig = px.area(
            **chart_args,
            title=f"<b>Product Consumption Trend with Volume Distribution ({report_type})</b>"
        )

    fig.update_traces(
        hovertemplate=(
            "<b>%{fullData.name}</b><br>" +
            "Volume: %{y:.1f} L<br>" +
            "Percentage Change: %{customdata[0]:+.1f}%" +
            "<extra></extra>"
        ),
        marker=dict(size=6)
    )

    # Set all text to Black
    fig.update_layout(
        height = 500,
        margin=dict(l=20, r=20, t=60, b=20),
        hovermode="x unified",
        hoverlabel=dict(bgcolor="white", font_color="black"),
        title_font=dict(color="black", size=20),
        xaxis=dict(
            tickfont=dict(color="black"),
            title_font=dict(color="black")
        ),
        yaxis=dict(
            title="Volume (Litres)",
            tickfont=dict(color="black"),
            title_font=dict(color="black")
        ),
        legend=dict(
            title_font=dict(color="black"),
            font=dict(color="black")
        )
    )

    # Axis Refinement
    if report_type == "Daily":
        fig.update_xaxes(type='linear', tickmode='linear', dtick=2, range=[0, 23])
    else:
        fig.update_xaxes(type='date')

    st.plotly_chart(fig, use_container_width=True)

def get_top_n_others(df, dimension, n=10):
    # 1. Group and sum the volume for the specific dimension
    df_counts = df.groupby(dimension)['Volume'].sum().reset_index()
    
    # 2. Sort by Volume descending
    df_counts = df_counts.sort_values('Volume', ascending=False)
    
    if len(df_counts) <= n:
        return df_counts
    
    # 3. Split into Top N and the rest
    top_n = df_counts.head(n).copy()
    others_vol = df_counts.iloc[n:]['Volume'].sum()
    
    # 4. Create the 'Others' row
    others_row = pd.DataFrame({
        dimension: ['Others'], 
        'Volume': [others_vol]
    })
    
    # 5. Combine and return
    return pd.concat([top_n, others_row], ignore_index=True)

def top_10_eqipment_categories(df_filtered):
    st.markdown("<h3 style='text-align: center; color: black;'>Top 10 Equipment Categories</h3>", unsafe_allow_html=True)
    df_cat_plot = get_top_n_others(df_filtered, 'Equipment_Category_Name', 10)
    
    fig_cat = px.pie(
        df_cat_plot, 
        values='Volume', 
        names='Equipment_Category_Name',
        hole=0.4,
        color_discrete_sequence=px.colors.qualitative.Pastel
    )

    fig_cat.update_traces(
        textposition='inside',
        insidetextfont=dict(color='black'),
        outsidetextfont=dict(color='black'),
        texttemplate='<b>%{label}</b><br>%{percent:.1%}<br>%{value:,.0f} L',
        hovertemplate="<b>%{label}</b><br>Volume: %{value:,.1f} L<br>Percentage: %{percent:.1%}<extra></extra>"
    )
    
    fig_cat.update_layout(
        showlegend=True,
        margin=dict(l=20, r=20, t=60, b=20),
        hoverlabel=dict(
            bgcolor="white",
            font_size=13,
            font_color="black",
            bordercolor="black"
        ),
        legend=dict(font=dict(color="black"))
    )
    st.plotly_chart(fig_cat, use_container_width=True)

def top_5_equipment_groups(df_filtered):
    st.markdown("<h3 style='text-align: center; color: black;'>Top 5 Equipment Groups</h3>", unsafe_allow_html=True)
    df_grp_plot = get_top_n_others(df_filtered, 'Equipment_Group_Name', 5)
    
    fig_grp = px.pie(
        df_grp_plot, 
        values='Volume', 
        names='Equipment_Group_Name',
        hole=0.4,
        color_discrete_sequence=px.colors.qualitative.Safe
    )

    fig_grp.update_traces(
        textposition='inside',
        insidetextfont=dict(color='black'),
        texttemplate='<b>%{label}</b><br>%{percent:.1%}<br>%{value:,.0f} L',
        hovertemplate="<b>%{label}</b><br>Volume: %{value:,.1f} L<br>Percentage: %{percent:.1%}<extra></extra>"
    )
    
    fig_grp.update_layout(
        showlegend=True,
        margin=dict(l=20, r=20, t=60, b=20),
        hoverlabel=dict(
            bgcolor="white",
            font_size=13,
            font_color="black",
            bordercolor="black"
        ),
        legend=dict(font=dict(color="black"))
    )
    st.plotly_chart(fig_grp, use_container_width=True)

def top_50_equipment_items(df_filtered):
    st.markdown("---")
    st.subheader("Top 50 Individual Equipment Assets")

    grand_total_volume = df_filtered['Volume'].sum()

    df_top_50 = (
        df_filtered.groupby(['Equipment ID', 'Equip_Desc', 'Equipment_Category_Name', 'Equipment_Group_Name'])['Volume']
        .sum()
        .nlargest(50)
        .reset_index()
    )
    
    df_top_50['Vol_Disp'] = df_top_50['Volume'].map('{:,.1f}'.format)
    df_top_50['Pct_Disp'] = ((df_top_50['Volume'] / grand_total_volume) * 100).map('{:,.1f}%'.format)

    styled_df = (
    df_top_50.style
        .set_table_styles([
            {
                "selector": "th",
                "props": [
                    ("color", "black"),
                    ("font-weight", "bold")
                ]
            }
        ])
    )
    st.dataframe(
        styled_df,
        column_config={
            "Vol_Disp": st.column_config.TextColumn("Total Volume (L)", help="Total fuel dispensed"),
            "Pct_Disp": st.column_config.TextColumn("% of Total Dispensed Volume"),
            "Equip_Desc": "Equipment Item",
            "Equipment_Category_Name": "Equipment Category",
            "Equipment_Group_Name": "Equipment Group",
            "Volume": None,
            "Equipment ID": "Equipment ID" 
        },
        use_container_width=True,
        hide_index=True
    )

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
        


# --- MAIN DASHBOARD ---
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
    
    q1_visualizations(df_filtered, report_type)
    q2_visualizations(df_filtered)


if __name__ == "__main__":
    main()

    
