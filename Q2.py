import streamlit as st
import pandas as pd
import plotly.express as px

def get_top_n_others(df, dimension, n=10):
    """
    Groups data by a specified dimension and aggregates the total volume.
    To maintain visual clarity in charts, it isolates the 'Top N' contributors 
    and consolidates all remaining records into a single 'Others' category.
    """
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
    """
    Renders a donut chart representing the Top 10 Equipment Categories by consumption.
    Features a centralized 'Total Volume' KPI with black text and dynamic 
    labels showing the category name, percentage share, and total litres.
    """
    st.markdown("<h3 style='text-align: center; color: black;'>Top 10 Equipment Categories</h3>", unsafe_allow_html=True)
    df_cat_plot = get_top_n_others(df_filtered, 'Equipment_Category_Name', 10)
    total_vol = df_filtered['Volume'].sum()
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
        annotations=[{
            "text": f"Total<br><b>{total_vol:,.0f} L</b>",
            "x": 0.5, 
            "y": 0.5,
            "font": {
                "size": 22,
                "color": "black"
            },
            "showarrow": False,
            "xanchor": "center",
            "yanchor": "middle"
        }],
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
    """
    Visualizes the Top 5 Equipment Groups using a donut chart.
    Provides a high-level summary of major organizational groups while 
    using a 'Safe' color palette and center-aligned volume annotations 
    for quick stakeholder assessment.
    """
    st.markdown("<h3 style='text-align: center; color: black;'>Top 5 Equipment Groups</h3>", unsafe_allow_html=True)
    df_grp_plot = get_top_n_others(df_filtered, 'Equipment_Group_Name', 5)
    total_vol = df_filtered['Volume'].sum()

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
        annotations=[{
            "text": f"Total<br><b>{total_vol:,.0f} L</b>",
            "x": 0.5, 
            "y": 0.5,
            "font": {
                "size": 22,
                "color": "black"
            },
            "showarrow": False,
            "xanchor": "center",
            "yanchor": "middle"
        }],
        showlegend=True,
        margin=dict(l=150, r=20, t=60, b=20),
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
    """
    Displays a detailed breakdown of the top 50 individual equipment assets.
    Includes a conditional styling 'heat' layer that highlights high-consumption 
    assets (those exceeding 5% of total dispensed volume) in red, facilitating 
    rapid identification of outliers.
    """
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
    df_top_50['raw_pct'] = (df_top_50['Volume'] / grand_total_volume) * 100
    df_top_50['Pct_Disp'] = df_top_50['raw_pct'].map('{:,.1f}%'.format)

    # A function to apply the background color conditionally
    def highlight_high_consumers(row):
        # If the percentage is greater than 5, apply the color to the whole row
        if row['raw_pct'] > 5:
            return ['background-color: #ffcccc'] * len(row)
        return [''] * len(row)

    styled_df = (
        df_top_50.style
        .set_table_styles([
            {
                "selector": "th",
                "props": [("color", "black"), ("font-weight", "bold")]
            }
        ])
        .apply(highlight_high_consumers, axis=1)
    )

    # Display the dataframe
    st.dataframe(
        styled_df,
        column_config={
            "Vol_Disp": st.column_config.TextColumn("Total Volume (L)"),
            "Pct_Disp": st.column_config.TextColumn("% of Total Dispensed Volume"),
            "Equip_Desc": "Equipment Item",
            "Equipment_Category_Name": "Equipment Category",
            "Equipment_Group_Name": "Equipment Group",
            "Equipment ID": "Equipment ID",
            "Volume": None,
            "raw_pct": None
        },
        use_container_width=True,
        hide_index=True
    )