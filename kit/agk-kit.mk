# The kit repository only (never installed). Included by agk.mk when this file exists.
# The kit's own tests: its tests of the checks and the kit-only tests of the installers.
agk-test:
	AGK_KIT_TESTS=1 $(PY) -m pytest -c tests/kit/pytest.ini tests/kit $(wildcard tests/kit_dev) -q
