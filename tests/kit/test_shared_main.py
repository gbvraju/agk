"""Sessions never build in the shared main folder (brief #1301, ADR-0551).

In a customer project in local mode one clone was shared by a conductor, two builders in their own
worktrees and a helper session opened by hand in the main folder. The helper built a pull request
there and left the folder on its branch with an untracked file; for about two hours the conductor
and the planner read that branch as their checkout and printed false `MALFORMED` lines.

After the change: `session.py claim` and `next --take` refuse from the main worktree of a clone
that several sessions share (`execution = "local"`, a `[flow] launch_adapter`, or another `agk-*`
worktree); `prepush.py` refuses a push from it except from the default branch; personal mode
warns only; the stop hook, `conductor.py sweep` and `doctor.py` print the main folder's state when
it is off the default branch or holds untracked files; and the plan's `Adds:` check reads the
files of `origin/<default branch>`, never the main folder's working files. Temporary clones,
invented data only (example.com); no network.
"""

from __future__ import annotations

import json
import os
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
from pathlib import Path

import pytest

KIT = Path(__file__).resolve().parents[2]
SCRIPTS = KIT / "scripts" / "agk"
sys.path.insert(0, str(SCRIPTS))

import common  # noqa: E402
import conductor  # noqa: E402
import doctor  # noqa: E402
import prepush  # noqa: E402
import session  # noqa: E402
import session_plan  # noqa: E402

REFUSED = "refused: this is the main folder that other sessions read"
STOP_HOOK = KIT / ".claude" / "hooks" / "stop_check.py"


def git(root: Path, *args: str) -> str:
    proc = subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
        ["git", *args], cwd=root, capture_output=True, text=True, check=True
    )
    return proc.stdout


def make_clone(base: Path, toml: str) -> Path:
    """A clone `main` on branch main with one commit and an `origin/main` ref."""
    root = base / "main"
    root.mkdir()
    git(root, "init", "-q", "-b", "main")
    git(root, "config", "user.email", "builder@example.com")
    git(root, "config", "user.name", "Builder")
    git(root, "config", "commit.gpgsign", "false")
    (root / "agk.toml").write_text(toml, encoding="utf-8")
    (root / "README.md").write_text("example\n", encoding="utf-8")
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "first")
    git(root, "update-ref", "refs/remotes/origin/main", "HEAD")
    return root


def add_worktree(root: Path, name: str) -> Path:
    tree = root.parent / name
    git(root, "worktree", "add", "-q", "--detach", str(tree), "origin/main")
    return tree


@pytest.fixture(autouse=True)
def not_remote(monkeypatch):
    """The cloud runtime's variable is the machine's, never the test's."""
    monkeypatch.delenv("CLAUDE_CODE_REMOTE", raising=False)


def no_network(monkeypatch):
    """`claim` reads GitHub after the guard: a read that fails shows the guard let it through."""
    monkeypatch.setattr(session, "repo_name", lambda root: "example/agk")
    monkeypatch.setattr(session, "pages", lambda route: None)


# --- (a) local mode: refused from the main worktree, allowed from an agk-* worktree -------------


def test_local_claim_refused_in_main(tmp_path, monkeypatch, capsys):
    """REQ-039: brief #1301 answer 1 and test (a): claim from the main worktree is refused."""
    root = make_clone(tmp_path, 'execution = "local"\n')
    no_network(monkeypatch)
    assert common.shared_main(root) is True
    assert session.claim(root, "s1", 5, None) == 1
    out = capsys.readouterr().out
    assert REFUSED in out
    assert "git worktree add ../agk-<session> origin/<default branch>" in out
    assert "(setting: execution)" in out


def test_local_claim_allowed_in_own_worktree(tmp_path, monkeypatch):
    """REQ-039: brief #1301 test (a): claim from an agk-* worktree passes the guard."""
    root = make_clone(tmp_path, 'execution = "local"\n')
    tree = add_worktree(root, "agk-s1")
    no_network(monkeypatch)
    assert common.shared_main(tree) is False
    with pytest.raises(common.CheckError, match="rule 5"):
        session.claim(tree, "s1", 5, None)


def test_next_take_refused_in_main(tmp_path, monkeypatch, capsys):
    """REQ-039: brief #1301 answer 1: `next --take` is refused, `next` alone only shows."""
    root = make_clone(tmp_path, '[flow]\nlaunch_adapter = "bash scripts/start-session-local.sh"\n')
    no_network(monkeypatch)
    assert session.next_brief(root, "s1", True) == 1
    out = capsys.readouterr().out
    assert REFUSED in out and "(setting: [flow] launch_adapter)" in out


def test_another_agk_worktree_makes_the_clone_shared(tmp_path, monkeypatch, capsys):
    """REQ-039: brief #1301 answer 1: another `agk-*` worktree makes the clone shared."""
    root = make_clone(tmp_path, "")
    add_worktree(root, "agk-s2")
    no_network(monkeypatch)
    assert session.claim(root, "s1", 5, None) == 1
    assert REFUSED in capsys.readouterr().out


# --- (b) CI mode: nothing refused ---------------------------------------------------------------


def test_ci_mode_refuses_nothing(tmp_path, monkeypatch):
    """REQ-039: brief #1301 test (b): no local execution, no adapter, no agk-* worktree."""
    root = make_clone(tmp_path, "")
    add_worktree(root, "elsewhere")
    no_network(monkeypatch)
    assert common.shared_main(root) is False
    with pytest.raises(common.CheckError, match="rule 5"):
        session.claim(root, "s1", 5, None)
    assert common.main_folder_line(root) is None


def test_cloud_clone_with_adapter_refuses_nothing(tmp_path, monkeypatch):
    """REQ-039: brief #1301 mode check CI (Q-1301-1): a cloud session's clone is its own, so the
    adapter setting alone does not make it shared there (CLAUDE_CODE_REMOTE, verify)."""
    root = make_clone(tmp_path, '[flow]\nlaunch_adapter = "bash scripts/start-session-local.sh"\n')
    monkeypatch.setenv("CLAUDE_CODE_REMOTE", "true")
    no_network(monkeypatch)
    assert common.shared_main(root) is False
    with pytest.raises(common.CheckError, match="rule 5"):
        session.claim(root, "s1", 5, None)


# --- (c) personal mode warns only ---------------------------------------------------------------


def test_personal_mode_warns_only(tmp_path, monkeypatch, capsys):
    """REQ-039: brief #1301 test (c): personal mode prints a warning and refuses nothing."""
    root = make_clone(tmp_path, 'execution = "local"\n[personal]\nforge = "files"\n')
    no_network(monkeypatch)
    with pytest.raises(common.CheckError, match="rule 5"):
        session.claim(root, "s1", 5, None)
    out = capsys.readouterr().out
    assert "warning: this is the main folder that other sessions read" in out
    assert REFUSED not in out


# --- prepush: refused from the shared main folder except on the default branch -----------------


def test_prepush_refused_off_default_branch(tmp_path, monkeypatch, capsys):
    """REQ-039: brief #1301 answer 1: prepush refuses from the main folder off its branch."""
    root = make_clone(tmp_path, 'execution = "local"\n')
    git(root, "checkout", "-q", "-b", "claude/brief-5")
    monkeypatch.chdir(root)
    assert prepush.main(["--quick"]) == 2
    assert REFUSED in capsys.readouterr().out


def test_prepush_guard_allows_default_branch_and_worktrees(tmp_path):
    """REQ-039: brief #1301 answer 1: the default branch, an own worktree and CI mode pass."""
    root = make_clone(tmp_path, 'execution = "local"\n')
    assert common.main_folder_refusal(root, push=True) is None
    tree = add_worktree(root, "agk-s1")
    git(tree, "checkout", "-q", "-b", "claude/brief-5")
    assert common.main_folder_refusal(tree, push=True) is None
    (tmp_path / "ci").mkdir()
    plain = make_clone(tmp_path / "ci", "")
    git(plain, "checkout", "-q", "-b", "claude/brief-5")
    assert common.main_folder_refusal(plain, push=True) is None


# --- (d) the stop hook prints the main folder's state -------------------------------------------


def run_hook(root: Path) -> subprocess.CompletedProcess:
    env = {k: v for k, v in os.environ.items() if k not in ("CLAUDE_CODE_REMOTE", "AGK_PR_BODY")}
    env["CLAUDE_PROJECT_DIR"] = str(root)
    return subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, str(STOP_HOOK)],
        input=json.dumps({"cwd": str(root)}),
        capture_output=True,
        text=True,
        env=env,
        timeout=60,
        check=False,
    )


TOML_OFF = 'execution = "local"\n[flow]\nstop_check = "off"\n'


def test_stop_hook_prints_other_branch(tmp_path):
    """REQ-039: brief #1301 test (d): the main folder on another branch is printed."""
    root = make_clone(tmp_path, TOML_OFF)
    git(root, "checkout", "-q", "-b", "claude/brief-5")
    proc = run_hook(root)
    assert proc.returncode == 0
    assert (
        "main folder: on claude/brief-5, 0 untracked; switch back with git checkout main"
        in proc.stderr
    )
    assert "decision" not in proc.stdout


def test_stop_hook_prints_untracked_file(tmp_path):
    """REQ-039: brief #1301 test (d): an untracked file in the main folder is printed."""
    root = make_clone(tmp_path, TOML_OFF)
    (root / "Makefile").write_text("all:\n", encoding="utf-8")
    proc = run_hook(root)
    assert proc.returncode == 0
    assert "main folder: on main, 1 untracked; switch back with git checkout main" in proc.stderr


def test_stop_hook_quiet_on_clean_main(tmp_path):
    """REQ-039: brief #1301 test (d): a clean main folder on the default branch prints nothing."""
    root = make_clone(tmp_path, TOML_OFF)
    proc = run_hook(root)
    assert "main folder:" not in proc.stderr


def test_ignored_files_are_not_counted(tmp_path):
    """REQ-039: brief #1301 answer 2: ignored paths are not untracked files."""
    root = make_clone(tmp_path, 'execution = "local"\n')
    (root / ".git" / "info" / "exclude").write_text(".agk-session-exit\n", encoding="utf-8")
    (root / ".agk-session-exit").write_text("0\n", encoding="utf-8")
    assert common.main_folder_line(root) is None


# --- (e) sweep and doctor print MAIN-FOLDER: ---------------------------------------------------


def test_sweep_prints_main_folder(tmp_path, monkeypatch, capsys):
    """REQ-039: brief #1301 test (e): `conductor.py sweep` prints `MAIN-FOLDER:` once."""
    root = make_clone(tmp_path, 'execution = "local"\n')
    tree = add_worktree(root, "agk-conductor")
    git(root, "checkout", "-q", "-b", "claude/brief-5")
    (root / "Makefile").write_text("all:\n", encoding="utf-8")
    monkeypatch.setattr(session, "repo_name", lambda r: "example/agk")
    monkeypatch.setattr(session, "gh", lambda route: {"default_branch": "main"})
    monkeypatch.setattr(conductor, "verdict_authors", lambda r: [])
    monkeypatch.setattr(conductor, "spec_approvers", lambda r: [])
    monkeypatch.setattr(conductor, "read", lambda route, what: [])
    monkeypatch.setattr(conductor, "proof_lines", lambda *a: [])
    monkeypatch.setattr(conductor.caps, "over_lines", lambda *a: [])
    monkeypatch.setattr(conductor, "branch_line", lambda *a: "branch: green")
    for name in ("slot_lines", "stall_report", "unacted_lines", "owner_lines", "start_lines"):
        monkeypatch.setattr(conductor, name, lambda *a: [])
    assert conductor.sweep(tree) == 0
    out = capsys.readouterr().out.splitlines()
    assert out.count("MAIN-FOLDER: on claude/brief-5, 1 untracked") == 1


def test_doctor_prints_main_folder(tmp_path):
    """REQ-039: brief #1301 test (e): `doctor.py` prints the same line, information only."""
    root = make_clone(tmp_path, 'execution = "local"\n')
    git(root, "checkout", "-q", "--detach")
    assert doctor.main_folder_lines(root) == ["MAIN-FOLDER: on a detached head, 0 untracked"]
    git(root, "checkout", "-q", "main")
    assert doctor.main_folder_lines(root) == []
    assert doctor.main_folder_lines(tmp_path / "not-a-repo") == []


# --- (f) the plan's Adds: check reads origin/<default branch> -----------------------------------


def test_adds_reads_default_branch_not_main_folder(tmp_path):
    """REQ-039: brief #1301 test (f): a file only in the main folder's branch or working files is
    not an existing file for `Adds:`; one on the default branch still is."""
    root = make_clone(tmp_path, 'execution = "local"\n')
    git(root, "checkout", "-q", "-b", "claude/brief-5")
    (root / "Makefile").write_text("all:\n", encoding="utf-8")
    git(root, "add", "Makefile")
    git(root, "commit", "-q", "-m", "a builder's change")
    (root / "notes.txt").write_text("untracked\n", encoding="utf-8")
    rules = session_plan.touch_rules(root, "origin/main")
    assert session_plan.touch_problems("Adds: Makefile, notes.txt\n", rules) == []
    assert session_plan.touch_problems("Adds: README.md\n", rules) == [
        "rule 4: Adds entry README.md names an existing file"
    ]
    # The checkout's own list, as before, when no ref is given.
    checkout = session_plan.touch_rules(root)
    assert session_plan.touch_problems("Adds: Makefile\n", checkout)


def test_adds_falls_back_without_the_ref(tmp_path):
    """REQ-039: brief #1301 test (f): a ref git cannot read falls back to the checkout's list."""
    root = make_clone(tmp_path, "")
    rules = session_plan.touch_rules(root, "origin/absent")
    assert "README.md" in rules["files"]


def test_brief_shape_reads_the_default_branch(tmp_path, monkeypatch):
    """REQ-039: brief #1301 answer 3: the planner's brief shape names `origin/<default branch>`."""
    root = make_clone(tmp_path, 'default_branch = "trunk"\n')
    seen = []

    def rules(r, ref=None):
        seen.append(ref)
        return {"root": r, "limit": 4, "files": [], "holding": [], "unshared": []}

    monkeypatch.setattr(session_plan, "touch_rules", rules)
    session.brief_shape(root, "example/agk")
    assert seen == ["origin/trunk"]
