# Nifty 100 Financial Intelligence Platform

A full-stack financial analytics platform covering 92 Nifty 100 companies.
Built over 45 days in 6 sprints. Each sprint's tasks are completed.

All monetary values are in Indian Rupees — Crore (Cr) unless stated otherwise.

## Table of Contents
- [Setup](#setup)
- [Project Structure](#project-structure)
- [Sprints Overview](#sprints-overview)
- [How to Run](#how-to-run)
- [Testing](#testing)
- [Data Quality](#data-quality)
- [Key Features](#key-features)
- [API Documentation](#api-documentation)
- [Dashboard](#dashboard)
- [Reports Generation](#reports-generation)
- [Project Status](#project-status)

## Setup
```bash
# Clone repository (if not already done)
git clone <repository-url>
cd Nifty100_Financial_Intelligence_Platform

# Create and activate virtual environment
python -m venv venv
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy environment example
cp .env.example .env

# Load initial data ( builds db/nifty100.db from data/raw/*.xlsx )
python -m src.etl.loader

# Verify data load
pytest tests/etl/ -v
```

## Project Structure
```
data/raw/               12 source Excel files (READ ONLY, never modify)
db/
  schema.sql            SQLite schema (12 tables)
  nifty100.db           generated database (gitignored)
src/
  etl/
    loader.py           ETL pipeline entry point: python -m src.etl.loader
    normaliser.py       normalize_year(), normalize_ticker(), normalize_numeric()
    validator.py        DQ-01..DQ-16 rule functions
  analytics/
    ratios.py           Profitability, leverage, efficiency ratios engine
    cagr.py             CAGR calculations with special cases
    cashflow_kpis.py    Cash flow intelligence module (Sprint 5)
  screener/             Financial screener with presets and custom filters (Sprint 3)
  dashboard/            Streamlit dashboard application (Sprint 4)
  reports/              PDF and report generation (tearsheets, sector reports, portfolio) (Sprint 5)
  nlp/                  Natural language processing for auto pros/cons generation (Sprint 5)
  api/                  FastAPI REST API application (Sprint 6)
tests/
  etl/                  Sprint 1 tests (101 passing)
  kpi/                  Sprint 2 tests (KPIs and CAGR)
  screener/             Sprint 3 tests
  dashboard/            Sprint 4 tests (if any)
  reports/              Sprint 5 tests
  api/                  Sprint 6 tests (health, companies, screener, sectors)
output/                 Generated CSV/Excel reports (gitignored)
logs/                   Runtime logs (gitignored)
notebooks/              SQL queries and exploration files
docs/                   Documentation (analyst guide, etc.)
requirements.txt        Python dependencies
SPRINT1_RETROSPECTIVE.md Sprint 1 retrospective
```

## Sprints Overview

### Sprint 1 — Data Foundation (Days 1-7)
- Loaded 92 companies from 12 Excel files into SQLite database
- Implemented ETL pipeline with data validation (16 DQ rules)
- Created 12-table schema: companies, profitandloss, balancesheet, cashflow, analysis, documents, prosandcons, sectors, stock_prices, market_cap, financial_ratios, peer_groups
- Established foreign key relationships
- **Exit criteria**: 92 companies loaded, FK integrity passing, 101 unit tests passing

### Sprint 2 — Financial Ratio Engine (Days 8-14)
- Calculated 27+ key performance indicators (KPIs)
- Implemented ratios: NPM, OPM, ROE, ROCE, D/E, ICR, Asset Turnover, etc.
- Handled edge cases: division by zero, negative values, missing data
- Added special handling for banks/NBFCs (use ROA instead of ROE for ROCE)
- Populated financial_ratios table with historical data
- **Exit criteria**: 1000+ rows in financial_ratios, KPI tests passing, ratio_edge_cases.log created, cross-validation within ±2%

### Sprint 3 — Financial Screener (Days 15-21)
- Built financial screening engine with predefined presets
- Created 6 screener presets for different investment strategies:
  1. Growth Investor
  2. Value Investor
  3. Dividend Yield
  4. Quality at Reasonable Price
  5. Turnaround Opportunity
  6. Financial Stability
- Implemented custom filter support via POST endpoint
- Added peer percentile engine for relative performance comparison
- **Exit criteria**: 6 preset screeners produce output, peer_percentiles table built, screener tests passing

### Sprint 4 — Streamlit Dashboard (Days 22-28)
- Developed interactive dashboard with 8 screens:
  1. Company Overview
  2. Financial Statements
  3. Ratio Analysis
  4. Cash Flow Analysis
  5. Screening Tools
  6. Peer Comparison
  7. Sector Analysis
  8. Visualization Module
- Integrated with backend API for live data
- **Exit criteria**: streamlit run src/dashboard/app.py launches without error, all 8 screens render

### Sprint 5 — Reports Generation & NLP (Days 29-35)
- Generated auto pros/cons for all companies using NLP rules
- Created Cash Flow Intelligence module (CFO quality, CapEx intensity, capital allocation patterns)
- Generated 92 company tearsheet PDFs (2 pages each)
- Generated 11 sector PDF reports
- Generated portfolio summary PDF
- **Exit criteria**: 
  - pros_cons_generated.csv has ≥1 pro and ≥1 con for every company
  - All 92 tearsheets exist and are ≥30 KB each
  - cashflow_intelligence.xlsx has 92 rows with required columns
  - Sprint 5 review completed

### Sprint 6 — REST API (Days 36-45)
- Built comprehensive FastAPI REST API
- Implemented endpoints for:
  - Companies (list, profile, financial statements, ratios, tearsheet)
  - Screener (presets, custom filters, preset execution)
  - Sectors (list, companies in sector)
  - Health check
- Added CORS middleware, request logging, proper error handling
- Created interactive API documentation (Swagger UI)
- **Exit criteria**: All API endpoints return correct data, 60+ total tests passing

## How to Run

### 1. Start the API Server
```bash
# From project root, with venv activated
uvicorn src.api.main:app --port 8000
```
API will be available at http://localhost:8000
Interactive docs at http://localhost:8000/docs

### 2. Start the Dashboard
```bash
# In a separate terminal, with venv activated
streamlit run src/dashboard/app.py
```
Dashboard will be available at http://localhost:8501

### 3. Generate Reports
```bash
# Tearsheets (company PDF reports)
python -m src.reports.tearsheet

# Sector reports
python -m src.reports.sector_report

# Portfolio summary PDF
python -m src.reports.portfolio_report

# Pros/cons generation
python -m src.nlp.pros_cons_generator

# Cash flow intelligence
python -m src.analytics.cashflow_kpis
```

### 4. Run ETL and KPI Calculation
```bash
# (Re)load data from Excel sources
python -m src.etl.loader

# Calculate all financial ratios
python -m src.analytics.ratios

# Calculate CAGR values
python -m src.analytics.cagr
```

## Testing
Run the full test suite:
```bash
pytest tests/ -v
```

Specific test suites:
```bash
# ETL tests (Sprint 1)
pytest tests/etl/ -v

# KPI tests (Sprint 2)
pytest tests/kpi/ -v

# Screener tests (Sprint 3)
pytest tests/screener/ -v

# API tests (Sprint 6)
pytest tests/api/ -v

# Data quality tests
pytest tests/dq/ -v
```

As of last verification: **356 tests passing**

## Data Quality
The platform enforces 16 data quality rules (DQ-01 through DQ-16):
- DQ-01: Company primary key uniqueness
- DQ-02: Annual primary key (company + year) uniqueness
- DQ-03: Foreign key integrity (no orphaned records)
- DQ-04: Balance sheet validation (Assets = Liabilities + Equity within tolerance)
- DQ-05: Operating profit margin consistency (warning only)
- DQ-06: ... (etc.)

Critical DQ failures cause records to be rejected during ETL.
All DQ violations are logged to output/ directory for review.

## Key Features

### Financial Ratios Engine
- 27+ KPIs calculated with proper edge case handling
- Special treatment for financial sectors (banks/NBFCs)
- Time-series storage for historical analysis

### Financial Screener
- 6 predefined investment strategy presets
- Custom filter support via API
- Peer-relative ranking within sectors
- Composite scoring system

### Interactive Dashboard
- 8-screen Streamlit interface
- Real-time data from API
- Interactive charts and filtering
- Export capabilities

### Automated Report Generation
- PDF tearsheets for each company (2 pages)
- PDF sector reports with median KPIs
- Portfolio summary PDF
- Excel-based cash flow intelligence report
- CSV pros/cons analysis with confidence scores

### RESTful API
- Comprehensive endpoint coverage
- Interactive Swagger documentation
- Proper error handling and validation
- CORS enabled for frontend integration
- Request/response logging

## API Documentation

Once the server is running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Key Endpoints

#### Companies
- `GET /api/v1/companies/` - List all companies with filtering
- `GET /api/v1/companies/{ticker}` - Detailed company profile
- `GET /api/v1/companies/{ticker}/pl` - Profit & Loss statement
- `GET /api/v1/companies/{ticker}/bs` - Balance sheet
- `GET /api/v1/companies/{ticker}/cashflow` - Cash flow statement
- `GET /api/v1/companies/{ticker}/ratios` - Financial ratios (latest or specific year)

#### Screener
- `GET /api/v1/screener/` - Screening with query parameters
- `GET /api/v1/screener/presets` - List predefined screens
- `GET /api/v1/screener/run/{preset_id}` - Execute a preset
- `POST /api/v1/screener/custom` - Custom screening with JSON body

#### Sectors
- `GET /api/v1/sectors/` - Sector summary with median KPIs
- `GET /api/v1/sectors/{sector}/companies` - Companies in a sector

#### Health
- `GET /api/v1/health` - System health and database statistics

## Dashboard
Access the Streamlit dashboard at http://localhost:8501 featuring:

### Screens
1. **Company Overview**: Key metrics, business description, sector info
2. **Financial Statements**: Interactive P&L, balance sheet, cash flow viewers
3. **Ratio Analysis**: Trend analysis, peer comparison, radar charts
4. **Cash Flow Analysis**: CFO quality, CapEx intensity, capital allocation
5. **Screening Tools**: Apply predefined or custom screens
6. **Peer Comparison**: Relative performance within sector
7. **Sector Analysis**: Sector-level metrics and composition
8. **Visualization Module**: Custom charts and exploration

## Reports Generation
Reports are generated to the following directories:
- `reports/tearsheets/` - Company-specific PDF reports (92 files)
- `reports/sector/` - Sector-specific PDF reports (11 files)
- `reports/portfolio/` - Portfolio summary PDF (1 file)
- `output/` - CSV/Excel reports:
  - pros_cons_generated.csv
  - cashflow_intelligence.xlsx
  - analysis_parsed.csv (NLP extracted data)
  - parse_failures.csv (NLP parsing issues)
  - distress_alerts.csv
  - pattern_changes.csv
  - skipped_tearsheets.csv

## Project Status
✅ **All 6 sprints completed**
✅ **356/356 tests passing**
✅ **API server functional**
✅ **Dashboard operational**
✅ **Reports generated**
✅ **Data quality validated**

### Last Verification
- Companies in database: 92
- Financial ratios records: 1041
- API tests: 12/12 passing
- Screener load test: 10 concurrent requests < 3 seconds
- All required output files present

### Next Steps / Maintenance
- Regular data updates as new Excel files become available
- Monitor for changes in source data format
- Periodic review of pros/cons rules and cash flow intelligence thresholds
- Consider adding new KPIs or screening criteria as needed

## License
Internal use only.

## Acknowledgments
Built with Python, FastAPI, Streamlit, pandas, scikit-learn, ReportLab, and many open-source libraries.