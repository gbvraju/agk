PY ?= python3

include agk.mk

.PHONY: governance test lint traceability

governance: agk-governance

lint: agk-lint

traceability: agk-traceability

# Kit tests, then the project's own tests (agk.toml project_tests).
test: agk-test agk-project-test
