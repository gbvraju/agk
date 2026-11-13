"""/agk:workflow-apply: a builder's proposed workflow file is checked, moved into place, committed
and answered by one owner command (brief #1189, REQ-039, ADR-0505).

Invented repositories in a temporary folder with a local bare remote, `gh` stubbed on `PATH`, no
network.
"""

from __future__ import annotations

import os
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
from pathlib import Path

import pytest
from test_session import Stub, clean_env

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts" / "agk"
REPO = "example/proj"
BRANCH = "claude/brief-7"
OLD = (
    "name: ci\non: [push]\njobs:\n  test:\n    runs-on: ubuntu-latest\n"
    "    steps:\n      - run: echo old\n"
)
NEW = (
    "name: ci\n"
    "on:\n"
    "  pull_request:\n"
    "    types: [opened, synchronize]\n"
    "jobs:\n"
    "  test:\n"
    "    runs-on: ubuntu-latest\n"
    "    steps:\n"
    "      - name: say\n"
    "        run: |\n"
    "          echo \"new: one\"\n"
    "          echo two\n"
)
PROPOSAL = ".agk/workflow-proposals/ci.yml"
TARGET = ".github/workflows/ci.yml"
QUESTION = (
    "Question: Q-7-2 for the maintainers: please apply the proposal with "
    "`/agk:workflow-apply 7`\n\nThe file is at .agk/workflow-proposals/ci.yml."
)


def git(cwd: Path, *args: str) -> str:
    proc = subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
        ["git", *args], cwd=cwd, capture_output=True, text=True, check=True, env=clean_env()
    )
    return proc.stdout.strip()


def write(root: Path, rel: str, text: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def identity(root: Path) -> None:
    git(root, "config", "user.email", "owner@example.com")
    git(root, "config", "user.name", "owner")
    git(root, "config", "commit.gpgsign", "false")


class World:
    """A bare remote, the builder's pushed branch and the owner's clone of the remote."""

    def __init__(self, tmp: Path, proposal: str = NEW) -> None:
        self.bare = tmp / "remote.git"
        git(tmp, "init", "-q", "--bare", "-b", "main", str(self.bare))
        seed = tmp / "seed"
        seed.mkdir()
        git(seed, "init", "-q", "-b", "main")
        identity(seed)
        write(seed, TARGET, OLD)
        write(seed, "README.md", "proj\n")
        git(seed, "add", "-A")
        git(seed, "commit", "-q", "-m", "base")
        git(seed, "remote", "add", "origin", str(self.bare))
        git(seed, "push", "-q", "origin", "main")
        git(seed, "checkout", "-q", "-b", BRANCH)
        write(seed, PROPOSAL, proposal)
        write(seed, "src/app.py", "x = 1\n")
        git(seed, "add", "-A")
        git(seed, "commit", "-q", "-m", "checkpoint: the proposal")
        git(seed, "push", "-q", "origin", BRANCH)
        self.head = git(seed, "rev-parse", "HEAD")
        self.owner = tmp / "owner"
        git(tmp, "clone", "-q", str(self.bare), str(self.owner))
        identity(self.owner)
        self.stub = Stub(tmp)

    def serve_pull(self, ref: str = BRANCH, sha: str | None = None, state: str = "open") -> None:
        self.stub.serve(
            f"repos/{REPO}/pulls/7",
            {
                "number": 7,
                "state": state,
                "head": {"ref": ref, "sha": sha or self.head, "repo": {"full_name": REPO}},
                "base": {"ref": "main", "repo": {"full_name": REPO, "default_branch": "main"}},
            },
        )

    def serve_comments(self, *bodies: str) -> None:
        self.stub.serve(
            f"repos/{REPO}/issues/7/comments",
            [{"id": i + 1, "user": {"login": "bot"}, "body": b} for i, b in enumerate(bodies)],
        )

    def run(self, *args: str, cwd: Path | None = None):
        env = clean_env()
        env.update(
            PATH=f"{self.stub.bin}{os.pathsep}{os.environ['PATH']}", GH_STUB_DIR=str(self.stub.dir)
        )
        return subprocess.run(  # nosec B603 - fixed argument list, no shell
            [sys.executable, str(SCRIPTS / "workflow_apply.py"), "--repo", REPO, *args],
            cwd=cwd or self.owner,
            capture_output=True,
            text=True,
            env=env,
            timeout=120,
        )

    def remote(self, *args: str) -> str:
        return git(self.bare, *args)

    def posts(self) -> list[list]:
        return [c for c in self.stub.calls() if c[0] != "GET"]


@pytest.fixture
def world(tmp_path: Path) -> World:
    w = World(tmp_path)
    w.serve_pull()
    w.serve_comments("Progress: abc done 1/3; next: tests", QUESTION)
    return w


def test_a_the_dry_run_lists_the_proposal_its_target_and_the_diff_and_changes_nothing(world):
    """REQ-039: answer 2 (a dry run by default)."""
    before = world.remote("rev-parse", f"refs/heads/{BRANCH}")
    owner_before = git(world.owner, "status", "--porcelain")
    proc = world.run("--pr", "7")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert f"{PROPOSAL} -> {TARGET}" in proc.stdout
    assert "-      - run: echo old" in proc.stdout
    assert "+          echo two" in proc.stdout
    assert "Q-7-2" in proc.stdout
    assert "dry run" in proc.stdout
    assert f"--yes --head {world.head}" in proc.stdout  # the head the owner was shown
    assert world.remote("rev-parse", f"refs/heads/{BRANCH}") == before
    assert git(world.owner, "status", "--porcelain") == owner_before
    assert world.posts() == []
    assert git(world.owner, "worktree", "list").count("\n") == 0  # the temporary worktree is gone


@pytest.mark.parametrize(
    ("text", "why"),
    [
        ("name: ci\non: [push\njobs:\n  test:\n    runs-on: x\n", "does not parse"),
        ("name: ci\njobs:\n  test:\n\truns-on: x\n", "does not parse"),
        ("name: ci\non:\n  push:\n    branches: ['main\n", "does not parse"),
        ("name: ci\non: [push]\nsteps:\n  - run: x\n", "names no jobs"),
        ("name: ci\non: [push]\njobs:\n", "names no jobs"),
    ],
)
def test_b_a_proposal_that_does_not_parse_is_refused_naming_the_file(tmp_path, text, why):
    """REQ-039: answer 2 (each proposal parses as YAML and names `jobs`)."""
    w = World(tmp_path, proposal=text)
    w.serve_pull()
    w.serve_comments(QUESTION)
    before = w.remote("rev-parse", f"refs/heads/{BRANCH}")
    proc = w.run("--pr", "7", "--yes", "--head", w.head)
    assert proc.returncode == 1, proc.stdout + proc.stderr
    assert f"refused: {PROPOSAL}" in proc.stdout and why in proc.stdout
    assert w.remote("rev-parse", f"refs/heads/{BRANCH}") == before
    assert w.posts() == []


def test_c_yes_commits_the_moved_file_removes_the_folder_pushes_and_answers(world):
    """REQ-039: answer 2 (`--yes` applies, commits, pushes and posts the `Answer:` line)."""
    proc = world.run("--pr", "7", "--yes", "--head", world.head)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    new = world.remote("rev-parse", f"refs/heads/{BRANCH}")
    assert new != world.head
    assert world.remote("rev-parse", f"{new}^") == world.head  # one commit on the branch's head
    assert world.remote("show", f"{new}:{TARGET}") + "\n" == NEW
    assert world.remote("ls-tree", "-r", "--name-only", new, ".agk/") == ""
    subject = world.remote("log", "-1", "--format=%s", new)
    assert subject == "workflow: apply the proposal of #7 (Q-7-2)"
    main = world.remote("rev-parse", "refs/heads/main")
    assert main == world.remote("rev-parse", f"{world.head}^")
    posts = world.posts()
    assert len(posts) == 1
    method, endpoint, rest = posts[0]
    assert (method, endpoint) == ("POST", f"repos/{REPO}/issues/7/comments")
    assert f"body=Answer: Q-7-2 done: {new} applied by /agk:workflow-apply" in rest
    assert "byte-for-byte" in proc.stdout


def test_c_the_q_id_is_read_from_the_newest_maintainers_question_naming_the_command(world):
    """REQ-039: answer 2 (the newest maintainers question that names the command)."""
    world.serve_comments(
        QUESTION,
        "Question: Q-7-3 for the maintainers: apply with /agk:workflow-apply 7 (the second file)",
        "Question: Q-7-4 a question for the conductor that names /agk:workflow-apply",
        "Question: Q-7-5 for the maintainers: another ask with no command",
    )
    proc = world.run("--pr", "7", "--yes", "--head", world.head)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "(Q-7-3)" in world.remote("log", "-1", "--format=%s", f"refs/heads/{BRANCH}")


def test_c_no_maintainers_question_naming_the_command_changes_nothing(world):
    """REQ-039: answer 2 (without the Q id there is nothing to answer; it prints what is
    missing)."""
    world.serve_comments("Question: Q-7-1 for the maintainers: a ruling please")
    proc = world.run("--pr", "7", "--yes", "--head", world.head)
    assert proc.returncode == 1
    assert "/agk:workflow-apply" in proc.stdout and "for the maintainers" in proc.stdout
    assert world.remote("rev-parse", f"refs/heads/{BRANCH}") == world.head
    assert world.posts() == []


def test_d_it_never_pushes_to_the_default_branch(world):
    """REQ-039: answer 2 (never to the default branch)."""
    world.serve_pull(ref="main", sha=world.remote("rev-parse", "refs/heads/main"))
    main = world.remote("rev-parse", "refs/heads/main")
    proc = world.run("--pr", "7", "--yes", "--head", world.head)
    assert proc.returncode == 1
    assert "default branch" in proc.stdout
    assert world.remote("rev-parse", "refs/heads/main") == main
    assert world.posts() == []


def test_d_it_never_force_pushes_a_branch_that_moved(world):
    """REQ-039: answer 2 (never a force-push: a branch that moved since the pull request was read is
    refused, and the push it makes is a fast-forward of the fetched head)."""
    world.serve_pull(sha="0" * 40)
    proc = world.run("--pr", "7", "--yes", "--head", world.head)
    assert proc.returncode == 1
    assert "moved" in proc.stdout
    assert world.remote("rev-parse", f"refs/heads/{BRANCH}") == world.head
    assert world.posts() == []
    source = (SCRIPTS / "workflow_apply.py").read_text(encoding="utf-8")
    pushes = [ln for ln in source.splitlines() if '"push"' in ln]
    assert len(pushes) == 1, pushes
    for flag in ("--force", "-f", "+refs/", '"+', "--mirror", "--delete"):
        assert flag not in pushes[0], flag


def test_d_a_closed_pull_request_or_a_fork_is_refused(world):
    """REQ-039: answer 2 (it prints, and never does, what it cannot do)."""
    world.serve_pull(state="closed")
    proc = world.run("--pr", "7", "--yes", "--head", world.head)
    assert proc.returncode == 1 and "not open" in proc.stdout
    world.stub.serve(
        f"repos/{REPO}/pulls/7",
        {
            "number": 7,
            "state": "open",
            "head": {"ref": BRANCH, "sha": world.head, "repo": {"full_name": "other/fork"}},
            "base": {"ref": "main", "repo": {"full_name": REPO, "default_branch": "main"}},
        },
    )
    proc = world.run("--pr", "7", "--yes", "--head", world.head)
    assert proc.returncode == 1 and "fork" in proc.stdout
    assert world.remote("rev-parse", f"refs/heads/{BRANCH}") == world.head
    assert world.posts() == []


def test_d_a_push_refused_for_the_workflow_permission_names_the_refresh(world):
    """REQ-039: answer 2 (a push refused for lack of the workflow permission names
    `gh auth refresh -s workflow`, and nothing is posted)."""
    hook = world.bare / "hooks" / "pre-receive"
    hook.write_text(
        "#!/bin/sh\necho 'refusing to allow an OAuth App to create or update workflow "
        "`.github/workflows/ci.yml` without `workflow` scope' >&2\nexit 1\n",
        encoding="utf-8",
    )
    hook.chmod(0o755)
    proc = world.run("--pr", "7", "--yes", "--head", world.head)
    assert proc.returncode == 1
    assert "gh auth refresh -s workflow" in proc.stdout
    assert world.remote("rev-parse", f"refs/heads/{BRANCH}") == world.head
    assert world.posts() == []


def test_d_no_proposal_on_the_branch_changes_nothing(tmp_path):
    """REQ-039: answer 2."""
    w = World(tmp_path)
    w.serve_comments(QUESTION)
    seed = tmp_path / "seed"
    git(seed, "rm", "-q", "-r", ".agk")
    git(seed, "commit", "-q", "-m", "drop")
    git(seed, "push", "-q", "origin", BRANCH)
    w.head = git(seed, "rev-parse", "HEAD")
    w.serve_pull()
    proc = w.run("--pr", "7", "--yes", "--head", w.head)
    assert proc.returncode == 1 and "no proposal" in proc.stdout
    assert w.posts() == []


def test_personal_mode_has_no_pull_requests(world):
    """REQ-039: brief context `personal` (the command prints that it needs one and exits)."""
    write(world.owner, "agk.toml", '[personal]\nforge = "files"\n')
    proc = world.run("--pr", "7", "--yes", "--head", world.head)
    assert proc.returncode == 1
    assert "pull request" in proc.stdout and "personal" in proc.stdout
    assert world.stub.calls() == []


# --- (e) governance: a leftover proposal blocks the merge ---------------------------------------


@pytest.fixture
def base(repo):
    repo.commit(
        {
            "config/protected-paths.txt": "# c\nconstitution/\nconfig/\n.claude/\n.github/\n",
            TARGET: OLD,
            "src/app.py": "x = 1\n",
        },
        "base",
    )
    repo.branch()
    return repo


def test_e_governance_fails_while_the_head_holds_a_proposal_and_passes_once_applied(base):
    """REQ-039: answer 3 (a leftover proposal never reaches the default branch)."""
    base.commit({PROPOSAL: NEW, "src/app.py": "x = 2\n"})
    proc = base.run("check_protected_changes.py", "--base", "main")
    assert proc.returncode == 1
    assert "FAIL protected-changes:" in proc.stdout
    assert ".agk/workflow-proposals/" in proc.stdout
    assert "apply it with /agk:workflow-apply <pr>" in proc.stdout
    adr = "# ADR-0003: x\n\n- Status: Proposed\n\nClasses: `.github/`\n"
    base.commit({PROPOSAL: None, TARGET: NEW, "docs/adr/0003-x.md": adr})
    proc = base.run("check_protected_changes.py", "--base", "main")
    assert proc.returncode == 0, proc.stdout


def test_e_a_proposal_fails_even_with_an_adr_and_names_no_value(base):
    """REQ-039: answer 3 (an ADR does not let a proposal through; the message names the path
    class)."""
    adr = "# ADR-0003: x\n\n- Status: Proposed\n\nClasses: `.github/`\n"
    base.commit({PROPOSAL: "secret-looking-value-123\n", "docs/adr/0003-x.md": adr})
    proc = base.run("check_protected_changes.py", "--base", "main")
    assert proc.returncode == 1
    assert "secret-looking-value-123" not in proc.stdout


def test_b_every_workflow_of_the_kit_passes_the_parse_check():
    """REQ-039: answer 2 (the structure check accepts the workflows a project really has)."""
    sys.path.insert(0, str(SCRIPTS))
    import workflow_apply  # noqa: PLC0415 - the script under test

    folder = SCRIPTS.parents[1] / ".github" / "workflows"
    files = sorted(folder.glob("*.yml"))
    assert files
    for path in files:
        assert workflow_apply.yaml_problem(path.read_text(encoding="utf-8")) is None, path.name


# --- review fix list on cc18354: what the owner approves, and links ------------------------------


def test_d_yes_needs_the_head_of_the_dry_run(world):
    """REQ-039: answer 2 (`--yes` applies only the head the dry run showed; fix list item 1)."""
    proc = world.run("--pr", "7", "--yes")
    assert proc.returncode == 2
    assert "--head" in proc.stdout + proc.stderr
    assert world.remote("rev-parse", f"refs/heads/{BRANCH}") == world.head
    assert world.posts() == []


def test_d_a_branch_that_moved_between_the_dry_run_and_yes_is_refused(world, tmp_path):
    """REQ-039: answer 2 (a push between the two runs is never applied unseen; fix list item 1)."""
    shown = world.run("--pr", "7")
    assert shown.returncode == 0 and f"--head {world.head}" in shown.stdout
    seed = tmp_path / "seed"
    write(seed, PROPOSAL, NEW.replace("echo two", "echo three"))
    git(seed, "commit", "-q", "-am", "checkpoint: a later proposal")
    git(seed, "push", "-q", "origin", BRANCH)
    later = git(seed, "rev-parse", "HEAD")
    world.serve_pull(sha=later)
    proc = world.run("--pr", "7", "--yes", "--head", world.head)
    assert proc.returncode == 1
    assert "dry run" in proc.stdout and "moved" in proc.stdout
    assert world.remote("rev-parse", f"refs/heads/{BRANCH}") == later
    assert world.posts() == []


def linked(tmp_path: Path, link: str, to: str, proposal: bool = True) -> World:
    """A world whose branch also commits LINK as a symbolic link to TO."""
    w = World(tmp_path)
    seed = tmp_path / "seed"
    path = seed / link
    if path.exists() or path.is_symlink():
        if path.is_dir() and not path.is_symlink():
            git(seed, "rm", "-q", "-r", link)
        else:
            path.unlink()
    path.parent.mkdir(parents=True, exist_ok=True)
    os.symlink(to, path)
    if not proposal:
        write(seed, PROPOSAL, NEW)
    git(seed, "add", "-A")
    git(seed, "commit", "-q", "-m", "checkpoint: a link")
    git(seed, "push", "-q", "origin", BRANCH)
    w.head = git(seed, "rev-parse", "HEAD")
    w.serve_pull()
    w.serve_comments(QUESTION)
    return w


@pytest.mark.parametrize("yes", [False, True])
def test_d_a_proposal_that_is_a_link_is_refused_naming_the_file(tmp_path, yes):
    """REQ-039: answer 2 (a proposal that is not a regular file is refused; fix list item 2)."""
    w = linked(tmp_path, PROPOSAL, "../../README.md")
    args = ["--yes", "--head", w.head] if yes else []
    proc = w.run("--pr", "7", *args)
    assert proc.returncode == 1
    assert f"refused: {PROPOSAL}" in proc.stdout and "not a regular file" in proc.stdout
    assert "proj" not in proc.stdout  # the linked file is never read
    assert w.remote("rev-parse", f"refs/heads/{BRANCH}") == w.head
    assert w.posts() == []


@pytest.mark.parametrize(
    ("link", "to"),
    [(TARGET, "OUTSIDE"), (".github/workflows", "../src"), (".github", "src")],
)
def test_d_a_target_path_through_a_link_is_refused_and_nothing_is_written(tmp_path, link, to):
    """REQ-039: answer 2 (no part of the target path may be a link; fix list item 2)."""
    outside = tmp_path / "owner-file.txt"
    outside.write_text("mine\n", encoding="utf-8")
    w = linked(tmp_path, link, str(outside) if to == "OUTSIDE" else to, proposal=False)
    proc = w.run("--pr", "7", "--yes", "--head", w.head)
    assert proc.returncode == 1
    assert "refused:" in proc.stdout and "symbolic link" in proc.stdout
    assert link in proc.stdout
    assert outside.read_text(encoding="utf-8") == "mine\n"
    assert w.remote("rev-parse", f"refs/heads/{BRANCH}") == w.head
    assert w.posts() == []
