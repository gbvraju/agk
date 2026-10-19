"""Tests of .claude/hooks/architect_guard.py (SPEC-0013 rule 9): a table of commands and paths.

The hook is run as Claude Code runs it: JSON on stdin, a denial as JSON on stdout, an allow as
no output. No test uses the network.
"""

from __future__ import annotations

import json
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
from pathlib import Path

import pytest

HOOK = Path(__file__).resolve().parents[2] / ".claude" / "hooks" / "architect_guard.py"
RULE9_MARK = "architect guard rule 9"


def run_hook(payload: object, project: Path):
    return subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, str(HOOK)],
        input=payload if isinstance(payload, str) else json.dumps(payload),
        capture_output=True,
        text=True,
        env={"PATH": "/usr/bin:/bin", "CLAUDE_PROJECT_DIR": str(project)},
    )


def denied(out: str) -> dict | None:
    return json.loads(out)["hookSpecificOutput"] if out.strip() else None


@pytest.fixture
def project(tmp_path: Path) -> Path:
    (tmp_path / "docs").mkdir()
    (tmp_path / "constitution").mkdir()
    (tmp_path / "scripts").mkdir()
    set_origin(tmp_path, "https://github.com/o/r.git")
    return tmp_path


def set_origin(project: Path, *urls: str) -> None:
    git_dir = project / ".git"
    git_dir.mkdir(exist_ok=True)
    lines = ["[core]", "\trepositoryformatversion = 0"]
    if urls:
        lines.append('[remote "origin"]')
        lines += [f"\turl = {u}" for u in urls]
        lines.append("\tfetch = +refs/heads/*:refs/remotes/origin/*")
    (git_dir / "config").write_text("\n".join(lines) + "\n", encoding="utf-8")


WRITE_OK = [
    "docs/notes.md",
    "docs/runs/new/deep/file.md",
    "constitution/vision.md",
    "./docs/a.md",
]
WRITE_NO = [
    "scripts/agk/x.py",
    "constitution/principles.md",
    "CLAUDE.md",
    "docs/../scripts/x.py",
    "../outside.md",
    "/etc/passwd",
    "docsx/a.md",
    "constitution/vision.md.bak",
    "",
]


@pytest.mark.parametrize("tool", ["Edit", "Write", "MultiEdit"])
@pytest.mark.parametrize("path", WRITE_OK)
def test_ac1_writes_under_docs_and_the_vision_are_allowed(project, tool, path):
    """REQ-020 AC1: rule 9 (Edit and Write only under docs/ and constitution/vision.md)."""
    proc = run_hook({"tool_name": tool, "tool_input": {"file_path": path}}, project)
    assert proc.returncode == 0 and proc.stdout == ""


@pytest.mark.parametrize("tool", ["Edit", "Write", "MultiEdit"])
@pytest.mark.parametrize("path", WRITE_NO)
def test_ac1_writes_elsewhere_are_denied_without_naming_the_path(project, tool, path):
    """REQ-020 AC1: rule 9."""
    proc = run_hook({"tool_name": tool, "tool_input": {"file_path": path}}, project)
    verdict = denied(proc.stdout)
    assert proc.returncode == 0 and verdict["permissionDecision"] == "deny"
    assert (
        verdict["hookEventName"] == "PreToolUse"
        and RULE9_MARK in verdict["permissionDecisionReason"]
    )
    assert path not in verdict["permissionDecisionReason"] or path == ""


def test_ac1_an_absolute_path_inside_docs_is_allowed_and_a_symlink_out_is_not(project, tmp_path):
    """REQ-020 AC1: rule 9 (the real path decides)."""
    assert (
        run_hook(
            {"tool_name": "Write", "tool_input": {"file_path": str(project / "docs" / "a.md")}},
            project,
        ).stdout
        == ""
    )
    outside = tmp_path.parent / "outside-target"
    outside.mkdir(exist_ok=True)
    (project / "docs" / "link").symlink_to(outside)
    proc = run_hook({"tool_name": "Write", "tool_input": {"file_path": "docs/link/x.md"}}, project)
    assert denied(proc.stdout)["permissionDecision"] == "deny"


def test_ac1_a_notebook_edit_is_judged_by_its_notebook_path(project):
    """REQ-020 AC1: rule 9."""
    ok = {"tool_name": "NotebookEdit", "tool_input": {"notebook_path": "docs/n.ipynb"}}
    no = {"tool_name": "NotebookEdit", "tool_input": {"notebook_path": "src/n.ipynb"}}
    assert run_hook(ok, project).stdout == "" and denied(run_hook(no, project).stdout)


BASH_OK = [
    "git status",
    "git diff origin/main...HEAD",
    "git log --oneline -5",
    "git show HEAD:docs/requirements.md",
    "git branch --show-current",
    "git branch --list",
    "git rev-parse HEAD",
    "git grep -n marker docs",
    "git grep -i --count needle -- docs",
    "git log --oneline --stat --name-only -5",
    "git diff --stat --name-only origin/main...HEAD",
    "git show --format=%H -s HEAD",
    "gh api repos/o/r/pulls/7",
    "gh api --method GET repos/o/r/pulls/7/files",
    "gh api -X GET repos/o/r/issues/7/comments --jq .[].body",
    "gh api --method GET repos/o/r/actions/runs -f status=success",
    "gh api --method POST repos/o/r/issues/7/comments -f body='Verdict: cleared abc1234'",
    "date -u",
    "date -u +%F",
    "make governance",
    "make -f agk.mk agk-governance",
    "python3 scripts/agk/check_specs.py --base origin/main",
    "python3 scripts/agk/facts.py --today 2026-10-19 .",
]
BASH_NO = [
    "git push origin HEAD",
    "git commit -m x",
    "git checkout main",
    "git reset --hard",
    "git branch newname",
    "git branch -D x",
    "git diff --output=x.patch",
    "git grep -Opython3 marker docs/x.py",
    "git grep -O python3 marker docs/x.py",
    "git grep -nOpython3 marker docs/x.py",
    "git grep --open-files-in-pager=python3 marker docs/x.py",
    "git grep --open-files-in-pager python3 marker",
    "git grep --open-files marker",
    "git grep --open marker",
    "git diff --ext-diff",
    "git diff --ext HEAD",
    "git diff --textconv HEAD",
    "git show --textconv HEAD:docs/x.py",
    "git log --show-signature",
    "git log --paginate",
    "git cat-file --filters HEAD:docs/x.py",
    "git cat-file --textconv HEAD:docs/x.py",
    "git log --output=x",
    "git grep --exec-path",
    "git log --git-dir=/tmp/x",
    "git blame -O x docs/a.md",
    "gh api --method POST repos/rs/cors/issues/1/comments -f body=hi",
    "gh api --method POST repos/o/other/issues/1/comments -f body=hi",
    "gh api --method POST repos/other/r/issues/1/comments -f body=hi",
    "git -c core.pager=sh status",
    "git status; rm -rf docs",
    "git status && make test",
    "git status | sh",
    "git log > out.txt",
    "git log $(whoami)",
    "git log `whoami`",
    "gh pr merge 7",
    "gh pr view 7",
    "gh api graphql -f query=x",
    "gh api --method PUT repos/o/r/pulls/7/merge",
    "gh api --method DELETE repos/o/r/git/refs/heads/x",
    "gh api --method POST repos/o/r/pulls/7/merge",
    "gh api --method POST repos/o/r/issues/7/labels -f labels=x",
    "gh api repos/o/r/pulls/7 -f title=x",
    "gh api --method POST repos/o/r/issues/7/comments --input body.json",
    "gh api user",
    "gh auth login",
    "make test",
    "make governance && rm x",
    "python3 scripts/agk/proof.py --base a --head b",
    "python3 scripts/agk/init.py .",
    "python3 scripts/agk/facts.py --write",
    "python3 -c 'print(1)'",
    "python3 scripts/agk/../../x.py",
    "rm -rf docs",
    "curl https://example.invalid",
    "echo hi",
    "ls",
    "cat docs/a.md",
    "",
    "date -s 2020-01-01",
]


@pytest.mark.parametrize("command", BASH_OK)
def test_ac1_the_listed_commands_are_allowed(project, command):
    """REQ-020 AC1: rule 9 (the architect's Bash list)."""
    proc = run_hook({"tool_name": "Bash", "tool_input": {"command": command}}, project)
    assert proc.returncode == 0 and proc.stdout == "", command


@pytest.mark.parametrize("command", BASH_NO)
def test_ac1_every_other_command_is_denied_without_echoing_it(project, command):
    """REQ-020 AC1: rule 9 (a merge, a push, a write, an operator, a substitution)."""
    proc = run_hook({"tool_name": "Bash", "tool_input": {"command": command}}, project)
    verdict = denied(proc.stdout)
    assert verdict and verdict["permissionDecision"] == "deny", command
    assert RULE9_MARK in verdict["permissionDecisionReason"]
    assert not command or command not in proc.stdout


def test_ac1_other_tools_and_a_broken_payload(project):
    """REQ-020 AC1: rule 9 (reads are not the guard's business; garbage is denied)."""
    for tool in ("Read", "Grep", "Glob"):
        assert (
            run_hook(
                {"tool_name": tool, "tool_input": {"file_path": "/etc/passwd"}}, project
            ).stdout
            == ""
        )
    for bad in ("not json", "[]", '"x"'):
        proc = run_hook(bad, project)
        assert proc.returncode == 0 and denied(proc.stdout)["permissionDecision"] == "deny"
    assert denied(run_hook({"tool_name": "Bash"}, project).stdout)
    assert denied(run_hook({"tool_name": "Write", "tool_input": {}}, project).stdout)


def test_ac1_the_hook_has_no_network_and_runs_no_command():
    """REQ-020 AC1: rule 9 (static reading)."""
    source = HOOK.read_text(encoding="utf-8")
    assert "subprocess" not in source and "socket" not in source and "urllib" not in source
    assert "os.system" not in source and "eval(" not in source and "exec(" not in source


COMMENT = "gh api --method POST repos/{}/issues/7/comments -f body=hi"


def allowed_comment(project: Path, repo: str) -> bool:
    payload = {"tool_name": "Bash", "tool_input": {"command": COMMENT.format(repo)}}
    return run_hook(payload, project).stdout == ""


@pytest.mark.parametrize(
    "url",
    [
        "https://github.com/o/r.git",
        "https://github.com/o/r",
        "git@github.com:o/r.git",
        "ssh://git@github.com/o/r.git",
        "http://local_proxy@127.0.0.1:1234/git/o/r",
    ],
)
def test_ac1_a_comment_post_names_the_repository_of_the_origin_remote(project, url):
    """REQ-020 AC1: rule 9 (a POST goes to this checkout's own repository)."""
    set_origin(project, url)
    assert allowed_comment(project, "o/r")
    assert allowed_comment(project, "O/R")  # GitHub names are not case sensitive
    for other in ("o/x", "x/r", "rs/cors", "o/r/extra"):
        assert not allowed_comment(project, other), (url, other)


def test_ac1_a_comment_post_is_denied_when_the_origin_cannot_be_read(project, tmp_path):
    """REQ-020 AC1: rule 9 (no origin, no .git, two different origins, an odd URL)."""
    set_origin(project)  # a config with no origin remote
    assert not allowed_comment(project, "o/r")
    (project / ".git" / "config").unlink()
    assert not allowed_comment(project, "o/r")
    set_origin(project, "https://github.com/o/r.git", "https://github.com/o/other.git")
    assert not allowed_comment(project, "o/r") and not allowed_comment(project, "o/other")
    set_origin(project, "https://github.com/o/r.git", "git@github.com:o/r.git")
    assert allowed_comment(project, "o/r")  # two urls of the same repository
    set_origin(project, "nonsense")
    assert not allowed_comment(project, "o/r")
    other = tmp_path.parent / "no-git-here"
    other.mkdir(exist_ok=True)
    assert not allowed_comment(other, "o/r")


def test_ac1_a_worktree_checkout_reads_the_common_git_config(project, tmp_path):
    """REQ-020 AC1: rule 9 (`.git` is a file in a worktree)."""
    main = tmp_path.parent / "main-checkout"
    (main / ".git" / "worktrees" / "w").mkdir(parents=True, exist_ok=True)
    set_origin(main, "https://github.com/o/r.git")
    (main / ".git" / "worktrees" / "w" / "commondir").write_text("../..\n", encoding="utf-8")
    work = tmp_path.parent / "worktree-checkout"
    work.mkdir(exist_ok=True)
    (work / ".git").write_text(f"gitdir: {main / '.git' / 'worktrees' / 'w'}\n", encoding="utf-8")
    assert allowed_comment(work, "o/r") and not allowed_comment(work, "x/r")


def test_ac1_reading_any_repository_stays_open(project):
    """REQ-020 AC1: rule 9 (GET is open to any `repos/` path)."""
    for command in (
        "gh api repos/rs/cors/pulls/1",
        "gh api --method GET repos/other/other/issues/3/comments",
    ):
        assert (
            run_hook({"tool_name": "Bash", "tool_input": {"command": command}}, project).stdout
            == ""
        )
