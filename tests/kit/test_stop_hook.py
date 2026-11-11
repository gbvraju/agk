"""Tests of .claude/hooks/stop_check.py and of the committed settings."""

from __future__ import annotations

import json
import os
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HOOK = ROOT / ".claude" / "hooks" / "stop_check.py"


def run_hook(project: Path, payload: dict):
    env = {**os.environ, "CLAUDE_PROJECT_DIR": str(project)}
    return subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, str(HOOK)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        env=env,
    )


def project(tmp_path: Path, recipe: str) -> Path:
    (tmp_path / "agk.mk").write_text(f"agk-governance:\n\t{recipe}\n")
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


def test_ac3_missing_agk_mk_blocks_stop(tmp_path):
    """REQ-002 AC3"""
    assert json.loads(run_hook(tmp_path, {}).stdout)["decision"] == "block"


def test_ac3_second_stop_attempt_is_allowed_to_avoid_loop(tmp_path):
    """REQ-002 AC3 (verify: stop_hook_active)"""
    proc = run_hook(project(tmp_path, "@exit 1"), {"stop_hook_active": True})
    assert proc.returncode == 0 and proc.stdout == ""


def test_garbage_stdin_does_not_crash(tmp_path):
    """REQ-002 AC3"""
    env = {**os.environ, "CLAUDE_PROJECT_DIR": str(project(tmp_path, "@exit 1"))}
    proc = subprocess.run(  # nosec B603 - fixed argument list, no shell
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
    """REQ-001 REQ-002 AC2: Edit rules (the form Claude Code consults) prompt, root-anchored."""
    perms = settings()["permissions"]
    ask = perms["ask"]
    assert not [r for r in perms["deny"] if r.startswith(("Edit(", "Write("))]
    assert not [r for r in ask if r.startswith("Write(")]
    for entry in (ROOT / "config" / "protected-paths.txt").read_text().splitlines():
        if not entry.strip() or entry.startswith("#"):
            continue
        glob = f"/{entry}**" if entry.endswith("/") else f"/{entry}"
        assert f"Edit({glob})" in ask


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
    for rule in (
        "Bash(gh pr merge:*)",
        "mcp__github__merge_pull_request",
        "mcp__github__enable_pr_auto_merge",
        "Bash(git reset --hard:*)",
    ):
        assert rule in perms["deny"]


def _matches(rule: str, command: str) -> bool:
    import fnmatch

    inner = rule[len("Bash(") : -1]
    if inner.endswith(":*"):
        inner = inner[:-2] + " *"
    if inner.endswith(" *") and fnmatch.fnmatchcase(command, inner[:-2]):
        return True
    return fnmatch.fnmatchcase(command, inner)


def test_ac3_hook_calls_the_agk_mk_form_not_the_makefile_alias(tmp_path):
    """REQ-002 AC3 (SPEC-0002 rule 5): a project whose only target is the Makefile alias is red."""
    (tmp_path / "Makefile").write_text("governance:\n\t@true\n")
    out = json.loads(run_hook(tmp_path, {}).stdout)
    assert out["decision"] == "block"


def test_ac2_settings_allow_the_agk_mk_targets():
    """REQ-002 AC2 (SPEC-0002 rule 5): the settings call the same form as the workflow."""
    allow = settings()["permissions"]["allow"]
    for target in ("agk-governance", "agk-lint", "agk-test"):
        assert f"Bash(make -f agk.mk {target})" in allow


# --- brief #1029 (ADR-0438): the hook reads the open pull request's body -----------------------

BODY = "Brief: #1\nCovered-by: ADR-0001\nSecret-scan: deferred to CI\n"
# The recipe proves AGK_PR_BODY names a file holding the body, and keeps its name for the test.
SEES_BODY = (
    '@test -n "$$AGK_PR_BODY" && grep -q Covered-by "$$AGK_PR_BODY"'
    ' && echo "$$AGK_PR_BODY" > seen.txt'
)
SEES_NONE = '@test -z "$$AGK_PR_BODY" && echo none > seen.txt'


def git(cwd: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)  # nosec B603 B607 - fixed list


def branch_project(tmp_path: Path, recipe: str, detached: bool = False) -> Path:
    proj = tmp_path / "proj"
    proj.mkdir()
    (proj / "agk.mk").write_text(f"agk-governance:\n\t{recipe}\n")
    (proj / ".gitignore").write_text("seen.txt\n")
    git(proj, "init", "-q", "-b", "claude/brief-1")
    git(proj, "remote", "add", "origin", "https://github.com/example/demo.git")
    git(proj, "add", ".")
    git(proj, "-c", "user.name=t", "-c", "user.email=t@example.com", "commit", "-q", "-m", "x")
    if detached:
        git(proj, "checkout", "-q", "--detach")
    return proj


def stub_gh(tmp_path: Path, stdout: str, code: int = 0) -> Path:
    """A `gh` on PATH that logs its arguments and prints `stdout`; no network."""
    bindir = tmp_path / "bin"
    bindir.mkdir()
    (tmp_path / "gh-out.json").write_text(stdout)
    gh = bindir / "gh"
    gh.write_text(
        "#!/bin/sh\n"
        f'printf "%s\\n" "$*" >> "{tmp_path}/gh-args.txt"\n'
        f'cat "{tmp_path}/gh-out.json"\n'
        f"exit {code}\n"
    )
    gh.chmod(0o755)
    return bindir


def run_on_branch(proj: Path, bindir: Path):
    env = {k: v for k, v in os.environ.items() if k != "AGK_PR_BODY"}
    env.update(CLAUDE_PROJECT_DIR=str(proj), PATH=f"{bindir}{os.pathsep}{env.get('PATH', '')}")
    return subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, str(HOOK)], input="{}", capture_output=True, text=True, env=env
    )


def test_a_open_pull_request_body_reaches_governance(tmp_path):
    """REQ-037 (brief #1029 answer 4, test a): the body with `Covered-by:` is in AGK_PR_BODY."""
    proj = branch_project(tmp_path, SEES_BODY)
    bindir = stub_gh(tmp_path, json.dumps([{"number": 7, "body": BODY}]))
    proc = run_on_branch(proj, bindir)
    assert proc.returncode == 0 and proc.stdout == "", proc.stdout
    args = (tmp_path / "gh-args.txt").read_text()
    assert "api" in args and "pulls?head=example:claude/brief-1&state=open" in args
    assert (proj / "seen.txt").is_file()


def test_b_no_pull_request_runs_governance_as_today(tmp_path):
    """REQ-037 (brief #1029 answer 4, test b): no pull request means no AGK_PR_BODY."""
    proj = branch_project(tmp_path, SEES_NONE)
    proc = run_on_branch(proj, stub_gh(tmp_path, "[]"))
    assert proc.returncode == 0 and proc.stdout == "", proc.stdout
    assert (proj / "seen.txt").read_text().strip() == "none"


def test_b_failing_gh_runs_governance_as_today(tmp_path):
    """REQ-037 (brief #1029 answer 4, test b): a failing or garbled `gh` changes nothing."""
    for name, out, code in (("fail", "error", 1), ("garbled", "not json", 0)):
        (tmp_path / name).mkdir()
        proj = branch_project(tmp_path / name, SEES_NONE)
        proc = run_on_branch(proj, stub_gh(tmp_path / name, out, code))
        assert proc.returncode == 0 and proc.stdout == "", (name, proc.stdout)
        assert (proj / "seen.txt").read_text().strip() == "none"


def test_b_detached_head_asks_no_pull_request(tmp_path):
    """REQ-037 (brief #1029 answer 4, test b): a detached head runs governance as today."""
    proj = branch_project(tmp_path, SEES_NONE, detached=True)
    proc = run_on_branch(proj, stub_gh(tmp_path, json.dumps([{"number": 7, "body": BODY}])))
    assert proc.returncode == 0 and proc.stdout == "", proc.stdout
    assert not (tmp_path / "gh-args.txt").exists()


def test_b_red_governance_still_blocks_with_the_body(tmp_path):
    """REQ-037 (brief #1029): the body changes what governance reads, never that red blocks."""
    proj = branch_project(tmp_path, "@echo FAIL demo; exit 1")
    proc = run_on_branch(proj, stub_gh(tmp_path, json.dumps([{"number": 7, "body": BODY}])))
    assert json.loads(proc.stdout)["decision"] == "block"


def test_c_temporary_body_file_is_removed(tmp_path):
    """REQ-037 (brief #1029 answer 4, test c): the body file is gone after the run."""
    for recipe in (SEES_BODY, SEES_BODY + "; exit 1"):
        sub = tmp_path / str(len(recipe))
        sub.mkdir()
        proj = branch_project(sub, recipe)
        run_on_branch(proj, stub_gh(sub, json.dumps([{"number": 7, "body": BODY}])))
        used = Path((proj / "seen.txt").read_text().strip())
        assert used.name and not used.exists()


def test_ac2_push_allows_head_and_claude_branches_and_no_deny_matches_them():
    """REQ-002 AC2, REQ-037 (brief #1029 answer 2): deny beats allow."""
    perms = settings()["permissions"]
    pushes = [r for r in perms["allow"] if r.startswith("Bash(git push")]
    assert pushes == ["Bash(git push -u origin HEAD)", "Bash(git push origin claude/*)"]
    for command in ("git push -u origin HEAD", "git push origin claude/brief-1"):
        for rule in perms["deny"]:
            if rule.startswith("Bash("):
                assert not _matches(rule, command), (rule, command)
