"""
src/reports/portfolio_report.py
Portfolio Summary PDF (Day 35)
Generates reports/portfolio/portfolio_summary.pdf — one page per company in alphabetical order by ticker
Each page: company name, sector, top 6 KPIs, trend arrows (up arrow if metric improved in latest year, down arrow if declined, right arrow if flat within 2%)
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
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False
    print("WARNING: ReportLab not available. Portfolio summary will be generated as text/CSV placeholder.")

# Ensure output directory exists
os.makedirs("reports/portfolio", exist_ok=True)

def get_latest_year_data():
    """
    Get latest year financial data for all companies
    Returns DataFrame with latest year data
    """
    conn = sqlite3.connect("db/nifty100.db")

    # Get latest year
    latest_year_query = "SELECT MAX(year) as latest_year FROM financial_ratios"
    latest_year_df = pd.read_sql(latest_year_query, conn)
    latest_year = latest_year_df.iloc[0]['latest_year']

    # Get previous year for trend calculation
    prev_year_query = """
    SELECT MAX(year) as prev_year
    FROM financial_ratios
    WHERE year < ?
    """
    prev_year_df = pd.read_sql(prev_year_query, conn, params=[latest_year])
    prev_year = prev_year_df.iloc[0]['prev_year'] if not prev_year_df.isnull().values.any() else None

    # Get latest year data
    latest_query = """
    SELECT fr.company_id, fr.year,
           fr.return_on_equity_pct, fr.return_on_capital_employed_pct,
           fr.net_profit_margin_pct, fr.debt_to_equity,
           fr.revenue_cagr_5yr, fr.free_cash_flow_cr
    FROM financial_ratios fr
    WHERE fr.year = ?
    """
    latest_df = pd.read_sql(latest_query, conn, params=[latest_year])

    # Get previous year data if available for trend calculation
    if prev_year:
        prev_query = """
        SELECT fr.company_id,
               fr.return_on_equity_pct as prev_roe,
               fr.return_on_capital_employed_pct as prev_roce,
               fr.net_profit_margin_pct as prev_npm,
               fr.debt_to_equity as prev_de,
               fr.revenue_cagr_5yr as prev_revenue_cagr,
               fr.free_cash_flow_cr as prev_fcf
        FROM financial_ratios fr
        WHERE fr.year = ?
        """
        prev_df = pd.read_sql(prev_query, conn, params=[prev_year])
        # Merge with latest data
        df = latest_df.merge(prev_df, on='company_id', how='left', suffixes=('', '_prev'))
    else:
        # If no previous year data, set previous values to None
        df = latest_df.copy()
        for col in ['return_on_equity_pct', 'return_on_capital_employed_pct', 'net_profit_margin_pct',
                   'debt_to_equity', 'revenue_cagr_5yr', 'free_cash_flow_cr']:
            df[f'{col}_prev'] = None

    # Get company names and sectors
    company_query = """
    SELECT c.id as company_id, c.company_name, s.broad_sector
    FROM companies c
    LEFT JOIN sectors s ON c.id = s.company_id
    """
    company_df = pd.read_sql(company_query, conn)

    # Merge all data
    df = df.merge(company_df, on='company_id', how='left')

    conn.close()

    return df, latest_year, prev_year

def calculate_trend(current, previous):
    """
    Calculate trend direction:
    - "↑" if improved (for ROE, ROCE, NPM, Revenue CAGR, FCF: higher is better; for D/E: lower is better)
    - "↓" if declined
    - "→" if flat within 2%
    Returns arrow symbol
    """
    if current is None or previous is None or pd.isna(current) or pd.isna(previous):
        return "→"  # Default to flat if data missing

    # For D/E ratio, lower is better, so we invert the comparison
    is_de_ratio = "debt_to_equity" in str(previous).lower() or "de" in str(previous).lower()

    if is_de_ratio:
        # For D/E: lower is better
        if previous == 0:  # Avoid division by zero
            change_pct = 0 if current == 0 else float('inf')
        else:
            change_pct = ((current - previous) / previous) * 100
        # For D/E, negative change is good (improvement)
        if change_pct < -2:  # Improved (decreased by more than 2%)
            return "↑"
        elif change_pct > 2:  # Declined (increased by more than 2%)
            return "↓"
        else:
            return "→"
    else:
        # For other metrics: higher is better
        if previous == 0:  # Avoid division by zero
            change_pct = 0 if current == 0 else float('inf')
        else:
            change_pct = ((current - previous) / previous) * 100

        if change_pct > 2:  # Improved (increased by more than 2%)
            return "↑"
        elif change_pct < -2:  # Declined (decreased by more than 2%)
            return "↓"
        else:
            return "→"

def get_pros_cons_for_company(company_id):
    """
    Get pros and cons for a company from prosandcons table
    Returns tuple of (pros_list, cons_list)
    """
    conn = sqlite3.connect("db/nifty100.db")

    try:
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
        else:
            pros, cons = [], []
    except:
        pros, cons = [], []

    conn.close()
    return pros, cons

def create_portfolio_page(canvas, doc, company_data):
    """
    Create a single page for the portfolio summary
    """
    width, height = A4

    elements = []

    # Header
    company_name = company_data.get('company_name', 'N/A')
    company_id = company_data.get('company_id', 'N/A')
    header_text = f"{company_name} ({company_id})"
    header_style = ParagraphStyle(
        'CustomHeader',
        parent=getSampleStyleSheet()['Heading1'],
        fontSize=16,
        spaceAfter=20,
        alignment=TA_CENTER,
        textColor=colors.darkblue
    )
    elements.append(Paragraph(header_text, header_style))

    # Sector info
    sector = company_data.get('broad_sector', 'N/A')
    sector_text = f"Sector: {sector}"
    sector_style = ParagraphStyle(
        'CustomSector',
        parent=getSampleStyleSheet()['Normal'],
        fontSize=10,
        spaceAfter=15,
        alignment=TA_CENTER,
        textColor=colors.grey
    )
    elements.append(Paragraph(sector_text, sector_style))

    # Get trend arrows
    roe_arrow = calculate_trend(
        company_data.get('return_on_equity_pct'),
        company_data.get('return_on_equity_pct_prev')
    )
    roce_arrow = calculate_trend(
        company_data.get('return_on_capital_employed_pct'),
        company_data.get('return_on_capital_employed_pct_prev')
    )
    npm_arrow = calculate_trend(
        company_data.get('net_profit_margin_pct'),
        company_data.get('net_profit_margin_pct_prev')
    )
    de_arrow = calculate_trend(
        company_data.get('debt_to_equity'),
        company_data.get('debt_to_equity_prev')
    )
    revenue_cagr_arrow = calculate_trend(
        company_data.get('revenue_cagr_5yr'),
        company_data.get('revenue_cagr_5yr_prev')
    )
    fcf_arrow = calculate_trend(
        company_data.get('free_cash_flow_cr'),
        company_data.get('free_cash_flow_cr_prev')
    )

    # KPIs with trend arrows
    kpi_data = [
        ["Metric", "Latest Value", "Trend"],
        ["ROE (%)", f"{company_data.get('return_on_equity_pct', 0):.2f}", roe_arrow],
        ["ROCE (%)", f"{company_data.get('return_on_capital_employed_pct', 0):.2f}", roce_arrow],
        ["Net Profit Margin (%)", f"{company_data.get('net_profit_margin_pct', 0):.2f}", npm_arrow],
        ["D/E Ratio", f"{company_data.get('debt_to_equity', 0):.2f}", de_arrow],
        ["Revenue CAGR (5yr) (%)", f"{company_data.get('revenue_cagr_5yr', 0):.2f}", revenue_cagr_arrow],
        ["FCF (Latest) (Cr)", f"{company_data.get('free_cash_flow_cr', 0):.2f}", fcf_arrow]
    ]

    # Create KPI table
    kpi_table = Table(kpi_data, colWidths=[width*0.4, width*0.3, width*0.1])
    kpi_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))

    elements.append(kpi_table)
    elements.append(Spacer(1, 20))

    # Pros and Cons
    pros_list, cons_list = get_pros_cons_for_company(company_id)

    # Pros section
    if pros_list:
        pros_title = Paragraph("<b>Key Strengths:</b>", ParagraphStyle('ProsTitle', parent=getSampleStyleSheet()['Normal'], fontSize=10, textColor=colors.darkgreen))
        elements.append(pros_title)
        for pro in pros_list[:3]:  # Show top 3 pros
            pros_text = f"• {pro}"
            pros_para = Paragraph(pros_text, ParagraphStyle('ProsText', parent=getSampleStyleSheet()['Normal'], fontSize=9, leftIndent=10, textColor=colors.darkgreen))
            elements.append(pros_para)
        elements.append(Spacer(1, 10))

    # Cons section
    if cons_list:
        cons_title = Paragraph("<b>Key Concerns:</b>", ParagraphStyle('ConsTitle', parent=getSampleStyleSheet()['Normal'], fontSize=10, textColor=colors.red))
        elements.append(cons_title)
        for con in cons_list[:3]:  # Show top 3 cons
            cons_text = f"• {con}"
            cons_para = Paragraph(cons_text, ParagraphStyle('ConsText', parent=getSampleStyleSheet()['Normal'], fontSize=9, leftIndent=10, textColor=colors.red))
            elements.append(cons_para)
        elements.append(Spacer(1, 10))

    # Footer with timestamp
    footer_text = f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Latest Data: {company_data.get('year', 'N/A')}"
    footer_style = ParagraphStyle(
        'CustomFooter',
        parent=getSampleStyleSheet()['Normal'],
        fontSize=8,
        alignment=TA_CENTER,
        textColor=colors.grey
    )
    elements.append(Paragraph(footer_text, footer_style))

    return elements

def main():
    """Main function to generate portfolio summary PDF"""
    print("Starting Portfolio Summary PDF Generation (Day 35)...")

    # Get latest year data
    df, latest_year, prev_year = get_latest_year_data()

    if df.empty:
        print("ERROR: No data found for portfolio summary")
        return

    print(f"Latest year: {latest_year}")
    print(f"Previous year for trend: {prev_year if prev_year else 'None (no trend data)'}")
    print(f"Processing {len(df)} companies...")

    if not REPORTLAB_AVAILABLE:
        # Generate placeholder text/CSV file
        portfolio_file = os.path.join("reports/portfolio", "portfolio_summary.txt")
        with open(portfolio_file, 'w', encoding='utf-8') as f:
            f.write("PORTFOLIO SUMMARY\n")
            f.write("="*50 + "\n\n")
            f.write(f"Latest Year: {latest_year}\n")
            f.write(f"Previous Year: {prev_year if prev_year else 'None'}\n")
            f.write(f"Total Companies: {len(df)}\n\n")

            # Sort by company_id for consistent ordering
            df_sorted = df.sort_values('company_id')

            for _, row in df_sorted.iterrows():
                f.write(f"Company: {row.get('company_name', 'N/A')} ({row.get('company_id', 'N/A')})\n")
                f.write(f"Sector: {row.get('broad_sector', 'N/A')}\n")
                f.write("-"*30 + "\n")
                f.write(f"  ROE: {row.get('return_on_equity_pct', 0):.2f}%\n")
                f.write(f"  ROCE: {row.get('return_on_capital_employed_pct', 0):.2f}%\n")
                f.write(f"  Net Profit Margin: {row.get('net_profit_margin_pct', 0):.2f}%\n")
                f.write(f"  D/E Ratio: {row.get('debt_to_equity', 0):.2f}\n")
                f.write(f"  Revenue CAGR (5yr): {row.get('revenue_cagr_5yr', 0):.2f}%\n")
                f.write(f"  FCF (Latest): {row.get('free_cash_flow_cr', 0):.2f} Cr\n")

                pros_list, cons_list = get_pros_cons_for_company(row.get('company_id', ''))
                if pros_list:
                    f.write("  Pros: " + "; ".join(pros_list[:2]) + "\n")
                if cons_list:
                    f.write("  Cons: " + "; ".join(cons_list[:2]) + "\n")
                f.write("\n")

        print(f"Generated placeholder portfolio summary: {portfolio_file}")
        print("Done!")
        return

    # Generate actual PDF with ReportLab
    portfolio_file = os.path.join("reports/portfolio", "portfolio_summary.pdf")

    try:
        doc = SimpleDocTemplate(portfolio_file, pagesize=A4,
                              rightMargin=30, leftMargin=30,
                              topMargin=30, bottomMargin=18)

        # Build the PDF
        story = []

        # Add title page
        title_style = ParagraphStyle(
            'TitleStyle',
            parent=getSampleStyleSheet()['Title'],
            fontSize=20,
            spaceAfter=30,
            alignment=TA_CENTER
        )
        story.append(Paragraph("Nifty 100 Financial Intelligence Platform", title_style))
        story.append(Paragraph("Portfolio Summary Report", getSampleStyleSheet()['Heading2']))
        story.append(Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", getSampleStyleSheet()['Normal']))
        story.append(Paragraph(f"Latest Data: {latest_year}", getSampleStyleSheet()['Normal']))
        story.append(Spacer(1, 20))
        story.append(Paragraph(f"Contains summary for {len(df)} companies in alphabetical order by ticker", getSampleStyleSheet()['Normal']))
        story.append(PageBreak())

        # Sort companies alphabetically by ticker for consistent ordering
        df_sorted = df.sort_values('company_id')

        # Add a page for each company
        for idx, (_, company_data) in enumerate(df_sorted.iterrows()):
            if idx > 0:  # Add page break except for first page
                story.append(PageBreak())

            # Create page content
            page_elements = create_portfolio_page(None, doc, company_data)
            story.extend(page_elements)

        # Build PDF
        doc.build(story)

        print(f"Generated portfolio summary PDF: {portfolio_file}")
        print(f"Contains {len(df_sorted)} company pages")

    except Exception as e:
        print(f"Error generating portfolio summary PDF: {e}")
        return

    print("\n" + "="*50)
    print("PORTFOLIO SUMMARY GENERATION COMPLETE")
    print("="*50)
    print(f"Output file: {portfolio_file}")
    print(f"Companies processed: {len(df)}")
    print(f"Latest year data: {latest_year}")
    print(f"Trend analysis: {'Available' if prev_year else 'Not available (single year data)'}")
    print("\nDone!")

if __name__ == "__main__":
    main()