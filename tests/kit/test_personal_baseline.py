"""SPEC-0041 build (h), first part: the baseline and the ten `[personal]` keys (brief #922).

`personal.py baseline` prints the test command it would run and runs it once only with
`--approve`, on the head tree written into the sidecar's `cache/trees/`, recording the head, the
command and the tests already failing in `records/baseline.json` (rule 16).
`common.personal_table` checks each of the ten keys of rule 18 by its type and range and refuses
naming the key, never the value. Invented data only.
"""

from __future__ import annotations

import hashlib
import json
import os
import shlex
import shutil
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts" / "agk"
sys.path.insert(0, str(SCRIPTS))

import common  # noqa: E402

JUNIT_STUB = """import pathlib, sys
pathlib.Path("ran.txt").write_text("ran", encoding="utf-8")
cases = [
    ("tests/test_shop.py", "test_cart_total", True),
    ("tests/test_shop.py", "test_login", False),
    ("tests/test_mail.py", "test_send_to_example_com", True),
]
rows = []
for file, name, ok in cases:
    body = "" if ok else '<failure message="assert 1 == 2"/>'
    rows.append(f'<testcase classname="x" file="{file}" name="{name}">{body}</testcase>')
text = "<testsuite>" + "".join(rows) + "</testsuite>"
pathlib.Path(sys.argv[1]).write_text(text, encoding="utf-8")
sys.exit(1)
"""
WHOLE_STUB = """import pathlib, sys
pathlib.Path("ran.txt").write_text("ran", encoding="utf-8")
sys.exit(1)
"""
GREEN_STUB = "import sys\nsys.exit(0)\n"


def run_git(root: Path, *args: str) -> str:
    proc = subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
        ["git", *args], cwd=root, capture_output=True, text=True, check=True
    )
    return proc.stdout


def make_clone(path: Path) -> Path:
    path.mkdir(parents=True)
    run_git(path, "init", "-q", "-b", "main")
    for key, value in (
        ("user.email", "t@example.com"),
        ("user.name", "t"),
        ("commit.gpgsign", "false"),
    ):
        run_git(path, "config", key, value)
    (path / "junit_stub.py").write_text(JUNIT_STUB, encoding="utf-8")
    (path / "whole_stub.py").write_text(WHOLE_STUB, encoding="utf-8")
    (path / "green_stub.py").write_text(GREEN_STUB, encoding="utf-8")
    run_git(path, "add", "-A")
    run_git(path, "commit", "-q", "-m", "initial")
    return path


def make_sidecar(path: Path, command: str | None) -> Path:
    path.mkdir(parents=True)
    line = f"test_command = {json.dumps(command)}\n" if command is not None else ""
    text = f'review_mode = "solo"\n[personal]\nforge = "files"\nschema = 1\n{line}'
    (path / "agk.toml").write_text(text, encoding="utf-8")
    return path


def command_of(stub: str, junit: bool) -> str:
    return f"{shlex.quote(sys.executable)} {stub}" + (" {junit}" if junit else "")


def baseline(clone: Path, sidecar: Path, *extra: str):
    skip = ("AGK_HOME", "AGK_BASE", "GITHUB_BASE_REF", "CI")
    env = {k: v for k, v in os.environ.items() if k not in skip}
    cmd = [sys.executable, str(SCRIPTS / "personal.py"), "baseline", "--clone", str(clone)]
    return subprocess.run(  # nosec B603 - fixed argument list, no shell
        [*cmd, "--sidecar", str(sidecar), *extra], capture_output=True, text=True, env=env
    )


def record(sidecar: Path) -> dict:
    return json.loads((sidecar / "records" / "baseline.json").read_text(encoding="utf-8"))


def snapshot(clone: Path) -> dict[str, str]:
    """Every file of the clone, its work tree and its `.git/`, by content."""
    return {
        p.relative_to(clone).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(clone.rglob("*"))
        if p.is_file()
    }


# Rule 16: the baseline.


def test_rule16_without_approve_it_prints_the_command_and_runs_nothing(tmp_path):
    """REQ-048 AC5: rule 16 (the command is printed; nothing runs and nothing is recorded)."""
    clone = make_clone(tmp_path / "clone")
    command = command_of("junit_stub.py", junit=True)
    sidecar = make_sidecar(tmp_path / "side", command)
    done = baseline(clone, sidecar)
    assert done.returncode == 0, done.stdout + done.stderr
    assert command in done.stdout
    assert "--approve" in done.stdout
    assert not (sidecar / "records" / "baseline.json").exists()
    assert not (sidecar / "cache").exists()
    assert not (clone / "ran.txt").exists()


def test_rule16_with_approve_and_junit_it_records_each_failing_test(tmp_path):
    """REQ-048 AC5: rule 16 (head, command and the failing tests, per test from `{junit}`)."""
    clone = make_clone(tmp_path / "clone")
    command = command_of("junit_stub.py", junit=True)
    sidecar = make_sidecar(tmp_path / "side", command)
    done = baseline(clone, sidecar, "--approve")
    assert done.returncode == 0, done.stdout + done.stderr
    head = run_git(clone, "rev-parse", "HEAD").strip()
    saved = record(sidecar)
    assert saved["head"] == head
    assert saved["command"] == command
    assert saved["per_test"] is True
    assert saved["run"] == "failed"
    assert saved["failing"] == ["tests/test_shop.py::test_login"]
    assert (sidecar / "cache" / "trees" / head / "ran.txt").is_file()


def test_rule16_without_junit_it_records_the_whole_run(tmp_path):
    """REQ-048 AC5: rule 16 and Q-S0041-19 (no `{junit}`: the whole run is the residual)."""
    clone = make_clone(tmp_path / "clone")
    command = command_of("whole_stub.py", junit=False)
    sidecar = make_sidecar(tmp_path / "side", command)
    done = baseline(clone, sidecar, "--approve")
    assert done.returncode == 0, done.stdout + done.stderr
    saved = record(sidecar)
    assert saved["per_test"] is False
    assert saved["run"] == "failed"
    assert saved["failing"] is None
    sidecar2 = make_sidecar(tmp_path / "side2", command_of("green_stub.py", junit=False))
    assert baseline(clone, sidecar2, "--approve").returncode == 0
    assert record(sidecar2)["run"] == "passed"


def test_rule16_the_declared_test_command_of_the_survey_is_the_fallback(tmp_path):
    """REQ-048 AC5: rule 16 (no setting: the one test command the inventory declares)."""
    clone = make_clone(tmp_path / "clone")
    sidecar = make_sidecar(tmp_path / "side", None)
    (sidecar / "cache").mkdir()
    declared = command_of("green_stub.py", junit=False)
    inventory = {"manifests": [{"path": "pyproject.toml", "test_commands": [declared]}]}
    (sidecar / "cache" / "inventory.json").write_text(json.dumps(inventory), encoding="utf-8")
    done = baseline(clone, sidecar)
    assert done.returncode == 0, done.stdout + done.stderr
    assert declared in done.stdout


@pytest.mark.parametrize("commands", [None, [], ["make check", "npm test"]])
def test_rule16_no_single_test_command_refuses_naming_the_setting(tmp_path, commands):
    """REQ-048 AC5: rule 16 (none, or several declared: refused naming `test_command`)."""
    clone = make_clone(tmp_path / "clone")
    sidecar = make_sidecar(tmp_path / "side", None)
    if commands is not None:
        (sidecar / "cache").mkdir()
        rows = [
            {"path": f"m{i}/package.json", "test_commands": [c]} for i, c in enumerate(commands)
        ]
        (sidecar / "cache" / "inventory.json").write_text(
            json.dumps({"manifests": rows}), encoding="utf-8"
        )
    done = baseline(clone, sidecar, "--approve")
    assert done.returncode == 1
    assert "personal.test_command" in done.stdout
    for value in commands or []:
        assert value not in done.stdout
    assert not (sidecar / "records" / "baseline.json").exists()


def test_rule4_the_clone_and_its_git_folder_are_unchanged_by_a_run(tmp_path):
    """REQ-048 AC5: rules 4 and 16 (the tree is archived in the sidecar; the clone is untouched)."""
    clone = make_clone(tmp_path / "clone")
    sidecar = make_sidecar(tmp_path / "side", command_of("junit_stub.py", junit=True))
    before = snapshot(clone)
    assert baseline(clone, sidecar, "--approve").returncode == 0
    assert snapshot(clone) == before
    assert run_git(clone, "status", "--porcelain") == ""


def test_rule16_a_folder_that_is_not_a_sidecar_is_refused(tmp_path):
    """REQ-048 AC5: rule 16 (no `[personal]` table: refused naming the setting)."""
    clone = make_clone(tmp_path / "clone")
    other = tmp_path / "other"
    other.mkdir()
    (other / "agk.toml").write_text('default_branch = "main"\n', encoding="utf-8")
    done = baseline(clone, other, "--approve")
    assert done.returncode == 1
    assert "setting: personal" in done.stdout


# Rule 18: the ten keys of the `[personal]` table.


def table_of(tmp_path: Path, name: str, line: str) -> Path:
    root = tmp_path / name
    root.mkdir()
    forge = "" if line.startswith("forge ") else 'forge = "files"\n'
    (root / "agk.toml").write_text(f"[personal]\n{forge}{line}\n", encoding="utf-8")
    return root


ACCEPTED = [
    'level = "evidence"',
    'ai_disclosure = "pr-note"',
    "survey_budget = 1",
    "survey_budget = 1000",
    "quote_lines = 0",
    "quote_lines = 20",
    'sync_remote = "backup"',
    'test_command = "make test"',
    "sign = true",
    "team_refs = false",
    "schema = 1",
    "schema = 7",
]

REFUSED = [
    ("forge", 'forge = "github"', "github"),
    ("level", "level = 3", "3"),
    ("ai_disclosure", 'ai_disclosure = "hidden"', "hidden"),
    ("survey_budget", "survey_budget = 0", "0"),
    ("survey_budget", "survey_budget = 1001", "1001"),
    ("survey_budget", "survey_budget = true", "true"),
    ("survey_budget", 'survey_budget = "forty"', "forty"),
    ("quote_lines", "quote_lines = 21", "21"),
    ("quote_lines", "quote_lines = -1", "-1"),
    ("quote_lines", "quote_lines = 2.5", "2.5"),
    ("sync_remote", 'sync_remote = ""', '""'),
    ("sync_remote", "sync_remote = 9", "9"),
    ("test_command", 'test_command = ""', '""'),
    ("test_command", 'test_command = "   "', '"   "'),
    ("test_command", 'test_command = ["make"]', "make"),
    ("sign", 'sign = "yes"', "yes"),
    ("team_refs", "team_refs = 1", "1"),
    ("schema", "schema = 0", "0"),
    ("schema", "schema = false", "false"),
    ("skip_floor", "skip_floor = true", "true"),
]


@pytest.mark.parametrize("line", ACCEPTED)
def test_rule18_each_key_accepts_its_type_and_range(tmp_path, line):
    """REQ-048 AC5: rule 18 (the ten keys, each at its accepted values)."""
    table = common.personal_table(table_of(tmp_path, "ok", line))
    key = line.split(" = ")[0]
    assert key in table


@pytest.mark.parametrize("key,line,value", REFUSED)
def test_rule18_a_wrong_type_or_range_or_an_unknown_key_is_refused_naming_the_key(
    tmp_path, key, line, value
):
    """REQ-048 AC5: rule 18 (refused naming the key, never the value; no key weakens the floor)."""
    with pytest.raises(common.CheckError) as err:
        common.personal_table(table_of(tmp_path, "bad", line))
    message = str(err.value)
    assert key in message
    assert "setting" in message
    assert value not in message.replace(key, "")


def test_rule18_a_repository_without_the_table_reads_as_today(tmp_path):
    """REQ-048 AC5: rule 18 (no `[personal]` table: None, the settings as before)."""
    root = tmp_path / "team"
    root.mkdir()
    (root / "agk.toml").write_text('default_branch = "main"\n', encoding="utf-8")
    assert common.personal_table(root) is None
    assert common.load_config(root)["default_branch"] == "main"


# Rule 18: the floor (brief #947), a secret scan and no new failing test, at every level.

FLOOR_STUB = """import pathlib, sys
bad = pathlib.Path("bad.txt").is_file()
cases = [("tests/test_shop.py", "test_cart_total", not bad), ("tests/test_shop.py", "test_login", False)]
if bad:
    cases.append(("tests/test_shop.py", "test_new_on_head", False))
rows = []
for file, name, ok in cases:
    body = "" if ok else '<failure message="assert 1 == 2"/>'
    rows.append(f'<testcase classname="x" file="{file}" name="{name}">{body}</testcase>')
pathlib.Path(sys.argv[1]).write_text("<testsuite>" + "".join(rows) + "</testsuite>", encoding="utf-8")
pathlib.Path("ran.txt").write_text("ran", encoding="utf-8")
sys.exit(1)
"""
WHOLE_FLOOR_STUB = """import pathlib, sys
pathlib.Path("ran.txt").write_text("ran", encoding="utf-8")
sys.exit(1 if pathlib.Path("bad.txt").is_file() else 0)
"""
SCAN_FINDING = "finding: shop.py:3 value-example-com-1234"
LEVELS = ["light", "tests-first", "spec", "review", "evidence"]


def scanner_dir(tmp_path: Path, finding: bool | None) -> str:
    """A PATH with git and, unless FINDING is None, a stub gitleaks that writes nothing."""
    bin_dir = tmp_path / ("bin-none" if finding is None else f"bin-{finding}")
    bin_dir.mkdir()
    git = shutil.which("git")
    assert git
    (bin_dir / "git").symlink_to(git)
    if finding is not None:
        stub = bin_dir / "gitleaks"
        code = f"print({SCAN_FINDING!r})\nraise SystemExit(1)" if finding else "raise SystemExit(0)"
        stub.write_text(f"#!{sys.executable}\nimport sys\n{code}\n", encoding="utf-8")
        stub.chmod(0o755)
    return str(bin_dir)


def floor_clone(tmp_path: Path, head_bad: bool, base_bad: bool = False) -> Path:
    """A clone whose `main` is the base and whose `work` branch is the head."""
    clone = tmp_path / "clone"
    clone.mkdir()
    run_git(clone, "init", "-q", "-b", "main")
    for key, value in (("user.email", "t@example.com"), ("user.name", "t"), ("commit.gpgsign", "false")):
        run_git(clone, "config", key, value)
    (clone / "floor_stub.py").write_text(FLOOR_STUB, encoding="utf-8")
    (clone / "whole_floor_stub.py").write_text(WHOLE_FLOOR_STUB, encoding="utf-8")
    if base_bad:
        (clone / "bad.txt").write_text("base", encoding="utf-8")
    run_git(clone, "add", "-A")
    run_git(clone, "commit", "-q", "-m", "base")
    run_git(clone, "checkout", "-q", "-b", "work")
    (clone / "shop.py").write_text("TOTAL = 3\n", encoding="utf-8")
    if head_bad:
        (clone / "bad.txt").write_text("head", encoding="utf-8")
    run_git(clone, "add", "-A")
    run_git(clone, "commit", "-q", "-m", "head")
    return clone


def floor_sidecar(tmp_path: Path, junit: bool, level: str | None = None) -> Path:
    stub = "floor_stub.py" if junit else "whole_floor_stub.py"
    sidecar = make_sidecar(tmp_path / "side", command_of(stub, junit))
    if level is not None:
        with (sidecar / "agk.toml").open("a", encoding="utf-8") as fh:
            fh.write(f'level = "{level}"\n')
    return sidecar


def floor(clone: Path, sidecar: Path, path: str, *extra: str):
    skip = ("AGK_HOME", "AGK_BASE", "GITHUB_BASE_REF", "CI", "PATH")
    env = {k: v for k, v in os.environ.items() if k not in skip}
    env["PATH"] = path
    cmd = [sys.executable, str(SCRIPTS / "personal.py"), "floor", "--clone", str(clone)]
    return subprocess.run(  # nosec B603 - fixed argument list, no shell
        [*cmd, "--sidecar", str(sidecar), "--base", "main", *extra],
        capture_output=True, text=True, env=env,
    )


def step_lines(out: str) -> list[str]:
    return [ln for ln in out.splitlines() if ln.startswith("floor: ") and "level" not in ln]


def test_floor_a_clean_range_passes_the_secret_scan(tmp_path):
    """REQ-048 AC5: rule 18 (gitleaks over the range finds nothing: step one passes)."""
    clone = floor_clone(tmp_path, head_bad=False)
    done = floor(clone, floor_sidecar(tmp_path, junit=True), scanner_dir(tmp_path, False), "--approve")
    assert "floor: secret-scan ok" in done.stdout, done.stdout + done.stderr
    assert "floor: no-regression ok" in done.stdout
    assert done.stdout.strip().endswith("floor: passed")
    assert done.returncode == 0


def test_floor_a_finding_fails_naming_the_step_never_the_finding(tmp_path):
    """REQ-048 AC5: rule 18 and principle 8 (a finding fails step one; its text is not printed)."""
    clone = floor_clone(tmp_path, head_bad=False)
    done = floor(clone, floor_sidecar(tmp_path, junit=True), scanner_dir(tmp_path, True), "--approve")
    assert done.returncode == 1
    assert "floor: secret-scan FAIL" in done.stdout
    assert "value-example-com" not in done.stdout + done.stderr
    assert done.stdout.strip().endswith("floor: failed")


def test_floor_without_gitleaks_fails_with_the_line_of_q_s0041_15(tmp_path):
    """REQ-048 AC5: rule 18 and Q-S0041-15 (no gitleaks: the floor fails; no deferral to CI)."""
    clone = floor_clone(tmp_path, head_bad=False)
    done = floor(clone, floor_sidecar(tmp_path, junit=True), scanner_dir(tmp_path, None), "--approve")
    assert done.returncode == 1
    assert "floor: secret scan not run (gitleaks not installed)" in done.stdout
    assert "deferred" not in done.stdout


def test_floor_per_test_a_test_that_passed_on_the_base_and_fails_on_the_head_fails(tmp_path):
    """REQ-048 AC5: rule 18 (with `{junit}`: the regression is named by its test id)."""
    clone = floor_clone(tmp_path, head_bad=True)
    done = floor(clone, floor_sidecar(tmp_path, junit=True), scanner_dir(tmp_path, False), "--approve")
    assert done.returncode == 1
    assert "floor: no-regression FAIL" in done.stdout
    assert "tests/test_shop.py::test_cart_total" in done.stdout
    assert "test_login" not in done.stdout
    assert "test_new_on_head" not in done.stdout


def test_floor_per_test_a_test_already_failing_on_the_base_does_not_fail(tmp_path):
    """REQ-048 AC5: rule 18 (an old failure is not a regression, though the head run exits 1)."""
    clone = floor_clone(tmp_path, head_bad=False)
    done = floor(clone, floor_sidecar(tmp_path, junit=True), scanner_dir(tmp_path, False), "--approve")
    assert "floor: no-regression ok" in done.stdout, done.stdout + done.stderr
    assert done.returncode == 0


@pytest.mark.parametrize(
    "base_bad,head_bad,line,code",
    [
        (False, False, "floor: no-regression ok", 0),
        (False, True, "floor: no-regression FAIL", 1),
        (True, True, "floor: no-regression unknown", 1),
        (True, False, "floor: no-regression unknown", 1),
    ],
)
def test_floor_whole_run_compares_the_two_runs(tmp_path, base_bad, head_bad, line, code):
    """REQ-048 AC5: rule 18 and Q-S0041-19 (no `{junit}`: a failing base is `unknown`, never a pass)."""
    clone = floor_clone(tmp_path, head_bad=head_bad, base_bad=base_bad)
    done = floor(clone, floor_sidecar(tmp_path, junit=False), scanner_dir(tmp_path, False), "--approve")
    assert line in done.stdout, done.stdout + done.stderr
    assert done.returncode == code
    if code:
        assert done.stdout.strip().endswith("floor: failed")


def test_floor_without_approve_runs_no_test_command(tmp_path):
    """REQ-048 AC5: rule 18 (without `--approve` the two runs are printed and nothing runs)."""
    clone = floor_clone(tmp_path, head_bad=False)
    sidecar = floor_sidecar(tmp_path, junit=True)
    done = floor(clone, sidecar, scanner_dir(tmp_path, False))
    assert done.returncode == 1
    assert "would run" in done.stdout
    assert "--approve" in done.stdout
    assert "floor: no-regression not run" in done.stdout
    assert not list(sidecar.rglob("ran.txt"))
    assert not (sidecar / "cache").exists()


@pytest.mark.parametrize("level", LEVELS)
def test_floor_every_level_gives_the_same_two_steps(tmp_path, level):
    """REQ-048 AC5: rule 18 and principle 11 (`level` is printed; no level changes a step)."""
    clone = floor_clone(tmp_path, head_bad=True)
    path = scanner_dir(tmp_path, False)
    plain = floor(clone, floor_sidecar(tmp_path / "a", junit=True), path, "--approve")
    leveled = floor(clone, floor_sidecar(tmp_path / "b", junit=True, level=level), path, "--approve")
    assert f"floor: level {level}" in leveled.stdout
    assert "floor: level light" in plain.stdout
    assert step_lines(leveled.stdout) == step_lines(plain.stdout)
    assert len(step_lines(leveled.stdout)) == 3
    assert leveled.returncode == plain.returncode == 1


def test_floor_the_clone_and_its_git_folder_are_unchanged(tmp_path):
    """REQ-048 AC5: rules 4 and 18 (both runs are in the sidecar's trees; the clone is only read)."""
    clone = floor_clone(tmp_path, head_bad=True)
    before = snapshot(clone)
    done = floor(clone, floor_sidecar(tmp_path, junit=True), scanner_dir(tmp_path, False), "--approve")
    assert done.returncode == 1
    assert snapshot(clone) == before
    assert run_git(clone, "status", "--porcelain") == ""
