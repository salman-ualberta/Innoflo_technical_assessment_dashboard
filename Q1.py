import streamlit as st
import pandas as pd
from utility import PRODUCT_COLORS, PRODUCT_LABEL_COLORS
import plotly.express as px

def top_card(df_filtered):
    """
    Renders the high-level KPI metrics at the top of the dashboard.
    Calculates and displays Total Dispensed Volume, the Top Consumed Product, 
    and the Average Daily Consumption based on the active days in the filtered dataset.
    """

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
    """
    Generates a horizontal bar chart visualizing the total volume per product type.
    Uses log-scale indexing to ensure low-volume products (oils/grease) remain 
    visible alongside high-volume products (Diesel). Includes dynamic data label 
    coloring for enhanced readability.
    """

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
    """
    Creates a time-series visualization showing consumption trends over time.
    Dynamically switches the X-axis between hourly (Daily view) and date-based (Monthly/Weekly).
    Provides users with a toggle to switch between a Line chart (Product Trends) 
    and an Area chart (Volume Distribution) while calculating percentage deltas between periods.
    """
    
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
            title=f"<b>Product Consumption Trend</b>"
        )
    else:
        fig = px.area(
            **chart_args,
            title=f"<b>Product Consumption Trend with Volume Distribution</b>"
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