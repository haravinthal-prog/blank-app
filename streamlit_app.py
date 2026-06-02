import streamlit as st
import pandas as pd
import altair as alt

# 1. Page Configuration
st.set_page_config(
    page_title="E-Commerce Sales Dashboard",
    page_icon="🛒",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 2. Measurement Registry (Data Dictionary)
# This serves as the central source of truth for column metrics and units.
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

# 3. Title & Description
st.title("🛒 Online Retail Sales Dashboard")
st.markdown("An interactive dashboard built with Streamlit and Altair featuring an explicit **Column Measurement Registry**.")

# Display the Column Measurement Registry inside an expandable panel
with st.expander("📋 View Column Measurement Registry & Data Dictionary", expanded=False):
    registry_df = pd.DataFrame.from_dict(MEASUREMENT_REGISTRY, orient='index')
    st.dataframe(registry_df, use_container_width=True)

# 4. Cached Data Loading
@st.cache_data
def load_data():
    df = pd.read_csv('data.csv', encoding='ISO-8859-1')
    
    # Preprocessing & calculations based on registry definitions
    df['InvoiceDate'] = pd.to_datetime(df['InvoiceDate'])
    df['TotalSales'] = df['Quantity'] * df['UnitPrice']
    df['Description'] = df['Description'].fillna('Unknown Product').str.strip()
    
    return df

# Initialize data
df = load_data()

# 5. Sidebar Filter Section
st.sidebar.header("🔍 Filter Options")

# Date Range Filter
min_date = df['InvoiceDate'].min().date()
max_date = df['InvoiceDate'].max().date()

start_date, end_date = st.sidebar.date_input(
    "Select Date Range",
    value=[min_date, max_date],
    min_value=min_date,
    max_value=max_date
)

# Country Filter
countries = ['All'] + sorted(df['Country'].unique().tolist())
selected_country = st.sidebar.selectbox("Select Country", countries)

# Apply Sidebar Filters to Data
filtered_df = df[(df['InvoiceDate'].dt.date >= start_date) & (df['InvoiceDate'].dt.date <= end_date)].copy()

if selected_country != 'All':
    filtered_df = filtered_df[filtered_df['Country'] == selected_country]


# 6. Key Performance Indicators (KPIs) with Registry Units
st.subheader("📊 Key Metrics Summary")
col1, col2, col3, col4 = st.columns(4)

total_revenue = filtered_df['TotalSales'].sum()
total_orders = filtered_df['InvoiceNo'].nunique()
total_customers = filtered_df['CustomerID'].dropna().nunique()
avg_order_value = total_revenue / total_orders if total_orders > 0 else 0

# Metrics explicitly stating unit descriptions from registry
col1.metric("Total Revenue", f"${total_revenue:,.2f}", help=MEASUREMENT_REGISTRY['TotalSales']['Unit of Measurement'])
col2.metric("Total Orders", f"{total_orders:,}", help=MEASUREMENT_REGISTRY['InvoiceNo']['Unit of Measurement'])
col3.metric("Unique Customers", f"{total_customers:,}", help=MEASUREMENT_REGISTRY['CustomerID']['Unit of Measurement'])
col4.metric("Avg Order Value", f"${avg_order_value:,.2f}", help="Average value ($) per single order code")

st.markdown("---")


# 7. Interactive Visualizations (Altair Charts)
st.subheader("📈 Sales Trends & Product Insights")

# Row 1: Monthly Trend and Top Products
row1_col1, row1_col2 = st.columns(2)

with row1_col1:
    st.markdown(f"### Monthly Revenue Trend ({MEASUREMENT_REGISTRY['TotalSales']['Unit of Measurement']})")
    monthly_sales = filtered_df.set_index('InvoiceDate').resample('ME')['TotalSales'].sum().reset_index()
    
    chart_trend = alt.Chart(monthly_sales).mark_line(point=True).encode(
        x=alt.X('InvoiceDate:T', title=f"Month ({MEASUREMENT_REGISTRY['InvoiceDate']['Unit of Measurement']})", axis=alt.Axis(format='%b %Y')),
        y=alt.Y('TotalSales:Q', title=f"Revenue ({MEASUREMENT_REGISTRY['TotalSales']['Unit of Measurement']})"),
        tooltip=[alt.Tooltip('InvoiceDate:T', title='Month', format='%b %Y'), 
                 alt.Tooltip('TotalSales:Q', title='Revenue', format=',.2f')]
    ).interactive()
    
    st.altair_chart(chart_trend, use_container_width=True)

with row1_col2:
    st.markdown(f"### Top 10 Best Selling Products ({MEASUREMENT_REGISTRY['TotalSales']['Unit of Measurement']})")
    top_products = filtered_df.groupby('Description')['TotalSales'].sum().reset_index()
    top_products = top_products.sort_values(by='TotalSales', ascending=False).head(10)
    
    chart_products = alt.Chart(top_products).mark_bar().encode(
        x=alt.X('TotalSales:Q', title=f"Revenue ({MEASUREMENT_REGISTRY['TotalSales']['Unit of Measurement']})"),
        y=alt.Y('Description:N', sort='-x', title='Product Description'),
        color=alt.Color('TotalSales:Q', scale=alt.Scale(scheme='viridis'), legend=None),
        tooltip=[alt.Tooltip('Description:N', title='Product'), 
                 alt.Tooltip('TotalSales:Q', title='Revenue', format=',.2f')]
    )
    
    st.altair_chart(chart_products, use_container_width=True)


# Row 2: Regional Distribution and Hourly Patterns
row2_col1, row2_col2 = st.columns(2)

with row2_col1:
    st.markdown(f"### Top 10 Countries by Revenue ({MEASUREMENT_REGISTRY['TotalSales']['Unit of Measurement']})")
    country_sales = filtered_df.groupby('Country')['TotalSales'].sum().reset_index()
    country_sales = country_sales.sort_values(by='TotalSales', ascending=False).head(10)
    
    chart_country = alt.Chart(country_sales).mark_bar().encode(
        x=alt.X('Country:N', sort='-y', title=f"Country ({MEASUREMENT_REGISTRY['Country']['Unit of Measurement']})"),
        y=alt.Y('TotalSales:Q', title=f"Revenue ({MEASUREMENT_REGISTRY['TotalSales']['Unit of Measurement']})"),
        color=alt.Color('TotalSales:Q', scale=alt.Scale(scheme='blues'), legend=None),
        tooltip=[alt.Tooltip('Country:N'), 
                 alt.Tooltip('TotalSales:Q', title='Revenue', format=',.2f')]
    )
    
    st.altair_chart(chart_country, use_container_width=True)

with row2_col2:
    st.markdown(f"### Hourly Sales Activity")
    filtered_df['Hour'] = filtered_df['InvoiceDate'].dt.hour
    hourly_sales = filtered_df.groupby('Hour')['TotalSales'].sum().reset_index()
    
    chart_hour = alt.Chart(hourly_sales).mark_line(point=True, color='#FF4B4B').encode(
        x=alt.X('Hour:O', title='Hour of Day (24 Hour Format)'),
        y=alt.Y('TotalSales:Q', title=f"Revenue ({MEASUREMENT_REGISTRY['TotalSales']['Unit of Measurement']})"),
        tooltip=[alt.Tooltip('Hour:O', title='Hour'), 
                 alt.Tooltip('TotalSales:Q', title='Revenue', format=',.2f')]
    ).interactive()
    
    st.altair_chart(chart_hour, use_container_width=True)


# 8. Raw Data Explorer
st.markdown("---")
st.subheader("📋 Raw Data Explorer")
show_data = st.checkbox("Show Raw Sample Data")
if show_data:
    st.dataframe(filtered_df.head(100), use_container_width=True)
