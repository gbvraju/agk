"""Kit tests: the path from an idea takes four stage pull requests (brief #2021, ADR-0836, REQ-050).

The stack options and their accept stand on one stage branch, two approvals stand at two heads of one
pull request, each tied to its own record's digest, and `[plan] stage_pulls` chooses `stage` or `step`.
Invented records under a temporary root (example.com); local git only, no network.
"""

from __future__ import annotations

import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
from pathlib import Path

import pytest

KIT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KIT_ROOT / "scripts" / "agk"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import config  # noqa: E402
import design_signoff  # noqa: E402
import steward_evidence  # noqa: E402
from test_stack_choice import STACK, engines, git, project, record  # noqa: E402

CHECK_ADRS = KIT_ROOT / "scripts" / "agk" / "check_adrs.py"
LINK = "https://github.example.com/o/r/pull/1#issuecomment-1"
HEAD = "a" * 40


def stage_branch(tmp: Path) -> Path:
    """A project whose default branch has no stack record; the stage branch adds the Proposed one."""
    root = project(tmp, None, '\n[testing]\nprofile = "balanced"\n', commit=True)
    (root / STACK).write_text(record(), encoding="utf-8")
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "the stack options")
    return root


def test_the_accept_follows_the_options_on_one_stage_branch(tmp_path):
    """REQ-050 answer 1: the Proposed stack record and its accept in one pull request pass both checks."""
    root = stage_branch(tmp_path)
    assert git(root, "ls-tree", "-r", "--name-only", "main", "docs/adr") == ""  # not on main
    proc = engines(root, "stack-accept", "--option", "A", "--reason", "nothing to host suits it")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert len(git(root, "log", "--format=%s", "main..HEAD").splitlines()) == 3
    check = engines(root, "stack-check")
    assert check.returncode == 0, check.stdout
    adrs = subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, "-I", str(CHECK_ADRS), "--base", "main"],
        cwd=root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=60,
    )
    assert "an Accepted ADR may change only" not in adrs.stdout, adrs.stdout
    assert "cannot be deleted" not in adrs.stdout, adrs.stdout


def signed(tmp: Path) -> Path:
    """An inventory approved at head A and a prototype v1 approved at a later head B."""
    (tmp / "docs" / "design" / "prototype" / "v1").mkdir(parents=True)
    (tmp / design_signoff.INVENTORY).write_text("# Inventory\n\n- home/empty\n", encoding="utf-8")
    page = tmp / "docs" / "design" / "prototype" / "v1" / "home--empty.html"
    page.write_text("<p>Welcome to example.com</p>\n", encoding="utf-8")
    inventory = design_signoff.inventory_digest(tmp)
    design = design_signoff.version_digest(tmp, "v1")
    (tmp / design_signoff.SIGNOFFS).write_text(
        "| kind | version | digest | head | date | comment |\n|---|---|---|---|---|---|\n"
        f"| inventory | - | {inventory} | {HEAD} | 2026-11-26 | {LINK} |\n"
        f"| design | v1 | {design} | {'b' * 40} | 2026-11-26 | {LINK} |\n",
        encoding="utf-8",
    )
    return tmp


def test_two_approvals_at_two_heads_both_count(tmp_path):
    """REQ-050 answer 2: each approval is tied to its own record's digest, not to the last head."""
    root = signed(tmp_path)
    found = design_signoff.rows(root)
    assert [(r["kind"], r["head"][0]) for r in found] == [("inventory", "a"), ("design", "b")]
    assert found[0]["digest"] == design_signoff.inventory_digest(root)
    assert design_signoff.signed_off(root, "v1")
    assert design_signoff.frozen_problems(root) == []


def test_a_fix_after_approval_voids_only_its_own_record(tmp_path):
    """REQ-050 answer 6: a fix to the prototype asks its approval again; the inventory's still counts."""
    root = signed(tmp_path)
    page = root / "docs" / "design" / "prototype" / "v1" / "home--empty.html"
    page.write_text("<p>Welcome back to example.com</p>\n", encoding="utf-8")
    assert not design_signoff.signed_off(root, "v1")
    assert design_signoff.frozen_problems(root) == [
        "rule 9: docs/design/prototype/v1: a signed-off version changed"
    ]
    assert design_signoff.rows(root)[0]["digest"] == design_signoff.inventory_digest(root)


def write_toml(tmp: Path, text: str) -> Path:
    (tmp / "agk.toml").write_text('default_branch = "main"\n' + text, encoding="utf-8")
    return tmp


@pytest.mark.parametrize(
    ("text", "expected"),
    [("", "step"), ("[plan]\n", "step"), ('[plan]\nstage_pulls = "stage"\n', "stage")],
)
def test_stage_pulls_reads_stage_or_step(tmp_path, text, expected):
    """REQ-050 answer 5: absent means `step`, so an upgrade changes nothing."""
    assert config.stage_pulls(write_toml(tmp_path, text)) == expected


@pytest.mark.parametrize("value", ['"stages"', "true", "4", '""'])
def test_another_value_is_refused_naming_the_setting(tmp_path, value):
    """REQ-050: the refusal names the setting, never the value."""
    root = write_toml(tmp_path, f"[plan]\nstage_pulls = {value}\n")
    with pytest.raises(config.StagePullsSettingError) as err:
        config.stage_pulls(root)
    assert str(err.value) == "the setting is refused (setting: plan.stage_pulls)"


def test_the_setting_is_a_known_plan_key():
    """REQ-050"""
    assert "stage_pulls" in config.TABLE_KEYS["plan"]


def test_every_stage_before_build_names_one_of_four_pull_requests():
    """REQ-050 answer 3: the steward's stage list says which pull request each stage is."""
    pulls = steward_evidence.STAGE_PULLS
    assert set(pulls) == set(steward_evidence.STAGES)
    assert pulls["build"] is None
    named = [pulls[s] for s in steward_evidence.STAGES if s != "build"]
    assert list(dict.fromkeys(named)) == ["discovery", "design", "technical design", "plan"]


def test_the_guide_and_skills_drop_one_pull_request_per_step():
    """REQ-050 answers 3 and 4: the texts name the four stages and keep today's per-step form as `step`."""
    guide = (KIT_ROOT / "docs" / "guides" / "planning.md").read_text(encoding="utf-8")
    idea = guide.split("## From an idea", 1)[1].split("\n## ", 1)[0]
    assert "Each step is its own pull request" not in idea
    for stage in ("Discovery", "Design", "Technical design", "Plan"):
        assert f"**{stage} pull request.**" in idea
    assert "stage_pulls" in idea and "ADR-0836" in idea
    stack = (KIT_ROOT / "skills" / "stack" / "SKILL.md").read_text(encoding="utf-8")
    assert "in its own pull request, that sets" not in stack
    assert "same branch" in stack
    for name in ("start", "vision"):
        text = (KIT_ROOT / "skills" / name / "SKILL.md").read_text(encoding="utf-8")
        assert "goes in its own pull request, merged first (ADR-0664" not in text
        assert "discovery pull request" in text
