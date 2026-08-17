"""
tests/etl/test_loader_regressions.py

Regression tests for real bugs found during manual review (Day 6).
Each test here documents a bug that actually shipped, so it can never
silently come back.
"""
import sqlite3
import pandas as pd
import pytest
from src.etl.loader import _load_period_table, build_schema


@pytest.fixture
def empty_db(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON;")
    monkeypatch.setattr("src.etl.loader.SCHEMA_PATH", "db/schema.sql")
    build_schema(conn)
    conn.execute("INSERT INTO companies (id, company_name) VALUES ('TCS', 'Tata Consultancy')")
    conn.commit()
    return conn


def test_normalized_year_not_overwritten_by_raw_year(empty_db, monkeypatch, tmp_path):
    """
    Bug: when the raw year column is literally named 'year' (true for
    profitandloss/balancesheet/cashflow), a naive rename(year_norm->year)
    creates a duplicate-named column and pandas can silently keep the
    UN-normalised raw string ('Mar 2024') instead of '2024-03'.
    """
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    df = pd.DataFrame({
        "id": [1], "company_id": ["TCS"], "year": ["Mar 2024"], "sales": [1000],
    })
    # write with the same 2-row-header shape _read_core expects
    with pd.ExcelWriter(raw_dir / "profitandloss.xlsx") as writer:
        pd.DataFrame([["title row", None]]).to_excel(writer, index=False, header=False, startrow=0)
        df.to_excel(writer, index=False, startrow=1)

    monkeypatch.setattr("src.etl.loader.RAW_DIR", str(raw_dir))
    _load_period_table(empty_db, "profitandloss", {"TCS"}, {"sales": "sales"}, "year", ["sales"])

    stored_year = empty_db.execute("SELECT year FROM profitandloss WHERE company_id='TCS'").fetchone()[0]
    assert stored_year == "2024-03", f"Expected normalised '2024-03', got raw '{stored_year}'"
