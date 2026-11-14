"""Tests of the business scope lock (brief #1219, ADR-0518; SPEC-0043 amendment 176; REQ-050).

`/agk:scope-lock` (`skills/scope-lock/SKILL.md`, run by the person) writes
`docs/plan/scope-lock.md` from the plan for readers who are not technical. When that file exists,
`check_plan.py` fails each of its lines that holds a requirement number (`REQ-n`), a file path, a
brief key (the name of a brief file under `docs/plan/briefs/`) or a builder or pull-request figure
(the words `builder`, `pull request`, `PR rate`), naming rule 10, the file and the line number and
never the text. A clean scope lock passes, and a plan without one is checked as before.
Invented files only (example.com), in `tmp_path`; no network.
"""

from __future__ import annotations

import re
from pathlib import Path

import check_plan

KIT_ROOT = Path(__file__).resolve().parents[2]
SKILL = KIT_ROOT / "skills" / "scope-lock" / "SKILL.md"
REFERENCE = KIT_ROOT / "docs" / "guides" / "reference.md"
GUIDE = KIT_ROOT / "docs" / "guides" / "planning.md"
LOCK = "docs/plan/scope-lock.md"

SOW = (
    "Source: Example statement of work\nKind: sow\nVersion: 1\nDate: 2026-10-01\n\n"
    "# Orders\n\n"
    "The portal at example.com lists orders.\n"  # line 8
)
SCOPE = "# Scope\n\n## In scope\n\n- Orders are listed `docs/sources/sow.md:8`\n"
REQUIREMENTS = (
    "# Requirements\n\n"
    "### REQ-101 — Orders are listed\n\n"
    "- Acceptance: AC1 the orders page at example.com lists orders\n"
    "- Status: planned\n- Source: `docs/sources/sow.md:8`\n"
)
MILESTONES = "# Milestones\n\n### M1 Orders\n\nExit: all 1 briefs merged.\nTarget: 2026-12-18\n"
BRIEF = "Advances: REQ-101\nTouches: app/list.py\nPriority: 1\nSize: S\nMilestone: M1\n"
CLEAN = (
    "# Scope lock: Example orders portal\n"
    "\n"
    "## Milestone 1: Orders (2026-11-16 to 2026-12-18, about 4 to 8 hours)\n"
    "\n"
    "- Orders list: a shop owner sees every order and opens one.\n"
    "\n"
    "Go-live: 2026-12-18.\n"
    "\n"
    "## After go-live\n"
    "\n"
    "- Order export, and/or a monthly summary, see https://example.com/roadmap.\n"
    "\n"
    "## Not included\n"
    "\n"
    "- Payments: the shop takes payment in its own till.\n"
    "\n"
    "## Questions\n"
    "\n"
    "- Who signs the order list off? Needed by 2026-11-30.\n"
)


def write(root: Path, rel: str, text: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def project(root: Path, lock: str | None = CLEAN) -> Path:
    """An invented project with a plan and, unless None, a scope lock."""
    write(root, "docs/sources/sow.md", SOW)
    write(root, "docs/plan/scope.md", SCOPE)
    write(root, "docs/plan/milestones.md", MILESTONES)
    write(root, "docs/plan/briefs/M1/m1-list.md", BRIEF)
    write(root, "docs/requirements.md", REQUIREMENTS)
    if lock is not None:
        write(root, LOCK, lock)
    return root


def check(root: Path, capsys) -> tuple[int, list[str]]:
    code = check_plan.main(["--root", str(root)])
    return code, capsys.readouterr().out.splitlines()


def failures(lines: list[str]) -> list[str]:
    return [line for line in lines if line.startswith("FAIL ")]


def with_line(text: str) -> str:
    """CLEAN with TEXT as its line 7 (after the milestone's first item)."""
    lines = CLEAN.splitlines()
    return "\n".join([*lines[:6], text, *lines[6:]]) + "\n"


# --- the check of rule 10 (brief #1219 answers 2 and 4) --------------------------------------


def test_a_clean_scope_lock_passes(tmp_path: Path, capsys) -> None:
    # REQ-050: brief #1219 answer 4, a clean scope lock passes; a link and "and/or" are no path.
    code, lines = check(project(tmp_path), capsys)
    assert failures(lines) == []
    assert code == 0
    assert lines[-1].startswith("ok plan: ")


def test_a_plan_without_a_scope_lock_is_checked_as_before(tmp_path: Path, capsys) -> None:
    # REQ-050: brief #1219 answer 2, the check runs only when the file exists.
    code, lines = check(project(tmp_path, lock=None), capsys)
    assert failures(lines) == []
    assert code == 0


def test_a_requirement_number_fails_naming_the_rule_and_line(tmp_path: Path, capsys) -> None:
    # REQ-050: brief #1219 answers 2 and 4, a REQ number fails with the rule and the line number.
    code, lines = check(project(tmp_path, with_line("- Delivers REQ-101 in full.")), capsys)
    assert code == 1
    assert failures(lines) == [f"FAIL plan: rule 10: {LOCK}:7: a requirement number"]
    assert "Delivers" not in "\n".join(lines)


def test_a_file_path_fails(tmp_path: Path, capsys) -> None:
    # REQ-050: brief #1219 answers 2 and 4, a file path fails; the text is never printed.
    for n, text in enumerate(
        ("- See docs/plan/scope.md for more.", "- Built in `app/list.py`.", "- Run ./setup.sh.")
    ):
        root = project(tmp_path / str(n), with_line(text))
        code, lines = check(root, capsys)
        assert code == 1, text
        assert failures(lines) == [f"FAIL plan: rule 10: {LOCK}:7: a file path"], text
        assert text not in "\n".join(lines)


def test_a_brief_key_fails(tmp_path: Path, capsys) -> None:
    # REQ-050: brief #1219 answer 2, the key of a brief file of the plan fails.
    code, lines = check(project(tmp_path, with_line("- Comes with m1-list.")), capsys)
    assert code == 1
    assert failures(lines) == [f"FAIL plan: rule 10: {LOCK}:7: a brief key"]


def test_a_builder_or_pull_request_figure_fails(tmp_path: Path, capsys) -> None:
    # REQ-050: brief #1219 answers 2 and 4, a builder figure fails naming the rule and the line.
    texts = (
        "- Three builders finish it in a week.",
        "- About 12 pull requests.",
        "- At our PR rate of 4 a day.",
        "- One Builder per screen.",
    )
    for n, text in enumerate(texts):
        root = project(tmp_path / str(n), with_line(text))
        code, lines = check(root, capsys)
        assert code == 1, text
        figure = f"FAIL plan: rule 10: {LOCK}:7: a builder or pull request figure"
        assert failures(lines) == [figure]
        assert text not in "\n".join(lines)


def test_each_kind_on_one_line_fails_once_each(tmp_path: Path, capsys) -> None:
    # REQ-050: brief #1219 answer 2, one line with several terms names each kind once, in order.
    text = "- REQ-101 and REQ-102 by two builders, see docs/plan/scope.md."
    code, lines = check(project(tmp_path, with_line(text)), capsys)
    assert code == 1
    assert failures(lines) == [
        f"FAIL plan: rule 10: {LOCK}:7: a requirement number",
        f"FAIL plan: rule 10: {LOCK}:7: a file path",
        f"FAIL plan: rule 10: {LOCK}:7: a builder or pull request figure",
    ]


def test_words_that_only_look_alike_pass(tmp_path: Path, capsys) -> None:
    # REQ-050: brief #1219 answer 2, whole words only: "rebuilder", "requirement" and a date pass.
    text = "- The requirement of 14/11 needs a rebuilder of trust; m1-listing is a word."
    code, lines = check(project(tmp_path, with_line(text)), capsys)
    assert failures(lines) == []
    assert code == 0


# --- the skill and its listing (brief #1219 answers 1, 3 and 4) ------------------------------


def frontmatter(text: str) -> dict[str, str]:
    head = text.split("---\n", 2)[1]
    return {k.strip(): v.strip() for k, _, v in (line.partition(":") for line in head.splitlines())}


def test_the_skill_is_run_by_the_person_and_writes_the_scope_lock() -> None:
    # REQ-050: brief #1219 answer 1, `/agk:scope-lock` writes the scope lock, run by the person.
    text = SKILL.read_text(encoding="utf-8")
    head = frontmatter(text)
    assert head["name"] == "scope-lock"
    assert head["disable-model-invocation"] == "true"
    assert "# /agk:scope-lock" in text
    assert LOCK in text
    for source in ("docs/plan/scope.md", "docs/plan/milestones.md", "docs/design/inventory.md"):
        assert source in text, source
    for part in ("go-live", "After go-live", "Not included", "Questions", "Risks", "Decisions"):
        assert part in text, part


def test_the_skill_runs_the_check_and_prints_the_issue_text_creating_none() -> None:
    # REQ-050: brief #1219 answers 1 and 2, the check runs; an issue text is printed, none created.
    text = SKILL.read_text(encoding="utf-8")
    assert 'python3 "${CLAUDE_PLUGIN_ROOT}/scripts/agk/check_plan.py"' in text
    assert "gh issue create" not in text
    assert "gh api" not in text
    assert re.search(r"creates? no issue", text)


def test_the_skill_names_a_print_command_and_never_installs_a_browser() -> None:
    # REQ-050: brief #1219 answer 3, a PDF is optional and no browser is installed.
    text = SKILL.read_text(encoding="utf-8")
    assert "--print-to-pdf" in text
    assert "never install" in text
    for verb in ("pip install", "npm install", "apt-get", "brew install", "winget"):
        assert verb not in text, verb


def test_the_skill_is_listed_in_the_reference_commands_and_the_guide() -> None:
    # REQ-050: brief #1219 answer 4, the reference's plugin table and the planning guide name it.
    lines = REFERENCE.read_text(encoding="utf-8").splitlines()
    rows = [x for x in lines if "`/agk:scope-lock`" in x]
    assert len(rows) == 1 and rows[0].startswith("| `/agk:scope-lock` |")
    assert "docs/plan/scope-lock.md" in rows[0]
    assert "/agk:scope-lock" in GUIDE.read_text(encoding="utf-8")
