"""`rules.py consolidate --plan | --apply`: the rule set cut by evidence, as a command (brief #647
build (b) as amended on 2026-11-10, ADR-0404; REQ-037 AC1).

`--plan` changes no file: one row per rule line of the instruction files (`[rules] files` in
`agk.toml`, AGK's list by default) with its verdict (`keep`, `retire` with the check that enforces
it, `guide`), its count from `rules.py dropped`, the counts before and after, and a plan hash.
`--apply --hash H` writes that same plan into the working tree, and refuses a changed plan or a
dirty tree. It never commits. All files are invented; no network.
"""

from __future__ import annotations

import json
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "agk" / "rules.py"
SESSION = (
    "# Session rules\n\nThe rules.\n\n"
    "1. A session never merges.\n"
    "2. A builder runs the final-clearance check after a Final commit, as example.com shows.\n"
    "3. To open a draft, run the REST call and wait for it.\n"
)
CORE = ("CLAUDE.md", "constitution/principles.md", "config/core-rules.md")
PLAN = (
    "# file number verdict [check]\n"
    "config/session-rules.md 2 retire scripts/agk/check_x.py\n"
    "config/session-rules.md 3 guide\n"
)


def git(root: Path, *args: str) -> str:
    proc = subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
        ["git", *args], cwd=root, capture_output=True, text=True, check=True
    )
    return proc.stdout


def write(root: Path, rel: str, text: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def project(tmp_path: Path, plan: str = PLAN, toml: str | None = None) -> Path:
    root = tmp_path / "repo"
    for rel in CORE:
        write(root, rel, "# T\n\n1. Do one thing.\n")
    write(root, "config/session-rules.md", SESSION)
    write(root, "config/review-checklist.md", "# C\n\n1. Ask.\n")
    write(root, ".claude/agents/a.md", "---\nname: a\n---\n\n1. Act.\n")
    write(root, "scripts/agk/check_x.py", "print('ok')\n")
    write(root, "config/rule-plan.txt", plan)
    write(root, "config/reviewers.yaml", "version: 1\nverdict_authors: [reviewer]\n")
    sys.path.insert(0, str(SCRIPT.parent))
    from rules import budget_lines

    write(
        root, "config/rule-budget.txt", "# budget\n" + "".join(f"{x}\n" for x in budget_lines(root))
    )
    if toml is not None:  # after the baseline, so a bad setting is still written
        write(root, "agk.toml", toml)
    git(root, "init", "-q")
    git(root, "add", "-A")
    git(root, "-c", "user.name=t", "-c", "user.email=t@example.com", "commit", "-qm", "init")
    return root


def api(tmp_path: Path) -> Path:
    folder = tmp_path / "api"
    folder.mkdir()
    pulls = [
        {"number": 5, "state": "open", "merged_at": None, "updated_at": "2026-11-09T09:00:00Z"}
    ]
    notes = [
        {
            "id": 51,
            "body": "Verdict: fix list 00aa11b\n\n1. a (rule: config/session-rules.md 2)\n"
            "2. b (rule: config/session-rules.md 2)\n",
            "created_at": "2026-11-09T10:00:00Z",
            "user": {"login": "reviewer"},
        }
    ]
    (folder / "pulls.json").write_text(json.dumps(pulls), encoding="utf-8")
    (folder / "comments-5.json").write_text(json.dumps(notes), encoding="utf-8")
    return folder


def run(root: Path, *args: str) -> subprocess.CompletedProcess:
    cmd = [sys.executable, str(SCRIPT), "consolidate", "--root", str(root), *args]
    return subprocess.run(cmd, capture_output=True, text=True, check=False)  # nosec B603 - fixed argument list, no shell


def plan_hash(out: str) -> str:
    return next(x.split()[1] for x in out.splitlines() if x.startswith("plan: "))


def tree(root: Path) -> dict[str, str]:
    return {
        p.relative_to(root).as_posix(): p.read_text(encoding="utf-8")
        for p in sorted(root.rglob("*"))
        if p.is_file() and ".git" not in p.relative_to(root).parts
    }


def test_req037_plan_writes_nothing_and_prints_a_row_per_rule_line(tmp_path):
    """REQ-037 AC1: one row per rule line with verdict and count; no file changes."""
    root = project(tmp_path)
    before = tree(root)
    shown = run(root, "--plan", "--since", "2026-11-01", "--api-dir", str(api(tmp_path)))
    assert shown.returncode == 0, shown.stdout
    assert tree(root) == before and git(root, "status", "--porcelain") == ""
    lines = shown.stdout.splitlines()
    assert "config/session-rules.md:5 1 keep 0" in lines
    assert "config/session-rules.md:6 2 retire scripts/agk/check_x.py 2" in lines
    assert "config/session-rules.md:7 3 guide 0" in lines
    assert ".claude/agents/a.md:5 1 keep 0" in lines
    assert any(x.startswith("before: ") for x in lines)
    assert any(x.startswith("after: ") and "in force" in x for x in lines)
    assert plan_hash(shown.stdout)


def test_req037_plan_without_since_prints_no_count(tmp_path):
    """REQ-037 AC1: no `--since` reads nothing from GitHub; the count is `-`, never 0."""
    root = project(tmp_path)
    shown = run(root, "--plan")
    assert shown.returncode == 0, shown.stdout
    assert "config/session-rules.md:5 1 keep -" in shown.stdout.splitlines()


def test_req037_a_retire_whose_check_is_not_found_is_refused(tmp_path):
    """REQ-037 AC1: a retired rule names a check that exists, verified by name."""
    root = project(tmp_path, plan="config/session-rules.md 2 retire scripts/agk/check_gone.py\n")
    shown = run(root, "--plan")
    assert shown.returncode == 1
    assert "config/rule-plan.txt" in shown.stdout and "check_gone.py" in shown.stdout


def test_req037_apply_writes_the_plan_it_printed(tmp_path):
    """REQ-037 AC1: the must-list, the guide, the catch-log line and the lowered baseline."""
    root = project(tmp_path)
    planned = run(root, "--plan")
    applied = run(root, "--apply", "--hash", plan_hash(planned.stdout))
    assert applied.returncode == 0, applied.stdout
    rules = (root / "config" / "session-rules.md").read_text(encoding="utf-8")
    assert "1. A session never merges.\n" in rules
    assert "2. Retired: enforced by `scripts/agk/check_x.py`" in rules
    assert "3. Moved to `docs/guides/session-how-to.md`" in rules
    assert "REST call" not in rules and "example.com shows" not in rules
    guide = (root / "docs" / "guides" / "session-how-to.md").read_text(encoding="utf-8")
    assert "To open a draft, run the REST call and wait for it." in guide
    log = (root / "docs" / "runs" / "rules-retired.md").read_text(encoding="utf-8")
    assert "config/session-rules.md 2" in log and "scripts/agk/check_x.py" in log
    from rules import budget_problems

    assert budget_problems(root) == []
    assert len(git(root, "log", "--format=%h").split()) == 1  # never commits
    again = run(root, "--plan")
    assert "config/session-rules.md:6 2 keep -" in again.stdout.splitlines()


def test_req037_apply_refuses_a_changed_plan_a_missing_hash_and_a_dirty_tree(tmp_path):
    """REQ-037 AC1: the plan hash and a clean tree are required; the refusal names the rule."""
    root = project(tmp_path)
    good = plan_hash(run(root, "--plan").stdout)
    before = tree(root)
    stale = run(root, "--apply", "--hash", "0" * 12)
    assert stale.returncode == 1 and "plan has changed" in stale.stdout
    assert run(root, "--apply").returncode == 2
    write(root, "notes.txt", "x\n")
    dirty = run(root, "--apply", "--hash", good)
    assert dirty.returncode == 1 and "working tree is dirty" in dirty.stdout
    (root / "notes.txt").unlink()
    assert tree(root) == before


def test_req037_a_project_list_of_rule_files_is_read(tmp_path):
    """REQ-037 AC1: `[rules] files` in agk.toml names a project's own instruction files."""
    toml = '[rules]\nfiles = ["CLAUDE.md", ".claude/agents/*.md"]\n'
    root = project(tmp_path, plan="", toml=toml)
    from rules import instruction_files

    assert instruction_files(root) == ["CLAUDE.md", ".claude/agents/a.md"]
    shown = run(root, "--plan")
    assert shown.returncode == 0, shown.stdout
    rows = [x for x in shown.stdout.splitlines() if " keep " in x]
    assert rows == ["CLAUDE.md:3 1 keep -", ".claude/agents/a.md:5 1 keep -"]


def test_req037_a_bad_rules_setting_is_refused_naming_it(tmp_path):
    """REQ-037 AC1: refusals name the setting, never the value."""
    root = project(tmp_path, plan="", toml='[rules]\nfiles = "CLAUDE.md"\n')
    shown = run(root, "--plan")
    assert shown.returncode == 1 and "[rules] files" in shown.stdout


def test_req037_this_repository_has_a_plan():
    """REQ-037 AC1: the committed plan file is read and every row names a known verdict."""
    shown = run(ROOT, "--plan")
    assert shown.returncode == 0, shown.stdout
    assert plan_hash(shown.stdout)
