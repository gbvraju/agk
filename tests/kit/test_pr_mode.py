"""Tests of the declared dependence and the mode (SPEC-0025 rules 5 to 7, REQ-032 AC5 to AC8).

`check_pr_mode.py` reads the pull request body, a file of the states of the named pull requests
and a file of the author's open pull requests; it reads files only. No network and no model.
"""

from __future__ import annotations

import ast
import json
import re
from pathlib import Path

from common import pr_mode

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github" / "workflows" / "governance.yml"
BODY = "Advances: REQ-001\nDepends-on: #12\nDepends-on: #15\n"


def configure(repo, mode: str | None) -> None:
    text = 'version = "0.0.1"\n' + (f'pr_mode = "{mode}"\n' if mode else "")
    repo.write("agk.toml", text)


def files(tmp_path: Path, body: str = BODY, states=None, opened=None) -> list[str]:
    args = ["--body", str(write(tmp_path / "body.md", body))]
    if states is not None:
        args += ["--states", str(write(tmp_path / "states.json", json.dumps(states)))]
    if opened is not None:
        args += ["--open", str(write(tmp_path / "open.json", "\n".join(map(json.dumps, opened))))]
    return args


def write(path: Path, text: str) -> Path:
    path.write_text(text, encoding="utf-8")
    return path


def run(repo, *args: str):
    return repo.run("check_pr_mode.py", *args)


# --- the mode (rule 6) ----------------------------------------------------------------------------


def test_ac6_the_default_mode_is_strict(repo):
    """REQ-032 AC6: rule 6 (no `pr_mode` in agk.toml, and no agk.toml at all)."""
    assert pr_mode(repo.root) == "strict"
    configure(repo, None)
    assert pr_mode(repo.root) == "strict"
    configure(repo, "flow")
    assert pr_mode(repo.root) == "flow"


def test_ac6_a_value_that_is_not_a_mode_is_refused_naming_the_setting_only(repo, tmp_path):
    """REQ-032 AC6: rule 6 (messages name the setting, never the value)."""
    configure(repo, "sideways")
    proc = run(repo, *files(tmp_path))
    assert proc.returncode == 1 and "pr_mode" in proc.stdout and "sideways" not in proc.stdout


# --- strict (rule 6) ------------------------------------------------------------------------------


def test_ac6_strict_fails_a_depends_on_line(repo, tmp_path):
    """REQ-032 AC6: rule 6 (a `Depends-on` line fails the check in strict mode)."""
    configure(repo, "strict")
    proc = run(repo, *files(tmp_path, states=[{"number": 12, "merged": True}]))
    assert proc.returncode == 1 and proc.stdout.startswith("FAIL pr-mode: rule 6"), proc.stdout
    assert "Depends-on" in proc.stdout and "pr_mode" in proc.stdout


def test_ac6_strict_fails_on_an_older_open_pull_request_of_the_author(repo, tmp_path):
    """REQ-032 AC6: rule 6 (the lowest number wins; the message names the older number)."""
    configure(repo, "strict")
    args = files(tmp_path, body="Advances: REQ-001\n", opened=[{"number": 40}, {"number": 41}])
    proc = run(repo, *args, "--number", "41")
    assert proc.returncode == 1 and proc.stdout.startswith("FAIL pr-mode: rule 6"), proc.stdout
    assert "#40" in proc.stdout
    older = run(repo, *args, "--number", "40")
    assert (older.returncode, older.stdout) == (0, "ok pr-mode\n"), older.stdout


def test_ac6_strict_passes_with_only_the_pull_request_itself_open(repo, tmp_path):
    """REQ-032 AC6: rule 6."""
    configure(repo, None)
    args = files(tmp_path, body="", opened=[{"number": 41}])
    proc = run(repo, *args, "--number", "41")
    assert (proc.returncode, proc.stdout) == (0, "ok pr-mode\n")


def test_ac6_without_the_open_pull_requests_file_the_check_skips_and_passes(repo, tmp_path):
    """REQ-032 AC6: rule 6 (`skipped (no open pull requests file)`)."""
    configure(repo, "strict")
    proc = run(repo, *files(tmp_path, body=""), "--number", "41")
    assert (proc.returncode, proc.stdout) == (0, "skipped (no open pull requests file)\n")
    assert run(repo).stdout == "skipped (no open pull requests file)\n"


# --- flow (rules 5 and 6) -------------------------------------------------------------------------


def test_ac7_flow_allows_several_open_pull_requests_and_depends_on(repo, tmp_path):
    """REQ-032 AC7: rule 6."""
    configure(repo, "flow")
    states = [{"number": 12, "merged": True}, {"number": 15, "merged": True}]
    args = files(tmp_path, states=states, opened=[{"number": 40}, {"number": 41}])
    proc = run(repo, *args, "--number", "41")
    assert (proc.returncode, proc.stdout) == (0, "ok pr-mode\n"), proc.stdout


def test_ac5_flow_fails_while_a_named_pull_request_is_not_merged(repo, tmp_path):
    """REQ-032 AC5: rule 5 (the message names the rule and the number)."""
    configure(repo, "flow")
    states = [{"number": 12, "merged": True}, {"number": 15, "merged": False}]
    proc = run(repo, *files(tmp_path, states=states, opened=[]))
    assert proc.returncode == 1 and proc.stdout.startswith("FAIL pr-mode: rule 5"), proc.stdout
    assert "#15" in proc.stdout and "#12" not in proc.stdout


def test_ac5_a_named_pull_request_missing_from_the_states_is_not_merged(repo, tmp_path):
    """REQ-032 AC5: rule 5."""
    configure(repo, "flow")
    proc = run(repo, *files(tmp_path, states=[{"number": 12, "merged": True}], opened=[]))
    assert proc.returncode == 1 and "#15" in proc.stdout, proc.stdout


def test_ac5_states_are_read_as_an_array_or_as_one_object_a_line(repo, tmp_path):
    """REQ-032 AC5: rule 5 (the workflow writes one compact object a line)."""
    configure(repo, "flow")
    lines = '{"number": 12, "merged": true}\n{"number": 15, "merged": true}\n'
    states = write(tmp_path / "lines.json", lines)
    proc = run(repo, "--body", str(write(tmp_path / "b.md", BODY)), "--states", str(states))
    assert proc.stdout == "skipped (no open pull requests file)\n" and proc.returncode == 0


def test_ac5_without_the_states_file_the_check_skips_and_passes(repo, tmp_path):
    """REQ-032 AC5: rule 5 (`skipped (no states file)`)."""
    configure(repo, "flow")
    proc = run(repo, *files(tmp_path, opened=[]))
    assert (proc.returncode, proc.stdout) == (0, "skipped (no states file)\n"), proc.stdout


def test_ac5_the_numbers_of_the_depends_on_lines_are_listed_for_the_workflow(repo, tmp_path):
    """REQ-032 AC5: rule 7 (the workflow fetches the states of exactly these numbers)."""
    lines = ["Depends-on: #12", "Depends-on:#13", "  Depends-on: #14", "text Depends-on: #16"]
    body = "\n".join([*lines, "Depends-on: #15", "Depends-on: #12", ""])
    proc = run(repo, "--list-depends", "--body", str(write(tmp_path / "b.md", body)))
    assert (proc.returncode, proc.stdout) == (0, "12\n14\n15\n")


# --- the workflow (rule 7) ------------------------------------------------------------------------


def test_ac8_the_workflow_keeps_three_read_permissions_and_fetches_with_get_only():
    """REQ-032 AC8: rule 7 (the new fetches are GET steps that write files)."""
    text = WORKFLOW.read_text(encoding="utf-8")
    assert re.search(
        r"^permissions:\n  contents: read\n  pull-requests: read\n  issues: read\n", text, re.M
    )
    assert text.count("permissions:") == 1
    calls = re.findall(r"gh api [^\n]*", text)
    assert calls and all("--method GET" in c for c in calls), calls
    assert '"$RUNNER_TEMP/states.json"' in text and '"$RUNNER_TEMP/open-prs.json"' in text
    assert "--method POST" not in text and "--method PATCH" not in text
    assert "--states" in text and "--open" in text and "--number" in text


def test_ac8_the_check_reads_files_only_and_imports_no_network_module():
    """REQ-032 AC8: rule 7 (no network call in a check)."""
    tree = ast.parse((ROOT / "scripts" / "agk" / "check_pr_mode.py").read_text(encoding="utf-8"))
    names = {
        a.name.split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names
    }
    names |= {
        n.module.split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and n.module
    }
    assert not names & {"socket", "urllib", "http", "requests", "ssl", "subprocess"}


def test_ac8_the_step_runs_unless_cancelled_and_is_in_the_governance_recipe():
    """REQ-032 AC8: rule 7."""
    mk = (ROOT / "agk.mk").read_text(encoding="utf-8")
    assert "$(PY) scripts/agk/check_pr_mode.py\n" in mk
    block = WORKFLOW.read_text(encoding="utf-8").split("      - name: check_pr_mode\n", 1)[1]
    assert block.startswith("        if: ${{ !cancelled() }}\n")
