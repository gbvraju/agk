PY ?= python3

.PHONY: governance test lint traceability

governance:
	$(PY) scripts/agk/check_protected_changes.py
	$(PY) scripts/agk/check_requirements.py
	$(PY) scripts/agk/check_adrs.py
	$(PY) scripts/agk/check_neutrality.py
	$(PY) scripts/agk/check_build_state.py
	$(PY) scripts/agk/reviewers.py --check

test:
	$(PY) -m pytest tests/kit -q

lint:
	ruff check .

traceability:
	$(PY) scripts/agk/traceability.py
