# The kit repository only (never installed: it is not in kit/manifest.json). GNU make reads this file
# before `Makefile`, so `make test` here runs the kit suite once. `agk.toml` `project_tests` is the
# same command as `agk-test` on purpose (the CI proof job runs it as "the project's tests"), and the
# installed `Makefile` runs both targets, which is twice the suite. `Makefile` (a kit file and a
# protected path), `agk.mk`, `kit/agk-kit.mk`, `agk.toml` and the proof job are left as they are:
# `make -f Makefile test` and `make agk-project-test` still run the second target.
PY ?= python3

include agk.mk

.PHONY: governance test lint traceability

governance: agk-governance

lint: agk-lint

traceability: agk-traceability

test: agk-test
