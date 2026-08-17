PYTHON := venv/bin/python

# Sprint 1 targets (functional)
load:
	@echo "[load] Running ETL: Excel -> nifty100.db"
	$(PYTHON) -m src.etl.loader

test:
	@echo "[test] Running unit test suite"
	venv/bin/pytest tests/ -v

clean:
	@echo "[clean] Removing generated DB, outputs, logs, caches"
	rm -f db/nifty100.db
	rm -f output/*.csv
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true

# Future-sprint stubs
ratios:
	@echo "[ratios] Sprint 2 - not implemented yet"

report:
	@echo "[report] Sprint 5 - not implemented yet"

dashboard:
	@echo "[dashboard] Sprint 5 - not implemented yet"

api:
	@echo "[api] Sprint 5-6 - not implemented yet"

.PHONY: load test clean ratios report dashboard api
