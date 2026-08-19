import pandas as pd
import sqlite3

DB_PATH = "db/nifty100.db"

def compute_valuation_summary(year="2024-03"):
    conn = sqlite3.connect(DB_PATH)

    # Get market cap data for the year (market_cap.year is integer)
    market_cap = pd.read_sql(
        "SELECT * FROM market_cap WHERE year = ?",
        conn,
        params=[year[:4]]
    )

    # Get financial ratios for the year
    financial_ratios = pd.read_sql(
        "SELECT * FROM financial_ratios WHERE year = ?",
        conn,
        params=[year]
    )

    # Merge market cap and financial ratios on company_id
    df = market_cap.merge(financial_ratios, on="company_id", how="inner")

    # Compute FCF yield: FCF / market_cap_crore * 100
    df["FCF_yield_pct"] = (df["free_cash_flow_cr"] / df["market_cap_crore"]) * 100

    # Get sectors data to get broad_sector for each company
    sectors = pd.read_sql("SELECT id, company_id, broad_sector FROM sectors", conn)
    # Merge to get broad_sector
    df = df.merge(sectors, on="company_id", how="left")

    # Compute sector median P/E for each broad_sector
    sector_median_pe = df.groupby("broad_sector")["pe_ratio"].median().reset_index()
    sector_median_pe.columns = ["broad_sector", "5yr_median_PE"]
    df = df.merge(sector_median_pe, on="broad_sector", how="left")

    # Compute PE vs sector median percentage
    df["PE_vs_sector_median_pct"] = (df["pe_ratio"] / df["5yr_median_PE"] - 1) * 100

    # Apply overvaluation flags
    def get_flag(pe_ratio, sector_median):
        if pd.isna(pe_ratio) or pd.isna(sector_median):
            return "Fair"
        if pe_ratio > sector_median * 1.5:
            return "Caution"
        elif pe_ratio < sector_median * 0.7:
            return "Discount"
        else:
            return "Fair"

    df["flag"] = df.apply(lambda row: get_flag(row["pe_ratio"], row["5yr_median_PE"]), axis=1)

    # Get company names
    companies = pd.read_sql("SELECT id, company_name FROM companies", conn)
    # Merge to get company_name
    df = df.merge(companies, left_on="company_id", right_on="id", how="left")

    # Select and rename columns for output
    output_cols = [
        "company_id", "company_name", "broad_sector",
        "pe_ratio", "pb_ratio", "ev_ebitda",
        "FCF_yield_pct", "5yr_median_PE", "PE_vs_sector_median_pct", "flag"
    ]
    output_df = df[output_cols].copy()
    output_df = output_df.rename(columns={
        "pe_ratio": "P/E",
        "pb_ratio": "P/B",
        "ev_ebitda": "EV/EBITDA",
        "5yr_median_PE": "5yr_median_PE",
        "PE_vs_sector_median_pct": "PE_vs_sector_median_pct",
        "FCF_yield_pct": "FCF_yield_pct"
    })

    conn.close()
    return output_df

def generate_valuation_files():
    df = compute_valuation_summary()

    # Save valuation_summary.xlsx
    df.to_excel("output/valuation_summary.xlsx", index=False)

    # Generate valuation_flags.csv (only Caution and Discount)
    flags_df = df[df["flag"].isin(["Caution", "Discount"])]
    flags_df.to_csv("output/valuation_flags.csv", index=False)

    return df

if __name__ == "__main__":
    generate_valuation_files()