import streamlit as st
import pandas as pd
from src.dashboard.utils.db import get_companies, get_ratios, get_pl, get_bs, get_cf, get_sectors

def show():
    st.title("Company Profile")

    # Get list of companies for search
    companies_df = get_companies()
    company_options = companies_df['company_name'].tolist()
    company_ticker_map = dict(zip(companies_df['company_name'], companies_df['id']))
    ticker_company_map = dict(zip(companies_df['id'], companies_df['company_name']))

    # Search box
    search_term = st.text_input("Search by company name or ticker", "")
    selected_company_name = None
    selected_ticker = None

    if search_term:
        # Filter companies by name or ticker
        mask = companies_df['company_name'].str.contains(search_term, case=False, na=False) | \
               companies_df['id'].str.contains(search_term, case=False, na=False)
        filtered = companies_df[mask]
        if not filtered.empty:
            # If exactly one match, select it; otherwise, let user choose from dropdown
            if len(filtered) == 1:
                selected_company_name = filtered.iloc[0]['company_name']
                selected_ticker = filtered.iloc[0]['id']
            else:
                selected_company_name = st.selectbox(
                    "Select company",
                    filtered['company_name'].tolist(),
                    key="profile_search_select"
                )
                selected_ticker = company_ticker_map[selected_company_name]
        else:
            st.warning("No companies found matching your search.")
    else:
        # If no search term, show a dropdown of all companies
        selected_company_name = st.selectbox(
            "Select company",
            options=[""] + company_options,
            index=0,
            key="profile_company_select"
        )
        if selected_company_name:
            selected_ticker = company_ticker_map[selected_company_name]

    if selected_ticker:
        # Fetch data for the selected company
        ratios_df = get_ratios(selected_ticker)
        pl_df = get_pl(selected_ticker)
        bs_df = get_bs(selected_ticker)
        cf_df = get_cf(selected_ticker)

        if not ratios_df.empty:
            # Get the latest year's data
            latest_year = ratios_df['year'].max() if not ratios_df.empty else None
            latest_ratios = ratios_df[ratios_df['year'] == latest_year].iloc[0] if latest_year else None

            # Company card
            st.subheader(f"{selected_company_name} ({selected_ticker})")
            # We don't have sector, sub-sector, about in the current tables; we would need to join with companies and sectors
            # For now, we'll show placeholder
            st.write(f"**Sector:** N/A")
            st.write(f"**Sub-Sector:** N/A")
            st.write(f"**About:** N/A")

            # 6 KPI tiles
            kpi1, kpi2, kpi3, kpi4, kpi5, kpi6 = st.columns(6)
            with kpi1:
                roe = latest_ratios['return_on_equity_pct'] if latest_ratios is not None and not pd.isna(latest_ratios['return_on_equity_pct']) else None
                st.metric("ROE", f"{roe:.2f}%" if roe is not None else "N/A")
            with kp2:
                roce = latest_ratios['return_on_capital_employed_pct'] if latest_ratios is not None and not pd.isna(latest_ratios['return_on_capital_employed_pct']) else None
                st.metric("ROCE", f"{roce:.2f}%" if roce is not None else "N/A")
            with kpi3:
                npm = latest_ratios['net_profit_margin_pct'] if latest_ratios is not None and not pd.isna(latest_ratios['net_profit_margin_pct']) else None
                st.metric("Net Profit Margin", f"{npm:.2f}%" if npm is not None else "N/A")
            with kpi4:
                de = latest_ratios['debt_to_equity'] if latest_ratios is not None and not pd.isna(latest_ratios['debt_to_equity']) else None
                st.metric("D/E", f"{de:.2f}" if de is not None else "N/A")
            with kpi5:
                rev_cagr = latest_ratios['revenue_cagr_5yr'] if latest_ratios is not None and not pd.isna(latest_ratios['revenue_cagr_5yr']) else None
                st.metric("Revenue CAGR 5yr", f"{rev_cagr:.2f}%" if rev_cagr is not None else "N/A")
            with kpi6:
                fcf = latest_ratios['free_cash_flow_cr'] if latest_ratios is not None and not pd.isna(latest_ratios['free_cash_flow_cr']) else None
                st.metric("FCF (Latest Year)", f"{fcf:.2f} Cr" if fcf is not None else "N/A")

            # Placeholder for charts
            st.subheader("Financial Charts")
            st.write("10-year bar chart for Revenue and Net Profit (Placeholder)")
            st.write("ROE and ROCE dual-axis line chart (Placeholder)")

            # Placeholder for pros and cons
            st.subheader("Pros & Cons")
            st.write("Pros and cons will be displayed here")
        else:
            st.warning("No financial data available for this company.")
    else:
        st.info("Please select a company to view its profile.")