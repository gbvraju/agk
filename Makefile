PY ?= python3

include agk.mk

.PHONY: governance test lint traceability

governance: agk-governance

lint: agk-lint

traceability: agk-traceability

# Kit tests first (agk-test), then the project's own tests under tests/ (pytest exit 5 = none collected).
test: agk-test
	@$(PY) -m pytest tests -q --ignore=tests/kit_dev; rc=$$?; if [ $$rc -eq 5 ]; then exit 0; fi; exit $$rc
