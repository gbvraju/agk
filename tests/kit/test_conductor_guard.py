"""Tests of .claude/hooks/conductor_guard.py (SPEC-0030 rule 6; REQ-037 AC5).

The hook runs as Claude Code runs it: JSON on stdin, a denial as JSON on stdout, an allow as no
output. No test uses the network.
"""

from __future__ import annotations

import json
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
from pathlib import Path

import pytest

HOOK = Path(__file__).resolve().parents[2] / ".claude" / "hooks" / "conductor_guard.py"
MARK = "conductor guard rule 6"
COMMENT = "gh api --method POST repos/o/r/issues/7/comments -f body=hello"


def run_hook(payload: object, project: Path, tmpdir: Path | None = None):
    env = {"PATH": "/usr/bin:/bin", "CLAUDE_PROJECT_DIR": str(project)}
    if tmpdir is not None:
        env["TMPDIR"] = str(tmpdir)
    return subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, str(HOOK)],
        input=payload if isinstance(payload, str) else json.dumps(payload),
        capture_output=True,
        text=True,
        env=env,
    )


def denial(out: str) -> dict | None:
    return json.loads(out)["hookSpecificOutput"] if out.strip() else None


@pytest.fixture
def project(tmp_path: Path) -> Path:
    (tmp_path / "docs").mkdir()
    git_dir = tmp_path / ".git"
    git_dir.mkdir()
    (git_dir / "config").write_text(
        '[remote "origin"]\n\turl = https://github.com/o/r.git\n', encoding="utf-8"
    )
    return tmp_path


BASH_OK = [
    "git status",
    "git log --oneline -5",
    "git diff origin/main...HEAD",
    "git show abc1234",
    "git merge-base origin/main HEAD",
    "gh api --method GET repos/o/r/pulls/7",
    "gh api repos/o/r/pulls/7/files",
    "gh api --method GET repos/o/r/commits/abc1234/check-runs",
    "gh api --method GET repos/o/r/actions/jobs/9/logs",
    COMMENT,
    "git fetch origin",
    "date -u",
]
BASH_NO = [
    "git push origin main",
    "git commit -m x",
    "git checkout main",
    "git merge origin/main",
    "git diff --output=/tmp/x",
    "gh pr merge 7",
    "gh pr comment 7 -b hi",
    "gh api --method PATCH repos/o/r/pulls/7 -f state=closed",
    "gh api --method PUT repos/o/r/pulls/7/merge",
    "gh api --method DELETE repos/o/r/git/refs/heads/x",
    "gh api --method POST repos/o/r/pulls/7/merge -f x=y",
    "gh api --method POST repos/o/r/issues/7/labels -f labels=x",
    "gh api --method POST repos/o/r/git/refs -f ref=x",
    "gh api --method POST repos/other/r/issues/7/comments -f body=hello",
    "gh api --method POST repos/o/r/issues/7/comments --input /tmp/x",
    "gh api --method POST repos/o/r/issues/7/comments",
    "gh api --method GET repos/o/r/pulls/7 --input /tmp/x",
    "make governance",
    "python3 scripts/agk/session.py next --session x",
    "python3 -I scripts/agk/check_adrs.py",
    "env -i git status",
    "git worktree add /tmp/agk-conductor-1 abc1234",
    "git fetch origin main",
    "git fetch origin --prune",
    "git fetch --all",
    "python3 scripts/agk/session.py watch --pr 7",
    "rm -rf docs",
    "cat CLAUDE.md",
    "git status; rm x",
    "git status && gh pr merge 7",
    "git log $(rm x)",
    "git log `rm x`",
    "git log > out.txt",
    "date -u | sh",
    "",
]


@pytest.mark.parametrize("command", BASH_OK)
def test_ac5_reads_and_the_one_comment_post_are_allowed(project, command):
    """REQ-037 AC5"""
    out = run_hook({"tool_name": "Bash", "tool_input": {"command": command}}, project)
    assert out.returncode == 0 and denial(out.stdout) is None, command


@pytest.mark.parametrize("command", BASH_NO)
def test_ac5_every_other_command_is_refused_naming_the_rule(project, command):
    """REQ-037 AC5"""
    out = run_hook({"tool_name": "Bash", "tool_input": {"command": command}}, project)
    found = denial(out.stdout)
    assert out.returncode == 0 and found is not None, command
    assert found["permissionDecision"] == "deny" and MARK in found["permissionDecisionReason"]
    assert command.strip() == "" or command not in found["permissionDecisionReason"]


@pytest.mark.parametrize("tool", ["Edit", "Write", "MultiEdit", "NotebookEdit"])
@pytest.mark.parametrize("path", ["docs/notes.md", "constitution/vision.md", "scripts/x.py", ""])
def test_ac5_no_file_write_in_the_work_tree_is_allowed_anywhere(project, tool, path):
    """REQ-037 AC5"""
    data = {"notebook_path" if tool == "NotebookEdit" else "file_path": path}
    found = denial(run_hook({"tool_name": tool, "tool_input": data}, project).stdout)
    assert found is not None and MARK in found["permissionDecisionReason"]
    assert path not in found["permissionDecisionReason"] or path == ""


def test_ac5_a_comment_post_to_another_repository_than_origin_is_refused(project):
    """REQ-037 AC5"""
    (project / ".git" / "config").write_text(
        '[remote "origin"]\n\turl = https://github.com/x/y.git\n', encoding="utf-8"
    )
    out = run_hook({"tool_name": "Bash", "tool_input": {"command": COMMENT}}, project)
    assert denial(out.stdout) is not None


def test_ac5_other_tools_pass_and_bad_input_is_refused(project):
    """REQ-037 AC5"""
    assert (
        denial(run_hook({"tool_name": "Read", "tool_input": {"file_path": "x"}}, project).stdout)
        is None
    )
    assert denial(run_hook("not json", project).stdout) is not None
    assert denial(run_hook({"tool_name": "Bash", "tool_input": {"command": 5}}, project).stdout)


# --- bounded runs of a pull request in a scratch worktree (verdict on #175) ----------------------


def env(home: object) -> str:
    """The prefix of a bounded run: a clean environment with the run's scratch directory as HOME."""
    return f'env -i PATH="$PATH" HOME={home} '


class Work:
    """A real checkout: `feature` is a branch of origin; `fork` is a commit on no origin branch."""

    def __init__(self, root: Path) -> None:
        self.root = root / "work"
        self.tmp = root / "tmp"
        self.tmp.mkdir()
        self.root.mkdir()
        self.git("init", "-q", "-b", "main")
        self.git("config", "user.email", "t@example.invalid")
        self.git("config", "user.name", "t")
        self.git("remote", "add", "origin", "https://github.com/o/r.git")
        (self.root / "a.txt").write_text("a\n", encoding="utf-8")
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "one")
        self.feature = self.git("rev-parse", "HEAD").strip()
        self.git("update-ref", "refs/remotes/origin/feature", self.feature)
        tree = self.git("rev-parse", "HEAD^{tree}").strip()
        self.fork = self.git("commit-tree", tree, "-m", "fork").strip()
        self.scratch = self.tmp / "agk-conductor-1"

    def git(self, *args: str) -> str:
        return subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
            ["git", *args], cwd=self.root, capture_output=True, text=True, check=True
        ).stdout

    def bash(self, command: str):
        payload = {"tool_name": "Bash", "tool_input": {"command": command}}
        return denial(run_hook(payload, self.root, self.tmp).stdout)

    def write(self, tool: str, path: Path | str):
        key = "notebook_path" if tool == "NotebookEdit" else "file_path"
        payload = {"tool_name": tool, "tool_input": {key: str(path)}}
        return denial(run_hook(payload, self.root, self.tmp).stdout)


@pytest.fixture
def work(tmp_path: Path) -> Work:
    return Work(tmp_path)


def test_ac5_a_run_in_a_scratch_worktree_of_an_origin_head_is_allowed(work):
    """REQ-037 AC5"""
    s = work.scratch
    E = env(s)
    assert work.bash(f"git worktree add {s} {work.feature}") is None
    assert work.bash(f"git worktree add {s} {work.feature[:9]}") is None
    assert work.bash(f"{E}make -C {s} test") is None
    assert work.bash(f"{E}make -C {s} governance") is None
    assert work.bash(f"{E}python3 -I {s}/scripts/agk/check_adrs.py --base main") is None
    assert work.bash(f"git worktree remove {s}") is None
    assert work.bash(f"git worktree remove --force {s}") is None


def test_ac5_a_head_that_is_on_no_origin_branch_is_refused(work):
    """REQ-037 AC5: the head repository differs from the base repository (a fork)."""
    found = work.bash(f"git worktree add {work.scratch} {work.fork}")
    assert found is not None and MARK in found["permissionDecisionReason"]
    assert work.fork not in found["permissionDecisionReason"]
    assert work.bash(f"git worktree add {work.scratch} deadbeefdeadbeef") is not None
    assert work.bash(f"git worktree add {work.scratch} main") is not None


def test_ac5_a_run_needs_the_clean_environment_prefix_and_a_scratch_directory(work):
    """REQ-037 AC5"""
    s, root = work.scratch, work.root
    E = env(s)
    for command in (
        f"make -C {s} test",
        f"env -i make -C {s} test",
        f'env -i PATH="$PATH" make -C {s} test',
        f'env PATH="$PATH" HOME="$HOME" make -C {s} test',
        f"{E}GH_TOKEN=x make -C {s} test",
        f"{E}make -C {s} deploy",
        f"{E}make -C {s} test governance",
        f"{E}make -C {root} test",
        f"{E}make -C . test",
        f"{E}make -C {root / 'agk-conductor-2'} test",
        f"{E}make -C {work.tmp / 'other'} test",
        f"{E}make -C {work.tmp / 'agk-conductor-1' / '..'} test",
        f"{E}make test",
        f"{E}python3 {s}/scripts/agk/check_adrs.py",
        f"{E}python3 -I {s}/scripts/agk/../../x.py",
        f"{E}python3 -I {s}/other/check_adrs.py",
        f"{E}python3 -I scripts/agk/check_adrs.py",
        f'{E}python3 -I -c "print(1)"',
        f"{E}git status",
        f"{E}make -C {s} test; rm x",
        f"x {E}make -C {s} test",
        f'env -i PATH="$PATH" HOME="$HOME" make -C {s} test',
        f'env -i PATH="$PATH" HOME="$HOME" python3 -I {s}/scripts/agk/check_adrs.py',
        f"{env(work.tmp / 'agk-conductor-2')}make -C {s} test",
        f"{env(root)}make -C {s} test",
        f"{env(work.tmp)}make -C {s} test",
        f"{env('~')}make -C {s} test",
        f"{env(s)}{env(s)}make -C {s} test",
        f'env -i PATH="$PATH" make -C {s} test',
        f"git worktree add {root / 'agk-conductor-3'} {work.feature}",
        f"git worktree add {work.tmp / 'scratch'} {work.feature}",
        f"git worktree remove {work.tmp / 'scratch'}",
        "git worktree prune",
        f"git worktree add --detach {s} {work.feature}",
        f"git worktree add -f {s} {work.feature}",
    ):
        assert work.bash(command) is not None, command


def test_ac5_a_write_is_allowed_only_under_a_scratch_directory(work):
    """REQ-037 AC5"""
    s = work.scratch
    assert work.write("Write", s / "mockup.html") is None
    assert work.write("Write", s / "deep" / "dir" / "x.txt") is None
    for path in (
        work.root / "docs" / "x.md",
        work.root / "a.txt",
        work.tmp / "other.txt",
        work.tmp / "agk-conductorx" / "x.txt",
        s / ".." / "x.txt",
        work.tmp / "agk-conductor-" / "x.txt",
        Path("/etc/passwd"),
        "relative.txt",
        "",
    ):
        found = work.write("Write", path)
        assert found is not None and MARK in found["permissionDecisionReason"], path
    for tool in ("Edit", "MultiEdit", "NotebookEdit"):
        assert work.write(tool, s / "x.txt") is not None, tool


def test_ac5_a_scratch_directory_that_links_into_the_work_tree_is_refused(work):
    """REQ-037 AC5"""
    work.tmp.joinpath("agk-conductor-9").symlink_to(work.root)
    assert work.write("Write", work.tmp / "agk-conductor-9" / "a.txt") is not None
    link = work.tmp / "agk-conductor-9"
    run = f"{env(link)}make -C {link} test"
    assert work.bash(run) is not None
