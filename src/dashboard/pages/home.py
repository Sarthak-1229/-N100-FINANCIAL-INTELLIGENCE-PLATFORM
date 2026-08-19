import streamlit as st
import pandas as pd
from src.dashboard.utils.db import get_companies, get_ratios, get_sectors

def show():
    st.title("Nifty 100 Analytics - Home")
    st.write("Welcome to the Nifty 100 Analytics Dashboard")

    # Get data
    companies_df = get_companies()
    sectors_df = get_sectors()

    # Show summary KPI tiles
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    with col1:
        st.metric("Total Companies", len(companies_df))
    with col2:
        # Average ROE
        st.metric("Average ROE", "N/A")
    with col3:
        st.metric("Median P/E", "N/A")
    with col4:
        st.metric("Median D/E", "N/A")
    with col5:
        st.metric("Median Revenue CAGR 5yr", "N/A")
    with col6:
        st.metric("Debt-Free Companies", "N/A")

    # Sector breakdown donut chart
    st.subheader("Sector Breakdown")
    if not sectors_df.empty:
        sector_counts = sectors_df['broad_sector'].value_counts()
        st.bar_chart(sector_counts)
    else:
        st.write("No sector data available")

    # Top-5 companies by composite quality score
    st.subheader("Top-5 Companies by Composite Score")
    st.write("Top-5 companies by composite score will be shown here")

    # Year selector in sidebar
    st.sidebar.subheader("Year Selector")
    year = st.sidebar.selectbox("Select Year", ["2024-03", "2023-03", "2022-03", "2021-03", "2020-03"])
    st.write(f"Selected year: {year}")