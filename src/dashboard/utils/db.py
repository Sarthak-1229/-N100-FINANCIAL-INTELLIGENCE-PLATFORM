import streamlit as st
import sqlite3
import pandas as pd

DB_PATH = "db/nifty100.db"

@st.cache_data(ttl=600)
def get_companies():
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql("SELECT id, company_name FROM companies", conn)
    conn.close()
    return df

@st.cache_data(ttl=600)
def get_ratios(ticker, year=None):
    conn = sqlite3.connect(DB_PATH)
    if year:
        df = pd.read_sql("SELECT * FROM financial_ratios WHERE company_id = ? AND year = ?", conn, params=(ticker, year))
    else:
        df = pd.read_sql("SELECT * FROM financial_ratios WHERE company_id = ?", conn, params=(ticker,))
    conn.close()
    return df

@st.cache_data(ttl=600)
def get_pl(ticker):
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql("SELECT * FROM profitandloss WHERE company_id = ?", conn, params=(ticker,))
    conn.close()
    return df

@st.cache_data(ttl=600)
def get_bs(ticker):
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql("SELECT * FROM balancesheet WHERE company_id = ?", conn, params=(ticker,))
    conn.close()
    return df

@st.cache_data(ttl=600)
def get_cf(ticker):
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql("SELECT * FROM cashflow WHERE company_id = ?", conn, params=(ticker,))
    conn.close()
    return df

@st.cache_data(ttl=600)
def get_sectors():
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql("SELECT * FROM sectors", conn)
    conn.close()
    return df

@st.cache_data(ttl=600)
def get_peers(group_name):
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql("SELECT company_id FROM peer_groups WHERE peer_group_name = ?", conn, params=(group_name,))
    conn.close()
    return df

@st.cache_data(ttl=600)
def get_valuation(ticker):
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql("SELECT * FROM valuation_summary WHERE company_id = ?", conn, params=(ticker,))
    conn.close()
    return df