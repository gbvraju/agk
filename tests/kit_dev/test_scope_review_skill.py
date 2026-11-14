"""Kit-only tests of `/agk:scope-review` (brief #1218, ADR-0517; REQ-050).

`skills/` is not vendored into a project, so these tests live in `tests/kit_dev/`. Step 1 compares
every source and imported design version with the requirements and briefs, without reading the
plan's own scope files, and writes one report outside `docs/`, changing no file of the repository.
Step 2, which the person starts, writes only `docs/plan/scope-triage.md`. Files only; no network.
"""

from __future__ import annotations

import re

from conftest import KIT_ROOT

SKILL = KIT_ROOT / "skills" / "scope-review" / "SKILL.md"
GUIDE = KIT_ROOT / "docs" / "guides" / "planning.md"
NOT_READ = ("docs/plan/scope.md", "docs/plan/prototype-coverage.md", "planning report")
STEP_2 = "## Step 2"


def text() -> str:
    return SKILL.read_text(encoding="utf-8")


def flat(value: str) -> str:
    return " ".join(value.split())


def steps() -> tuple[str, str]:
    """The skill's body before `## Step 2` (step 1) and from it (step 2)."""
    body = text().split("---\n", 2)[2]
    assert body.count(STEP_2) == 1
    first, _, second = body.partition(STEP_2)
    return flat(first), flat(second)


def test_the_skill_is_a_command_the_person_runs():
    """REQ-050 AC2: answer 1, `/agk:scope-review` with model invocation turned off."""
    head = flat(text().split("---\n", 2)[1])
    assert head.startswith("name: scope-review description: ")
    assert "disable-model-invocation: true" in head
    assert "# /agk:scope-review" in text()


def test_step_1_names_the_three_files_it_must_not_read():
    """REQ-050 AC2: answer 1, never `scope.md`, `prototype-coverage.md` or a planning report."""
    first, _ = steps()
    for name in NOT_READ:
        assert name in first, name
    assert "fresh session" in first
    assert "Do not read" in first


def test_step_1_compares_every_source_and_design_version_with_requirements_and_briefs():
    """REQ-050 AC2: answer 1, what it reads and what each finding names."""
    first, _ = steps()
    for name in (
        "docs/sources/",
        "docs/design/imported/",
        "docs/requirements.md",
        "docs/plan/briefs/",
    ):
        assert f"`{name}" in first, name
    for kind in ("screen", "state", "field", "rule", "role", "requirement", "conflict"):
        assert kind in first, kind
    assert "both sides" in first
    assert "location" in first


def test_step_1_writes_one_report_outside_docs_and_nothing_under_docs():
    """REQ-050 AC2: answer 1, the report path is the person's, outside `docs/`; no file changes."""
    first, _ = steps()
    assert "outside `docs/`" in first
    assert "changes no file in the repository" in first
    # No instruction of step 1 writes, creates or edits a path under docs/.
    writes = re.findall(r"\b(?:write|writes|create|creates|edit|edits)\b[^.]*?`docs/", first, re.I)
    assert writes == [], writes
    assert "scope-triage" not in first


def test_step_1_runs_the_data_guard_before_any_source_is_read():
    """REQ-050 AC2: SPEC-0043 rule 3, the guard before any line of a source."""
    first, _ = steps()
    guard = 'python3 "${CLAUDE_PLUGIN_ROOT}/scripts/agk/plan_intake.py" states'
    assert guard in first
    assert first.index(guard) < first.index("`docs/requirements.md")


def test_step_2_is_started_by_the_person_and_writes_only_the_triage_file():
    """REQ-050 AC2: answer 2, the four outcomes, written to `docs/plan/scope-triage.md`."""
    _, second = steps()
    assert "only when the person asks" in second
    assert "`docs/plan/scope-triage.md`" in second
    for outcome in ("covered", "gap", "out of scope", "decision"):
        assert f"**{outcome}**" in second, outcome
    assert "recommendation" in second
    assert "milestone of its area" in second
    paths = set(re.findall(r"`(docs/[^`]*)`", second))
    written = {p for p in paths if re.search(rf"writes?[^.]*`{re.escape(p)}`", second, re.I)}
    assert written == {"docs/plan/scope-triage.md"}, written


def test_the_guide_orders_the_review_before_the_plan_approval_in_both_paths():
    """REQ-050 AC2: answer 3, before `Approve: plan` in each path of the planning guide."""
    guide = GUIDE.read_text(encoding="utf-8")
    for heading in ("## The path", "## From a prototype and an OpenSpec file"):
        section = guide.split(heading, 1)[1].split("\n## ", 1)[0]
        assert "/agk:scope-review" in section, heading
        assert section.index("/agk:scope-review") < section.index("Approve: plan"), heading
