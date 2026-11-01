# agk commands. Included by the Makefile of an installed repository, or called directly:
#   make -f agk.mk agk-governance | agk-lint | agk-test | agk-project-test | agk-traceability
PY ?= python3
AGK_RUFF_FLAGS := --isolated --line-length 100 --target-version py311 --select E,F,I,B,UP

.PHONY: agk-governance agk-lint agk-test agk-project-test agk-traceability

agk-governance:
	$(PY) scripts/agk/check_protected_changes.py
	$(PY) scripts/agk/check_requirements.py
	$(PY) scripts/agk/check_adrs.py
	$(PY) scripts/agk/check_numbers.py
	$(PY) scripts/agk/check_specs.py
	$(PY) scripts/agk/check_neutrality.py
	$(PY) scripts/agk/check_build_state.py
	$(PY) scripts/agk/check_kit_tests.py
	$(PY) scripts/agk/check_design.py
	$(PY) scripts/agk/reviewers.py --check
	$(PY) scripts/agk/reviewers.py --check-codeowners
	$(PY) scripts/agk/check_pr_mode.py
	$(PY) scripts/agk/check_final_clearance.py

agk-lint:
	ruff check $(AGK_RUFF_FLAGS) $(wildcard $(shell $(PY) scripts/agk/config.py lint_paths))

# The kit's own tests are not installed in a project (lean install); they run in the kit repository,
# which defines this target in kit/agk-kit.mk. A project has no such file and gets the notice.
ifneq ($(wildcard kit/agk-kit.mk),)
include kit/agk-kit.mk
else
agk-test:
	@echo "agk: the kit's own tests are not installed in this repository; they run in the kit repository"
endif

# The project's own tests, from agk.toml `project_tests` (a shell command); empty means none to run here.
# The project's tests; with [testing] pr_tests = "selected" a pull request runs only its selected tests (ADR-0242).
agk-project-test:
	@$(PY) scripts/agk/project_tests.py

agk-traceability:
	$(PY) scripts/agk/traceability.py
