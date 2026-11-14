"""Tests of the stop hook's changed-only mode (brief #1254, ADR-0531).

`.claude/hooks/stop_check.py` reads what the session changed (local git only) and runs only the
governance checks whose inputs those paths touch (`scripts/agk/governance_map.py`); no change runs
nothing; a path the map does not know runs the full set; `[flow] stop_check` chooses the mode.
Every repository here is a temporary one with invented data; no test reaches a network (`gh` is a
stub on PATH that fails).
"""

from __future__ import annotations

import json
import os
import re
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
HOOK = ROOT / ".claude" / "hooks" / "stop_check.py"
sys.path.insert(0, str(ROOT / "scripts" / "agk"))

import governance_map  # noqa: E402

import config  # noqa: E402


def git(cwd: Path, *args: str) -> None:
    subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
        ["git", "-c", "user.name=t", "-c", "user.email=t@example.com", *args],
        cwd=cwd,
        check=True,
        capture_output=True,
    )


def make_project(tmp_path: Path, toml: str = "", red: str = "") -> Path:
    """A repository on `main` with `origin/main` at its first commit. Each governance script is a
    stub that logs its name to `ran.log` (and exits 1 when named by `red`); the `agk.mk` recipe
    logs `FULL`, so a test sees which form ran."""
    proj = tmp_path / "proj"
    (proj / "scripts" / "agk").mkdir(parents=True)
    (proj / "docs" / "plan").mkdir(parents=True)
    (proj / "docs" / "plan" / "plan.md").write_text("# Plan\n\nexample.com\n")
    (proj / "agk.toml").write_text(f'default_branch = "main"\n{toml}')
    (proj / ".gitignore").write_text("ran.log\n")
    scripts = {argv[0] for _, argv in governance_map.CHECKS}
    for script in scripts:
        name = Path(script).name
        code = 1 if name == red else 0
        (proj / script).write_text(
            "import sys\n"
            f"open('ran.log', 'a').write({name!r} + '\\n')\n"
            f"print('FAIL demo' if {code} else 'ok')\n"
            f"sys.exit({code})\n"
        )
    (proj / "agk.mk").write_text("agk-governance:\n\t@echo FULL >> ran.log\n")
    git(proj, "init", "-q", "-b", "main")
    git(proj, "add", ".")
    git(proj, "commit", "-q", "-m", "base")
    git(proj, "remote", "add", "origin", "https://example.com/demo/demo.git")
    git(proj, "update-ref", "refs/remotes/origin/main", "HEAD")
    return proj


def no_gh(tmp_path: Path) -> Path:
    bindir = tmp_path / "bin"
    bindir.mkdir(exist_ok=True)
    gh = bindir / "gh"
    gh.write_text("#!/bin/sh\nexit 1\n")
    gh.chmod(0o755)
    return bindir


def run_hook(proj: Path, tmp_path: Path):
    env = {k: v for k, v in os.environ.items() if k != "AGK_PR_BODY"}
    env.update(
        CLAUDE_PROJECT_DIR=str(proj),
        PATH=f"{no_gh(tmp_path)}{os.pathsep}{env.get('PATH', '')}",
    )
    return subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, str(HOOK)], input="{}", capture_output=True, text=True, env=env
    )


def ran(proj: Path) -> list[str]:
    log = proj / "ran.log"
    return log.read_text().split() if log.is_file() else []


def test_1_no_change_runs_nothing_and_allows_the_stop(tmp_path):
    """REQ-039 (brief #1254 answers 1 and 5): a clean tree with no branch commit runs no check."""
    proj = make_project(tmp_path)
    proc = run_hook(proj, tmp_path)
    assert proc.returncode == 0 and proc.stdout == "", proc.stdout
    assert ran(proj) == []
    assert "stop check: no changes" in proc.stderr


def test_2_plan_change_runs_only_the_plan_check_and_the_always_set(tmp_path):
    """REQ-039 (brief #1254 answers 2 and 5): `docs/plan/x.md` selects the plan check."""
    proj = make_project(tmp_path)
    (proj / "docs" / "plan" / "x.md").write_text("# X\n")
    proc = run_hook(proj, tmp_path)
    assert proc.returncode == 0 and proc.stdout == "", proc.stdout
    names = ran(proj)
    assert "FULL" not in names and "check_plan.py" in names
    expected = governance_map.select(["docs/plan/x.md"])
    assert expected is not None and len(names) == len(expected) < len(governance_map.CHECKS)
    assert "check_requirements.py" not in names and "check_design.py" not in names
    assert re.search(rf"stop check: {len(expected)} checks for 1 changed files, \d", proc.stderr)


def test_2_committed_branch_change_counts_as_changed(tmp_path):
    """REQ-039 (brief #1254 answer 1): a commit on the branch that is not on the default branch."""
    proj = make_project(tmp_path)
    git(proj, "checkout", "-q", "-b", "claude/brief-1")
    (proj / "docs" / "plan" / "y.md").write_text("# Y\n")
    git(proj, "add", ".")
    git(proj, "commit", "-q", "-m", "y")
    proc = run_hook(proj, tmp_path)
    assert "check_plan.py" in ran(proj) and "FULL" not in ran(proj), proc.stderr


def test_3_unknown_path_runs_the_full_set(tmp_path):
    """REQ-039 (brief #1254 answers 2 and 5): a path the map does not know runs agk.mk as today."""
    proj = make_project(tmp_path)
    (proj / "src").mkdir()
    (proj / "src" / "app.py").write_text("x = 1\n")
    proc = run_hook(proj, tmp_path)
    assert proc.returncode == 0 and proc.stdout == "", proc.stdout
    assert ran(proj) == ["FULL"]
    assert f"stop check: {len(governance_map.CHECKS)} checks for 1 changed files" in proc.stderr


def test_4_a_red_selected_check_blocks_the_stop(tmp_path):
    """REQ-039 (brief #1254 answers 2 and 5): a check that runs still blocks while red."""
    proj = make_project(tmp_path, red="check_plan.py")
    (proj / "docs" / "plan" / "x.md").write_text("# X\n")
    out = json.loads(run_hook(proj, tmp_path).stdout)
    assert out["decision"] == "block"
    assert "check_plan.py" in out["reason"] and "FAIL demo" in out["reason"]


def test_4_a_red_check_that_is_not_selected_does_not_run(tmp_path):
    """REQ-039 (brief #1254 answer 2): the design check is not read for a plan change."""
    proj = make_project(tmp_path, red="check_design.py")
    (proj / "docs" / "plan" / "x.md").write_text("# X\n")
    proc = run_hook(proj, tmp_path)
    assert proc.returncode == 0 and proc.stdout == "", proc.stdout


def test_5_full_mode_behaves_as_today(tmp_path):
    """REQ-039 (brief #1254 answers 3 and 5): `stop_check = "full"` runs agk.mk with no change."""
    proj = make_project(tmp_path, '[flow]\nstop_check = "full"\n')
    proc = run_hook(proj, tmp_path)
    assert proc.returncode == 0 and proc.stdout == "", proc.stdout
    assert ran(proj) == ["FULL"]


def test_5_off_mode_runs_nothing_in_team_mode(tmp_path):
    """REQ-039 (brief #1254 answer 3): `"off"` with review_mode team runs no check."""
    proj = make_project(tmp_path, '[flow]\nstop_check = "off"\n')
    (proj / "src").mkdir()
    (proj / "src" / "app.py").write_text("x = 1\n")
    proc = run_hook(proj, tmp_path)
    assert proc.returncode == 0 and proc.stdout == "" and ran(proj) == []
    assert "stop check: off" in proc.stderr


def test_6_off_mode_is_refused_in_solo_mode(tmp_path):
    """REQ-039 (brief #1254 answers 3 and 5): solo mode has no other gate before a push."""
    toml = 'review_mode = "solo"\n[flow]\nstop_check = "off"\n'
    proj = make_project(tmp_path, toml)
    with pytest.raises(config.StopCheckSettingError) as err:
        config.stop_check_mode(proj)
    assert "flow.stop_check" in str(err.value) and '"off"' not in str(err.value)
    (proj / "src").mkdir()
    (proj / "src" / "app.py").write_text("x = 1\n")
    proc = run_hook(proj, tmp_path)
    assert ran(proj) == ["FULL"], proc.stderr
    assert "setting: flow.stop_check" in proc.stderr


def test_mode_default_and_refusals(tmp_path):
    """REQ-039 (brief #1254 answer 3): `"changed"` by default; any other value is refused."""
    proj = make_project(tmp_path)
    assert config.stop_check_mode(proj) == "changed"
    for value in ('"full"', '"changed"', '"off"'):
        (proj / "agk.toml").write_text(f"[flow]\nstop_check = {value}\n")
        assert config.stop_check_mode(proj) == value.strip('"')
    for value in ('"some"', "1", "true"):
        (proj / "agk.toml").write_text(f"[flow]\nstop_check = {value}\n")
        with pytest.raises(config.StopCheckSettingError):
            config.stop_check_mode(proj)
    assert "stop_check" in config.TABLE_KEYS["flow"]


def test_map_lists_the_agk_mk_recipe_in_order():
    """REQ-039 (brief #1254 answer 2): the map's commands are exactly the agk-governance recipe."""
    text = (ROOT / "agk.mk").read_text()
    recipe = text.split("agk-governance:\n", 1)[1].split("\n\n", 1)[0]
    lines = [line.strip().removeprefix("$(PY) ") for line in recipe.splitlines()]
    assert lines == [" ".join(argv) for _, argv in governance_map.CHECKS]
    names = {name for name, _ in governance_map.CHECKS}
    assert governance_map.ALWAYS <= names
    for _, selected in governance_map.INPUTS:
        assert selected <= names


def test_select_rules():
    """REQ-039 (brief #1254 answer 2): no path selects nothing; an unknown one selects all."""
    assert governance_map.select([]) == []
    assert governance_map.select(["docs/plan/a.md", "src/x.py"]) is None
    plan = governance_map.select(["docs/sources/s.md"])
    assert plan is not None and ("scripts/agk/check_plan.py",) in plan
    req = governance_map.select(["docs/requirements.md"])
    assert req is not None and ("scripts/agk/check_requirements.py",) in req
    design = governance_map.select(["docs/design/theme.md"])
    assert design is not None and ("scripts/agk/check_design.py",) in design
    guides = governance_map.select(["docs/guides/x.md", "changelog.d/x.md"])
    assert guides is not None and len(guides) == len(governance_map.ALWAYS)
    order = [argv for _, argv in governance_map.CHECKS]
    assert design == sorted(design, key=order.index)


def test_changed_paths_reads_renames_and_untracked(tmp_path):
    """REQ-039 (brief #1254 answer 1): both sides of a rename and an untracked file count."""
    proj = make_project(tmp_path)
    git(proj, "mv", "docs/plan/plan.md", "docs/plan/moved.md")
    (proj / "docs" / "sources").mkdir()
    (proj / "docs" / "sources" / "new.md").write_text("Source: x\n")
    paths = governance_map.changed_paths(proj, "main")
    assert paths is not None
    assert {"docs/plan/plan.md", "docs/plan/moved.md", "docs/sources/new.md"} <= set(paths)


def test_changed_paths_is_none_outside_git_or_without_the_default_branch(tmp_path):
    """REQ-039 (brief #1254 answer 2): what cannot be read runs the full set."""
    assert governance_map.changed_paths(tmp_path, "main") is None
    proj = make_project(tmp_path)
    assert governance_map.changed_paths(proj, "trunk") is None
