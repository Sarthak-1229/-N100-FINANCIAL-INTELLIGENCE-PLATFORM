-- Nifty 100 Financial Intelligence Platform — Database Schema
-- Sprint 1 / Day 4
--
-- Design notes:
--  * companies.id is the natural key (the NSE ticker, e.g. 'TCS') — every
--    other table's company_id is a FOREIGN KEY pointing back to it.
--  * profitandloss/balancesheet/cashflow/financial_ratios use `year` as a
--    normalised 'YYYY-MM' string (fiscal period end), because some
--    companies report on non-March fiscal years (Dec/Jun/Sep).
--  * Every table has a surrogate INTEGER PRIMARY KEY `id` (simple, fast
--    joins) PLUS a UNIQUE constraint on the real-world natural key, so
--    duplicates are rejected by the database itself, not just by our code.

PRAGMA foreign_keys = ON;

-- ── 1. companies : the root table everything else references ─────────
CREATE TABLE IF NOT EXISTS companies (
    id                  TEXT PRIMARY KEY,       -- NSE ticker, e.g. 'TCS'
    company_name        TEXT NOT NULL,
    company_logo        TEXT,
    chart_link          TEXT,
    about_company       TEXT,
    website             TEXT,
    nse_profile         TEXT,
    bse_profile         TEXT,
    face_value          REAL,
    book_value          REAL,
    roce_percentage     REAL,
    roe_percentage      REAL
);

-- ── 2. profitandloss ────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS profitandloss (
    id                  INTEGER PRIMARY KEY,
    company_id          TEXT NOT NULL REFERENCES companies(id),
    year                TEXT NOT NULL,          -- normalised 'YYYY-MM'
    sales                INTEGER,
    expenses             INTEGER,
    operating_profit     REAL,
    opm_percentage        REAL,
    other_income          INTEGER,
    interest              INTEGER,
    depreciation          INTEGER,
    profit_before_tax     INTEGER,
    tax_percentage        REAL,
    net_profit            INTEGER,
    eps                   REAL,
    dividend_payout       REAL,
    UNIQUE(company_id, year)
);

-- ── 3. balancesheet ─────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS balancesheet (
    id                  INTEGER PRIMARY KEY,
    company_id          TEXT NOT NULL REFERENCES companies(id),
    year                TEXT NOT NULL,
    equity_capital       REAL,
    reserves              INTEGER,
    borrowings            INTEGER,
    other_liabilities     INTEGER,
    total_liabilities     INTEGER,
    fixed_assets          INTEGER,
    cwip                  INTEGER,
    investments           INTEGER,
    other_asset            INTEGER,
    total_assets           INTEGER,
    UNIQUE(company_id, year)
);

-- ── 4. cashflow ─────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS cashflow (
    id                  INTEGER PRIMARY KEY,
    company_id          TEXT NOT NULL REFERENCES companies(id),
    year                TEXT NOT NULL,
    operating_activity    REAL,
    investing_activity     REAL,
    financing_activity     REAL,
    net_cash_flow           REAL,
    UNIQUE(company_id, year)
);

-- ── 5. analysis : long-term growth stats, sparse (only some companies) ─
CREATE TABLE IF NOT EXISTS analysis (
    id                  INTEGER PRIMARY KEY,
    company_id          TEXT NOT NULL REFERENCES companies(id),
    period_years         INTEGER,               -- 3, 5, or 10
    sales_growth_pct       REAL,
    profit_growth_pct      REAL,
    stock_price_cagr_pct   REAL,
    roe_pct                 REAL
);

-- ── 6. documents : annual report links ─────────────────────────────
CREATE TABLE IF NOT EXISTS documents (
    id                  INTEGER PRIMARY KEY,
    company_id          TEXT NOT NULL REFERENCES companies(id),
    year                 INTEGER NOT NULL,
    annual_report_url     TEXT,
    UNIQUE(company_id, year)
);

-- ── 7. prosandcons ──────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS prosandcons (
    id                  INTEGER PRIMARY KEY,
    company_id          TEXT NOT NULL REFERENCES companies(id),
    pros                 TEXT,
    cons                  TEXT
);

-- ── 8. sectors : one row per company ───────────────────────────────
CREATE TABLE IF NOT EXISTS sectors (
    id                  INTEGER PRIMARY KEY,
    company_id          TEXT NOT NULL UNIQUE REFERENCES companies(id),
    broad_sector          TEXT,
    sub_sector             TEXT,
    index_weight_pct        REAL,
    market_cap_category      TEXT
);

-- ── 9. stock_prices : monthly OHLCV ────────────────────────────────
CREATE TABLE IF NOT EXISTS stock_prices (
    id                  INTEGER PRIMARY KEY,
    company_id          TEXT NOT NULL REFERENCES companies(id),
    date                  TEXT NOT NULL,         -- 'YYYY-MM-DD'
    open_price             REAL,
    high_price              REAL,
    low_price                REAL,
    close_price               REAL,
    volume                     INTEGER,
    adjusted_close              REAL,
    UNIQUE(company_id, date)
);

-- ── 10. market_cap ──────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS market_cap (
    id                  INTEGER PRIMARY KEY,
    company_id          TEXT NOT NULL REFERENCES companies(id),
    year                  INTEGER NOT NULL,      -- already clean, no normalising needed
    market_cap_crore       REAL,
    enterprise_value_crore   REAL,
    pe_ratio                   REAL,
    pb_ratio                     REAL,
    ev_ebitda                      REAL,
    dividend_yield_pct                REAL,
    UNIQUE(company_id, year)
);

-- ── 11. financial_ratios : precomputed reference (Sprint 2 recomputes) ─
CREATE TABLE IF NOT EXISTS financial_ratios (
    id                  INTEGER PRIMARY KEY,
    company_id          TEXT NOT NULL REFERENCES companies(id),
    year                  TEXT NOT NULL,         -- normalised 'YYYY-MM'
    net_profit_margin_pct        REAL,
    operating_profit_margin_pct    REAL,
    return_on_equity_pct             REAL,
    debt_to_equity                     REAL,
    interest_coverage                   REAL,
    asset_turnover                       REAL,
    free_cash_flow_cr                     REAL,
    capex_cr                               REAL,
    earnings_per_share                      REAL,
    book_value_per_share                     REAL,
    dividend_payout_ratio_pct                 REAL,
    total_debt_cr                              REAL,
    cash_from_operations_cr                     REAL,
    UNIQUE(company_id, year)
);

-- ── 12. peer_groups ─────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS peer_groups (
    id                  INTEGER PRIMARY KEY,
    peer_group_name      TEXT NOT NULL,
    company_id             TEXT NOT NULL REFERENCES companies(id),
    is_benchmark              INTEGER              -- SQLite has no BOOLEAN; 0/1
);

-- ── Indexes for the FK columns (SQLite doesn't auto-index them) ────
CREATE INDEX IF NOT EXISTS idx_pl_company   ON profitandloss(company_id);
CREATE INDEX IF NOT EXISTS idx_bs_company   ON balancesheet(company_id);
CREATE INDEX IF NOT EXISTS idx_cf_company   ON cashflow(company_id);
CREATE INDEX IF NOT EXISTS idx_an_company   ON analysis(company_id);
CREATE INDEX IF NOT EXISTS idx_doc_company  ON documents(company_id);
CREATE INDEX IF NOT EXISTS idx_pc_company   ON prosandcons(company_id);
CREATE INDEX IF NOT EXISTS idx_sp_company   ON stock_prices(company_id);
CREATE INDEX IF NOT EXISTS idx_mc_company   ON market_cap(company_id);
CREATE INDEX IF NOT EXISTS idx_fr_company   ON financial_ratios(company_id);
CREATE INDEX IF NOT EXISTS idx_pg_company   ON peer_groups(company_id);
