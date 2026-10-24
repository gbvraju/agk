"""Kit-only tests of the kit version the intake prints and checks (SPEC-0027 rules 1 to 3).

The script that ran says its kit version first and refuses to run against a project that records a
newer one. The script is copied into `tmp_path` with a manifest of the version under test, so each
case chooses the version of "the script that ran". No network and no model.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from conftest import KIT_ROOT, clean_env
from test_intake import SENTENCE, write
from test_intake import repo as intake_repo  # noqa: F401  (the fixture of test_intake)


@pytest.fixture
def repo(request):
    return request.getfixturevalue("intake_repo")


def script_copy(tmp_path: Path, version: str | None) -> Path:
    """A copy of the scripts with `kit/manifest.json` holding VERSION (none: no manifest)."""
    root = tmp_path / "plugin"
    shutil.copytree(KIT_ROOT / "scripts" / "agk", root / "scripts" / "agk")
    if version is not None:
        (root / "kit").mkdir()
        (root / "kit" / "manifest.json").write_text(json.dumps({"kit_version": version}))
    return root / "scripts" / "agk" / "intake.py"


def record(repo, version: str | None) -> None:
    if version is not None:
        write(repo, "agk.toml", f'version = "{version}"\n')


def run(script: Path, repo, *args: str):
    return subprocess.run(
        [sys.executable, str(script), *args, "--root", str(repo), "--date", "2026-10-18"],
        capture_output=True,
        text=True,
        env=clean_env(),
    )


def lines(proc) -> list[str]:
    return proc.stdout.splitlines()


# --- the first line (rule 1) ----------------------------------------------------------------------


@pytest.mark.parametrize(
    "args",
    [
        ("ids", "--sentence", SENTENCE, "--ref", "main"),
        ("check", "--base", "main"),
        ("check", "--final", "--base", "main"),
        ("next-steps", "--base", "main"),
        ("renumber", "REQ-004", "--ref", "main"),
        ("stub", "--req", "REQ-004", "--title", "Export", "--sentence", SENTENCE, "--ref", "main"),
    ],
    ids=["ids", "check", "check-final", "next-steps", "renumber", "stub"],
)
def test_ac1_every_command_prints_the_kit_version_of_the_script_first(repo, tmp_path, args):
    """REQ-034 AC1: rule 1 (the kit_version of the manifest beside the script)."""
    script = script_copy(tmp_path, "0.77.0")
    proc = run(script, repo, *args)
    assert lines(proc)[0] == "intake: kit 0.77.0", proc.stdout


def test_ac1_ids_prints_its_json_on_the_lines_after_the_version(repo, tmp_path):
    """REQ-034 AC1: rule 1 (the rest of the output is unchanged)."""
    script = script_copy(tmp_path, "0.77.0")
    proc = run(script, repo, "ids", "--sentence", SENTENCE, "--ref", "main")
    assert proc.returncode == 0 and lines(proc)[0] == "intake: kit 0.77.0"
    assert json.loads("\n".join(lines(proc)[1:]))["req"] == "REQ-004"


def test_ac1_a_usage_error_prints_no_version_and_a_manifest_that_cannot_be_read_refuses(
    repo, tmp_path
):
    """REQ-034 AC1: rule 1 (the version is never guessed)."""
    proc = run(script_copy(tmp_path / "a", "0.77.0"), repo, "frobnicate")
    assert proc.returncode == 2 and proc.stdout == ""
    proc = run(script_copy(tmp_path / "b", None), repo, "check", "--base", "main")
    assert proc.returncode == 1 and lines(proc)[0].startswith("refused: rule 1")
    assert "intake: kit" not in proc.stdout


# --- an older script is refused, a newer one runs (rules 2 and 3) ---------------------------------


def test_ac2_an_older_script_is_refused_naming_both_versions_and_writes_nothing(repo, tmp_path):
    """REQ-034 AC2: rule 2 (the first line is still the version)."""
    record(repo, "0.40.0")
    before = subprocess.run(
        ["git", "status", "--porcelain"], cwd=repo, capture_output=True, text=True
    ).stdout
    script = script_copy(tmp_path, "0.32.0")
    proc = run(
        script, repo, "stub", "--req", "REQ-004", "--title", "Export", "--sentence", SENTENCE
    )
    assert proc.returncode == 1
    assert lines(proc)[0] == "intake: kit 0.32.0"
    assert lines(proc)[1].startswith("refused: rule 2")
    assert "0.32.0" in lines(proc)[1] and "0.40.0" in lines(proc)[1]
    after = subprocess.run(
        ["git", "status", "--porcelain"], cwd=repo, capture_output=True, text=True
    ).stdout
    assert after == before.replace("?? agk.toml\n", "") + "?? agk.toml\n"  # only the test's file


def test_ac2_versions_are_compared_as_numbers_not_as_text(repo, tmp_path):
    """REQ-034 AC2: rule 2 (0.9.0 is older than 0.10.0)."""
    record(repo, "0.10.0")
    proc = run(script_copy(tmp_path, "0.9.0"), repo, "check", "--base", "main")
    assert proc.returncode == 1 and lines(proc)[1].startswith("refused: rule 2")
    record(repo, "0.9.0")
    proc = run(script_copy(tmp_path / "again", "0.10.0"), repo, "check", "--base", "main")
    assert not any(ln.startswith("refused: rule 2") for ln in lines(proc))


def test_ac3_a_newer_script_runs_and_prints_one_note(repo, tmp_path):
    """REQ-034 AC3: rule 3 (the note is the second line; the command goes on)."""
    record(repo, "0.40.0")
    proc = run(
        script_copy(tmp_path, "0.50.0"), repo, "ids", "--sentence", SENTENCE, "--ref", "main"
    )
    assert proc.returncode == 0
    assert lines(proc)[0] == "intake: kit 0.50.0"
    assert lines(proc)[1].startswith("note: ") and "0.50.0" in lines(proc)[1]
    assert "0.40.0" in lines(proc)[1]
    assert sum(ln.startswith("note: ") for ln in lines(proc)) == 1


@pytest.mark.parametrize("recorded", ["0.50.0", "main", None])
def test_ac3_an_equal_version_or_none_recorded_or_not_numbers_runs_with_no_note(
    repo, tmp_path, recorded
):
    """REQ-034 AC3: rule 3 (no comparison without two dotted numbers)."""
    record(repo, recorded)
    proc = run(
        script_copy(tmp_path, "0.50.0"), repo, "ids", "--sentence", SENTENCE, "--ref", "main"
    )
    assert proc.returncode == 0 and lines(proc)[0] == "intake: kit 0.50.0"
    assert not any(ln.startswith(("note:", "refused:")) for ln in lines(proc))


def test_ac3_the_comparison_makes_no_network_call():
    """REQ-034 AC3: rule 3 (the script imports no network module)."""
    import ast

    tree = ast.parse((KIT_ROOT / "scripts" / "agk" / "intake.py").read_text(encoding="utf-8"))
    names = {
        a.name.split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names
    }
    names |= {
        n.module.split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and n.module
    }
    assert not names & {"socket", "urllib", "http", "requests", "ssl"}
