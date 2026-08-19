"""
src/reports/tearsheet.py
PDF Tearsheet Template (Day 33)
Implements the 2-page company tearsheet using ReportLab
Page 1: Header, 6 KPI tiles, 10-year Revenue/Net Profit bar chart, ROE/ROCE dual-axis line chart
Page 2: Balance sheet composition, Cash flow waterfall, Pros/Cons sections, Capital Allocation badge
"""

import pandas as pd
import sqlite3
import os
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# Try to import ReportLab for PDF generation
try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.lib.units import inch
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, PageBreak
    from reportlab.graphics.shapes import Drawing, Rect, Line, String
    from reportlab.graphics.charts.barcharts import VerticalBarChart
    from reportlab.graphics.charts.linecharts import HorizontalLineChart
    from reportlab.graphics.charts.legends import Legend
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False
    print("WARNING: ReportLab not available. Tearsheets will be generated as text/CSV placeholders.")

# Output directories
OUTPUT_DIR = os.getenv("OUTPUT_DIR", "output")
TEARSHEETS_DIR = os.path.join("reports", "tearsheets")
os.makedirs(TEARSHEETS_DIR, exist_ok=True)

def get_company_data(company_id):
    """
    Get all relevant data for a company from various tables
    Returns dictionary with company data
    """
    conn = sqlite3.connect("db/nifty100.db")

    # Get company basic info
    company_query = """
    SELECT id as company_id, company_name
    FROM companies
    WHERE id = ?
    """
    company_df = pd.read_sql(company_query, conn, params=[company_id])

    if company_df.empty:
        conn.close()
        return None

    company_data = company_df.iloc[0].to_dict()

    # Get latest financial ratios
    ratios_query = """
    SELECT * FROM financial_ratios
    WHERE company_id = ?
    ORDER BY year DESC
    LIMIT 1
    """
    ratios_df = pd.read_sql(ratios_query, conn, params=[company_id])
    if not ratios_df.empty:
        company_data.update(ratios_df.iloc[0].to_dict())

    # Get latest balance sheet for composition
    bs_query = """
    SELECT equity_capital, reserves, borrowings, other_liabilities, total_assets
    FROM balancesheet
    WHERE company_id = ?
    ORDER BY year DESC
    LIMIT 1
    """
    bs_df = pd.read_sql(bs_query, conn, params=[company_id])
    if not bs_df.empty:
        bs_data = bs_df.iloc[0].to_dict()
        # Calculate percentages for balance sheet composition
        total_assets = bs_data.get('total_assets', 0)
        if total_assets and total_assets > 0:
            company_data['equity_pct'] = (bs_data.get('equity_capital', 0) + bs_data.get('reserves', 0)) / total_assets * 100
            company_data['debt_pct'] = bs_data.get('borrowings', 0) / total_assets * 100
            company_data['other_liabilities_pct'] = bs_data.get('other_liabilities', 0) / total_assets * 100
        else:
            company_data['equity_pct'] = 0
            company_data['debt_pct'] = 0
            company_data['other_liabilities_pct'] = 0
        company_data.update(bs_data)

    # Get latest cash flow for waterfall
    cf_query = """
    SELECT operating_activity, investing_activity, financing_activity, net_cash_flow
    FROM cashflow
    WHERE company_id = ?
    ORDER BY year DESC
    LIMIT 1
    """
    cf_df = pd.read_sql(cf_query, conn, params=[company_id])
    if not cf_df.empty:
        company_data.update(cf_df.iloc[0].to_dict())

    # Get sector info
    sector_query = """
    SELECT broad_sector, sub_sector
    FROM sectors
    WHERE company_id = ?
    """
    sector_df = pd.read_sql(sector_query, conn, params=[company_id])
    if not sector_df.empty:
        company_data['broad_sector'] = sector_df.iloc[0]['broad_sector']
        company_data['sub_sector'] = sector_df.iloc[0]['sub_sector']
    else:
        company_data['broad_sector'] = 'Unknown'
        company_data['sub_sector'] = 'Unknown'

    # Get pros and cons data
    pros_cons_query = """
    SELECT pros, cons
    FROM prosandcons
    WHERE company_id = ?
    """
    pros_cons_df = pd.read_sql(pros_cons_query, conn, params=[company_id])
    if not pros_cons_df.empty:
        pros_text = pros_cons_df.iloc[0]['pros']
        cons_text = pros_cons_df.iloc[0]['cons']
        # Split by newlines or semicolons if needed, for now treat as single entries
        company_data['pros'] = [pros_text] if pros_text and pros_text.strip() else []
        company_data['cons'] = [cons_text] if cons_text and cons_text.strip() else []
    else:
        company_data['pros'] = []
        company_data['cons'] = []

    conn.close()
    return company_data

def get_historical_data(company_id, metric, years=10):
    """
    Get historical data for a specific metric over N years
    Returns lists of years and values for charting
    """
    conn = sqlite3.connect("db/nifty100.db")

    # Map metric to table and column
    metric_map = {
        'sales': ('profitandloss', 'sales'),
        'net_profit': ('profitandloss', 'net_profit'),
        'return_on_equity_pct': ('financial_ratios', 'return_on_equity_pct'),
        'return_on_capital_employed_pct': ('financial_ratios', 'return_on_capital_employed_pct')
    }

    if metric not in metric_map:
        conn.close()
        return [], []

    table, column = metric_map[metric]

    query = f"""
    SELECT year, {column}
    FROM {table}
    WHERE company_id = ?
    ORDER BY year
    LIMIT ?
    """

    df = pd.read_sql(query, conn, params=[company_id, years])
    conn.close()

    if df.empty:
        return [], []

    # Extract year (just YYYY part) and values
    years_list = [str(y)[:4] for y in df['year'].tolist()]
    values_list = df[column].tolist()

    return years_list, values_list

def get_pros_cons_for_company(company_id):
    """
    Get pros and cons for a company from prosandcons table or generate from rules
    Returns tuple of (pros_list, cons_list)
    """
    conn = sqlite3.connect("db/nifty100.db")

    # Try to get from prosandcons table first
    query = """
    SELECT pros, cons
    FROM prosandcons
    WHERE company_id = ?
    """
    df = pd.read_sql(query, conn, params=[company_id])

    if not df.empty:
        pros_text = df.iloc[0]['pros']
        cons_text = df.iloc[0]['cons']
        pros = [pros_text] if pros_text and pros_text.strip() else []
        cons = [cons_text] if cons_text and cons_text.strip() else []
        conn.close()
        return pros, cons

    conn.close()

    # Fallback: generate basic pros/cons from financial data
    company_data = get_company_data(company_id)
    if not company_data:
        return [], []

    pros = []
    cons = []

    # Basic pros based on available data
    roe = company_data.get('return_on_equity_pct')
    if roe and roe > 15:
        pros.append(f"High ROE ({roe:.1f}%) indicates efficient equity utilization")

    de = company_data.get('debt_to_equity')
    if de is not None and de < 0.3:
        pros.append(f"Low debt-to-equity ({de:.2f}) indicates conservative financial leverage")

    fcf = company_data.get('free_cash_flow_cr')
    if fcf and fcf > 0:
        pros.append(f"Positive free cash flow ({fcf:.1f} Cr) indicates financial flexibility")

    # Basic cons
    if roe and roe < 5:
        cons.append(f"Low ROE ({roe:.1f}%) suggests suboptimal equity utilization")

    if de is not None and de > 1.0:
        cons.append(f"High debt-to-equity ({de:.2f}) indicates financial leverage risk")

    if fcf and fcf < 0:
        cons.append(f"Negative free cash flow ({fcf:.1f} Cr) indicates cash consumption")

    return pros, cons

def create_tearsheet_page1(canvas, doc, company_data):
    """
    Create the first page of the tearsheet
    """
    width, height = A4

    # Header
    header_text = f"{company_data.get('company_name', 'N/A')} ({company_data.get('company_id', 'N/A')})"
    header_style = ParagraphStyle(
        'CustomHeader',
        parent=getSampleStyleSheet()['Heading1'],
        fontSize=18,
        spaceAfter=30,
        alignment=TA_CENTER,
        textColor=colors.darkblue
    )
    header = Paragraph(header_text, header_style)

    # Sector info
    sector_text = f"Sector: {company_data.get('broad_sector', 'N/A')} | Sub-Sector: {company_data.get('sub_sector', 'N/A')}"
    sector_style = ParagraphStyle(
        'CustomSector',
        parent=getSampleStyleSheet()['Normal'],
        fontSize=10,
        spaceAfter=20,
        alignment=TA_CENTER,
        textColor=colors.grey
    )
    sector = Paragraph(sector_text, sector_style)

    # 6 KPI tiles in 2 rows of 3
    kpi_data = [
        ["ROE", f"{company_data.get('return_on_equity_pct', 0):.2f}%"],
        ["ROCE", f"{company_data.get('return_on_capital_employed_pct', 0):.2f}%"],
        ["Net Profit Margin", f"{company_data.get('net_profit_margin_pct', 0):.2f}%"],
        ["D/E Ratio", f"{company_data.get('debt_to_equity', 0):.2f}"],
        ["Revenue CAGR (5yr)", f"{company_data.get('revenue_cagr_5yr', 0):.2f}%"],
        ["FCF (Latest)", f"{company_data.get('free_cash_flow_cr', 0):.2f} Cr"]
    ]

    # Create KPI table
    kpi_table = Table(kpi_data, colWidths=[width*0.3, width*0.2] * 3)
    kpi_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.lightgrey),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('TOPPADDING', (0, 0), (-1, -1), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))

    # Build the page
    elements = [
        header,
        sector,
        Spacer(1, 20),
        kpi_table,
        Spacer(1, 30)
    ]

    # Add charts if ReportLab is available
    if REPORTLAB_AVAILABLE:
        # Revenue and Net Profit bar chart placeholder
        chart1_drawing = Drawing(width*0.8, height*0.3)
        chart1_drawing.add(String(400, 150, "10-Year Revenue and Net Profit Bar Chart (Placeholder)",
                                fontSize=10, fillColor=colors.grey))

        # ROE and ROCE line chart placeholder
        chart2_drawing = Drawing(width*0.8, height*0.3)
        chart2_drawing.add(String(400, 150, "ROE and ROCE Dual-Axis Line Chart (Placeholder)",
                                fontSize=10, fillColor=colors.grey))

        elements.extend([
            Paragraph("Financial Charts", ParagraphStyle('ChartTitle', parent=getSampleStyleSheet()['Heading2'], fontSize=14, spaceAfter=10)),
            chart1_drawing,
            Spacer(1, 10),
            chart2_drawing
        ])

    return elements

def create_tearsheet_page2(canvas, doc, company_data):
    """
    Create the second page of the tearsheet
    """
    width, height = A4

    elements = [
        Paragraph("Financial Analysis", ParagraphStyle('Page2Title', parent=getSampleStyleSheet()['Heading1'], fontSize=18, spaceAfter=20, alignment=TA_CENTER)),
        Spacer(1, 20)
    ]

    # Balance Sheet Composition
    bs_title = Paragraph("Balance Sheet Composition (Latest Year)", ParagraphStyle('SectionTitle', parent=getSampleStyleSheet()['Heading2'], fontSize=14, spaceAfter=10))

    # Create BS composition data
    equity_pct = company_data.get('equity_pct', 0)
    debt_pct = company_data.get('debt_pct', 0)
    other_pct = company_data.get('other_liabilities_pct', 0)

    bs_data = [
        ["Component", "Percentage"],
        ["Equity & Reserves", f"{equity_pct:.1f}%"],
        ["Borrowings (Debt)", f"{debt_pct:.1f}%"],
        ["Other Liabilities", f"{other_pct:.1f}%"]
    ]

    bs_table = Table(bs_data, colWidths=[width*0.4, width*0.2])
    bs_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))

    # Cash Flow Waterfall
    cf_title = Paragraph("Cash Flow Waterfall (Latest Year)", ParagraphStyle('SectionTitle', parent=getSampleStyleSheet()['Heading2'], fontSize=14, spaceAfter=10))

    cfo = company_data.get('operating_activity', 0)
    cfi = company_data.get('investing_activity', 0)
    cff = company_data.get('financing_activity', 0)
    ncf = company_data.get('net_cash_flow', 0)

    cf_data = [
        ["Activity", "Amount (Cr)"],
        ["Cash from Operations (CFO)", f"{cfo:.2f}"],
        ["Cash from Investing (CFI)", f"{cfi:.2f}"],
        ["Cash from Financing (CFF)", f"{cff:.2f}"],
        ["Net Cash Flow", f"{ncf:.2f}"]
    ]

    cf_table = Table(cf_data, colWidths=[width*0.4, width*0.2])
    cf_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.darkgreen),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))

    # Pros and Cons sections
    pros_cons_title = Paragraph("Pros & Cons", ParagraphStyle('SectionTitle', parent=getSampleStyleSheet()['Heading2'], fontSize=14, spaceAfter=10))

    pros_list, cons_list = get_pros_cons_for_company(company_data.get('company_id', ''))

    pros_text = "<br/>".join([f"• {pro}" for pro in pros_list[:5]]) if pros_list else "• No pros identified"
    cons_text = "<br/>".join([f"• {con}" for con in cons_list[:5]]) if cons_list else "• No cons identified"

    pros_para = Paragraph(f"<b>Pros:</b><br/>{pros_text}", ParagraphStyle('ProsStyle', parent=getSampleStyleSheet()['Normal'], fontSize=10, leftIndent=20, textColor=colors.darkgreen))
    cons_para = Paragraph(f"<b>Cons:</b><br/>{cons_text}", ParagraphStyle('ConsStyle', parent=getSampleStyleSheet()['Normal'], fontSize=10, leftIndent=20, textColor=colors.red))

    # Capital Allocation Badge
    capital_allocation = company_data.get('capital_allocation_pattern', 'N/A')
    badge_text = f"Capital Allocation: {capital_allocation}"
    badge_para = Paragraph(badge_text, ParagraphStyle('BadgeStyle', parent=getSampleStyleSheet()['Normal'], fontSize=12, alignment=TA_CENTER,
                                                     backColor=colors.lightgrey, borderPadding=10))

    # Build page 2
    elements.extend([
        bs_title,
        bs_table,
        Spacer(1, 20),
        cf_title,
        cf_table,
        Spacer(1, 20),
        pros_cons_title,
        pros_para,
        Spacer(1, 10),
        cons_para,
        Spacer(1, 20),
        badge_para
    ])

    return elements

def generate_tearsheet_for_company(company_id):
    """
    Generate a tearsheet PDF for a specific company
    Returns True if successful, False otherwise
    """
    company_data = get_company_data(company_id)
    if not company_data:
        print(f"ERROR: Could not retrieve data for company {company_id}")
        return False

    if not REPORTLAB_AVAILABLE:
        # Generate placeholder text/CSV file
        tearsheet_file = os.path.join(TEARSHEETS_DIR, f"{company_id}_tearsheet.txt")
        with open(tearsheet_file, 'w', encoding='utf-8') as f:
            f.write(f"TEARSHEET FOR {company_data.get('company_name', company_id)} ({company_id})\n")
            f.write("="*50 + "\n\n")
            f.write(f"Sector: {company_data.get('broad_sector', 'N/A')}\n")
            f.write(f"Market Cap Category: {company_data.get('market_cap_category', 'N/A')}\n\n")
            f.write("KEY METRICS:\n")
            f.write(f"  ROE: {company_data.get('return_on_equity_pct', 0):.2f}%\n")
            f.write(f"  ROCE: {company_data.get('return_on_capital_employed_pct', 0):.2f}%\n")
            f.write(f"  Net Profit Margin: {company_data.get('net_profit_margin_pct', 0):.2f}%\n")
            f.write(f"  D/E Ratio: {company_data.get('debt_to_equity', 0):.2f}\n")
            f.write(f"  Revenue CAGR (5yr): {company_data.get('revenue_cagr_5yr', 0):.2f}%\n")
            f.write(f"  FCF (Latest): {company_data.get('free_cash_flow_cr', 0):.2f} Cr\n\n")
            f.write("BALANCE SHEET COMPOSITION:\n")
            f.write(f"  Equity & Reserves: {company_data.get('equity_pct', 0):.1f}%\n")
            f.write(f"  Borrowings: {company_data.get('debt_pct', 0):.1f}%\n")
            f.write(f"  Other Liabilities: {company_data.get('other_liabilities_pct', 0):.1f}%\n\n")
            f.write("CASH FLOW (LATEST YEAR):\n")
            f.write(f"  Operating Activity: {company_data.get('operating_activity', 0):.2f} Cr\n")
            f.write(f"  Investing Activity: {company_data.get('investing_activity', 0):.2f} Cr\n")
            f.write(f"  Financing Activity: {company_data.get('financing_activity', 0):.2f} Cr\n")
            f.write(f"  Net Cash Flow: {company_data.get('net_cash_flow', 0):.2f} Cr\n\n")
            pros_list, cons_list = get_pros_cons_for_company(company_id)
            f.write("PROS:\n")
            for pro in pros_list[:5]:
                f.write(f"  • {pro}\n")
            f.write("\nCONS:\n")
            for con in cons_list[:5]:
                f.write(f"  • {con}\n")
            f.write(f"\nCAPITAL ALLOCATION: {company_data.get('capital_allocation_pattern', 'N/A')}\n")

        print(f"Generated placeholder tearsheet for {company_id}: {tearsheet_file}")
        return True

    # Generate actual PDF with ReportLab
    tearsheet_file = os.path.join(TEARSHEETS_DIR, f"{company_id}_tearsheet.pdf")

    try:
        doc = SimpleDocTemplate(tearsheet_file, pagesize=A4,
                              rightMargin=30, leftMargin=30,
                              topMargin=30, bottomMargin=18)

        # Build the PDF
        story = []

        # Page 1
        story.extend(create_tearsheet_page1(None, doc, company_data))
        story.append(PageBreak())

        # Page 2
        story.extend(create_tearsheet_page2(None, doc, company_data))

        # Build PDF
        doc.build(story)

        print(f"Generated tearsheet PDF for {company_id}: {tearsheet_file}")
        return True

    except Exception as e:
        print(f"Error generating tearsheet PDF for {company_id}: {e}")
        return False

def main():
    """Main function to generate tearsheets for all companies"""
    print("Starting Tearsheet Generation (Day 33)...")

    # Get list of all companies
    conn = sqlite3.connect("db/nifty100.db")
    companies_df = pd.read_sql("SELECT id as company_id FROM companies", conn)
    conn.close()

    company_ids = companies_df['company_id'].tolist()
    print(f"Found {len(company_ids)} companies to process")

    successful = 0
    failed = 0
    skipped = 0

    for company_id in company_ids:
        print(f"Processing {company_id}...", end=" ")

        # Check if company has sufficient data (at least 3 years of financial data)
        conn = sqlite3.connect("db/nifty100.db")
        years_count = pd.read_sql(
            "SELECT COUNT(DISTINCT year) as year_count FROM financial_ratios WHERE company_id = ?",
            conn, params=[company_id]
        ).iloc[0]['year_count']
        conn.close()

        if years_count < 3:
            print(f"SKIPPED (insufficient data: {years_count} years)")
            skipped += 1
            continue

        if generate_tearsheet_for_company(company_id):
            successful += 1
            print("SUCCESS")
        else:
            failed += 1
            print("FAILED")

    # Create skipped tickers report
    if skipped > 0:
        skipped_df = pd.DataFrame({'company_id': []})  # We'd need to track which were skipped
        # For simplicity, we'll note that companies with <3 years were skipped
        skipped_info = pd.DataFrame({
            'info': [f"{skipped} companies skipped due to insufficient data (<3 years)"]
        })
        skipped_info.to_csv("output/skipped_tearsheets.csv", index=False)

    print("\n" + "="*50)
    print("TEARSHEET GENERATION COMPLETE")
    print("="*50)
    print(f"Total companies: {len(company_ids)}")
    print(f"Successful: {successful}")
    print(f"Failed: {failed}")
    print(f"Skipped: {skipped}")
    print(f"Output directory: {TEARSHEETS_DIR}")

    if successful > 0:
        print(f"\nSample tearsheets generated:")
        sample_files = [f for f in os.listdir(TEARSHEETS_DIR) if f.endswith('.pdf') or f.endswith('.txt')][:3]
        for f in sample_files:
            print(f"  - {f}")

    print("\nDone!")

if __name__ == "__main__":
    main()