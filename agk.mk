# agk commands. Included by the Makefile of an installed repository, or called directly:
#   make -f agk.mk agk-governance | agk-lint | agk-test | agk-project-test | agk-traceability
PY ?= python3
AGK_RUFF_FLAGS := --isolated --line-length 100 --target-version py311 --select E,F,I,B,UP

.PHONY: agk-governance agk-lint agk-test agk-project-test agk-traceability

agk-governance:
	$(PY) scripts/agk/check_protected_changes.py
	$(PY) scripts/agk/check_requirements.py
	$(PY) scripts/agk/check_adrs.py
	$(PY) scripts/agk/check_specs.py
	$(PY) scripts/agk/check_neutrality.py
	$(PY) scripts/agk/check_build_state.py
	$(PY) scripts/agk/reviewers.py --check
	$(PY) scripts/agk/reviewers.py --check-codeowners

agk-lint:
	ruff check $(AGK_RUFF_FLAGS) $(shell $(PY) scripts/agk/config.py lint_paths)

agk-test:
	AGK_KIT_TESTS=1 $(PY) -m pytest -c tests/kit/pytest.ini tests/kit $(wildcard tests/kit_dev) -q

# The project's own tests, from agk.toml `project_tests` (a shell command); empty means none to run here.
agk-project-test:
	@cmd="$$($(PY) scripts/agk/config.py project_tests)"; \
	if [ -z "$$cmd" ]; then echo "agk: no project_tests configured; the project runs its own tests"; exit 0; fi; \
	sh -c "$$cmd"

agk-traceability:
	$(PY) scripts/agk/traceability.py
