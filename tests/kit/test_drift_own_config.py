"""This repository's own unused-code and coverage commands (REQ-011, brief 593, ADR-0290).

`agk.toml` sets `unused_code` (vulture over `scripts/agk` and `.claude/hooks`) and `coverage` (the
covered percentage of `scripts/agk` under a named part of the kit suite), so the Saturday
drift audit (SPEC-0004 rule 25) runs both for this repository. The runner is replaced in the
tests: no network, no tool is started, except one fixture run of vulture that is skipped where it
is not installed.
"""

from __future__ import annotations

import re
import shutil
import subprocess  # nosec B404 - fixed argument list, no shell
import sys
from pathlib import Path

import drift_fixtures as fx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "agk"))

import common  # noqa: E402
import drift_audit  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
HIDING = ("--ignore-names", "--ignore-decorators", "--exclude", "grep", "|| true", "|| :", "# noqa")


def own() -> dict[str, str]:
    cfg = common.load_config(ROOT)
    return {"unused_code": cfg["unused_code"], "coverage": cfg["coverage"]}


def run_d9() -> tuple[list, list[str]]:
    """D9 on this repository's agk.toml with a replaced runner; the commands it was given."""
    seen: list[str] = []

    def execute(command, root, limit, merge_stderr=False):
        seen.append(command)
        if "coverage" in command and "vulture" not in command:
            return 0, "19\n", ""
        return 3, "scripts/agk/a.py:1: unused variable 'x' (100% confidence)\n", ""

    return drift_audit.d9(ROOT, None, execute=execute), seen


# --- D9 on this repository's agk.toml ----------------------------------------------------------


def test_d9_runs_both_commands_of_this_repository():
    found, seen = run_d9()
    assert [f.subject for f in found] == ["coverage", "unused_code"]
    assert len(seen) == 2
    assert {f.subject: f.sentence for f in found}["coverage"].startswith("covered 19%")
    assert {f.subject: f.sentence for f in found}["unused_code"].startswith("1 unused-code finding")


def test_the_unused_code_command_is_vulture_over_code_and_hooks_at_80():
    command = own()["unused_code"]
    assert "vulture scripts/agk .claude/hooks --min-confidence 80" in command
    # installed first when missing, the way project_tests installs pytest
    assert "pip install" in command and "vulture" in command.split("pip install")[1]


def test_the_coverage_command_measures_scripts_agk_under_the_kit_suite():
    command = own()["coverage"]
    assert "--source=scripts/agk" in command and "tests/kit/pytest.ini" in command
    assert "AGK_KIT_TESTS=1" in command and "pip install" in command
    assert command.rstrip().endswith("--format=total")  # last line: the covered percentage only


def test_the_coverage_command_stays_inside_proof_timeout():
    """A named part of the suite, not all of it: the full suite alone takes 1161 s (ADR-0282)."""
    assert "tests/kit " not in own()["coverage"] + " " and "tests/kit_dev" not in own()["coverage"]
    assert re.search(r"tests/kit/test_\w+\*?\.py", own()["coverage"])


def test_the_settings_of_the_shipped_templates_stay_empty():
    for rel in ("kit/templates/agk.toml", "kit/templates/agk.adopt.toml"):
        text = (ROOT / rel).read_text(encoding="utf-8")
        assert re.search(r'^unused_code = ""$', text, flags=re.M)
        assert re.search(r'^coverage = ""$', text, flags=re.M)
    assert common.DEFAULT_CONFIG["unused_code"] == "" and common.DEFAULT_CONFIG["coverage"] == ""


# --- the whitelist must not hide findings ------------------------------------------------------


def called_by_name(name: str) -> bool:
    """A hook registration, an `if __name__` entry point (`main`), or a `getattr` of the name."""
    sources = [*(ROOT / "scripts" / "agk").glob("*.py"), *(ROOT / ".claude" / "hooks").glob("*.py")]
    text = "\n".join(p.read_text(encoding="utf-8") for p in sources)
    if name == "main" and "if __name__" in text:
        return True
    if re.search(rf"getattr\([^)]*[\"']{re.escape(name)}[\"']", text):
        return True
    settings = (ROOT / ".claude" / "settings.json").read_text(encoding="utf-8")
    return re.search(rf"\b{re.escape(name)}\b", settings) is not None


def whitelist_files(command: str) -> list[str]:
    """The files the command hands vulture beyond the scanned code: any `.py` outside it."""
    tokens = re.findall(r"[\w./-]+\.py", command)
    return [t for t in tokens if not t.startswith(("scripts/agk/", ".claude/hooks/"))]


def whitelist_problems(text: str) -> list[str]:
    """Each entry is `name  # reason` and the name is called by name."""
    bad = []
    for line in text.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        name, _, reason = line.partition("#")
        if not reason.strip():
            bad.append(f"no reason: {line.strip()}")
        elif not called_by_name(name.strip()):
            bad.append(f"not called by name: {name.strip()}")
    return bad


def test_every_whitelist_entry_is_a_name_that_is_called_by_name():
    for rel in whitelist_files(own()["unused_code"]):
        assert whitelist_problems((ROOT / rel).read_text(encoding="utf-8")) == []


def test_the_rule_rejects_a_hiding_entry():
    assert whitelist_problems("main  # entry point\n") == []
    assert whitelist_problems("never_used_anywhere  # because\n") == [
        "not called by name: never_used_anywhere"
    ]
    assert whitelist_problems("main\n") == ["no reason: main"]


def test_the_command_has_no_other_way_to_hide_a_finding():
    command = own()["unused_code"]
    assert not [token for token in HIDING if token in command]


# --- a truly unused function is listed ---------------------------------------------------------


@pytest.mark.skipif(shutil.which("vulture") is None, reason="vulture is not installed")
def test_a_fixture_with_one_unused_function_is_listed(tmp_path):
    """The same command shape, run once on a fixture; vulture rates an unused function at 60%, so
    this fixture lowers the threshold to show the tool lists it (Q-593-1)."""
    repo = fx.base(tmp_path / "repo")
    repo.write(
        "scripts/agk/lib.py", "def used():\n    return 1\n\n\ndef never_called():\n    return 2\n"
    )
    repo.write("scripts/agk/run.py", "from lib import used\n\nused()\n")
    repo.write("scripts/agk/tool.py", "")  # the base fixture's own variable is not the subject
    command = own()["unused_code"].replace("--min-confidence 80", "--min-confidence 60")
    command = command.replace(".claude/hooks", "")
    repo.write(
        "agk.toml", f"default_branch = 'main'\ntest_dirs = ['tests']\nunused_code = '{command}'\n"
    )
    repo.commit(1)
    found = drift_audit.d9(repo.root, None)
    assert len(found) == 1
    assert found[0].sentence.startswith("1 unused-code finding:")
    assert "never_called" in found[0].sentence


def test_vulture_lists_the_fixture_function_through_the_plain_cli(tmp_path):
    if shutil.which("vulture") is None:
        pytest.skip("vulture is not installed")
    (tmp_path / "m.py").write_text("def never_called():\n    return 2\n", encoding="utf-8")
    out = subprocess.run(  # nosec B603 B607 - fixed list, no shell
        ["vulture", str(tmp_path), "--min-confidence", "60"], capture_output=True, text=True
    ).stdout
    assert "never_called" in out


def test_every_tool_the_commands_install_is_pinned_to_an_exact_version():
    for key in ("unused_code", "coverage"):
        command = own()[key]
        installs = command.split("pip install -q ")[1].split(";")[0].split()
        assert installs, key
        for spec in installs:
            assert re.fullmatch(r"[a-z]+==\d+(\.\d+)+", spec), (key, spec)
