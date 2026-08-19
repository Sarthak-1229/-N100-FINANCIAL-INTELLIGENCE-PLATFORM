import streamlit as st
from src.dashboard.pages import home, profile, screener, peers, trends, sectors, capital, reports

st.set_page_config(
    page_title="Nifty 100 Analytics",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.sidebar.title("Navigation")
page = st.sidebar.selectbox(
    "Choose a screen",
    ["Home", "Company Profile", "Screener", "Peers", "Trends", "Sectors", "Capital Allocation", "Annual Reports"]
)

if page == "Home":
    home.show()
elif page == "Company Profile":
    profile.show()
elif page == "Screener":
    screener.show()
elif page == "Peers":
    peers.show()
elif page == "Trends":
    trends.show()
elif page == "Sectors":
    sectors.show()
elif page == "Capital Allocation":
    capital.show()
elif page == "Annual Reports":
    reports.show()