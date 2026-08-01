PYTHON := .venv/bin/python

.PHONY: report test clean

report:
	PYTHONPATH=src $(PYTHON) -m flat_flyer

test:
	PYTHONPATH=src .venv/bin/pytest tests/ -q

clean:
	rm -rf data/processed reports .pytest_cache
