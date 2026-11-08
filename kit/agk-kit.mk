# The kit repository only (never installed). Included by agk.mk when this file exists.
# The kit's own tests: its tests of the checks and the kit-only tests of the installers.
# The full suite takes `[testing] workers` of agk.toml as prepush and project_tests.py do (brief #631, ADR-0305):
# `-n <workers>` when the suite's interpreter imports xdist, else the command of today after one line naming the setting.
# With `[testing] pr_tests = "selected"` and EVENT=pull_request (the workflow passes it) the run is the plan of the step
# `Project tests` (project_tests.plan: impact.py's selection, run by the [proof] area); a push, any other event, a release
# and a full plan run the full suite (brief #749, ADR-0348). One line says which mode ran and the selected count.
# A bad setting fails the target with one line naming it. The command run is printed last.
AGK_KIT_SUITE = AGK_KIT_TESTS=1 $(PY) -m pytest -c tests/kit/pytest.ini $(strip tests/kit $(wildcard tests/kit_dev)) -q
define AGK_KIT_CHOOSE
import os, re, sys
sys.path.insert(0, "scripts/agk")
from pathlib import Path
from common import CheckError
from impact import pr_tests
from prepush import NO_PARALLEL, NO_XDIST, full_command
import project_tests
here = Path.cwd()
event = os.environ.get("EVENT", "").strip()
try:
    command, single = full_command(here, sys.argv[1], here)
    if pr_tests(here) != "selected":
        runs, lines = [("full", "", ".", "pr_tests full")], []
    elif event != project_tests.EVENT:
        runs, lines = [("full", "", ".", f"event {event or 'unknown'}")], []
    else:
        runs, lines = project_tests.plan(here, command)
        # The plan's own line about the workers of `project_tests` is not this run's: `single` is.
        lines = [x for x in lines if x not in (NO_PARALLEL, NO_XDIST)]
except CheckError as exc:
    sys.exit(f"tests: {exc}")
full = next((r for r in runs if r[0] == "full"), None)
if full:
    lines.append(f"tests: mode full ({full[3]})")
    picked = [single, command] if single else [command]
else:
    counted = [re.match(r"regression: (\d+) test files? selected", x) for x in lines]
    n = next((int(m.group(1)) for m in counted if m), 0)
    lines.append(f"tests: mode selected, {n} test file{'' if n == 1 else 's'} (event {event})")
    picked = [" && ".join(f"(cd {c!r} && ({cmd}))" for _, cmd, c, _ in runs) or "true"]
project_tests.say(lines)
print("\n".join(picked))
endef
export AGK_KIT_CHOOSE

agk-test:
	@lines="$$($(PY) -c "$$AGK_KIT_CHOOSE" '$(AGK_KIT_SUITE)')" || exit 1; \
	printf '%s\n' "$$lines"; sh -c "$$(printf '%s\n' "$$lines" | tail -n 1)"
