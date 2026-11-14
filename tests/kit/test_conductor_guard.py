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


def test_ac5_a_run_may_set_agk_base_to_a_sha_and_no_other_variable(work):
    """REQ-037 AC5 (the verdict on 482448d: reproduce a step that inherits AGK_BASE)"""
    s, sha = work.scratch, work.feature
    for tail in (f"make -C {s} test", f"python3 -I {s}/scripts/agk/check_adrs.py"):
        assert work.bash(f"{env(s)}AGK_BASE={sha} {tail}") is None, tail
        assert work.bash(f"{env(s)}AGK_BASE={sha[:7]} {tail}") is None, tail
    for bad in (
        f"GH_TOKEN=x make -C {s} test",
        f"AGK_BASE=main make -C {s} test",
        f"AGK_BASE= make -C {s} test",
        f"AGK_BASE={sha}x make -C {s} test",
        f"AGK_BASE=abc make -C {s} test",
        f"AGK_BASE={sha} GH_TOKEN=x make -C {s} test",
        f"AGK_BASE={sha} AGK_BASE={sha} make -C {s} test",
        f"GH_TOKEN=x AGK_BASE={sha} make -C {s} test",
        f"AGK_BASE={sha}",
        f"AGK_BASE={sha} git status",
    ):
        found = work.bash(f"{env(s)}{bad}")
        assert found is not None and MARK in found["permissionDecisionReason"], bad


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


# --- a `#` is read the way bash reads it (brief #351, ADR-0199) -----------------------------------

SESSION_SCRIPT = "scripts/agk/session.py"
HASH_NO = [
    "git status#;id",
    "git diff origin/main...HEAD#;id",
    "gh api repos/x/y#;touch z",
    "gh api --method GET repos/o/r/pulls/7 #;id",
    f"python3 {SESSION_SCRIPT} queue --role conductor#;id",
    f"python3 {SESSION_SCRIPT} review-queue --all#;id",
    "date -u#;id",
    "gh api --method POST repos/o/r/issues/7/comments -f body=hello#;id",
    "gh api --method POST repos/o/r/issues/7/comments -f body=see #12",
]
HASH_OK = [
    "gh api --method POST repos/o/r/issues/7/comments -f 'body=see #12;id'",
    'gh api --method POST repos/o/r/issues/7/comments -f "body=see #12"',
]


@pytest.fixture
def with_script(project: Path) -> Path:
    (project / "scripts" / "agk").mkdir(parents=True)
    (project / SESSION_SCRIPT).write_text("print('x')\n", encoding="utf-8")
    return project


def test_the_session_forms_are_allowed_without_a_hash(with_script):
    """REQ-002: brief #351 answer 3 (every form allowed today stays allowed)."""
    for command in (
        f"python3 {SESSION_SCRIPT} queue --role conductor",
        f"python3 {SESSION_SCRIPT} review-queue --all",
    ):
        assert denial(run_hook(bash_of(command, with_script), with_script).stdout) is None


def bash_of(command: str, cwd: Path | None = None) -> dict:
    payload: dict = {"tool_name": "Bash", "tool_input": {"command": command}}
    if cwd is not None:
        payload["cwd"] = str(cwd)
    return payload


@pytest.mark.parametrize("command", HASH_NO)
def test_a_hash_outside_quotes_is_refused_in_every_allowed_form(with_script, command):
    """REQ-002: brief #351 answers 1, 2 and 3 (git reads, gh api, session.py, the comment)."""
    found = denial(run_hook(bash_of(command, with_script), with_script).stdout)
    assert found is not None and MARK in found["permissionDecisionReason"], command
    assert command not in found["permissionDecisionReason"]


@pytest.mark.parametrize("command", HASH_OK)
def test_a_hash_inside_quotes_in_a_comment_body_stays_allowed(with_script, command):
    """REQ-002: brief #351 answer 3."""
    assert denial(run_hook(bash_of(command, with_script), with_script).stdout) is None, command


def test_a_hash_in_a_bounded_run_is_refused(work):
    """REQ-002: brief #351 answer 2 (the bounded run)."""
    s = work.scratch
    E = env(s)
    assert work.bash(f"{E}make -C {s} test") is None
    for command in (
        f"{E}make -C {s} test#;id",
        f"{E}make -C {s} test #;id",
        f"{E}python3 -I {s}/scripts/agk/check_adrs.py --base main#;id",
        f"git worktree add {s} {work.feature}#;id",
        f"git worktree remove {s}#;id",
    ):
        found = work.bash(command)
        assert found is not None and MARK in found["permissionDecisionReason"], command


# --- the guarded merge (brief #531, ADR-0265; SPEC-0039 rule 8) -----------------------------------

MERGE_SCRIPT = "scripts/agk/merge_cleared.py"
FULL = "a1b2c3d4e5" * 4
ALLOW_RULE = "conductor guard rule 6: the guarded merge"
FLOW_ON = '[flow]\nauto_merge = true\nauto_merge_method = "squash"\n'
FLOW_OFF = "[flow]\nauto_merge = false\n"
REPO_ROOT = Path(__file__).resolve().parents[2]


def git_in(root: Path, *args: str, text: str | None = None) -> str:
    env = {
        "PATH": "/usr/bin:/bin",
        "GIT_CONFIG_NOSYSTEM": "1",
        "HOME": str(root),
        "GIT_AUTHOR_NAME": "t",
        "GIT_AUTHOR_EMAIL": "t@example.com",
        "GIT_COMMITTER_NAME": "t",
        "GIT_COMMITTER_EMAIL": "t@example.com",
    }
    return subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
        ["git", "-C", str(root), *args], input=text, capture_output=True, text=True, check=True,
        env=env,
    ).stdout.strip()  # fmt: skip


def merge_project(tmp_path: Path, here: str, there: str | None) -> Path:
    """A project whose checkout's agk.toml has the flow table HERE and whose `origin/main` has
    THERE (None: no default branch fetched)."""
    root = tmp_path / "project"
    (root / "scripts" / "agk").mkdir(parents=True)
    (root / MERGE_SCRIPT).write_text("print('x')\n", encoding="utf-8")
    git_in(root, "init", "-q")
    git_in(root, "remote", "add", "origin", "https://github.com/o/r.git")
    (root / "agk.toml").write_text(f'default_branch = "main"\n{here}', encoding="utf-8")
    if there is not None:
        blob = git_in(
            root, "hash-object", "-w", "--stdin", text=f'default_branch = "main"\n{there}'
        )
        tree = git_in(root, "mktree", text=f"100644 blob {blob}\tagk.toml\n")
        commit = git_in(root, "commit-tree", tree, "-m", "main", text="")
        git_in(root, "update-ref", "refs/remotes/origin/main", commit)
    return root


def merge_decision(root: Path, command: str, shadow: bool = False) -> dict | None:
    temp = root.parent / "systmp"
    temp.mkdir(exist_ok=True)
    env = {"PATH": "/usr/bin:/bin", "CLAUDE_PROJECT_DIR": str(root), "TMPDIR": str(temp)}
    proc = subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, str(HOOK), *(["--shadow"] if shadow else [])],
        input=json.dumps(bash_of(command, root)),
        capture_output=True,
        text=True,
        env=env,
        cwd=str(root),
    )
    assert proc.returncode == 0, proc.stderr
    return json.loads(proc.stdout)["hookSpecificOutput"] if proc.stdout.strip() else None


def allows_merge(found: dict | None) -> bool:
    return (
        found is not None
        and found["permissionDecision"] == "allow"
        and found["permissionDecisionReason"].startswith(ALLOW_RULE)
    )


@pytest.mark.parametrize(
    "command",
    [
        f"python3 {MERGE_SCRIPT} --pr 7 --sha {FULL}",
        f"python {MERGE_SCRIPT} --pr 7 --sha {FULL}",
        f"python3 ./{MERGE_SCRIPT} --pr 1234 --sha {FULL}",
    ],
)
def test_the_exact_merge_command_is_allowed_with_auto_merge_on_in_both_places(tmp_path, command):
    """REQ-046 AC5: SPEC-0039 rule 8 (the one exception, as the guard reads `auto_start`)."""
    root = merge_project(tmp_path, FLOW_ON, FLOW_ON)
    assert allows_merge(merge_decision(root, command)), command


def test_the_full_path_of_the_projects_own_script_is_allowed(tmp_path):
    """REQ-046 AC5: SPEC-0039 rule 8 (the project's own regular file)."""
    root = merge_project(tmp_path, FLOW_ON, FLOW_ON)
    command = f"python3 {root / MERGE_SCRIPT} --pr 7 --sha {FULL}"
    assert allows_merge(merge_decision(root, command))


@pytest.mark.parametrize(
    ("here", "there"),
    [
        (FLOW_OFF, FLOW_ON),
        (FLOW_ON, FLOW_OFF),
        ("", FLOW_ON),
        (FLOW_ON, ""),
        (FLOW_ON, None),
        ('[flow]\nauto_merge = true\nauto_merge_method = "merge"\n', FLOW_ON),
        ('[flow]\nauto_merge = "true"\nauto_merge_method = "squash"\n', FLOW_ON),
        ("[flow\n", FLOW_ON),
    ],
)
def test_the_merge_command_is_denied_unless_the_setting_is_on_in_both_places(tmp_path, here, there):
    """REQ-046 AC5: SPEC-0039 rule 8 (off, absent or malformed in either place denies)."""
    root = merge_project(tmp_path, here, there)
    found = merge_decision(root, f"python3 {MERGE_SCRIPT} --pr 7 --sha {FULL}")
    assert found is not None and found["permissionDecision"] == "deny"
    assert found["permissionDecisionReason"].startswith(MARK)


@pytest.mark.parametrize(
    "command",
    [
        f"python3 {MERGE_SCRIPT} --pr 7 --sha {FULL[:12]}",
        f"python3 {MERGE_SCRIPT} --pr 7 --sha {FULL.upper()}",
        f"python3 {MERGE_SCRIPT} --pr 7 --sha {FULL}0",
        f"python3 {MERGE_SCRIPT} --pr 07x --sha {FULL}",
        f"python3 {MERGE_SCRIPT} --pr 0 --sha {FULL}",
        f"python3 {MERGE_SCRIPT} --sha {FULL} --pr 7",
        f"python3 {MERGE_SCRIPT} --pr 7 --sha {FULL} --force",
        f"python3 {MERGE_SCRIPT} --pr 7",
        f"python3 -I {MERGE_SCRIPT} --pr 7 --sha {FULL}",
        f"python3.12 {MERGE_SCRIPT} --pr 7 --sha {FULL}",
        f"python3 ../copy/scripts/agk/merge_cleared.py --pr 7 --sha {FULL}",
        f"python3 other/merge_cleared.py --pr 7 --sha {FULL}",
        f"python3 {MERGE_SCRIPT} --pr 7 --sha {FULL}; gh pr merge 7",
        f"AGK_X=1 python3 {MERGE_SCRIPT} --pr 7 --sha {FULL}",
        f"gh api --method PUT repos/o/r/pulls/7/merge -f sha={FULL} -f merge_method=squash",
        f"gh api -X PUT repos/o/r/pulls/7/merge -f sha={FULL}",
        "gh api -XPUT repos/o/r/pulls/7/merge",
        "gh api -X=PUT repos/o/r/pulls/7/merge",
        "gh api -Xput repos/o/r/pulls/7/merge",
        "gh api -XDELETE repos/o/r/issues/comments/9",
        "gh api -X=DELETE repos/o/r/issues/comments/9",
        "gh api --unknown repos/o/r/pulls/7/merge",
        "gh api --unknown=PUT repos/o/r/pulls/7",
        "gh api -Z repos/o/r/pulls/7",
        "gh pr merge 7 --squash",
        f"python3 scripts/agk/session.py merge --pr 7 --sha {FULL}",
    ],
)
def test_every_other_form_and_every_other_merge_path_is_denied(tmp_path, command):
    """REQ-046 AC5: SPEC-0039 rule 8 (a short sha, an extra option, another copy, another path)."""
    root = merge_project(tmp_path, FLOW_ON, FLOW_ON)
    other = root / "other"
    other.mkdir()
    (other / "merge_cleared.py").write_text("print('x')\n", encoding="utf-8")
    found = merge_decision(root, command)
    assert found is not None and found["permissionDecision"] == "deny", command


def test_a_link_to_the_script_is_denied(tmp_path):
    """REQ-046 AC5: SPEC-0039 rule 8 (never through a link)."""
    root = merge_project(tmp_path, FLOW_ON, FLOW_ON)
    (root / "linked.py").symlink_to(root / MERGE_SCRIPT)
    found = merge_decision(root, f"python3 linked.py --pr 7 --sha {FULL}")
    assert found is not None and found["permissionDecision"] == "deny"


def test_the_shadow_reviewer_never_runs_the_merge(tmp_path):
    """REQ-046 AC5: SPEC-0039 rule 8 (only the conductor role)."""
    root = merge_project(tmp_path, FLOW_ON, FLOW_ON)
    found = merge_decision(root, f"python3 {MERGE_SCRIPT} --pr 7 --sha {FULL}", shadow=True)
    assert found is not None and found["permissionDecision"] == "deny"


def test_builders_are_never_allowed_the_command_and_no_project_wide_deny_is_added():
    """REQ-046 AC5: SPEC-0039 rule 8, Q-S0039-15 and amendment 136 (the one exact form is allowed
    so an unattended conductor can merge; every other form stays on ask; nothing is denied)."""
    data = json.loads((REPO_ROOT / ".claude" / "settings.json").read_text(encoding="utf-8"))
    ask, allow = data["permissions"]["ask"], data["permissions"]["allow"]
    exact = "Bash(python3 scripts/agk/merge_cleared.py*)"
    assert exact in allow
    assert "Bash(python scripts/agk/merge_cleared.py*)" in ask
    assert [e for e in allow if "merge_cleared" in e] == [exact]
    assert not any("merge_cleared" in e for e in data["permissions"]["deny"])


def numbered(path: Path, number: int) -> str:
    lines = path.read_text(encoding="utf-8").splitlines()
    return next(x for x in lines if x.startswith(f"{number}. "))


PRINCIPLE_2 = (
    "2. Agents never merge, and never bypass checks. The one exception: with `auto_merge = true` "
    "on the default branch, the conductor alone may merge a pull request it cleared, and only "
    "through `scripts/agk/merge_cleared.py`."
)
SESSION_RULE_2 = (
    "2. A session never merges, never tags, never enables auto-merge, never posts a verdict and "
    "never touches a secret. The one exception: with `auto_merge = true` on the default branch, "
    "the conductor alone may merge a pull request it cleared, and only through "
    "`scripts/agk/merge_cleared.py`."
)


def test_principle_2_and_session_rule_2_each_gain_exactly_the_one_sentence():
    """REQ-046 AC5: SPEC-0039 rule 8 and Q-S0039-14 (one sentence each, nothing else)."""
    principles = REPO_ROOT / "constitution" / "principles.md"
    assert numbered(principles, 2) == PRINCIPLE_2
    assert numbered(REPO_ROOT / "config" / "session-rules.md", 2) == SESSION_RULE_2
    rules = [x for x in principles.read_text(encoding="utf-8").splitlines() if x[:1].isdigit()]
    assert len(rules) == 12


# --- brief #1263 (ADR-0534): the conductor runs the router in local mode -------------------------

ROUTE_SCRIPT = "scripts/agk/route.py"
ROUTE_MARK = "setting: execution"
RECORD_ISSUE = {"number": 90, "title": "Local mode since 2026-11-14"}
SEARCH_GH = """#!/usr/bin/env python3
import json, os, sys
args = sys.argv[1:]
with open(os.environ["GH_LOG"], "a") as log:
    log.write(json.dumps(args) + "\\n")
endpoint = next(a for a in args if not a.startswith("-") and a not in ("api", "GET"))
answer = json.loads(os.environ["GH_ANSWER"])
if endpoint.startswith("search/issues") and answer is not None:
    print(json.dumps({"total_count": len(answer), "items": answer}))
    sys.exit(0)
if endpoint.startswith("repos/o/r/issues") and answer is not None:
    print(json.dumps(answer))
    sys.exit(0)
sys.exit(1)
"""


def route_project(project: Path, execution: str | None = None) -> Path:
    (project / "scripts" / "agk").mkdir(parents=True, exist_ok=True)
    (project / ROUTE_SCRIPT).write_text("print('x')\n", encoding="utf-8")
    if execution is not None:
        (project / "agk.toml").write_text(f'execution = "{execution}"\n', encoding="utf-8")
    return project


def run_route_hook(project: Path, command: str, issues: list | None, tmp: Path):
    """The hook with a recorded `gh` on PATH that answers the search with ISSUES (None: fails)."""
    bin_dir = tmp / "ghbin"
    bin_dir.mkdir(exist_ok=True)
    gh = bin_dir / "gh"
    gh.write_text(SEARCH_GH, encoding="utf-8")
    gh.chmod(0o755)
    log = tmp / "gh.log"
    env = {
        "PATH": f"{bin_dir}:/usr/bin:/bin",
        "CLAUDE_PROJECT_DIR": str(project),
        "GH_LOG": str(log),
        "GH_ANSWER": json.dumps(issues),
    }
    proc = subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, str(HOOK)],
        input=json.dumps(bash_of(command, project)),
        capture_output=True,
        text=True,
        env=env,
    )
    calls = [json.loads(x) for x in log.read_text().splitlines()] if log.exists() else []
    return denial(proc.stdout), calls


@pytest.mark.parametrize(
    "command",
    [
        f"python3 {ROUTE_SCRIPT} --all",
        f"python {ROUTE_SCRIPT} --all",
        f"python3 {ROUTE_SCRIPT} --pr 12",
    ],
)
def test_a_the_router_is_allowed_while_the_record_issue_is_open(project, tmp_path, command):
    """REQ-039: brief #1263 (a), local mode as route.py reads it (one search call)."""
    root = route_project(project)
    found, calls = run_route_hook(root, command, [RECORD_ISSUE], tmp_path)
    assert found is None
    assert len(calls) == 1 and any(a.startswith("search/issues") for a in calls[0])


def test_a_execution_local_allows_the_router_without_reading_github(project, tmp_path):
    """REQ-039: brief #1263 answer 6, `execution = "local"` answers without any issue read."""
    root = route_project(project, "local")
    found, calls = run_route_hook(root, f"python3 {ROUTE_SCRIPT} --all", None, tmp_path)
    assert found is None and calls == []


@pytest.mark.parametrize(
    "command",
    [
        f"python3 {ROUTE_SCRIPT} --all --dry-run",
        f"python3 {ROUTE_SCRIPT} --pr 12;x",
        f"python3 {ROUTE_SCRIPT} --pr 12x",
        f"python3 {ROUTE_SCRIPT} --pr",
        f"python3 {ROUTE_SCRIPT} --branch",
        f"python3 {ROUTE_SCRIPT} --health",
        f"python3 {ROUTE_SCRIPT}",
        f"python3 {ROUTE_SCRIPT} --all --pr 12",
        "python3 other/route.py --all",
        "python3 scripts/agk/merge_cleared.py --all",
        f"python3 -I {ROUTE_SCRIPT} --all",
        f"bash {ROUTE_SCRIPT} --all",
    ],
)
def test_b_every_other_form_path_or_script_is_refused(project, tmp_path, command):
    """REQ-039: brief #1263 (b), exactly the two forms, the project's own route.py."""
    root = route_project(project, "local")
    found, _ = run_route_hook(root, command, [RECORD_ISSUE], tmp_path)
    assert found is not None and found["permissionDecision"] == "deny"
    assert MARK in found["permissionDecisionReason"]


def test_b_a_link_to_the_router_is_refused(project, tmp_path):
    """REQ-039: brief #1263 (b), never through a link."""
    root = route_project(project, "local")
    elsewhere = tmp_path / "route.py"
    elsewhere.write_text("print('x')\n", encoding="utf-8")
    (root / ROUTE_SCRIPT).unlink()
    (root / ROUTE_SCRIPT).symlink_to(elsewhere)
    found, _ = run_route_hook(root, f"python3 {ROUTE_SCRIPT} --all", None, tmp_path)
    assert found is not None


@pytest.mark.parametrize("issues", [[], None])
def test_c_no_record_issue_is_refused_naming_the_setting(project, tmp_path, issues):
    """REQ-039: brief #1263 (c), CI mode: the router workflow moves the labels there."""
    root = route_project(project, "github")
    found, _ = run_route_hook(root, f"python3 {ROUTE_SCRIPT} --all", issues, tmp_path)
    assert found is not None and found["permissionDecision"] == "deny"
    reason = found["permissionDecisionReason"]
    assert MARK in reason and ROUTE_MARK in reason
    assert "Local mode since" not in reason  # the setting, never a value


def test_c_the_shadow_never_runs_the_router(project, tmp_path):
    """REQ-039: brief #1263, the shadow reviewer gets no new command."""
    root = route_project(project, "local")
    payload = bash_of(f"python3 {ROUTE_SCRIPT} --all", root)
    proc = subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, str(HOOK), "--shadow"],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        env={"PATH": "/usr/bin:/bin", "CLAUDE_PROJECT_DIR": str(root)},
    )
    assert denial(proc.stdout) is not None


def test_d_the_agent_and_the_review_pass_name_the_command_once_each():
    """REQ-039: brief #1263 (d), the conductor's pass runs the router in local mode."""
    command = "python3 scripts/agk/route.py --all"
    agent = (REPO_ROOT / ".claude" / "agents" / "conductor.md").read_text(encoding="utf-8")
    skill = (REPO_ROOT / "skills" / "review-pass" / "SKILL.md").read_text(encoding="utf-8")
    assert agent.count(command) == 1
    assert skill.count(command) == 1
    guide = (REPO_ROOT / "docs" / "guides" / "local-mode.md").read_text(encoding="utf-8")
    assert "Until the conductor's guard allows that command" not in guide


# --- brief #1281 (ADR-0542): the conductor checks a local evidence record -----------------------

EVIDENCE_SCRIPT = "scripts/agk/evidence.py"
HEX = "0123456789abcdef0123456789abcdef01234567"


class Evidence(Work):
    """A real clone with the project's own evidence.py, a scratch record and a shared record."""

    def __init__(self, root: Path) -> None:
        super().__init__(root)
        (self.root / "scripts" / "agk").mkdir(parents=True)
        (self.root / EVIDENCE_SCRIPT).write_text("print('x')\n", encoding="utf-8")
        self.scratch.mkdir()
        self.record = self.scratch / "record.json"
        self.record.write_text("{}\n", encoding="utf-8")
        shared = self.root / ".git" / "agk-evidence"
        shared.mkdir()
        self.shared = shared / f"{HEX}.json"
        self.shared.write_text("{}\n", encoding="utf-8")

    def decide(self, command: str, *args: str):
        payload = bash_of(command, self.root)
        proc = subprocess.run(  # nosec B603 - fixed argument list, no shell
            [sys.executable, str(HOOK), *args],
            input=json.dumps(payload),
            capture_output=True,
            text=True,
            env={
                "PATH": "/usr/bin:/bin",
                "CLAUDE_PROJECT_DIR": str(self.root),
                "TMPDIR": str(self.tmp),
            },
        )
        return denial(proc.stdout)


@pytest.fixture
def ev(tmp_path: Path) -> Evidence:
    return Evidence(tmp_path)


EVIDENCE_OK = [
    f"python3 {EVIDENCE_SCRIPT} check --head {HEX}",
    f"python {EVIDENCE_SCRIPT} check --head abc1234",
    f"python3 {EVIDENCE_SCRIPT} check --head abc1234 --sample 3 --json",
    f"python3 {EVIDENCE_SCRIPT} check --json --head abc1234",
    f"python3 ./{EVIDENCE_SCRIPT} check --head abc1234",
    f"python3 {EVIDENCE_SCRIPT} check {{record}} --head abc1234",
    f"python3 {EVIDENCE_SCRIPT} check {{record}} --head {HEX} --sample 2 --json",
    f"python3 {EVIDENCE_SCRIPT} check {{shared}} --head {HEX}",
]


@pytest.mark.parametrize("command", EVIDENCE_OK)
def test_a_both_forms_of_the_evidence_check_are_allowed(ev, command):
    """REQ-039: brief #1281 answer 3 (a): no record, or one of a scratch or the shared folder."""
    found = ev.decide(command.format(record=ev.record, shared=ev.shared))
    assert found is None, command


def test_a_the_full_path_of_the_projects_own_script_is_allowed(ev):
    """REQ-039: brief #1281 answer 1, the project's own regular file named by its full path."""
    assert ev.decide(f"python3 {ev.root / EVIDENCE_SCRIPT} check --head {HEX}") is None


EVIDENCE_NO = [
    f"python3 {EVIDENCE_SCRIPT} check",
    f"python3 {EVIDENCE_SCRIPT} check {{record}}",
    f"python3 {EVIDENCE_SCRIPT}",
    f"python3 {EVIDENCE_SCRIPT} --help",
    f"python3 {EVIDENCE_SCRIPT} rerun --head {HEX}",
    f"python3 {EVIDENCE_SCRIPT} check --head {HEX} --write",
    f"python3 {EVIDENCE_SCRIPT} check --head {HEX} --record x",
    f"python3 {EVIDENCE_SCRIPT} check --head {HEX} --head {HEX}",
    f"python3 {EVIDENCE_SCRIPT} check --head {HEX} --json --json",
    f"python3 {EVIDENCE_SCRIPT} check --head {HEX} --sample 2 --sample 3",
    f"python3 {EVIDENCE_SCRIPT} check --head abc123",
    f"python3 {EVIDENCE_SCRIPT} check --head {HEX}0",
    f"python3 {EVIDENCE_SCRIPT} check --head HEAD",
    f"python3 {EVIDENCE_SCRIPT} check --head",
    f"python3 {EVIDENCE_SCRIPT} check --head {HEX} --sample 0",
    f"python3 {EVIDENCE_SCRIPT} check --head {HEX} --sample x",
    f"python3 {EVIDENCE_SCRIPT} check --head={HEX}",
    f"python3 {EVIDENCE_SCRIPT} check {{record}} {{shared}} --head {HEX}",
    f"python3 {EVIDENCE_SCRIPT} check {{inside}} --head {HEX}",
    f"python3 {EVIDENCE_SCRIPT} check {{missing}} --head {HEX}",
    f"python3 {EVIDENCE_SCRIPT} check {{folder}} --head {HEX}",
    f"python3 {EVIDENCE_SCRIPT} check record.json --head {HEX}",
    f"python3 {EVIDENCE_SCRIPT} check /etc/hostname --head {HEX}",
    f"python3 {EVIDENCE_SCRIPT} check --head {HEX}; rm -rf x",
    f"python3 {EVIDENCE_SCRIPT} check --head {HEX} && date -u",
    f"python3 {EVIDENCE_SCRIPT} check --head {HEX} > out.txt",
    f"python3 {EVIDENCE_SCRIPT} check --head $(git rev-parse HEAD)",
    f"python3 {EVIDENCE_SCRIPT} check --head {HEX} | tee x",
    f"python3 -I {EVIDENCE_SCRIPT} check --head {HEX}",
    f"python3 other/evidence.py check --head {HEX}",
    f"python3 {{scratch}}/scripts/agk/evidence.py check --head {HEX}",
    f"bash {EVIDENCE_SCRIPT} check --head {HEX}",
    f"python3 scripts/agk/prepush.py check --head {HEX}",
]


@pytest.mark.parametrize("command", EVIDENCE_NO)
def test_b_every_other_form_option_shell_character_or_copy_is_refused(ev, command):
    """REQ-039: brief #1281 answer 3 (b), naming the guard's rule."""
    inside = ev.root / "record.json"
    inside.write_text("{}\n", encoding="utf-8")
    copy = ev.scratch / "scripts" / "agk"
    copy.mkdir(parents=True, exist_ok=True)
    (copy / "evidence.py").write_text("print('x')\n", encoding="utf-8")
    text = command.format(
        record=ev.record,
        shared=ev.shared,
        inside=inside,
        missing=ev.scratch / "none.json",
        folder=ev.scratch,
        scratch=ev.scratch,
    )
    found = ev.decide(text)
    assert found is not None and found["permissionDecision"] == "deny", text
    assert MARK in found["permissionDecisionReason"]


def test_b_a_record_that_links_out_of_the_scratch_directory_is_refused(ev):
    """REQ-039: brief #1281 answer 1, RECORD a regular file of the scratch, never a link."""
    outside = ev.tmp / "elsewhere.json"
    outside.write_text("{}\n", encoding="utf-8")
    link = ev.scratch / "link.json"
    link.symlink_to(outside)
    assert ev.decide(f"python3 {EVIDENCE_SCRIPT} check {link} --head {HEX}") is not None


def test_b_a_link_to_the_script_is_refused(ev):
    """REQ-039: brief #1281 answer 1, the project's own script, never through a link."""
    elsewhere = ev.tmp / "evidence.py"
    elsewhere.write_text("print('x')\n", encoding="utf-8")
    (ev.root / EVIDENCE_SCRIPT).unlink()
    (ev.root / EVIDENCE_SCRIPT).symlink_to(elsewhere)
    assert ev.decide(f"python3 {EVIDENCE_SCRIPT} check --head {HEX}") is not None


def test_b_the_shadow_never_runs_the_evidence_check(ev):
    """REQ-039: brief #1281, the shadow reviewer gets no new command."""
    assert ev.decide(f"python3 {EVIDENCE_SCRIPT} check --head {HEX}", "--shadow") is not None


def test_the_agent_names_the_check_before_a_clearing_verdict_and_in_the_guard_list():
    """REQ-039: brief #1281 answer 2, the local-mode paragraph and the guard's list."""
    agent = (REPO_ROOT / ".claude" / "agents" / "conductor.md").read_text(encoding="utf-8")
    local = next(p for p in agent.split("\n\n") if p.startswith("Local mode."))
    assert "python3 scripts/agk/evidence.py check --head <sha>" in local
    assert "before a clearing verdict" in local
    never = next(line for line in agent.splitlines() if line.startswith("- Edit a file"))
    assert "`evidence.py check`" in never
