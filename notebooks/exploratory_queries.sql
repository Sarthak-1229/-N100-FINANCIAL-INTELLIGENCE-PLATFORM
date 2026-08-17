-- notebooks/exploratory_queries.sql
-- Sprint 1 / Day 7 — 10 sanity-check queries over nifty100.db
-- Run with: sqlite3 db/nifty100.db < notebooks/exploratory_queries.sql

-- 1. Row counts per table (matches load_audit.csv "rows_loaded")
SELECT 'companies' AS tbl, COUNT(*) AS n FROM companies
UNION ALL SELECT 'profitandloss', COUNT(*) FROM profitandloss
UNION ALL SELECT 'balancesheet', COUNT(*) FROM balancesheet
UNION ALL SELECT 'cashflow', COUNT(*) FROM cashflow
UNION ALL SELECT 'analysis', COUNT(*) FROM analysis
UNION ALL SELECT 'documents', COUNT(*) FROM documents
UNION ALL SELECT 'prosandcons', COUNT(*) FROM prosandcons
UNION ALL SELECT 'sectors', COUNT(*) FROM sectors
UNION ALL SELECT 'stock_prices', COUNT(*) FROM stock_prices
UNION ALL SELECT 'market_cap', COUNT(*) FROM market_cap
UNION ALL SELECT 'financial_ratios', COUNT(*) FROM financial_ratios
UNION ALL SELECT 'peer_groups', COUNT(*) FROM peer_groups;

-- 2. Top 10 companies by FY24 sales
SELECT company_id, sales
FROM profitandloss
WHERE year = '2024-03'
ORDER BY sales DESC
LIMIT 10;

-- 3. Sector breakdown: number of companies and average index weight per sector
SELECT broad_sector, COUNT(*) AS n_companies, ROUND(AVG(index_weight_pct), 2) AS avg_weight
FROM sectors
GROUP BY broad_sector
ORDER BY n_companies DESC;

-- 4. Companies with fewer than 5 years of P&L history (DQ-16 flag)
SELECT company_id, COUNT(DISTINCT year) AS n_years
FROM profitandloss
GROUP BY company_id
HAVING n_years < 5
ORDER BY n_years;

-- 5. Year-over-year sales growth for a single company (parameterise company_id manually)
SELECT year, sales,
       ROUND(100.0 * (sales - LAG(sales) OVER (ORDER BY year)) / LAG(sales) OVER (ORDER BY year), 1) AS yoy_growth_pct
FROM profitandloss
WHERE company_id = 'TCS'
ORDER BY year;

-- 6. Companies where the balance sheet did not balance within 1% (DQ-04 flags)
-- (cross-reference against output/validation_failures.csv for the full audit trail)
SELECT company_id, year, total_assets, total_liabilities,
       ROUND(ABS(total_assets - total_liabilities) * 100.0 / total_assets, 2) AS pct_diff
FROM balancesheet
WHERE total_assets > 0
  AND ABS(total_assets - total_liabilities) * 1.0 / total_assets >= 0.01
ORDER BY pct_diff DESC
LIMIT 10;

-- 7. Average FY24 P/E ratio by sector (join market_cap + sectors)
SELECT s.broad_sector, ROUND(AVG(mc.pe_ratio), 1) AS avg_pe
FROM market_cap mc
JOIN sectors s ON s.company_id = mc.company_id
WHERE mc.year = 2024 AND mc.pe_ratio IS NOT NULL
GROUP BY s.broad_sector
ORDER BY avg_pe DESC;

-- 8. Highest and lowest ROE companies (from the companies table's precomputed field)
SELECT id, company_name, roe_percentage
FROM companies
WHERE roe_percentage IS NOT NULL
ORDER BY roe_percentage DESC
LIMIT 5;

-- 9. Peer group membership: who's in the "Private Banks" peer group and are they the benchmark?
SELECT pg.company_id, c.company_name, pg.is_benchmark
FROM peer_groups pg
JOIN companies c ON c.id = pg.company_id
WHERE pg.peer_group_name = 'Private Banks';

-- 10. Data quality summary: violation counts by rule and severity
--     (this mirrors output/validation_failures.csv, useful once it's
--      also loaded into a table -- for now this documents the shape
--      analysts should expect when querying that CSV)
-- SELECT rule_id, severity, COUNT(*) FROM validation_failures GROUP BY rule_id, severity;
