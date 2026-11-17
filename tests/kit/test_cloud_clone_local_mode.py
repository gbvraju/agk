"""A cloud builder keeps its own clone in local mode (brief #1482, ADR-0629, Q-1471-1).

Before: with `execution = "local"`, `common.clone_shared_by` returned `setting: execution` in a
cloud session too, so `session.py claim` and `push-check` refused every cloud builder in its own
clone's main folder. After: in a cloud session (`CLAUDE_CODE_REMOTE` is `true` (verify)) local
mode alone does not make the clone shared, as the `[flow] launch_adapter` setting already does
not; an `agk-*` worktree still does, and a machine is refused as before. Saved trees only,
invented data only (example.com); no network.
"""

from __future__ import annotations

import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
from pathlib import Path

import pytest

KIT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KIT / "scripts" / "agk"))

import common  # noqa: E402

LOCAL = 'execution = "local"\n'


def git(root: Path, *args: str) -> None:
    subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
        ["git", *args], cwd=root, capture_output=True, text=True, check=True
    )


def make_clone(base: Path) -> Path:
    root = base / "main"
    root.mkdir()
    git(root, "init", "-q", "-b", "main")
    git(root, "config", "user.email", "builder@example.com")
    git(root, "config", "user.name", "Builder")
    git(root, "config", "commit.gpgsign", "false")
    (root / "agk.toml").write_text(LOCAL, encoding="utf-8")
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "first")
    return root


def test_local_mode_in_a_cloud_session_is_not_shared(tmp_path, monkeypatch):
    """REQ-039: brief #1482 answer 4, local mode in a cloud session: the clone is its own."""
    monkeypatch.setenv("CLAUDE_CODE_REMOTE", "true")
    root = make_clone(tmp_path)
    assert common.clone_shared_by(root) is None
    assert common.shared_main(root) is False
    assert common.main_folder_refusal(root) is None


def test_local_mode_on_a_machine_is_shared(tmp_path, monkeypatch):
    """REQ-039: brief #1482 answer 4, local mode on a machine: refused as before."""
    monkeypatch.delenv("CLAUDE_CODE_REMOTE", raising=False)
    root = make_clone(tmp_path)
    assert common.clone_shared_by(root) == "setting: execution"
    line, refused = common.main_folder_refusal(root)
    assert refused and "(setting: execution)" in line


def test_cloud_session_with_an_agk_worktree_is_shared(tmp_path, monkeypatch):
    """REQ-039: brief #1482 answer 4, an `agk-*` worktree still makes a cloud clone shared."""
    monkeypatch.setenv("CLAUDE_CODE_REMOTE", "true")
    root = make_clone(tmp_path)
    git(root, "worktree", "add", "-q", "--detach", str(tmp_path / "agk-cb0001"), "HEAD")
    assert common.clone_shared_by(root) == "found: another agk-* worktree"


@pytest.mark.parametrize("value", ["", "false", "TRUE", "1", "yes"])
def test_remote_variable_other_than_true_is_shared(tmp_path, monkeypatch, value):
    """REQ-039: brief #1482 answer 4, `CLAUDE_CODE_REMOTE` set to anything but `true`: shared."""
    monkeypatch.setenv("CLAUDE_CODE_REMOTE", value)
    root = make_clone(tmp_path)
    assert common.clone_shared_by(root) == "setting: execution"
