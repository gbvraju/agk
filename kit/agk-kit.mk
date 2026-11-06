# The kit repository only (never installed). Included by agk.mk when this file exists.
# The kit's own tests: its tests of the checks and the kit-only tests of the installers.
# The full suite takes `[testing] workers` of agk.toml as prepush and project_tests.py do (brief #631, ADR-0305):
# `-n <workers>` when the suite's interpreter imports xdist, else the command of today after one line naming the setting.
# A bad setting fails the target with one line naming it. The command run is printed first.
AGK_KIT_SUITE = AGK_KIT_TESTS=1 $(PY) -m pytest -c tests/kit/pytest.ini $(strip tests/kit $(wildcard tests/kit_dev)) -q
AGK_KIT_CHOOSE = import sys; sys.path.insert(0, "scripts/agk"); exec("from pathlib import Path\nfrom common import \
  CheckError\nfrom prepush import full_command\nhere = Path.cwd()\ntry:\n    command, single = full_command(here, \
  sys.argv[1], here)\nexcept CheckError as exc:\n    sys.exit(f\"tests: {exc}\")\nif single:\n    print(single)\nprint(command)")

agk-test:
	@lines="$$($(PY) -c '$(AGK_KIT_CHOOSE)' '$(AGK_KIT_SUITE)')" || exit 1; \
	printf '%s\n' "$$lines"; sh -c "$$(printf '%s\n' "$$lines" | tail -n 1)"
