import streamlit as st
import pandas as pd
import altair as alt

# ==============================================================================
# 1. PAGE CONFIGURATION
# ==============================================================================
st.set_page_config(
    page_title="E-Commerce Performance & Quality Dashboard",
    page_icon="🛒",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==============================================================================
# 2. MEASUREMENT REGISTRY & DATA DICTIONARY
# ==============================================================================
MEASUREMENT_REGISTRY = {
    'InvoiceNo': {
        'Data Type': 'Categorical / ID',
        'Unit of Measurement': 'Alpha-numeric Code',
        'Description': 'A unique 6-digit identifier assigned to each transaction.'
    },
    'StockCode': {
        'Data Type': 'Categorical / ID',
        'Unit of Measurement': 'Alpha-numeric Code',
        'Description': 'A unique code assigned to each distinct product.'
    },
    'Description': {
        'Data Type': 'Text / Nominal',
        'Unit of Measurement': 'String Label',
        'Description': 'The commercial name/description of the product.'
    },
    'Quantity': {
        'Data Type': 'Quantitative / Integer',
        'Unit of Measurement': 'Pieces / Units sold',
        'Description': 'The number of units purchased per transaction row.'
    },
    'InvoiceDate': {
        'Data Type': 'Temporal / Datetime',
        'Unit of Measurement': 'YYYY-MM-DD HH:MM',
        'Description': 'The exact timestamp when the transaction was generated.'
    },
    'UnitPrice': {
        'Data Type': 'Quantitative / Continuous',
        'Unit of Measurement': 'Currency ($)',
        'Description': 'The price per single item unit.'
    },
    'CustomerID': {
        'Data Type': 'Categorical / ID',
        'Unit of Measurement': '5-digit Numeric ID',
        'Description': 'A unique identifier assigned to each registered customer.'
    },
    'Country': {
        'Data Type': 'Categorical / Nominal',
        'Unit of Measurement': 'Geographic Region',
        'Description': 'The nation where the purchasing customer is located.'
    },
    'TotalSales': {
        'Data Type': 'Quantitative / Continuous',
        'Unit of Measurement': 'Currency ($)',
        'Description': 'Calculated transaction value, derived via: Quantity × UnitPrice.'
    }
}

# ==============================================================================
# 3. CACHED DATA LOADING (COMPRESSED DATA READER)
# ==============================================================================
@st.cache_data
def load_data():
    # Pandas automatically handles the decompression of the gzip file
    df = pd.read_csv('compressed_data.csv.gz', encoding='ISO-8859-1', compression='gzip')
    
    # Standard cleanups & conversions based on Registry specifications
    df['InvoiceDate'] = pd.to_datetime(df['InvoiceDate'])
    df['TotalSales'] = df['Quantity'] * df['UnitPrice']
    df['Description'] = df['Description'].fillna('Unknown Product').str.strip()
    
    # --------------------------------------------------------------------------
    # TIMELINESS SIMULATION LOGIC
    # --------------------------------------------------------------------------
    # Since the raw online retail dataset logs only order timestamps, we create 
    # a target operational benchmark ("Expected Dispatch SLA") to evaluate Timeliness.
    # Rule: Orders placed before 12:00 PM should be dispatched within 4 hours. 
    # Orders placed after 12:00 PM should be dispatched within 16 hours.
    
    df['Expected_Dispatch_Date'] = df['InvoiceDate'] + pd.to_timedelta(
        df['InvoiceDate'].dt.hour.apply(lambda h: 4 if h < 12 else 16), unit='h'
    )
    
    # Simulate an actual physical dispatch timestamp (adding controlled random processing delays)
    # Most will be on time, some will exceed the SLA deadline
    import numpy as np
    np.random.seed(42) # Ensuring deterministic behavior across refreshes
    random_delays = np.random.exponential(scale=3, size=len(df)) # delay in hours
    df['Actual_Dispatch_Date'] = df['InvoiceDate'] + pd.to_timedelta(random_delays, unit='h')
    
    return df

# Initialize data
df = load_data()

# ==============================================================================
# 4. SIDEBAR FILTER OPTIONS
# ==============================================================================
st.sidebar.header("🔍 Global Dashboard Filters")

# Date Range Slider Filter
min_date = df['InvoiceDate'].min().date()
max_date = df['InvoiceDate'].max().date()

start_date, end_date = st.sidebar.date_input(
    "Select Date Range",
    value=[min_date, max_date],
    min_value=min_date,
    max_value=max_date
)

# Geographic Country Filter
countries = ['All'] + sorted(df['Country'].unique().tolist())
selected_country = st.sidebar.selectbox("Select Country Destination", countries)

# Apply Active Filtering Conditions to the Working Frame
filtered_df = df[(df['InvoiceDate'].dt.date >= start_date) & (df['InvoiceDate'].dt.date <= end_date)].copy()

if selected_country != 'All':
    filtered_df = filtered_df[filtered_df['Country'] == selected_country]

# ==============================================================================
# 5. DASHBOARD HEADER & REGISTRY EXPANDER
# ==============================================================================
st.title("🛒 E-Commerce Performance & Data Quality Dashboard")
st.markdown("A unified view monitoring core financial transactions, operational throughput, and system data timeliness.")

with st.expander("📋 View Data Registry & Technical Attributes Dictionary", expanded=False):
    registry_df = pd.DataFrame.from_dict(MEASUREMENT_REGISTRY, orient='index')
    st.dataframe(registry_df, use_container_width=True)

st.markdown("---")

# ==============================================================================
# 6. DATA QUALITY SCORECARD VIEW (TIMELINESS DIMENSION)
# ==============================================================================
st.subheader("🎯 Data Quality Scorecard View")

# Calculation for Timeliness Metric
# Timeliness Score % = (Orders dispatched on or before Expected SLA Date / Total Orders) * 100
on_time_dispatches = (filtered_df['Actual_Dispatch_Date'] <= filtered_df['Expected_Dispatch_Date']).sum()
total_dispatches = len(filtered_df)

timeliness_percentage = (on_time_dispatches / total_dispatches) * 100 if total_dispatches > 0 else 0.0
target_benchmark = 85.0 # Predefined operational KPI target
timeliness_delta = timeliness_percentage - target_benchmark

# UI Scorecard Layout Setup
card_col1, card_col2, card_col3 = st.columns([1.5, 2, 1.5])

with card_col1:
    st.metric(
        label="Data Dimension: Timeliness",
        value=f"{timeliness_percentage:.2f}%",
        delta=f"{timeliness_delta:+.2f}% vs Target ({target_benchmark}%)",
        delta_color="normal",
        help="Evaluates operational dispatch execution window against system SLA limits."
    )

with card_col2:
    st.markdown("<p style='margin-bottom:0px; font-weight:bold;'>SLA Target Progress</p>", unsafe_allow_html=True)
    st.progress(min(max(timeliness_percentage / 100, 0.0), 1.0))

with card_col3:
    status_label = "🟢 Healthy (Above SLA Target)" if timeliness_percentage >= target_benchmark else "🔴 Warning (Below SLA Target)"
    st.markdown("<p style='margin-bottom:0px; font-weight:bold;'>Dimension Status</p>", unsafe_allow_html=True)
    st.subheader(status_label)

st.markdown("---")

# ==============================================================================
# 7. FINANCIAL PERFORMANCE METRICS (KPIs)
# ==============================================================================
st.subheader("📊 Transaction Performance KPIs")
kpi_col1, kpi_col2, kpi_col3, kpi_col4 = st.columns(4)

total_revenue = filtered_df['TotalSales'].sum()
total_orders = filtered_df['InvoiceNo'].nunique()
total_customers = filtered_df['CustomerID'].dropna().nunique()
avg_order_value = total_revenue / total_orders if total_orders > 0 else 0

kpi_col1.metric("Total Revenue", f"${total_revenue:,.2f}", help=MEASUREMENT_REGISTRY['TotalSales']['Unit of Measurement'])
kpi_col2.metric("Total Orders Orders", f"{total_orders:,}", help=MEASUREMENT_REGISTRY['InvoiceNo']['Unit of Measurement'])
kpi_col3.metric("Unique Customers", f"{total_customers:,}", help=MEASUREMENT_REGISTRY['CustomerID']['Unit of Measurement'])
kpi_col4.metric("Avg Order Value", f"${avg_order_value:,.2f}", help="Average gross value generated per unique order number")

st.markdown("---")

# ==============================================================================
# 8. ANALYTICAL VISUALIZATIONS (ALTAIR CHARTS)
# ==============================================================================
st.subheader("📈 Operational Intelligence Trends")

row1_col1, row1_col2 = st.columns(2)

with row1_col1:
    st.markdown(f"### Monthly Revenue Trend ({MEASUREMENT_REGISTRY['TotalSales']['Unit of Measurement']})")
    monthly_sales = filtered_df.set_index('InvoiceDate').resample('ME')['TotalSales'].sum().reset_index()
    
    chart_trend = alt.Chart(monthly_sales).mark_line(point=True).encode(
        x=alt.X('InvoiceDate:T', title=f"Timeline ({MEASUREMENT_REGISTRY['InvoiceDate']['Unit of Measurement']})", axis=alt.Axis(format='%b %Y')),
        y=alt.Y('TotalSales:Q', title="Gross Sales Revenue ($)"),
        tooltip=[alt.Tooltip('InvoiceDate:T', title='Reporting Month', format='%b %Y'), 
                 alt.Tooltip('TotalSales:Q', title='Gross Revenue', format=',.2f')]
    ).interactive()
    st.altair_chart(chart_trend, use_container_width=True)

with row1_col2:
    st.markdown("### Top 10 Best Selling Inventory Items")
    top_products = filtered_df.groupby('Description')['TotalSales'].sum().reset_index()
    top_products = top_products.sort_values(by='TotalSales', ascending=False).head(10)
    
    chart_products = alt.Chart(top_products).mark_bar().encode(
        x=alt.X('TotalSales:Q', title="Aggregated Value ($)"),
        y=alt.Y('Description:N', sort='-x', title=MEASUREMENT_REGISTRY['Description']['Description']),
        color=alt.Color('TotalSales:Q', scale=alt.Scale(scheme='viridis'), legend=None),
        tooltip=[alt.Tooltip('Description:N', title='Inventory Item'), 
                 alt.Tooltip('TotalSales:Q', title='Calculated Revenue', format=',.2f')]
    )
    st.altair_chart(chart_products, use_container_width=True)

row2_col1, row2_col2 = st.columns(2)

with row2_col1:
    st.markdown("### Top 10 Marketplace Demographics")
    country_sales = filtered_df.groupby('Country')['TotalSales'].sum().reset_index()
    country_sales = country_sales.sort_values(by='TotalSales', ascending=False).head(10)
    
    chart_country = alt.Chart(country_sales).mark_bar().encode(
        x=alt.X('Country:N', sort='-y', title=f"Target Market ({MEASUREMENT_REGISTRY['Country']['Unit of Measurement']})"),
        y=alt.Y('TotalSales:Q', title="Total Outflow Generated ($)"),
        color=alt.Color('TotalSales:Q', scale=alt.Scale(scheme='blues'), legend=None),
        tooltip=[alt.Tooltip('Country:N', title='Nation Flag'), 
                 alt.Tooltip('TotalSales:Q', title='Combined Revenue', format=',.2f')]
    )
    st.altair_chart(chart_country, use_container_width=True)

with row2_col2:
    st.markdown("### Transaction Placement Hourly Activity Profiles")
    filtered_df['Hour'] = filtered_df['InvoiceDate'].dt.hour
    hourly_sales = filtered_df.groupby('Hour')['TotalSales'].sum().reset_index()
    
    chart_hour = alt.Chart(hourly_sales).mark_line(point=True, color='#FF4B4B').encode(
        x=alt.X('Hour:O', title="System Time Matrix (24-Hour Base Clock)"),
        y=alt.Y('TotalSales:Q', title="Processed Throughput Revenue ($)"),
        tooltip=[alt.Tooltip('Hour:O', title='Active Hour Window'), 
                 alt.Tooltip('TotalSales:Q', title='Volume Revenue', format=',.2f')]
    ).interactive()
    st.altair_chart(chart_hour, use_container_width=True)

# ==============================================================================
# 9. TRANS-DATA RAW STORAGE BROWSER
# ==============================================================================
st.markdown("---")
st.subheader("📋 Audit Data Explorer Ledger")
if st.checkbox("Decrypt and Reveal Local Registry Rows"):
    st.dataframe(filtered_df.head(100), use_container_width=True)
