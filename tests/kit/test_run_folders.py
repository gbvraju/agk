"""The run folders are retired without a break (SPEC-0046 rule 11, build (f), REQ-053 AC7).

The three `[testing]` keys of ADR-0299 (`results_dir`, `keep_passed`, `keep_runs`) stay accepted
with their checks, so a malformed value is still refused naming the setting, but they do nothing:
no folder is made and `AGK_RUN_DIR` is not set. When one is set, `prepush.py` and `doctor.py` print
one line `deprecated: testing.results_dir (ADR-0303)`. Build (g) removes the keys in a later
release.

The projects are invented; nothing reaches the network.
"""

from __future__ import annotations

import json
from pathlib import Path

import doctor
import impact
import proof as proof_module
import pytest
from common import CheckError
from test_prepush import MK_OK, TOML, path_with, scanner
from test_proof import start

LINE = "deprecated: testing.results_dir (ADR-0303)"
ON = 'results_dir = ".agk-runs"\n'
UNSET = 'test -z "${AGK_RUN_DIR+set}"'  # passes only when the variable is not set


def settings(tmp_path: Path, testing: str | None = ON) -> Path:
    (tmp_path / "agk.toml").write_text(
        'default_branch = "main"\n' + (f"[testing]\n{testing}" if testing is not None else ""),
        encoding="utf-8",
    )
    return tmp_path


@pytest.mark.parametrize(
    ("testing", "expected"),
    [
        (None, None),
        ('profile = "balanced"\n', None),
        (ON, LINE),
        ("keep_passed = true\n", LINE),
        ("keep_runs = 3\n", LINE),
        (ON + "keep_passed = false\nkeep_runs = 5\n", LINE),
    ],
)
def test_the_deprecation_line_when_one_key_is_set(tmp_path, testing, expected):
    """REQ-053 AC7: SPEC-0046 rule 11 (one line when any of the three keys is set, else none)."""
    assert impact.run_folder_deprecation(settings(tmp_path, testing)) == expected


@pytest.mark.parametrize(
    ("line", "setting"),
    [
        ('results_dir = "../out"\n', "testing.results_dir"),
        ('results_dir = "/tmp/out"\n', "testing.results_dir"),
        ("results_dir = 3\n", "testing.results_dir"),
        ('keep_passed = "yes"\n', "testing.keep_passed"),
        ("keep_runs = 0\n", "testing.keep_runs"),
        ("keep_runs = true\n", "testing.keep_runs"),
    ],
)
def test_the_keys_keep_their_checks(tmp_path, line, setting):
    """REQ-053 AC7: SPEC-0046 rule 11 (accepted with their checks: a malformed value is refused
    naming the setting, never the value)."""
    with pytest.raises(CheckError) as caught:
        impact.run_folder_deprecation(settings(tmp_path, line))
    assert f"(setting: {setting})" in str(caught.value)
    assert "out" not in str(caught.value).replace("testing.", "")


def test_proof_has_no_run_folder_any_more():
    """REQ-053 AC7: SPEC-0046 rule 11 (no folder is made by any run)."""
    assert not hasattr(proof_module, "run_folder")
    assert not hasattr(impact, "run_settings")


def prepush_project(repo, command: str, testing: str = "[testing]\n" + ON) -> None:
    toml = TOML.replace("echo RAN_PROJECT_TESTS", command)
    files = {"agk.toml": toml + testing, "agk.mk": MK_OK, "src/code.txt": "base\n"}
    repo.commit(files, "base")
    repo.branch("feature")
    repo.commit({"src/code.txt": "change\n", "tests/test_new.py": "# new\n"}, "change")


@pytest.fixture
def outside(tmp_path_factory) -> Path:
    """A folder outside the fixture repository, so the records keep its tree clean."""
    return tmp_path_factory.mktemp("outside")


@pytest.mark.parametrize(
    "testing",
    [
        "[testing]\n" + ON,
        '[testing]\nprofile = "thorough"\nkeep_passed = true\nkeep_runs = 3\n' + ON,
    ],
)
def test_prepush_with_the_keys_makes_no_folder_sets_no_variable_and_says_so(
    repo, outside, testing
):
    """REQ-053 AC7: SPEC-0046 rule 11 (no folder, no AGK_RUN_DIR, no `run_dir`, one line)."""
    prepush_project(repo, UNSET, testing)
    record = outside / "record.json"
    args = ["--record", str(record), "--no-lock"]
    proc = repo.run("prepush.py", *args, PATH=path_with(scanner(outside, 0)))
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert proc.stdout.splitlines().count(LINE) == 1
    assert not (repo.root / ".agk-runs").exists()
    data = json.loads(record.read_text(encoding="utf-8"))
    assert "run_dir" not in data
    assert data["notes"].count(LINE) == 1
    assert repo.git("status", "--porcelain") == ""


def test_a_failed_prepush_with_the_keys_makes_no_folder(repo, outside):
    """REQ-053 AC7: SPEC-0046 rule 11 (a failure keeps nothing on disk either)."""
    prepush_project(repo, 'echo evidence > "${AGK_RUN_DIR:-/dev/null}"; exit 3')
    proc = repo.run("prepush.py", PATH=path_with(scanner(outside, 0)))
    assert proc.returncode == 1, proc.stdout + proc.stderr
    assert LINE in proc.stdout.splitlines()
    assert not (repo.root / ".agk-runs").exists()
    assert repo.git("status", "--porcelain") == ""


@pytest.mark.parametrize("testing", ["", '[testing]\nprofile = "thorough"\n'])
def test_without_the_keys_prepush_prints_no_deprecation(repo, outside, testing):
    """REQ-053 AC7: SPEC-0046 rule 11 (nothing changes for a project without the keys)."""
    prepush_project(repo, UNSET, testing)
    proc = repo.run("prepush.py", "--no-lock", PATH=path_with(scanner(outside, 0)))
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "deprecated:" not in proc.stdout


def test_doctor_prints_the_deprecation_line(tmp_path):
    """REQ-053 AC7: SPEC-0046 rule 11 (doctor's line when a key is set, none without)."""
    assert doctor.deprecation_lines(settings(mk(tmp_path / "on"))) == [LINE]
    assert doctor.deprecation_lines(settings(mk(tmp_path / "off"), None)) == []
    assert doctor.deprecation_lines(settings(mk(tmp_path / "bad"), "keep_runs = 0\n")) == []
    text = doctor.render_text([], "0.0.0", None, [LINE])
    assert text.splitlines()[-2:] == [LINE, "summary: 0 ok, 0 fail, 0 cannot-check"]


def mk(path: Path) -> Path:
    path.mkdir()
    return path


def test_proof_sets_no_run_folder(repo):
    """REQ-053 AC7: SPEC-0046 rule 11 (proof's command sees no AGK_RUN_DIR, no folder made)."""
    start(repo, 'test -z "$AGK_RUN_DIR" && test -f feature.txt')
    repo.commit({"feature.txt": "x\n", "tests/test_new.py": "# new\n"}, "change and test")
    proc = repo.run("proof.py", AGK_RUN_DIR="")
    assert proc.stdout.strip() == "proof: proven", proc.stdout + proc.stderr
    assert not (repo.root / ".agk-runs").exists()
