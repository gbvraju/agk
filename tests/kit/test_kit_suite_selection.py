"""The kit's own pull requests run only their selected tests; the full suite runs on the default
branch (brief #749, ADR-0348, REQ-016).

`make -f agk.mk agk-test` (`kit/agk-kit.mk`, the governance step `Tests of the checks`) reads the
event that the workflow passes as `EVENT`. With `[testing] pr_tests = "selected"` and the event
`pull_request` it runs the tests that `impact.py` selects for the change, through the same plan as
the step `Project tests` (`project_tests.plan`: the same map, `always_full` list, `profile` and
`[proof]` area); otherwise, and whenever that plan is full, the kit's full suite as before. It
prints which mode ran and the selected count; a bad setting fails it with one line naming it.

Brief #980 (ADR-0422, REQ-051): a selected pytest run gains `-n <workers>` by the full suite's rule
when its interpreter imports xdist, and a selection of at least `[testing] full_when_share` of the
suite's test files runs the full suite instead; the selected file list never changes.

Each case is an invented kit tree in a temporary git repository. `PY` is a stub runner: it records
a `-m pytest` call (the full suite) in a log outside the tree and runs every other call with the
real interpreter; the `[proof]` area's command only records the files it was given.
"""

from __future__ import annotations

import os
import shutil
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github" / "workflows" / "governance.yml"
MAP = 'map = [ { code = "src/billing/**", tests = ["tests/kit/test_pay.py"] } ]\n'
SELECTED = 'profile = "fast"\npr_tests = "selected"\nalways_full = ["src/core.py"]\n' + MAP


@pytest.fixture
def outside(tmp_path_factory) -> Path:
    return tmp_path_factory.mktemp("outside")


def toml(
    outside: Path, testing: str = SELECTED, version: str = "1.0.0", area: str | None = None
) -> str:
    log = outside / "ran.log"
    area = area or f"echo kit {{files}} >> {log}"
    return (
        f'version = "{version}"\n'
        'default_branch = "main"\nlint_paths = ["scripts/agk"]\n'
        'test_dirs = ["tests/kit"]\ntest_patterns = ["test_*.py"]\n'
        f"project_tests = 'echo project >> {log}'\n"
        "[proof]\n"
        f'kit = {{ dirs = ["tests/kit"], patterns = ["test_*.py"], '
        f"command = '{area}' }}\n"
        "[testing]\n" + testing
    )


def stub(outside: Path) -> Path:
    """The stub runner given as `PY`: a `-m` call is the full suite, recorded; the rest run."""
    path = outside / "py"
    path.write_text(
        "#!/bin/sh\n"
        f'if [ "$1" = "-m" ]; then echo "suite $*" >> "{outside / "ran.log"}"; '
        'exit "${STUB_CODE:-0}"; fi\n'
        f'exec "{sys.executable}" "$@"\n',
        encoding="utf-8",
    )
    path.chmod(0o755)
    return path


def git(root: Path, *args: str) -> str:
    proc = subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
        ["git", *args], cwd=root, capture_output=True, text=True, check=True
    )
    return proc.stdout


def write(root: Path, files: dict[str, str]) -> None:
    for rel, text in files.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")


def kit_tree(
    tmp_path: Path,
    base_toml: str,
    change: dict[str, str] | None = None,
    head_toml: str | None = None,
) -> Path:
    """An invented kit tree: agk.mk, kit/agk-kit.mk and scripts/agk of the kit, a base commit on
    main and a feature branch with one change commit."""
    root = tmp_path / "kit"
    shutil.copytree(
        ROOT / "scripts" / "agk",
        root / "scripts" / "agk",
        ignore=shutil.ignore_patterns("__pycache__"),
    )
    (root / "kit").mkdir()
    shutil.copy(ROOT / "agk.mk", root / "agk.mk")
    shutil.copy(ROOT / "kit" / "agk-kit.mk", root / "kit" / "agk-kit.mk")
    git(root, "init", "-q", "-b", "main")
    git(root, "config", "user.email", "builder@example.com")
    git(root, "config", "user.name", "Builder")
    write(
        root,
        {
            "agk.toml": base_toml,
            "src/billing/pay.py": "base\n",
            "src/core.py": "base\n",
            "tests/kit/test_pay.py": "# guards pay\n",
            "tests/kit/test_core.py": "# guards core\n",
            "tests/kit/test_one.py": "# guards one\n",
            "tests/kit/test_two.py": "# guards two\n",
            "tests/kit/test_three.py": "# guards three\n",
            "docs/notes.md": "base\n",
        },
    )
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "base")
    git(root, "checkout", "-q", "-b", "feature")
    files = dict(change or {"src/billing/pay.py": "change\n"})
    if head_toml is not None:
        files["agk.toml"] = head_toml
    write(root, files)
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "change")
    return root


def run(root: Path, outside: Path, event: str | None, **extra: str):
    drop = (
        "GITHUB_BASE_REF",
        "AGK_BASE",
        "CI",
        "EVENT",
        "GITHUB_STEP_SUMMARY",
        "STUB_CODE",
        "AGK_TEST_WORKERS",  # the caller's one-machine number never reaches the run (brief #1032)
    )
    env = {k: v for k, v in os.environ.items() if k not in drop}
    env["AGK_BASE"] = git(root, "rev-parse", "main").strip()
    if event is not None:
        env["EVENT"] = event
    env.update(extra)
    return subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
        ["make", "-s", "-f", "agk.mk", "agk-test", f"PY={stub(outside)}"],
        cwd=root,
        capture_output=True,
        text=True,
        env=env,
        timeout=300,
    )


def ran(outside: Path) -> list[str]:
    log = outside / "ran.log"
    return log.read_text(encoding="utf-8").split("\n")[:-1] if log.exists() else []


def is_full(lines: list[str]) -> bool:
    return lines == ["suite -m pytest -c tests/kit/pytest.ini tests/kit -q"]


def test_a_pull_request_runs_only_the_selected_files(tmp_path, outside):
    """REQ-016: brief #749 answer 1 (a mapped change on a pull request runs its selection)."""
    root = kit_tree(tmp_path, toml(outside))
    proc = run(root, outside, "pull_request")
    out = proc.stdout + proc.stderr
    assert proc.returncode == 0, out
    assert ran(outside) == ["kit tests/kit/test_pay.py"], out
    assert "tests: mode selected, 1 test file (event pull_request)" in out.splitlines(), out


def test_an_always_full_change_runs_the_full_suite(tmp_path, outside):
    """REQ-016: brief #749 answer 3 (`always_full` stays the safety net)."""
    root = kit_tree(tmp_path, toml(outside), change={"src/core.py": "change\n"})
    proc = run(root, outside, "pull_request")
    out = proc.stdout + proc.stderr
    assert proc.returncode == 0, out
    assert is_full(ran(outside)), out
    assert "tests: mode full (always_full src/core.py matches src/core.py)" in out, out


@pytest.mark.parametrize("event", ["push", None])
def test_a_push_or_an_unknown_event_runs_the_full_suite(tmp_path, outside, event):
    """REQ-016: brief #749 answer 2 (a push to the default branch runs the full suite)."""
    root = kit_tree(tmp_path, toml(outside))
    proc = run(root, outside, event)
    out = proc.stdout + proc.stderr
    assert proc.returncode == 0, out
    assert is_full(ran(outside)), out
    assert f"tests: mode full (event {event or 'unknown'})" in out.splitlines(), out


def test_a_release_pull_request_runs_the_full_suite(tmp_path, outside):
    """REQ-016: brief #749 answer 2 (a release pull request runs the full suite)."""
    root = kit_tree(tmp_path, toml(outside), head_toml=toml(outside, version="1.1.0"))
    proc = run(root, outside, "pull_request")
    out = proc.stdout + proc.stderr
    assert proc.returncode == 0, out
    assert is_full(ran(outside)), out
    assert "tests: mode full (release: version raised in agk.toml)" in out, out


def test_without_selected_a_pull_request_runs_the_full_suite(tmp_path, outside):
    """REQ-016: brief #749 answer 1 (without `pr_tests = "selected"` nothing changes)."""
    root = kit_tree(tmp_path, toml(outside, testing='profile = "fast"\n' + MAP))
    proc = run(root, outside, "pull_request")
    out = proc.stdout + proc.stderr
    assert proc.returncode == 0, out
    assert is_full(ran(outside)), out
    assert "tests: mode full (pr_tests full)" in out.splitlines(), out


def test_a_docs_only_pull_request_runs_nothing(tmp_path, outside):
    """REQ-016: brief #749 answer 1 (a documentation change selects nothing, as Project tests)."""
    root = kit_tree(tmp_path, toml(outside), change={"docs/notes.md": "change\n"})
    proc = run(root, outside, "pull_request")
    out = proc.stdout + proc.stderr
    assert proc.returncode == 0, out
    assert ran(outside) == [], out
    assert "tests: mode selected, 0 test files (event pull_request)" in out.splitlines(), out


def test_a_failing_full_suite_fails_the_target(tmp_path, outside):
    """REQ-016: brief #749 answer 2 (the full run keeps its exit code)."""
    root = kit_tree(tmp_path, toml(outside))
    proc = run(root, outside, "push", STUB_CODE="1")
    assert proc.returncode != 0
    assert is_full(ran(outside))


def test_a_bad_setting_fails_with_one_line_naming_it(tmp_path, outside):
    """REQ-016: brief #749 answer 4 (a bad setting fails, naming the setting, never the value)."""
    bad = SELECTED.replace('pr_tests = "selected"', 'pr_tests = "sometimes"')
    root = kit_tree(tmp_path, toml(outside, testing=bad))
    proc = run(root, outside, "pull_request")
    out = proc.stdout + proc.stderr
    own = [line for line in out.splitlines() if line and not line.startswith("make")]
    assert proc.returncode != 0
    assert ran(outside) == []
    assert len(own) == 1 and "setting: pr_tests" in own[0], out
    assert "sometimes" not in out


def test_the_workflow_passes_the_event_to_tests_of_the_checks():
    """REQ-016: brief #749 answer 2 (`Tests of the checks` gets `EVENT`, as `Project tests`)."""
    text = WORKFLOW.read_text(encoding="utf-8")
    step = text.split("- name: Tests of the checks\n", 1)[1].split("- name: ", 1)[0]
    assert "EVENT: ${{ github.event_name }}" in step, step
    assert "run: make -f agk.mk agk-test" in step


def interpreter(outside: Path) -> Path:
    """A stub `python3` for a `[proof]` area: `-c` is the xdist probe (fails with NO_XDIST set),
    any other call is recorded as `area <args>`."""
    path = outside / "bin" / "python3"
    path.parent.mkdir(exist_ok=True)
    path.write_text(
        "#!/bin/sh\n"
        'if [ "$1" = "-c" ]; then [ -z "$NO_XDIST" ]; exit $?; fi\n'
        f'echo "area $*" >> "{outside / "ran.log"}"\n',
        encoding="utf-8",
    )
    path.chmod(0o755)
    return path


def pytest_area(outside: Path, prefixed: bool) -> str:
    """A `[proof]` area command that is a pytest command; PREFIXED puts a shell step before it, as
    the kit's own `[proof.kit]` command does."""
    command = f"AGK_KIT_TESTS=1 {interpreter(outside)} -m pytest -q {{files}}"
    return f"(true) >/dev/null 2>&1 || true; {command}" if prefixed else command


@pytest.mark.parametrize(
    ("workers", "extra"),
    [("3", {}), ('"auto"', {"AGK_TEST_WORKERS": "3"})],
    ids=["number", "auto-pinned"],
)
@pytest.mark.parametrize("prefixed", [False, True])
def test_a_selected_pytest_run_gets_the_workers_when_xdist_imports(
    tmp_path, outside, prefixed, workers, extra
):
    """REQ-051: brief #980 answer 2, test (a) (a selected run takes `-n` as the full suite does).
    The number is pinned, never the machine's CPU count or free memory (brief #1032): a number as
    written, and `"auto"` with `AGK_TEST_WORKERS` set for the run alone."""
    testing = SELECTED + f"workers = {workers}\n"
    root = kit_tree(tmp_path, toml(outside, testing, area=pytest_area(outside, prefixed)))
    proc = run(root, outside, "pull_request", **extra)
    out = proc.stdout + proc.stderr
    assert proc.returncode == 0, out
    assert ran(outside) == ["area -m pytest -q tests/kit/test_pay.py -n 3"], out
    assert "tests: mode selected, 1 test file (event pull_request)" in out.splitlines(), out


def test_without_xdist_the_selected_run_stays_single_and_names_the_setting(tmp_path, outside):
    """REQ-051: brief #980 answer 2, test (b) (no xdist: no `-n`, one line names the setting)."""
    testing = SELECTED + "workers = 3\n"
    root = kit_tree(tmp_path, toml(outside, testing, area=pytest_area(outside, True)))
    proc = run(root, outside, "pull_request", NO_XDIST="1")
    out = proc.stdout + proc.stderr
    assert proc.returncode == 0, out
    assert ran(outside) == ["area -m pytest -q tests/kit/test_pay.py"], out
    named = [line for line in out.splitlines() if "setting: testing.workers" in line]
    assert len(named) == 1 and "one process" in named[0], out


def test_a_selected_run_with_one_worker_is_unchanged(tmp_path, outside):
    """REQ-051: brief #980 answer 2 (with `workers` 1 the selected run is the command of today)."""
    testing = SELECTED + "workers = 1\n"
    root = kit_tree(tmp_path, toml(outside, testing, area=pytest_area(outside, False)))
    proc = run(root, outside, "pull_request")
    out = proc.stdout + proc.stderr
    assert proc.returncode == 0, out
    assert ran(outside) == ["area -m pytest -q tests/kit/test_pay.py"], out
    assert "setting: testing.workers" not in out, out


def test_a_selection_at_the_share_runs_the_full_suite(tmp_path, outside):
    """REQ-051: brief #980 answer 3 and test (c) (a wide selection runs the full suite)."""
    testing = SELECTED + "full_when_share = 0.2\n"
    root = kit_tree(tmp_path, toml(outside, testing))
    proc = run(root, outside, "pull_request")
    out = proc.stdout + proc.stderr
    assert proc.returncode == 0, out
    assert is_full(ran(outside)), out
    assert "tests: mode full (selection 1 of 5 files)" in out.splitlines(), out


def test_a_selection_below_the_share_stays_selected(tmp_path, outside):
    """REQ-051: brief #980 answer 3 (below the share, the default 0.5 here, the selection runs)."""
    root = kit_tree(tmp_path, toml(outside, SELECTED + "full_when_share = 0.5\n"))
    proc = run(root, outside, "pull_request")
    out = proc.stdout + proc.stderr
    assert proc.returncode == 0, out
    assert ran(outside) == ["kit tests/kit/test_pay.py"], out


@pytest.mark.parametrize("value", ["0", "1.5", '"half"', "true"])
def test_a_bad_share_fails_naming_the_setting(tmp_path, outside, value):
    """REQ-051: brief #980 answer 3 (a bad `full_when_share` is refused, naming the setting)."""
    root = kit_tree(tmp_path, toml(outside, SELECTED + f"full_when_share = {value}\n"))
    proc = run(root, outside, "pull_request")
    out = proc.stdout + proc.stderr
    assert proc.returncode != 0
    assert ran(outside) == []
    assert "setting: testing.full_when_share" in out, out


def test_the_selected_file_list_is_the_same_with_workers(tmp_path, outside):
    """REQ-051: brief #980 answer 4 and test (d) (only how the selection runs changes)."""
    seen = []
    for workers in ("1", '"auto"'):
        (outside / "ran.log").unlink(missing_ok=True)
        testing = SELECTED + f"workers = {workers}\n"
        here = tmp_path / workers.strip('"')
        root = kit_tree(here, toml(outside, testing, area=pytest_area(outside, True)))
        proc = run(root, outside, "pull_request")
        out = proc.stdout + proc.stderr
        assert proc.returncode == 0, out
        lines = ran(outside)
        assert len(lines) == 1, out
        files = [w for w in lines[0].split() if w.startswith("tests/")]
        selected = [x for x in out.splitlines() if x.startswith("regression: ")]
        seen.append((sorted(files), selected))
    assert seen[0] == seen[1]
    assert seen[0][0] == ["tests/kit/test_pay.py"]


def prepush_module():
    sys.path.insert(0, str(ROOT / "scripts" / "agk"))
    import prepush

    return prepush


@pytest.mark.parametrize(
    ("command", "python"),
    [
        ("python3 -m pytest -q a.py", "python3"),
        ("pip -q install x || true; AGK_KIT_TESTS=1 python3 -m pytest -q a.py", "python3"),
        ("(cd x; python3 -m pytest a.py)", None),
        ("echo x # ; python3 -m pytest a.py", None),
        ("echo boom; exit 1", None),
        ("npm test -- a.js", None),
    ],
)
def test_the_pytest_command_that_n_reaches(command, python):
    """REQ-051: brief #980 answer 2 (only a pytest command that a final `-n` reaches gains it)."""
    assert prepush_module().last_pytest(command) == python


def test_prepush_selected_runs_gain_the_workers_and_full_is_untouched(tmp_path, monkeypatch):
    """REQ-051: brief #980 answer 2, context local (prepush regression runs take the rule)."""
    prepush = prepush_module()
    monkeypatch.setattr(prepush, "workers_setting", lambda root: 4)
    monkeypatch.setattr(prepush, "imports_xdist", lambda python, folder: True)
    sets = [
        ("kit", "python3 -m pytest -q a.py", ".", "why"),
        ("web", "npm test -- a.js", ".", "why"),
        ("full", "make test", ".", "why"),
    ]
    made, lines = prepush.selected_workers(tmp_path, sets)
    assert [c for _, c, _, _ in made] == [
        "python3 -m pytest -q a.py -n 4",
        "npm test -- a.js",
        "make test",
    ]
    assert lines == [prepush.SELECTED_NOT_PYTEST.format(name="web")]
    monkeypatch.setattr(prepush, "imports_xdist", lambda python, folder: False)
    made, lines = prepush.selected_workers(tmp_path, sets[:1])
    assert made == sets[:1] and lines == [prepush.NO_XDIST]


def module(name: str):
    sys.path.insert(0, str(ROOT / "scripts" / "agk"))
    return __import__(name)


def test_without_xdist_the_full_and_a_selected_run_print_the_one_line_once(monkeypatch, tmp_path):
    """REQ-051: brief #980 answer 2 and SPEC-0044 rule 4 (fix list on b5095b4, item 3: the one
    line of the rule, printed once when the full run and a linked selected run both fall back)."""
    prepush, chooser = module("prepush"), module("project_tests")
    monkeypatch.setenv("EVENT", chooser.EVENT)
    monkeypatch.setattr(prepush, "workers_setting", lambda root: 3)
    monkeypatch.setattr(prepush, "imports_xdist", lambda python, folder: False)
    link = ("web", "python3 -m pytest -q tests/web/test_b.py", ".", chooser.LINK_REASON + "x")
    found = type("Found", (), {"selected": [type("S", (), {"test": "tests/kit/a.py"})()]})()
    found.map_notes = []
    patched = {
        "resolve_base": lambda root, ref: "main",
        "merge_base": lambda root, base: "mb",
        "version_at": lambda root, ref: "1.0.0",
        "refresh": lambda root: None,
        "impact": lambda root, mb, head: found,
        "proof_areas": lambda root: [],
        "regression_sets": lambda root, f, a: ([("kit", "x", ".", "why"), link], []),
        "text": lambda f: [],
        "suite_test_files": lambda root, areas: 1,
        "full_when_share": lambda root: 0.5,
        "full_command": lambda root, project, folder: ("python3 -m pytest -q", prepush.NO_XDIST),
    }
    for name, value in patched.items():
        monkeypatch.setattr(chooser, name, value)
    sets, lines = chooser.plan(tmp_path, "python3 -m pytest -q")
    assert [s[0] for s in sets] == ["full", "web"]
    assert lines.count(prepush.NO_XDIST) == 1, lines
    assert not [line for line in lines if "selected runs stay" in line], lines


def test_a_record_of_a_selected_run_with_workers_agrees(monkeypatch, tmp_path):
    """REQ-051: brief #980 answer 2 (fix list on b5095b4, item 2: `evidence.py` rebuilds a
    selected regression run with the workers prepush gave it, so the record reads no `differs`)."""
    prepush, evidence = module("prepush"), module("evidence")
    monkeypatch.setattr(prepush, "workers_setting", lambda root: 4)
    monkeypatch.setattr(prepush, "imports_xdist", lambda python, folder: True)
    sets = [
        ("kit", "python3 -m pytest -q tests/kit/test_pay.py", ".", "why"),
        ("web", "npm test -- a.js", ".", "why"),
    ]
    shown = '{"runs": [], "regression": {"table": true}}'
    monkeypatch.setattr(evidence, "spawn", lambda argv, cwd, env, limit: (0, shown))
    monkeypatch.setattr(evidence, "impact", lambda tree, mb, head: None)
    monkeypatch.setattr(evidence, "proof_areas", lambda tree: [])
    monkeypatch.setattr(evidence, "regression_sets", lambda tree, found, areas: (sets, []))
    recorded, _ = prepush.selected_workers(tmp_path, sets)  # what gate runs and records
    planned = evidence.planned_runs(tmp_path, ["test_plan"], {}, "mb", 10)
    for name, command, cwd, _reason in recorded:
        assert planned[("regression", name)] == (command, tmp_path / cwd)
    assert planned[("regression", "kit")][0].endswith(" -n 4")
