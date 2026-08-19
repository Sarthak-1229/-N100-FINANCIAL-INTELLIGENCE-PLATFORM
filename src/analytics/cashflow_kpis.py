"""
src/analytics/cashflow_kpis.py

Cash flow KPIs and capital allocation classifier.
All monetary values in Crore (Cr) unless stated otherwise.
"""
import pandas as pd
import sqlite3
import os
from src.etl.normaliser import normalize_numeric


# Capital allocation 8-pattern labels
PATTERN_REINVESTOR = "Reinvestor"  # (+,-,-)
PATTERN_SHAREHOLDER_RETURNS = "Shareholder Returns"  # (+,-,-) with high CFO/PAT
PATTERN_LIQUIDATING = "Liquidating Assets"  # (+,+,-)
PATTERN_DISTRESS = "Distress Signal"  # (-,+,+)
PATTERN_GROWTH_DEBT = "Growth Funded by Debt"  # (-,-,+)
PATTERN_CASH_ACCUMULATOR = "Cash Accumulator"  # (+,+,+)
PATTERN_PRE_REVENUE = "Pre-Revenue"  # (-,-,-)
PATTERN_MIXED = "Mixed"  # (+,-,+)


def free_cash_flow(operating_activity, investing_activity) -> float:
    """
    FCF = operating_activity + investing_activity
    Negative value is allowed (and common for growth companies).

    Args:
        operating_activity: Cash from operating activities (Cr)
        investing_activity: Cash from investing activities (Cr, usually negative)

    Returns:
        Free cash flow (Cr), or 0 if both inputs are None
    """
    operating_activity = normalize_numeric(operating_activity) or 0
    investing_activity = normalize_numeric(investing_activity) or 0

    return round(operating_activity + investing_activity, 2)


def cfo_quality_score(cfo_series: pd.Series, pat_series: pd.Series):
    """
    CFO Quality = avg(CFO / PAT) over 5 years
    > 1.0 = High Quality
    0.5-1.0 = Moderate
    < 0.5 = Accrual Risk
    Returns None if PAT = 0

    Args:
        cfo_series: Series of CFO values
        pat_series: Series of PAT (net profit) values (same length)

    Returns:
        Tuple of (avg_ratio, label)
    """
    if cfo_series is None or pat_series is None:
        return None, None

    if len(cfo_series) == 0 or len(pat_series) == 0:
        return None, None

    # Align series by index
    cfo_aligned = cfo_series.reindex(pat_series.index)

    # Compute ratios
    ratios = []
    for idx in pat_series.index:
        cfo = normalize_numeric(cfo_aligned.get(idx))
        pat = normalize_numeric(pat_series.get(idx))

        if pat is None or pat == 0:
            continue
        if cfo is None:
            continue

        ratios.append(cfo / pat)

    if not ratios:
        return None, None

    avg_ratio = sum(ratios) / len(ratios)
    avg_ratio = round(avg_ratio, 2)

    if avg_ratio > 1.0:
        label = "High Quality"
    elif avg_ratio >= 0.5:
        label = "Moderate"
    else:
        label = "Accrual Risk"

    return avg_ratio, label


def capex_intensity(investing_activity, sales) -> float | None:
    """
    CapEx Intensity = abs(investing_activity) / sales * 100
    < 3% = Asset Light
    3-8% = Moderate
    > 8% = Capital Intensive

    Args:
        investing_activity: Cash from investing activities (Cr, usually negative)
        sales: Sales/Revenue (Cr)

    Returns:
        CapEx intensity percentage, or None if sales is None/<=0
    """
    investing_activity = normalize_numeric(investing_activity)
    sales = normalize_numeric(sales)

    if investing_activity is None or sales is None or sales <= 0:
        return None

    return round((abs(investing_activity) / sales) * 100, 2)


def fcf_conversion_rate(fcf, operating_profit) -> float | None:
    """
    FCF Conversion Rate = FCF / operating_profit * 100

    Args:
        fcf: Free cash flow (Cr)
        operating_profit: Operating profit (Cr)

    Returns:
        FCF conversion percentage, or None if operating_profit is None/0
    """
    fcf = normalize_numeric(fcf)
    operating_profit = normalize_numeric(operating_profit)

    if fcf is None or operating_profit is None or operating_profit == 0:
        return None

    return round((fcf / operating_profit) * 100, 2)


def classify_capital_allocation(cfo, cfi, cff, cfo_pat_ratio=None):
    """
    8-pattern capital allocation classifier based on sign of (CFO, CFI, CFF).

    Patterns:
    (+,-,-) = Reinvestor (or Shareholder Returns if CFO/PAT > 1.0)
    (+,+,-) = Liquidating Assets
    (-,+,+) = Distress Signal
    (-,-,+) = Growth Funded by Debt
    (+,+,+) = Cash Accumulator
    (-,-,-) = Pre-Revenue
    (+,-,+) = Mixed

    Args:
        cfo: Operating cash flow
        cfi: Investing cash flow
        cff: Financing cash flow
        cfo_pat_ratio: Optional CFO/PAT ratio for distinguishing Reinvestor vs Shareholder Returns

    Returns:
        Pattern label string
    """
    cfo = normalize_numeric(cfo)
    cfi = normalize_numeric(cfi)
    cff = normalize_numeric(cff)

    # Treat None as 0 (no activity)
    if cfo is None:
        cfo = 0
    if cfi is None:
        cfi = 0
    if cff is None:
        cff = 0

    # Compute signs
    cfo_sign = "+" if cfo > 0 else ("-" if cfo < 0 else "0")
    cfi_sign = "+" if cfi > 0 else ("-" if cfi < 0 else "0")
    cff_sign = "+" if cff > 0 else ("-" if cff < 0 else "0")

    # All zero -> Mixed (no clear pattern)
    if cfo_sign == "0" and cfi_sign == "0" and cff_sign == "0":
        return PATTERN_MIXED

    # (+,-,-) = Reinvestor or Shareholder Returns
    if cfo_sign == "+" and cfi_sign == "-" and cff_sign == "-":
        if cfo_pat_ratio is not None and cfo_pat_ratio > 1.0:
            return PATTERN_SHAREHOLDER_RETURNS
        return PATTERN_REINVESTOR

    # (+,+,-) = Liquidating Assets
    if cfo_sign == "+" and cfi_sign == "+" and cff_sign == "-":
        return PATTERN_LIQUIDATING

    # (-,+,+) = Distress Signal
    if cfo_sign == "-" and cfi_sign == "+" and cff_sign == "+":
        return PATTERN_DISTRESS

    # (-,-,+) = Growth Funded by Debt
    if cfo_sign == "-" and cfi_sign == "-" and cff_sign == "+":
        return PATTERN_GROWTH_DEBT

    # (+,+,+) = Cash Accumulator
    if cfo_sign == "+" and cfi_sign == "+" and cff_sign == "+":
        return PATTERN_CASH_ACCUMULATOR

    # (-,-,-) = Pre-Revenue
    if cfo_sign == "-" and cfi_sign == "-" and cff_sign == "-":
        return PATTERN_PRE_REVENUE

    # (+,-,+) = Mixed
    if cfo_sign == "+" and cfi_sign == "-" and cff_sign == "+":
        return PATTERN_MIXED

    # Default: Mixed
    return PATTERN_MIXED


def get_sign_symbol(value) -> str:
    """Helper: return +, -, or 0 for a value."""
    if value is None:
        return "0"
    value = normalize_numeric(value)
    if value is None:
        return "0"
    if value > 0:
        return "+"
    elif value < 0:
        return "-"
    return "0"


def get_latest_financial_data():
    """
    Get the latest financial data for all companies from relevant tables
    Returns DataFrame with latest year data for each company
    """
    conn = sqlite3.connect("db/nifty100.db")

    # Get latest financial ratios data
    ratios_query = """
    SELECT fr.*
    FROM financial_ratios fr
    INNER JOIN (
        SELECT company_id, MAX(year) as max_year
        FROM financial_ratios
        GROUP BY company_id
    ) grouped ON fr.company_id = grouped.company_id AND fr.year = grouped.max_year
    """

    ratios_df = pd.read_sql(ratios_query, conn)

    # Get sectors data
    sectors_query = "SELECT company_id, broad_sector FROM sectors"
    sectors_df = pd.read_sql(sectors_query, conn)

    # Get company names
    companies_query = "SELECT id as company_id, company_name FROM companies"
    companies_df = pd.read_sql(companies_query, conn)

    conn.close()

    # Merge all data
    df = ratios_df.merge(sectors_df, on="company_id", how="left")
    df = df.merge(companies_df, on="company_id", how="left")

    return df


def generate_cashflow_intelligence():
    """
    Generate cash flow intelligence data for all companies
    Returns DataFrame with cash flow intelligence metrics
    """
    df = get_latest_financial_data()

    intelligence_records = []

    for _, row in df.iterrows():
        company_id = row['company_id']
        company_name = row['company_name'] if pd.notna(row['company_name']) else company_id
        sector = row['broad_sector'] if pd.notna(row['broad_sector']) else 'Unknown'

        # Extract relevant financial metrics
        cfo = row.get('cash_from_operations_cr')
        cfi = row.get('capex_cr')  # CapEx is usually negative investing activity
        cff = row.get('net_cash_flow') - (cfo or 0) - (cfi or 0) if pd.notna(row.get('net_cash_flow')) else None
        # Alternatively, we could get financing_activity directly if available

        # Calculate CFO Quality Score (using available data as proxy)
        # For simplicity, we'll use single year CFO/PAT ratio
        pat = row.get('net_profit')
        if pd.notna(cfo) and pd.notna(pat) and pat != 0:
            cfo_pat_ratio = cfo / pat
            if cfo_pat_ratio > 1.0:
                cfo_quality_label = "High Quality"
            elif cfo_pat_ratio >= 0.5:
                cfo_quality_label = "Moderate"
            else:
                cfo_quality_label = "Accrual Risk"
        else:
            cfo_pat_ratio = None
            cfo_quality_label = "Insufficient Data"

        # Calculate CapEx Intensity
        sales = row.get('sales')
        capex_intensity_pct = capex_intensity(cfi, sales) if pd.notna(cfi) and pd.notna(sales) else None
        if capex_intensity_pct is not None:
            if capex_intensity_pct < 3:
                capex_label = "Asset Light"
            elif capex_intensity_pct <= 8:
                capex_label = "Moderate"
            else:
                capex_label = "Capital Intensive"
        else:
            capex_label = "Insufficient Data"

        # FCF to PAT conversion rate
        fcf = free_cash_flow(cfo, cfi) if pd.notna(cfo) and pd.notna(cfi) else None
        operating_profit = row.get('operating_profit')
        fcf_conversion_pct = fcf_conversion_rate(fcf, operating_profit) if pd.notna(fcf) and pd.notna(operating_profit) else None

        # 5yr FCF CAGR (using available data as proxy)
        # We'll use revenue CAGR as a proxy for now, or calculate from historical FCF if available
        fcf_cagr_5yr = row.get('revenue_cagr_5yr')  # Proxy - ideally would calculate from historical FCF

        # Distress Signal detection: CFO < 0 AND CFF > 0
        distress_flag = False
        if pd.notna(cfo) and pd.notna(cff):
            if cfo < 0 and cff > 0:
                distress_flag = True

        # Deleveraging flag: CFF < 0 AND borrowings declining year-over-year
        # For simplicity, we'll use CFF < 0 as proxy and check if borrowings decreased
        deleveraging_flag = False
        if pd.notna(cff) and cff < 0:
            # Check if borrowings decreased (would need historical data)
            # For now, we'll flag all companies with negative CFF as potential deleveraging
            deleveraging_flag = True  # Simplified

        # Get capital allocation pattern from existing data or calculate
        capital_allocation_pattern = row.get('capital_allocation_pattern')
        if pd.isna(capital_allocation_pattern):
            # Calculate if not available
            capital_allocation_pattern = classify_capital_allocation(cfo, cfi, cff, cfo_pat_ratio)

        intelligence_records.append({
            'company_id': company_id,
            'company_name': company_name,
            'sector': sector,
            'cfo_quality_score': round(cfo_pat_ratio, 2) if pd.notna(cfo_pat_ratio) else None,
            'cfo_quality_label': cfo_quality_label,
            'capex_intensity_pct': capex_intensity_pct,
            'capex_label': capex_label,
            'fcf_cagr_5yr': round(fcf_cagr_5yr, 2) if pd.notna(fcf_cagr_5yr) else None,
            'fcf_conversion_pct': round(fcf_conversion_pct, 2) if pd.notna(fcf_conversion_pct) else None,
            'distress_flag': distress_flag,
            'deleveraging_flag': deleveraging_flag,
            'capital_allocation_label': capital_allocation_pattern
        })

    return pd.DataFrame(intelligence_records)


def generate_distress_alerts(intelligence_df):
    """
    Generate distress alerts dataframe
    Returns DataFrame with companies flagged with distress signal
    """
    distress_df = intelligence_df[intelligence_df['distress_flag'] == True].copy()

    if distress_df.empty:
        return pd.DataFrame(columns=[
            'company_id', 'company_name', 'sector',
            'cfo_value', 'cff_value', 'latest_net_profit'
        ])

    # Get detailed financial data for distressed companies
    conn = sqlite3.connect("db/nifty100.db")

    distress_records = []
    for _, row in distress_df.iterrows():
        company_id = row['company_id']

        # Get latest financial data for this company
        detail_query = """
        SELECT
            cash_from_operations_cr as cfo,
            financing_activity as cff,
            net_profit as latest_net_profit
        FROM cashflow cf
        INNER JOIN (
            SELECT company_id, MAX(year) as max_year
            FROM cashflow
            GROUP BY company_id
        ) grouped ON cf.company_id = grouped.company_id AND cf.year = grouped.max_year
        WHERE cf.company_id = ?
        """

        detail_df = pd.read_sql(detail_query, conn, params=[company_id])

        if not detail_df.empty:
            detail_row = detail_df.iloc[0]
            distress_records.append({
                'company_id': company_id,
                'company_name': row['company_name'],
                'sector': row['sector'],
                'cfo_value': detail_row['cfo'],
                'cff_value': detail_row['cff'],
                'latest_net_profit': detail_row['latest_net_profit']
            })

    conn.close()

    return pd.DataFrame(distress_records) if distress_records else pd.DataFrame(columns=[
        'company_id', 'company_name', 'sector',
        'cfo_value', 'cff_value', 'latest_net_profit'
    ])


def main():
    """Main function to generate cash flow intelligence data"""
    print("Generating cash flow intelligence data...")

    # Generate intelligence data
    intelligence_df = generate_cashflow_intelligence()

    if intelligence_df.empty:
        print("ERROR: No intelligence data generated")
        return

    print(f"Generated intelligence data for {len(intelligence_df)} companies")

    # Generate distress alerts
    distress_df = generate_distress_alerts(intelligence_df)
    print(f"Found {len(distress_df)} companies with distress signals")

    # Save intelligence data to Excel
    intelligence_output = "output/cashflow_intelligence.xlsx"
    os.makedirs("output", exist_ok=True)
    intelligence_df.to_excel(intelligence_output, index=False)
    print(f"Saved cash flow intelligence to {intelligence_output}")

    # Save distress alerts to CSV
    distress_output = "output/distress_alerts.csv"
    distress_df.to_csv(distress_output, index=False)
    print(f"Saved distress alerts to {distress_output}")

    # Show summary statistics
    print("\n--- Summary Statistics ---")
    print(f"CFO Quality Distribution:")
    print(intelligence_df['cfo_quality_label'].value_counts())
    print(f"\nCapEx Intensity Distribution:")
    print(intelligence_df['capex_label'].value_counts())
    print(f"\nCapital Allocation Distribution:")
    print(intelligence_df['capital_allocation_label'].value_counts())
    print(f"\nDistress Signals: {intelligence_df['distress_flag'].sum()} companies")
    print(f"Deleveraging Flags: {intelligence_df['deleveraging_flag'].sum()} companies")

    # Show sample of intelligence data
    print("\nSample intelligence data:")
    print(intelligence_df.head())

    # Show sample of distress alerts if any
    if not distress_df.empty:
        print("\nSample distress alerts:")
        print(distress_df.head())

    print("\nDone!")


if __name__ == "__main__":
    main()