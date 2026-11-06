"""A flaky test is rerun alone once and recorded, never hidden (brief #670, ADR-0323, proposed
amendment 135 to SPEC-0044 rule 1).

With `[testing] rerun_alone = true`, `project_tests.py` reruns each test that failed in the full run
alone, once. A pass alone is one strike in `docs/runs/flakes.md`, written by `flakes.py add` (owner:
`AGK_SESSION`, else `unassigned`; expiry 30 days), with the failure's signature and issue action
printed; a test that fails alone is a real failure. The run exits 0 only when every failed test
passed alone. Without the key every command behaves as today. `flakes.py check` lists an entry past
its expiry. A fixture suite (one flaky, one failing, one passing) in `tmp_path`, invented data, no
network.
"""

from __future__ import annotations

import os
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
from pathlib import Path

import flakes
import impact
import pytest
from common import CheckError

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts" / "agk"
LEDGER = "docs/runs/flakes.md"
HEAD = (
    "| test | owner | strikes | status | expires | issue |\n| --- | --- | --- | --- | --- | --- |\n"
)
TODAY = "2031-05-10"
FLAKY = "tests/test_b_flaky.py::test_flaky"
FAILING = "tests/test_c_fail.py::test_fails"

# The flaky test fails only after another file of the suite ran in the same process.
SUITE = {
    "tests/test_a_dirty.py": "import builtins\n\n\ndef test_dirty():\n"
    "    builtins.fixture_dirty = True\n",
    "tests/test_b_flaky.py": "import builtins\n\n\ndef test_flaky():\n"
    "    assert not getattr(builtins, 'fixture_dirty', False), 'shared state left over'\n",
    "tests/test_c_fail.py": "def test_fails():\n    assert 1 == 2, 'always red'\n",
    "tests/test_d_pass.py": "def test_passes():\n    assert True\n",
}


def git(root: Path, *args: str) -> None:
    subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
        ["git", *args], cwd=root, capture_output=True, text=True, check=True
    )


def project(tmp_path: Path, testing: str | None, failing: bool = True, command: str = "") -> Path:
    root = tmp_path / "proj"
    for rel, text in SUITE.items():
        if failing or "fail" not in rel:
            (root / rel).parent.mkdir(parents=True, exist_ok=True)
            (root / rel).write_text(text, encoding="utf-8")
    command = command or f"{sys.executable} -m pytest -q -p no:cacheprovider tests"
    text = f"default_branch = \"main\"\nproject_tests = '{command}'\n"
    if testing is not None:
        text += "[testing]\n" + testing
    (root / "agk.toml").write_text(text, encoding="utf-8")
    git(root, "init", "-q", "-b", "main")
    return root


def run_tests(root: Path, *args: str, session: str | None = None):
    env = {k: v for k, v in os.environ.items() if k not in ("EVENT", "AGK_BASE", "AGK_SESSION")}
    env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
    if session:
        env["AGK_SESSION"] = session
    return subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, str(SCRIPTS / "project_tests.py"), *args],
        cwd=root,
        capture_output=True,
        text=True,
        env=env,
        timeout=300,
    )


def run_flakes(root: Path, *args: str):
    proc = subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, str(SCRIPTS / "flakes.py"), *args],
        cwd=root,
        capture_output=True,
        text=True,
    )
    return proc.returncode, proc.stdout.splitlines()


def rows(root: Path) -> list[list[str]]:
    text = (root / LEDGER).read_text(encoding="utf-8")
    found = [flakes.cells(line) for line in text.splitlines()]
    return [r for r in found if r and r[0] not in ("test", "---")]


# --- answer 1 and the payload: absent key, today's behaviour ------------------------------------


def test_without_the_key_a_flaky_failure_is_red_and_nothing_is_written(tmp_path):
    """REQ-051 AC2: brief #670 answer 1 (key absent: today's behaviour, no rerun, no ledger)."""
    root = project(tmp_path, None, failing=False)
    proc = run_tests(root)
    assert proc.returncode == 1
    assert "rerun" not in proc.stdout
    assert "project tests:" not in proc.stdout
    assert not (root / LEDGER).exists()


def test_with_a_testing_table_but_no_key_nothing_is_rerun(tmp_path):
    """REQ-051 AC2: brief #670 answer 1 (`rerun_alone` absent from the table: today's path)."""
    root = project(tmp_path, "workers = 1\n", failing=False)
    proc = run_tests(root)
    assert proc.returncode == 1
    assert "rerun" not in proc.stdout
    assert not (root / LEDGER).exists()


def test_rerun_alone_false_is_todays_behaviour(tmp_path):
    """REQ-051 AC2: brief #670 answer 1 (`rerun_alone = false`)."""
    root = project(tmp_path, "rerun_alone = false\n", failing=False)
    proc = run_tests(root)
    assert proc.returncode == 1
    assert "rerun" not in proc.stdout
    assert not (root / LEDGER).exists()


def test_a_bad_value_is_refused_naming_the_setting(tmp_path):
    """REQ-051 AC2: brief #670 answer 1 (a malformed key names the setting, never the value)."""
    root = project(tmp_path, 'rerun_alone = "yes"\n')
    with pytest.raises(CheckError, match=r"setting: testing\.rerun_alone"):
        impact.testing_table(root)
    proc = run_tests(root)
    assert proc.returncode == 1
    assert "setting: testing.rerun_alone" in proc.stdout
    assert '"yes"' not in proc.stdout


def test_the_reader_is_false_without_the_table_or_the_key(tmp_path):
    """REQ-051 AC2: brief #670 answer 1 (`impact.rerun_alone` defaults to false)."""
    assert impact.rerun_alone(project(tmp_path / "a", None)) is False
    assert impact.rerun_alone(project(tmp_path / "b", "workers = 1\n")) is False
    assert impact.rerun_alone(project(tmp_path / "c", "rerun_alone = true\n")) is True


def test_the_option_without_the_setting_is_refused(tmp_path):
    """REQ-051 AC2: brief #670 answer 1 (`--rerun-alone` is on only with the setting)."""
    root = project(tmp_path, None, failing=False)
    proc = run_tests(root, "--rerun-alone")
    assert proc.returncode == 1
    assert "setting: testing.rerun_alone" in proc.stdout
    assert not (root / LEDGER).exists()


def test_no_rerun_alone_turns_it_off_for_one_call(tmp_path):
    """REQ-051 AC2: brief #670 answer 1 (`--no-rerun-alone` is today's path)."""
    root = project(tmp_path, "rerun_alone = true\n", failing=False)
    proc = run_tests(root, "--no-rerun-alone")
    assert proc.returncode == 1
    assert "rerun" not in proc.stdout
    assert not (root / LEDGER).exists()


def test_an_unknown_option_is_refused(tmp_path):
    """REQ-051 AC2: brief #670 answer 1 (a bad call names the option)."""
    root = project(tmp_path, None)
    proc = run_tests(root, "--retry")
    assert proc.returncode == 2
    assert "usage: project_tests.py" in proc.stdout


# --- answers 1 to 3: the rerun, the strike and a real failure -----------------------------------


def test_a_flaky_test_passes_alone_records_one_strike_and_the_run_is_green(tmp_path):
    """REQ-051 AC2: brief #670 answers 1 and 2 (a pass alone is a strike; the rest passed)."""
    root = project(tmp_path, "rerun_alone = true\n", failing=False)
    proc = run_tests(root, session="builder-b9")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert f"project tests: rerun alone: {FLAKY} passed; strike 1 recorded in {LEDGER}" in (
        proc.stdout
    )
    assert "project tests: failure signature " in proc.stdout
    assert "project tests: failure issue: action: none (setting: failures.issues)" in proc.stdout
    [row] = rows(root)
    assert row[:4] == [FLAKY, "builder-b9", "1", "watch"]
    assert flakes.as_date(row[4]) is not None
    assert row[5] == ""


def test_the_owner_is_unassigned_without_a_session(tmp_path):
    """REQ-051 AC2: brief #670 answer 2 (owner: the session, else `unassigned`)."""
    root = project(tmp_path, "rerun_alone = true\n", failing=False)
    proc = run_tests(root)
    assert proc.returncode == 0, proc.stdout
    assert rows(root)[0][1] == "unassigned"


def test_a_test_that_fails_alone_is_a_real_failure(tmp_path):
    """REQ-051 AC2: brief #670 answer 3 (a failure alone stays red; the flaky is a strike)."""
    root = project(tmp_path, "rerun_alone = true\n")
    proc = run_tests(root, session="builder-b9")
    assert proc.returncode == 1
    assert f"project tests: rerun alone: {FAILING} failed again" in proc.stdout
    assert f"project tests: rerun alone: {FLAKY} passed; strike 1" in proc.stdout
    assert [r[0] for r in rows(root)] == [FLAKY]


def test_a_second_flaky_run_is_strike_two_and_a_brief_is_due(tmp_path):
    """REQ-051 AC2: brief #670 answer 2 (two strikes: a brief is due; the expiry is kept)."""
    root = project(tmp_path, "rerun_alone = true\n", failing=False)
    assert run_tests(root, session="builder-b9").returncode == 0
    first = rows(root)[0][4]
    proc = run_tests(root, session="builder-c2")
    assert proc.returncode == 0
    assert f"strike 2 recorded in {LEDGER}" in proc.stdout
    assert "brief due" in proc.stdout
    [row] = rows(root)
    assert row[1:5] == ["builder-b9", "2", "watch", first]


def test_a_non_pytest_command_is_not_rerun(tmp_path):
    """REQ-051 AC2: brief #670 answer 3 (no rerun the kit cannot build: today's exit, one line)."""
    root = project(tmp_path, "rerun_alone = true\n", command="exit 3")
    proc = run_tests(root)
    assert proc.returncode == 3
    assert "project tests: rerun alone needs a pytest command" in proc.stdout
    assert not (root / LEDGER).exists()


def test_a_green_run_reruns_nothing(tmp_path):
    """REQ-051 AC2: brief #670 answer 1 (no failure, no rerun, no ledger)."""
    root = project(tmp_path, "rerun_alone = true\n", failing=False)
    (root / "tests" / "test_a_dirty.py").unlink()
    proc = run_tests(root)
    assert proc.returncode == 0
    assert "rerun" not in proc.stdout
    assert not (root / LEDGER).exists()


def test_the_rerun_command_keeps_the_config_options_and_drops_the_paths():
    """REQ-051 AC2: brief #670 answer 1 (the test alone, with the project's -c and -p)."""
    import project_tests

    command = "python3 -m pytest -q -c tests/kit/pytest.ini -p no:cacheprovider tests/kit"
    assert project_tests.alone_command(command, "tests/kit/test_a.py::t") == (
        "python3 -m pytest -c tests/kit/pytest.ini -p no:cacheprovider tests/kit/test_a.py::t"
    )
    assert project_tests.alone_command("A=1 pytest tests", "t.py::x") == "A=1 pytest t.py::x"
    assert project_tests.alone_command("make test", "t.py::x") is None


# --- answer 2: `flakes.py add` and `flakes.py check` --------------------------------------------


def test_add_creates_the_ledger_with_one_strike(repo):
    """REQ-051 AC2: brief #670 answer 2 (`flakes.py add`: owner, strikes, watch, 30-day expiry)."""
    code, out = run_flakes(
        repo.root, "add", "--test", FLAKY, "--owner", "builder-b9", "--today", TODAY
    )
    assert code == 0, out
    assert out == [
        f"flakes: strike 1 for {FLAKY} (owner builder-b9; expires 2031-06-09) in {LEDGER}"
    ]
    assert rows(repo.root) == [[FLAKY, "builder-b9", "1", "watch", "2031-06-09", ""]]
    assert run_flakes(repo.root, "--today", TODAY)[0] == 0


def test_add_counts_a_second_strike_keeps_owner_and_expiry_and_sets_the_issue(repo):
    """REQ-051 AC2: brief #670 answer 2 (strike two is a brief due unless an issue is named)."""
    repo.commit(
        {
            LEDGER: "# Flake ledger\n\n"
            + HEAD
            + f"| {FLAKY} | builder-b9 | 1 | watch | 2031-05-20 |  |\n"
            + "| tests/test_x.py::t | conductor | 0 | watch |  |  |\n\nNotes below.\n"
        }
    )
    code, out = run_flakes(
        repo.root, "add", "--test", FLAKY, "--owner", "builder-c2", "--today", TODAY
    )
    assert code == 0
    assert out[0].startswith(f"flakes: strike 2 for {FLAKY} (owner builder-b9; expires 2031-05-20)")
    assert out[1] == f"flakes: brief due: {FLAKY} has 2 strikes and no issue"
    code, out = run_flakes(repo.root, "add", "--test", FLAKY, "--issue", "#71", "--today", TODAY)
    assert code == 0
    text = (repo.root / LEDGER).read_text(encoding="utf-8")
    assert f"| {FLAKY} | builder-b9 | 3 | watch | 2031-05-20 | #71 |" in text
    assert text.endswith("\nNotes below.\n")
    assert rows(repo.root)[1][0] == "tests/test_x.py::t"


def test_add_refuses_a_malformed_ledger_and_a_bad_test_id(repo):
    """REQ-051 AC2: brief #670 answer 2 (a refusal names the option or the ledger)."""
    bad = "# Flake ledger\n\n" + HEAD + "| tests/test_a.py::t | a person | 1 | watch |  |  |\n"
    repo.commit({LEDGER: bad})
    code, out = run_flakes(repo.root, "add", "--test", FLAKY, "--today", TODAY)
    assert code == 2
    assert out == [f"flakes: the ledger has malformed rows; fix them first ({LEDGER})"]
    assert (repo.root / LEDGER).read_text(encoding="utf-8") == bad
    code, out = run_flakes(repo.root, "add", "--test", "a|b", "--today", TODAY)
    assert (code, out) == (2, ["flakes: the test id is not one table cell (option: --test)"])
    code, out = run_flakes(repo.root, "add", "--test", FLAKY, "--owner", "a person")
    assert (code, out) == (2, ["flakes: the owner is not one role or session id (option: --owner)"])
    code, out = run_flakes(repo.root, "add", "--today", TODAY)
    assert code == 2


def test_check_lists_a_watched_strike_past_its_expiry(repo):
    """REQ-051 AC2: brief #670 answer 2 (past the expiry the entry fails the check)."""
    row = f"| {FLAKY} | builder-b9 | 1 | watch | 2031-05-09 |  |"
    repo.commit({LEDGER: "# Flake ledger\n\n" + HEAD + row + "\n"})
    code, out = run_flakes(repo.root, "check", "--today", TODAY)
    assert code == 1
    assert out[0] == f"expired: line 5: {FLAKY} (owner builder-b9; watched until 2031-05-09)"
    assert run_flakes(repo.root, "--today", TODAY) == (code, out)
    assert run_flakes(repo.root, "check", "--today", "2031-05-09")[0] == 0
