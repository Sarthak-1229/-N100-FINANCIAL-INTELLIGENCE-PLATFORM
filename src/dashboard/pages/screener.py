import streamlit as st
import pandas as pd
from src.screener.engine import run_screener, run_all_presets, export_screener_output
import os

def show():
    st.title("Financial Screener")
    st.write("Filter companies based on financial metrics")

    # Sidebar for filters
    st.sidebar.header("Filters")

    # Preset buttons
    st.sidebar.subheader("Presets")
    preset_cols = st.sidebar.columns(3)
    presets = ["quality_compounder", "value_pick", "growth_accelerator",
               "dividend_champion", "debt_free_blue_chip", "turnaround_watch"]

    selected_preset = None
    for i, preset in enumerate(presets):
        if preset_cols[i % 3].button(preset.replace('_', ' ').title()):
            selected_preset = preset

    # Manual filters (we'll implement a few for now)
    st.sidebar.subheader("Manual Filters")
    roe_min = st.sidebar.slider("ROE Min (%)", 0.0, 50.0, 0.0, 0.5)
    de_max = st.sidebar.slider("D/E Max", 0.0, 5.0, 5.0, 0.1)
    fcf_min = st.sidebar.slider("FCF Min (Cr)", -1000.0, 1000.0, -1000.0, 50.0)
    revenue_cagr_min = st.sidebar.slider("Revenue CAGR 5yr Min (%)", -50.0, 50.0, -50.0, 1.0)

    # Apply filters
    if st.sidebar.button("Apply Filters") or selected_preset:
        if selected_preset:
            result_df = run_screener(preset=selected_preset)
            st.success(f"Applied preset: {selected_preset.replace('_', ' ').title()}")
        else:
            filters = {}
            if roe_min > 0:
                filters['roe_min'] = roe_min
            if de_max < 5.0:
                filters['de_max'] = de_max
            if fcf_min > -1000.0:
                filters['fcf_min'] = fcf_min
            if revenue_cagr_min > -50.0:
                filters['revenue_cagr_5yr_min'] = revenue_cagr_min
            result_df = run_screener(custom_filters=filters)

        if not result_df.empty:
            st.write(f"Found {len(result_df)} companies matching your criteria")

            # Display results table
            display_cols = ['company_id', 'company_name', 'broad_sector', 'final_score',
                          'return_on_equity_pct', 'debt_to_equity', 'free_cash_flow_cr',
                          'revenue_cagr_5yr']
            # Only keep columns that exist
            display_cols = [col for col in display_cols if col in result_df.columns]
            st.dataframe(result_df[display_cols])

            # CSV download
            csv = result_df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="Download results as CSV",
                data=csv,
                file_name='screener_results.csv',
                mime='text/csv',
            )
        else:
            st.warning("No companies match your criteria")
    else:
        st.info("Select a preset or set filters and click 'Apply Filters' to see results")