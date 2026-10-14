"""Tests of .claude/hooks/stop_check.py and of the committed settings."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HOOK = ROOT / ".claude" / "hooks" / "stop_check.py"


def run_hook(project: Path, payload: dict):
    env = {**os.environ, "CLAUDE_PROJECT_DIR": str(project)}
    return subprocess.run(
        [sys.executable, str(HOOK)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        env=env,
    )


def project(tmp_path: Path, recipe: str) -> Path:
    (tmp_path / "Makefile").write_text(f"governance:\n\t{recipe}\n")
    return tmp_path


def test_ac3_green_governance_allows_stop(tmp_path):
    """REQ-002 AC3"""
    proc = run_hook(project(tmp_path, "@true"), {})
    assert proc.returncode == 0 and proc.stdout == ""


def test_ac3_red_governance_blocks_stop(tmp_path):
    """REQ-002 AC3"""
    proc = run_hook(project(tmp_path, "@echo FAIL demo; exit 1"), {})
    out = json.loads(proc.stdout)
    assert proc.returncode == 0
    assert out["decision"] == "block" and "FAIL demo" in out["reason"]


def test_ac3_missing_makefile_blocks_stop(tmp_path):
    """REQ-002 AC3"""
    assert json.loads(run_hook(tmp_path, {}).stdout)["decision"] == "block"


def test_ac3_second_stop_attempt_is_allowed_to_avoid_loop(tmp_path):
    """REQ-002 AC3 (verify: stop_hook_active)"""
    proc = run_hook(project(tmp_path, "@exit 1"), {"stop_hook_active": True})
    assert proc.returncode == 0 and proc.stdout == ""


def test_garbage_stdin_does_not_crash(tmp_path):
    """REQ-002 AC3"""
    env = {**os.environ, "CLAUDE_PROJECT_DIR": str(project(tmp_path, "@exit 1"))}
    proc = subprocess.run(
        [sys.executable, str(HOOK)], input="not json", capture_output=True, text=True, env=env
    )
    assert json.loads(proc.stdout)["decision"] == "block"


def settings() -> dict:
    return json.loads((ROOT / ".claude" / "settings.json").read_text())


def test_ac2_settings_deny_force_push_and_hard_reset():
    """REQ-002 AC2"""
    deny = settings()["permissions"]["deny"]
    assert "Bash(git push --force:*)" in deny
    assert "Bash(git push -f:*)" in deny
    assert "Bash(git reset --hard:*)" in deny


def test_ac2_settings_deny_agent_merge():
    """REQ-002"""
    deny = settings()["permissions"]["deny"]
    assert "Bash(gh pr merge:*)" in deny
    assert "mcp__github__merge_pull_request" in deny
    assert "mcp__github__enable_pr_auto_merge" in deny


def test_ac2_settings_ask_before_editing_every_protected_path():
    """REQ-001 REQ-002 AC2: protected-path edits prompt (key `ask`, verify)."""
    perms = settings()["permissions"]
    deny = perms["ask"]
    assert not [r for r in perms["deny"] if r.startswith(("Edit(", "Write("))]
    for entry in (ROOT / "config" / "protected-paths.txt").read_text().splitlines():
        if not entry.strip() or entry.startswith("#"):
            continue
        glob = f"./{entry}**" if entry.endswith("/") else f"./{entry}"
        for tool in ("Edit", "Write"):
            assert f"{tool}({glob})" in deny


def test_ac3_stop_hook_is_registered():
    """REQ-002 AC3"""
    hooks = settings()["hooks"]["Stop"][0]["hooks"]
    assert any("stop_check.py" in h["command"] for h in hooks)


def test_ac2_deny_covers_push_variants_in_any_flag_position():
    """REQ-002 AC2: -f, --force-with-lease, +refspec, --delete, flag after remote."""
    deny = settings()["permissions"]["deny"]
    for rule in (
        "Bash(git push --force*)",
        "Bash(git push * --force*)",
        "Bash(git push -f*)",
        "Bash(git push * -f*)",
        "Bash(git push --delete*)",
        "Bash(git push * --delete*)",
        "Bash(git push -d*)",
        "Bash(git push * -d*)",
        "Bash(git push +*)",
        "Bash(git push * +*)",
        "Bash(git reset * --hard*)",
    ):
        assert rule in deny


def test_ac3_stop_hook_active_exits_zero_silently_even_when_red(tmp_path):
    """REQ-002 AC3: with stop_hook_active true the hook exits 0 and prints nothing."""
    for proj in (project(tmp_path, "@exit 1"), tmp_path / "empty"):
        proj.mkdir(exist_ok=True)
        proc = run_hook(proj, {"stop_hook_active": True})
        assert proc.returncode == 0
        assert proc.stdout == "" and proc.stderr == ""


def test_ac2_deny_keeps_merge_and_history_rewrite_rules():
    """REQ-002 AC2"""
    perms = settings()["permissions"]
    assert "Bash(git push * :*)" not in perms["deny"]
    for rule in ("Bash(gh pr merge:*)", "mcp__github__merge_pull_request",
                 "mcp__github__enable_pr_auto_merge", "Bash(git reset --hard:*)"):
        assert rule in perms["deny"]
