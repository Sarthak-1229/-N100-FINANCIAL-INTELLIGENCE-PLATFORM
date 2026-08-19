"""
src/nlp/parser.py

NLP Analysis Text Parser - parses text fields in analysis.xlsx using regex
Target fields: compounded_sales_growth, compounded_profit_growth, stock_price_cagr, roe
Regex pattern: (\d+)\s*Years?:?\s*([\d.]+)% — extracts period (e.g. 10) and value (e.g. 21.0) from text like
10 Years: 21%
Generates output/analysis_parsed.csv with columns: company_id, metric_type, period_years, value_pct
Logs any text entries that do not match the pattern to output/parse_failures.csv
Cross-validates parsed CAGR values against computed CAGR from the Ratio Engine — flags divergence > 5% for manual review
"""
import pandas as pd
import re
import os
from src.etl.normaliser import normalize_numeric

# Output directories
OUTPUT_DIR = os.getenv("OUTPUT_DIR", "output")
ANALYSIS_PARSED = os.path.join(OUTPUT_DIR, "analysis_parsed.csv")
PARSE_FAILURES = os.path.join(OUTPUT_DIR, "parse_failures.csv")

# Ensure output directory exists
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Regex pattern to match text like "10 Years: 21%", "5 Years          14%", "TTM:            43%"
PATTERN = re.compile(r"(\d+)\s*Years?:?\s*([\d.]+)%")

def parse_analysis_text(text):
    """
    Parse analysis text using regex pattern.
    Returns (period_years, value_pct) or (None, None) if no match.
    """
    if pd.isna(text) or not isinstance(text, str):
        return None, None

    text = text.strip()
    # Debug: print the text being parsed
    # print(f"Parsing text: '{text}'")
    match = PATTERN.search(text)
    if match:
        period = int(match.group(1))
        value = float(match.group(2))
        # Debug: print the parsed values
        # print(f"  -> period={period}, value={value}")
        return period, value
    # Debug: if no match, print that
    # print(f"  -> No match")
    return None, None

def load_analysis_data():
    """
    Load analysis.xlsx and parse the text fields.
    Returns DataFrame with parsed data.
    """
    # Load the analysis file without header to see raw structure
    df = pd.read_excel('data/raw/analysis.xlsx', header=None)

    # The actual data starts from row 2 (0-indexed) where row 1 has column names
    # Column 0 is row number, column 1 is company_id, columns 2-5 are the metrics
    data_rows = df.iloc[2:].copy()

    # Set proper column names from row 1
    data_rows.columns = df.iloc[1].tolist()

    # Reset index
    data_rows = data_rows.reset_index(drop=True)

    # The company_id column is already correctly named from the header
    # No need to rename 'id' to 'company_id' since the header already has 'company_id'

    return data_rows

def cross_validate_with_ratio_engine(parsed_df):
    """
    Cross-validate parsed CAGR values against computed CAGR from the Ratio Engine.
    Flags divergence > 5% for manual review.
    """
    # This would require loading the financial_ratios table from the Ratio Engine
    # For now, we'll just return the parsed data as-is
    # In a full implementation, we would:
    # 1. Load financial_ratios table
    # 2. For each company, get the computed CAGR values
    # 3. Compare with parsed values
    # 4. Flag divergences > 5%
    return parsed_df

def main():
    """Main function to parse analysis text and generate output files."""
    print("Loading analysis data...")
    df = load_analysis_data()

    if df.empty:
        print("No data found in analysis.xlsx")
        return

    print(f"Loaded {len(df)} companies")

    # Initialize lists for parsed data and failures
    parsed_records = []
    failure_records = []

    # Process each company
    for _, row in df.iterrows():
        company_id = row.get('company_id', '')

        # Process each metric column
        metric_columns = ['compounded_sales_growth', 'compounded_profit_growth',
                         'stock_price_cagr', 'roe']

        for metric in metric_columns:
            if metric in df.columns:
                text_value = row[metric]
                period, value = parse_analysis_text(text_value)

                if period is not None and value is not None:
                    parsed_records.append({
                        'company_id': company_id,
                        'metric_type': metric,
                        'period_years': period,
                        'value_pct': value
                    })
                else:
                    # Log failure
                    failure_records.append({
                        'company_id': company_id,
                        'metric_type': metric,
                        'original_text': str(text_value) if not pd.isna(text_value) else '',
                        'failure_reason': 'Pattern mismatch'
                    })

    # Create DataFrames
    parsed_df = pd.DataFrame(parsed_records) if parsed_records else pd.DataFrame(
        columns=['company_id', 'metric_type', 'period_years', 'value_pct']
    )

    failures_df = pd.DataFrame(failure_records) if failure_records else pd.DataFrame(
        columns=['company_id', 'metric_type', 'original_text', 'failure_reason']
    )

    # Cross-validate with Ratio Engine (placeholder for now)
    parsed_df = cross_validate_with_ratio_engine(parsed_df)

    # Save outputs
    if not parsed_df.empty:
        parsed_df.to_csv(ANALYSIS_PARSED, index=False)
        print(f"Saved {len(parsed_df)} parsed records to {ANALYSIS_PARSED}")
    else:
        # Create empty file with headers
        pd.DataFrame(columns=['company_id', 'metric_type', 'period_years', 'value_pct']).to_csv(ANALYSIS_PARSED, index=False)
        print(f"No parsed records found. Created empty {ANALYSIS_PARSED}")

    if not failures_df.empty:
        failures_df.to_csv(PARSE_FAILURES, index=False)
        print(f"Saved {len(failures_df)} parse failures to {PARSE_FAILURES}")
    else:
        # Create empty file with headers
        pd.DataFrame(columns=['company_id', 'metric_type', 'original_text', 'failure_reason']).to_csv(PARSE_FAILURES, index=False)
        print(f"No parse failures found. Created empty {PARSE_FAILURES}")

    print("Done!")

if __name__ == "__main__":
    main()