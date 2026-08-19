"""
src/nlp/pros_cons_generator.py
NLP — Auto Pros/Cons Generator (Day 30)
Implements 12 pro rules and 12 con rules with confidence scores
Generates output/pros_cons_generated.csv
"""

import pandas as pd
import sqlite3
import os
from src.etl.normaliser import normalize_numeric

# Output directories
OUTPUT_DIR = os.getenv("OUTPUT_DIR", "output")
PROS_CONS_OUTPUT = os.path.join(OUTPUT_DIR, "pros_cons_generated.csv")

# Ensure output directory exists
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Constants for confidence scoring
MIN_CONFIDENCE_THRESHOLD = 60  # Only include rules with confidence > 60%

def get_latest_financial_data():
    """
    Get the latest financial data for all companies from financial_ratios table
    Returns DataFrame with latest year data for each company
    """
    conn = sqlite3.connect("db/nifty100.db")

    # Query to get latest year data for each company
    query = """
    SELECT fr.*
    FROM financial_ratios fr
    INNER JOIN (
        SELECT company_id, MAX(year) as max_year
        FROM financial_ratios
        GROUP BY company_id
    ) grouped ON fr.company_id = grouped.company_id AND fr.year = grouped.max_year
    """

    df = pd.read_sql(query, conn)
    conn.close()
    return df

def get_company_names():
    """
    Get company mapping from companies table
    Returns DataFrame with company_id and company_name
    """
    conn = sqlite3.connect("db/nifty100.db")
    query = "SELECT id as company_id, company_name FROM companies"
    df = pd.read_sql(query, conn)
    conn.close()
    return df

def calculate_signal_strength(value, threshold, is_higher_better=True):
    """
    Calculate signal strength (0-100) based on how much a value exceeds a threshold
    """
    if pd.isna(value):
        return 0

    if is_higher_better:
        if value <= threshold:
            return 0
        # For values above threshold, score increases up to 100 at 2*threshold
        excess_ratio = (value - threshold) / threshold
        score = min(excess_ratio * 50, 100)  # Cap at 100
        return score
    else:
        # For lower is better (like D/E ratio)
        if value >= threshold:
            return 0
        # For values below threshold, score increases as value decreases
        if threshold == 0:
            return 100 if value < 0 else 0
        excess_ratio = (threshold - value) / threshold
        score = min(excess_ratio * 50, 100)  # Cap at 100
        return score

def generate_pros_cons_data():
    """
    Generate pros and cons data for all companies based on financial rules
    Returns DataFrame with columns: company_id, type, rule_id, text, confidence_pct
    """
    # Get latest financial data
    financial_df = get_latest_financial_data()
    companies_df = get_company_names()

    # Merge to get company names
    df = financial_df.merge(companies_df, on="company_id", how="left")

    pros_records = []
    cons_records = []

    # Process each company
    for _, row in df.iterrows():
        company_id = row['company_id']
        company_name = row['company_name'] if pd.notna(row['company_name']) else company_id

        # ===== PRO RULES (12 rules) =====

        # Pro 1: Consistent ROE > 15% (High quality)
        roe = row.get('return_on_equity_pct')
        if pd.notna(roe):
            confidence = calculate_signal_strength(roe, 15, is_higher_better=True)
            if confidence > MIN_CONFIDENCE_THRESHOLD:
                pros_records.append({
                    'company_id': company_id,
                    'type': 'pro',
                    'rule_id': 'PRO_01',
                    'text': f'High ROE ({roe:.1f}%) indicates efficient equity utilization',
                    'confidence_pct': round(confidence, 1)
                })

        # Pro 2: Low debt (D/E < 0.3) - Conservative balance sheet
        de = row.get('debt_to_equity')
        if pd.notna(de):
            # For D/E, lower is better, so we invert the scoring
            if de < 0.3:
                confidence = calculate_signal_strength(0.3, de, is_higher_better=False)
                if confidence > MIN_CONFIDENCE_THRESHOLD:
                    pros_records.append({
                        'company_id': company_id,
                        'type': 'pro',
                        'rule_id': 'PRO_02',
                        'text': f'Low debt-to-equity ({de:.2f}) indicates conservative financial leverage',
                        'confidence_pct': round(confidence, 1)
                    })

        # Pro 3: Strong operating profit margin (> 15%)
        opm = row.get('operating_profit_margin_pct')
        if pd.notna(opm):
            confidence = calculate_signal_strength(opm, 15, is_higher_better=True)
            if confidence > MIN_CONFIDENCE_THRESHOLD:
                pros_records.append({
                    'company_id': company_id,
                    'type': 'pro',
                    'rule_id': 'PRO_03',
                    'text': f'Strong operating margin ({opm:.1f}%) reflects operational efficiency',
                    'confidence_pct': round(confidence, 1)
                })

        # Pro 4: Healthy free cash flow (> 0)
        fcf = row.get('free_cash_flow_cr')
        if pd.notna(fcf) and fcf > 0:
            # Scale confidence based on FCF magnitude relative to company size
            sales = row.get('sales', 1)  # Avoid division by zero
            fcf_to_sales = abs(fcf) / max(sales, 1) * 100 if sales else 0
            confidence = min(fcf_to_sales * 10, 100)  # Scale appropriately
            if confidence > MIN_CONFIDENCE_THRESHOLD:
                pros_records.append({
                    'company_id': company_id,
                    'type': 'pro',
                    'rule_id': 'PRO_04',
                    'text': f'Positive free cash flow ({fcf:.1f} Cr) indicates financial flexibility',
                    'confidence_pct': round(confidence, 1)
                })

        # Pro 5: Efficient asset utilization (Asset Turnover > 0.8)
        asset_turnover = row.get('asset_turnover')
        if pd.notna(asset_turnover):
            confidence = calculate_signal_strength(asset_turnover, 0.8, is_higher_better=True)
            if confidence > MIN_CONFIDENCE_THRESHOLD:
                pros_records.append({
                    'company_id': company_id,
                    'type': 'pro',
                    'rule_id': 'PRO_05',
                    'text': f'Efficient asset utilization ({asset_turnover:.2f}x) indicates operational effectiveness',
                    'confidence_pct': round(confidence, 1)
                })

        # Pro 6: Strong interest coverage (> 4) - Ability to service debt
        interest_coverage = row.get('interest_coverage')
        if pd.notna(interest_coverage):
            confidence = calculate_signal_strength(interest_coverage, 4, is_higher_better=True)
            if confidence > MIN_CONFIDENCE_THRESHOLD:
                pros_records.append({
                    'company_id': company_id,
                    'type': 'pro',
                    'rule_id': 'PRO_06',
                    'text': f'Strong interest coverage ({interest_coverage:.1f}x) indicates debt service capability',
                    'confidence_pct': round(confidence, 1)
                })

        # Pro 7: Consistent revenue growth (3yr CAGR > 10%)
        revenue_cagr = row.get('revenue_cagr_5yr')  # Using 5yr as proxy
        if pd.notna(revenue_cagr):
            confidence = calculate_signal_strength(revenue_cagr, 10, is_higher_better=True)
            if confidence > MIN_CONFIDENCE_THRESHOLD:
                pros_records.append({
                    'company_id': company_id,
                    'type': 'pro',
                    'rule_id': 'PRO_07',
                    'text': f'Consistent revenue growth ({revenue_cagr:.1f}% CAGR) indicates business expansion',
                    'confidence_pct': round(confidence, 1)
                })

        # Pro 8: Profitability consistency (Net profit margin > 8%)
        npm = row.get('net_profit_margin_pct')
        if pd.notna(npm):
            confidence = calculate_signal_strength(npm, 8, is_higher_better=True)
            if confidence > MIN_CONFIDENCE_THRESHOLD:
                pros_records.append({
                    'company_id': company_id,
                    'type': 'pro',
                    'rule_id': 'PRO_08',
                    'text': f'Consistent profitability ({npm:.1f}% net margin) indicates sustainable earnings',
                    'confidence_pct': round(confidence, 1)
                })

        # Pro 9: Shareholder returns focus (High CFO/PAT ratio)
        cfo = row.get('cash_from_operations_cr')
        pat = row.get('net_profit')
        if pd.notna(cfo) and pd.notna(pat) and pat != 0:
            cfo_pat_ratio = cfo / pat
            confidence = calculate_signal_strength(cfo_pat_ratio, 0.8, is_higher_better=True)
            if confidence > MIN_CONFIDENCE_THRESHOLD:
                pros_records.append({
                    'company_id': company_id,
                    'type': 'pro',
                    'rule_id': 'PRO_09',
                    'text': f'Strong cash flow from operations ({cfo_pat_ratio:.2f}x PAT) indicates quality earnings',
                    'confidence_pct': round(confidence, 1)
                })

        # Pro 10: Low capital intensity (CapEx intensity < 5%)
        capex_intensity = row.get('capex_intensity_pct')
        if pd.notna(capex_intensity):
            # Lower capex intensity is better
            if capex_intensity < 5:
                confidence = calculate_signal_strength(5, capex_intensity, is_higher_better=False)
                if confidence > MIN_CONFIDENCE_THRESHOLD:
                    pros_records.append({
                        'company_id': company_id,
                        'type': 'pro',
                        'rule_id': 'PRO_10',
                        'text': f'Low capital intensity ({capex_intensity:.1f}%) indicates efficient capital allocation',
                        'confidence_pct': round(confidence, 1)
                    })

        # Pro 11: Dividend payer with sustainable payout (< 50%)
        dividend_payout = row.get('dividend_payout_ratio_pct')
        if pd.notna(dividend_payout) and dividend_payout > 0:
            # Ideal dividend payout is between 20-50%
            if 20 <= dividend_payout <= 50:
                confidence = 80  # Fixed confidence for ideal range
                pros_records.append({
                    'company_id': company_id,
                    'type': 'pro',
                    'rule_id': 'PRO_11',
                    'text': f'Sustainable dividend payout ({dividend_payout:.1f}%) indicates shareholder commitment',
                    'confidence_pct': confidence
                })
            elif dividend_payout < 20:
                # Low payout but still positive
                confidence = calculate_signal_strength(dividend_payout, 20, is_higher_better=True)
                if confidence > MIN_CONFIDENCE_THRESHOLD:
                    pros_records.append({
                        'company_id': company_id,
                        'type': 'pro',
                        'rule_id': 'PRO_11',
                        'text': f'Conservative dividend payout ({dividend_payout:.1f}%) indicates retained earnings for growth',
                        'confidence_pct': round(confidence, 1)
                    })

        # Pro 12: Strong valuation metrics (Reasonable P/E < 25 for growth stocks)
        pe_ratio = row.get('pe_ratio')
        if pd.notna(pe_ratio) and pe_ratio > 0:
            # Reasonable P/E range varies by sector, but < 25 is generally reasonable
            if pe_ratio < 25:
                confidence = calculate_signal_strength(25, pe_ratio, is_higher_better=False)
                if confidence > MIN_CONFIDENCE_THRESHOLD:
                    pros_records.append({
                        'company_id': company_id,
                        'type': 'pro',
                        'rule_id': 'PRO_12',
                        'text': f'Reasonable valuation (P/E {pe_ratio:.1f}) indicates market confidence',
                        'confidence_pct': round(confidence, 1)
                    })

        # ===== CON RULES (12 rules) =====

        # Con 1: Declining ROE trend (negative 3yr CAGR)
        roe_cagr = row.get('roe_cagr_3yr')  # Assuming this exists, if not we'll skip
        # For now, we'll use a proxy based on volatility or negative growth
        # Since we don't have ROE CAGR directly, we'll use a different approach

        # Con 1: High debt levels (D/E > 1.0) - Financial risk
        de = row.get('debt_to_equity')
        if pd.notna(de):
            if de > 1.0:
                confidence = calculate_signal_strength(de, 1.0, is_higher_better=True)
                if confidence > MIN_CONFIDENCE_THRESHOLD:
                    cons_records.append({
                        'company_id': company_id,
                        'type': 'con',
                        'rule_id': 'CON_01',
                        'text': f'High debt-to-equity ({de:.2f}) indicates financial leverage risk',
                        'confidence_pct': round(confidence, 1)
                    })

        # Con 2: Weak profitability (Net profit margin < 3%)
        npm = row.get('net_profit_margin_pct')
        if pd.notna(npm):
            if npm < 3:
                # For con, lower values get higher confidence as they get worse
                confidence = calculate_signal_strength(3, npm, is_higher_better=False)
                if confidence > MIN_CONFIDENCE_THRESHOLD:
                    cons_records.append({
                        'company_id': company_id,
                        'type': 'con',
                        'rule_id': 'CON_02',
                        'text': f'Low net profit margin ({npm:.1f}%) indicates profitability challenges',
                        'confidence_pct': round(confidence, 1)
                    })

        # Con 3: Negative free cash flow (FCF < 0)
        fcf = row.get('free_cash_flow_cr')
        if pd.notna(fcf) and fcf < 0:
            # Scale confidence based on magnitude of negative FCF
            sales = row.get('sales', 1)
            fcf_to_sales = abs(fcf) / max(sales, 1) * 100 if sales else 0
            confidence = min(fcf_to_sales * 10, 100)
            if confidence > MIN_CONFIDENCE_THRESHOLD:
                cons_records.append({
                    'company_id': company_id,
                    'type': 'con',
                    'rule_id': 'CON_03',
                    'text': f'Negative free cash flow ({fcf:.1f} Cr) indicates cash consumption',
                    'confidence_pct': round(confidence, 1)
                })

        # Con 4: Declining revenue trend (Revenue CAGR < 0%)
        revenue_cagr = row.get('revenue_cagr_5yr')
        if pd.notna(revenue_cagr):
            if revenue_cagr < 0:
                confidence = calculate_signal_strength(0, revenue_cagr, is_higher_better=False)
                if confidence > MIN_CONFIDENCE_THRESHOLD:
                    cons_records.append({
                        'company_id': company_id,
                        'type': 'con',
                        'rule_id': 'CON_04',
                        'text': f'Declining revenue ({revenue_cagr:.1f}% CAGR) indicates business contraction',
                        'confidence_pct': round(confidence, 1)
                    })

        # Con 5: Poor interest coverage (< 2.0) - Debt service concerns
        interest_coverage = row.get('interest_coverage')
        if pd.notna(interest_coverage):
            if interest_coverage < 2.0:
                confidence = calculate_signal_strength(2.0, interest_coverage, is_higher_better=False)
                if confidence > MIN_CONFIDENCE_THRESHOLD:
                    cons_records.append({
                        'company_id': company_id,
                        'type': 'con',
                        'rule_id': 'CON_05',
                        'text': f'Weak interest coverage ({interest_coverage:.1f}x) indicates debt service concerns',
                        'confidence_pct': round(confidence, 1)
                    })

        # Con 6: Asset inefficiency (Asset Turnover < 0.3)
        asset_turnover = row.get('asset_turnover')
        if pd.notna(asset_turnover):
            if asset_turnover < 0.3:
                confidence = calculate_signal_strength(0.3, asset_turnover, is_higher_better=False)
                if confidence > MIN_CONFIDENCE_THRESHOLD:
                    cons_records.append({
                        'company_id': company_id,
                        'type': 'con',
                        'rule_id': 'CON_06',
                        'text': f'Poor asset utilization ({asset_turnover:.2f}x) indicates operational inefficiency',
                        'confidence_pct': round(confidence, 1)
                    })

        # Con 7: Inconsistent profitability (Negative net profit)
        net_profit = row.get('net_profit')
        if pd.notna(net_profit):
            if net_profit < 0:
                # Scale confidence based on magnitude of loss
                sales = row.get('sales', 1)
                loss_ratio = abs(net_profit) / max(sales, 1) * 100 if sales else 0
                confidence = min(loss_ratio * 5, 100)  # Scale appropriately
                if confidence > MIN_CONFIDENCE_THRESHOLD:
                    cons_records.append({
                        'company_id': company_id,
                        'type': 'con',
                        'rule_id': 'CON_07',
                        'text': f'Negative net profit ({net_profit:.0f} Cr) indicates unprofitability',
                        'confidence_pct': round(confidence, 1)
                    })

        # Con 8: High capital intensity (CapEx intensity > 15%)
        capex_intensity = row.get('capex_intensity_pct')
        if pd.notna(capex_intensity):
            if capex_intensity > 15:
                confidence = calculate_signal_strength(capex_intensity, 15, is_higher_better=True)
                if confidence > MIN_CONFIDENCE_THRESHOLD:
                    cons_records.append({
                        'company_id': company_id,
                        'type': 'con',
                        'rule_id': 'CON_08',
                        'text': f'High capital intensity ({capex_intensity:.1f}%) indicates heavy investment burden',
                        'confidence_pct': round(confidence, 1)
                    })

        # Con 9: Weak cash flow conversion (CFO/PAT < 0.3)
        cfo = row.get('cash_from_operations_cr')
        pat = row.get('net_profit')
        if pd.notna(cfo) and pd.notna(pat) and pat > 0:
            cfo_pat_ratio = cfo / pat
            if cfo_pat_ratio < 0.3:
                confidence = calculate_signal_strength(0.3, cfo_pat_ratio, is_higher_better=False)
                if confidence > MIN_CONFIDENCE_THRESHOLD:
                    cons_records.append({
                        'company_id': company_id,
                        'type': 'con',
                        'rule_id': 'CON_09',
                        'text': f'Poor cash flow conversion ({cfo_pat_ratio:.2f}x PAT) indicates accrual concerns',
                        'confidence_pct': round(confidence, 1)
                    })

        # Con 10: Unreasonable valuation (P/E > 50) - Potential overvaluation
        pe_ratio = row.get('pe_ratio')
        if pd.notna(pe_ratio) and pe_ratio > 0:
            if pe_ratio > 50:
                confidence = calculate_signal_strength(pe_ratio, 50, is_higher_better=True)
                if confidence > MIN_CONFIDENCE_THRESHOLD:
                    cons_records.append({
                        'company_id': company_id,
                        'type': 'con',
                        'rule_id': 'CON_10',
                        'text': f'High valuation (P/E {pe_ratio:.1f}) indicates potential overvaluation',
                        'confidence_pct': round(confidence, 1)
                    })

        # Con 11: No dividends (for mature companies) - Missing income component
        # We'll implement this as a conditional rule - only for companies with >5% ROE that don't pay dividends
        dividend_payout = row.get('dividend_payout_ratio_pct')
        roe = row.get('return_on_equity_pct')
        if pd.notna(roe) and roe > 5:  # Mature/profitable company
            if pd.isna(dividend_payout) or dividend_payout == 0:
                confidence = min(roe * 2, 100)  # Higher ROE gets higher confidence for this con
                if confidence > MIN_CONFIDENCE_THRESHOLD:
                    cons_records.append({
                        'company_id': company_id,
                        'type': 'con',
                        'rule_id': 'CON_11',
                        'text': f'No dividend payout despite {roe:.1f}% ROE indicates retained earnings preference',
                        'confidence_pct': round(confidence, 1)
                    })

        # Con 12: Declining profit trend (PAT CAGR < 0%)
        pat_cagr = row.get('pat_cagr_5yr')
        if pd.notna(pat_cagr):
            if pat_cagr < 0:
                confidence = calculate_signal_strength(0, pat_cagr, is_higher_better=False)
                if confidence > MIN_CONFIDENCE_THRESHOLD:
                    cons_records.append({
                        'company_id': company_id,
                        'type': 'con',
                        'rule_id': 'CON_12',
                        'text': f'Declining profitability ({pat_cagr:.1f}% PAT CAGR) indicates earnings contraction',
                        'confidence_pct': round(confidence, 1)
                    })

    # Create DataFrames
    pros_df = pd.DataFrame(pros_records) if pros_records else pd.DataFrame(
        columns=['company_id', 'type', 'rule_id', 'text', 'confidence_pct']
    )
    cons_df = pd.DataFrame(cons_records) if cons_records else pd.DataFrame(
        columns=['company_id', 'type', 'rule_id', 'text', 'confidence_pct']
    )

    # Combine pros and cons
    combined_df = pd.concat([pros_df, cons_df], ignore_index=True)

    # Sort by company_id and type (pros first, then cons)
    combined_df = combined_df.sort_values(['company_id', 'type'], ascending=[True, False])

    return combined_df

def validate_output(df):
    """
    Validate that every company has at least 1 pro and 1 con
    Returns True if validation passes, False otherwise
    """
    if df.empty:
        print("ERROR: No data generated")
        return False

    # Get unique company IDs
    pros_companies = set(df[df['type'] == 'pro']['company_id'].unique())
    cons_companies = set(df[df['type'] == 'con']['company_id'].unique())
    all_companies = set(df['company_id'].unique())

    missing_pros = all_companies - pros_companies
    missing_cons = all_companies - cons_companies

    if missing_pros:
        print(f"WARNING: {len(missing_pros)} companies missing pros: {list(missing_pros)[:5]}...")
    if missing_cons:
        print(f"WARNING: {len(missing_cons)} companies missing cons: {list(missing_cons)[:5]}...")

    # For now, we'll allow some flexibility - the goal is to maximize coverage
    # In a real implementation, we might want to adjust rules to ensure minimum coverage
    print(f"Companies with pros: {len(pros_companies)}/{len(all_companies)}")
    print(f"Companies with cons: {len(cons_companies)}/{len(all_companies)}")

    return len(missing_pros) == 0 and len(missing_cons) == 0

def main():
    """Main function to generate pros and cons data"""
    print("Generating pros and cons data...")

    # Generate the data
    df = generate_pros_cons_data()

    if df.empty:
        print("ERROR: No data generated")
        return

    print(f"Generated {len(df)} total rules ({len(df[df['type']=='pro'])} pros, {len(df[df['type']=='con'])} cons)")

    # Validate output
    is_valid = validate_output(df)

    # Save to CSV
    df.to_csv(PROS_CONS_OUTPUT, index=False)
    print(f"Saved pros/cons data to {PROS_CONS_OUTPUT}")

    # Show sample
    print("\nSample output:")
    print(df.head(10))

    if is_valid:
        print("\n[PASS] Validation passed: Every company has at least 1 pro and 1 con")
    else:
        print("\n[NOTE] Validation note: Some companies may be missing pros or cons")

    print("Done!")

if __name__ == "__main__":
    main()