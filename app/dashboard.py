import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from google.cloud import storage
from io import StringIO



@st.cache_data
def load_data():
    """Load and merge data from Google Cloud Storage"""
    try:
        client = storage.Client()
        bucket = client.bucket("demo_ikra")
        
        # Load customer interaction data
        cust_data = pd.read_csv(StringIO(
            bucket.blob('Dataset/Customer_Interaction_Data_v3.csv')
            .download_as_text()
        ))
        
        # Load product catalog data
        prod_data = pd.read_csv(StringIO(
            bucket.blob('Dataset/final_product_catalog_v2.csv')
            .download_as_text()
        ))
        
        # Merge and preprocess data
        merged_df = pd.merge(cust_data, prod_data, on="Product_ID")
        if 'Purchase_Date' in merged_df.columns:
            merged_df['Purchase_Date'] = pd.to_datetime(merged_df['Purchase_Date'])
        else:
            raise ValueError("Column 'Purchase_Date' not found in merged dataframes.")
            
        return merged_df
    except Exception as e:
        st.warning(f"Error loading data: {str(e)}")
        return pd.DataFrame()

def calculate_metrics(data):
    """Calculate all business metrics from filtered data"""
    metrics = {
        # Core metrics
        'Conversion Rate': (data['Order_Value'] > 0).sum() / len(data),
        'Total Sales': data['Order_Value'].sum(),
        'Retention Rate': (data['Repeat_Purchase_Score'] > 0.5).sum() / data['Customer_ID'].nunique(),
        'CTR' : (data['Engagement_Score'] > 0.5).sum() / len(data),
        'CSAT Score': -data[['Return_Rate', 'Purchase_Probability_Score']].corr().iloc[0, 1],
        
        # Engagement metrics
        'User Engagement': data.groupby(['Age', 'Gender'])['Time_Spent_Per_Product'].mean().reset_index(),
        
        # Churn metrics
        'Churn Rate': data.groupby('Income_Bracket').apply(
            lambda x: ((x['Engagement_Score'] < 0.3) & (x['Repeat_Purchase_Score'] == 0))
            .sum() / x['Customer_ID'].nunique()),
        
        # Product metrics
        'Top Products': data.groupby('Product_ID').agg({
            'Category': 'first',  # Get the first category for each Product_ID
            'Order_Value': 'sum',
            'Rating': 'mean'
        }).reset_index()
        .query('Rating > 4.5')  # Filter for ratings greater than 4.5
        .sort_values('Order_Value', ascending=False)
        [['Category', 'Order_Value', 'Rating']].head(10),
        
        # Location metrics
        'Location Sales': data.groupby('Location')['Order_Value'].mean()
        .sort_values(ascending=False).reset_index(),
        
        # AOV metrics
        'AOV over time': data.groupby(data['Purchase_Date'].dt.to_period('Q'))['Order_Value'].mean().reset_index()
    }

    # Format 'Purchase_Date' as strings for JSON serialization
    metrics['AOV over time']['Purchase_Date'] = metrics['AOV over time']['Purchase_Date'].astype(str)

    return metrics

# Cache the filtered year data to improve performance
@st.cache_data
def get_year_data(data, year):
    return data[data['Purchase_Date'].dt.year == year]

def setup_filters(data):
    """Setup year filtering components in the sidebar."""
    min_year = data['Purchase_Date'].dt.year.min()
    max_year = data['Purchase_Date'].dt.year.max()
    years = list(range(int(min_year), int(max_year) + 1))
    
    selected_year = st.sidebar.selectbox(
        'Select Year',
        options=years,
        index=len(years) - 1  # Default to most recent year
    )
    
    show_all = st.sidebar.checkbox("Show All Years")
    
    if show_all:
        return data.copy()
    else:
        return get_year_data(data, selected_year)

def dashboard_function():
    # Data loading and filtering
    data = load_data()
    filtered_data = setup_filters(data)
    metrics = calculate_metrics(filtered_data)

    # Dashboard layout
    # st.title("E-Commerce Performance Dashboard")
    
    # Metrics Row 1 (core metrics)
    col1, col2 = st.columns((2,4), border=True)

    with col1:
        with col1:
            st.metric("Total Sales", f"${metrics['Total Sales']:,.0f}")


        col_1a, col_1b = st.columns((1.5,1.5), border=True)
        with col_1a:
            st.metric("Conversion Rate", f"{metrics['Conversion Rate']:.0%}")
        with col_1b:
            st.metric("CTR", f"{metrics['CTR']:,.2%}")

        col_1c, col_1d = st.columns((1.5,1.5), border=True)
        with col_1c:
            st.metric("CSAT", f"{metrics['CSAT Score']:,.2%}")
        with col_1d:
            st.metric("Retention Rate", f"{metrics['Retention Rate']:,.2%}")

    # Sales by location metrics
    with col2:
        fig = go.Figure(data=[go.Bar(
        x=metrics['Location Sales']['Location'],
        y=metrics['Location Sales']['Order_Value'],
        width=0.4,  # bar width
        marker=dict(line=dict(color='#000000', width=1)),
        textfont=dict(size=13, color='black', family="Arial, sans-serif"),
        marker_color=["#1E4DB4", "#3F8EF3", "#89C4FF", "#899CFF", "#313E99"]
        )])

        fig.update_layout(
        title_text="Average Order Value by Location",
        template="plotly_dark",
        height= 300,
        xaxis_title = "Location",
        yaxis_title = "Order Value"
        )
        st.plotly_chart(fig, use_container_width=True)
        

    # Metrics Row 2 (top product and AOV over time)
    col3, col4 = st.columns((2,4), border=True)

    # Top Products Table
    with col3:
        st.subheader("Top Performing Products")
        st.dataframe(metrics['Top Products'].style.format({
            'Order_Value': '${:,.2f}',
            'Rating': '{:.2f}'
        }), use_container_width=True,
        hide_index=True,
        column_config={
                        "Category": st.column_config.TextColumn(
                            "Category",
                        ),
                        "Order_Value": st.column_config.TextColumn(
                            "Order Value",
                        ),
                        "Rating": st.column_config.ProgressColumn(
                             "Rating",
                            format="%f",
                            min_value=0,
                            max_value=max(metrics['Top Products'].Rating),
                         )}
                     )
    
    # sum or avg order value over time
    with col4:
        fig = px.line(metrics['AOV over time'],
                      x='Purchase_Date',
                      y='Order_Value',
                      title='Average Order Value Quarterly',
                      markers=True,
                      color_discrete_sequence=["#899CFF"])
        
        fig.update_xaxes(
        tickvals=metrics['AOV over time']['Purchase_Date'],
        tickformat='%Y-Q%q',  # Displays as "2020-Q1", etc.
        tickangle=-45,
        title='Quarter')

        fig.update_yaxes(title='Average Order Value')

        st.plotly_chart(fig, use_container_width=True)


    # Metrics Row 3 (Return rate by demographics & Churn Rate Overtime)
    col5, col6 = st.columns((2, 4), border=True)

    # churn Rate by income bracket
    with col5:
        fig = go.Figure(data=[go.Bar(
        x=metrics['Churn Rate'].index,  # X-axis labels (Income Bracket)
        y=metrics['Churn Rate'].values,  # Y-axis values (Churn Rate)
        marker=dict(line=dict(color='#000000', width=1)),  # Optional: Add border to bars
        width=0.4  # Set bar width to be slim
        )])

        # Update layout
        fig.update_layout(
        title_text="Churn Rate by Income Bracket",
        xaxis_title="Income Bracket",
        yaxis_title="Churn Rate",
        # paper_bgcolor= "#2E2E2E",
        template="plotly_dark",
        # height=300  # Set height if needed
        )
        st.plotly_chart(fig, use_container_width=True)
    
    # timespent by gender
    with col6:
        fig = px.line(metrics['User Engagement'], 
                     x='Age', y='Time_Spent_Per_Product',
                     color='Gender', markers=True,
                     title="Average Time Spent by Demographics",
                     color_discrete_sequence=["#1E4DB4", "#FF4B4C", "#3F8EF3"])
        st.plotly_chart(fig, use_container_width=True)