"""Tests of personas and user stories in the plan (SPEC-0043 rules 4 to 7 and 9 with amendment 164
item 2, build (p), ADR-0462; REQ-050).

REQ-050 AC2 and AC3.

The proposals hold `personas` (`P1`, `P2`, ... with a name, goals and sources) and each requirement
names its `persona` and one `story` `As <name>, I want ..., so that ...`. `validate` refuses a
requirement without a persona or a story, an unknown persona key, a story of another form and a
persona without sources or goals, naming the rule and the key, never the text. A user the sources
only imply is an open question with `(verify)`, never a persona. `render` writes
`docs/plan/personas.md` and the `Persona:` and `Story:` lines; `check_plan.py` fails a proposed
requirement whose `Persona:` names no persona there, and `--trace` prints the persona column.
Invented sources only (example.com), no network.
"""

from __future__ import annotations

import copy
import socket
from pathlib import Path

import check_plan
import pytest
from test_plan_intake import PRD, SOW, STORY, TITLE, refused, validate, write
from test_plan_render import proposals, render
from test_plan_render import repo as repo  # noqa: F401 - the fixture, reused

OWNER = "Shop owner"  # a persona's name; never printed by a refusal
CLERK = "Order clerk"
SECOND = {"key": "P2", "name": CLERK, "goals": ["Packs each order", "Finds late orders"]}
SECOND |= {"sources": [f"{SOW}:8"]}
IMPLIED = {"key": "Q2", "text": "Who approves refunds? (verify)", "sources": [f"{SOW}#Payments"]}


@pytest.fixture(autouse=True)
def no_network(monkeypatch) -> None:
    def refuse(*args, **kwargs):
        raise AssertionError("the plan tools open no socket")

    monkeypatch.setattr(socket, "socket", refuse)


def two_personas() -> dict:
    """Two personas, and a second requirement whose story is the second persona's."""
    data = proposals()
    data["personas"].append(copy.deepcopy(SECOND))
    second = copy.deepcopy(data["requirements"][0]) | {"key": "R2", "persona": "P2"}
    second["story"] = f"As {CLERK}, I want late orders flagged, so that none ships late"
    data["requirements"].append(second)
    data["areas"][0]["requirements"].append("R2")
    data["briefs"][1]["advances"] = ["R2"]
    return data


def read(root: Path, rel: str) -> str:
    return (root / rel).read_text(encoding="utf-8")


def no_text(out: str) -> None:
    for text in (OWNER, CLERK, STORY, "the order list", "every order"):
        assert text not in out, out


# --- rules 4 and 5: validate -------------------------------------------------------------------


def test_ac2_two_personas_and_their_stories_pass(repo: Path, capsys) -> None:
    """REQ-050 AC2: rule 4 with amendment 164 item 2, each requirement names its persona."""
    code, out = validate(repo, two_personas(), capsys)
    assert code == 0 and out.strip() == "ok proposals", out


@pytest.mark.parametrize("key", ["persona", "story"])
def test_ac2_a_requirement_without_a_persona_or_a_story_is_refused(
    repo: Path, key: str, capsys
) -> None:
    """REQ-050 AC2: rules 4 and 5, the requirement's key and the missing field, no text."""
    data = two_personas()
    del data["requirements"][1][key]
    out = refused(repo, data, capsys, f"rule 4: requirements R2: missing key {key}")
    no_text(out)


def test_ac2_an_unknown_persona_key_is_refused(repo: Path, capsys) -> None:
    """REQ-050 AC2: rule 5, a persona key that names no persona."""
    data = two_personas()
    data["requirements"][1]["persona"] = "P7"
    out = refused(repo, data, capsys, "rule 5: requirements R2: persona names nothing")
    no_text(out)


@pytest.mark.parametrize(
    "story",
    [
        f"As {CLERK}, I want the order list, so that I see every order",  # another persona's name
        f"As {OWNER}, I want the order list because I see every order",  # no `, so that `
        f"I want the order list, so that I see every order, as {OWNER}",  # not `As <name>, `
        f"As {OWNER}, I need the order list, so that I see every order",  # not `I want `
    ],
)
def test_ac2_a_story_of_another_form_is_refused(repo: Path, story: str, capsys) -> None:
    """REQ-050 AC2: rule 5 with `Q-1089-4`, the form only: `As <name>, I want ..., so that ...`."""
    data = two_personas()
    data["requirements"][0]["story"] = story
    out = refused(repo, data, capsys, "rule 5: requirements R1: story is not ")
    assert "As <the persona's name>, I want <capability>, so that <outcome>" in out
    no_text(out)


@pytest.mark.parametrize("field", ["sources", "goals"])
def test_ac2_a_persona_without_sources_or_goals_is_refused(repo: Path, field: str, capsys) -> None:
    """REQ-050 AC2: rule 4, a persona's `sources` and `goals` are non-empty, as for every item."""
    data = two_personas()
    data["personas"][1][field] = []
    out = refused(repo, data, capsys, f"rule 4: personas P2: {field} is empty")
    no_text(out)


def test_ac2_a_persona_whose_source_does_not_resolve_is_refused(repo: Path, capsys) -> None:
    """REQ-050 AC2: rule 5, a persona's location resolves like every item's."""
    data = two_personas()
    data["personas"][1]["sources"] = [f"{SOW}:999"]
    refused(repo, data, capsys, "rule 5: personas P2: a location's line does not exist")


def test_ac2_the_proposals_must_hold_personas_keyed_in_order(repo: Path, capsys) -> None:
    """REQ-050 AC2: rule 4, `personas` is a key of the proposals and its keys run P1, P2, ..."""
    data = two_personas()
    del data["personas"]
    refused(repo, data, capsys, "rule 4: proposals: missing key personas")
    data = two_personas()
    data["personas"][1]["key"] = "P3"
    refused(repo, data, capsys, "rule 4: personas P3: keys run P1, P2, ... in order")
    data = two_personas()
    data["personas"][1]["role"] = "clerk"
    refused(repo, data, capsys, "rule 4: personas P2: unknown key role")


def test_ac2_a_repeated_persona_key_is_refused(repo: Path, capsys) -> None:
    """REQ-050 AC2: rule 4, keys are unique within a section."""
    data = two_personas()
    data["personas"].append(copy.deepcopy(SECOND))
    refused(repo, data, capsys, "rule 4: personas P2: the key is repeated")


# --- rule 6: an implied user is an open question -----------------------------------------------


def test_ac2_an_implied_user_is_an_open_question_never_a_persona(repo: Path, capsys) -> None:
    """REQ-050 AC2: rule 6 with amendment 164 item 2, printed for the person, with `(verify)`."""
    data = two_personas()
    data["scope"]["open_questions"].append(copy.deepcopy(IMPLIED))
    code, out = render(repo, data, capsys)
    assert code == 0, out
    questions = out[out.index("Open questions for the person") : out.index("created ")]
    assert f"- Who approves refunds? (verify) (`{SOW}#Payments`)" in questions
    assert "Who approves refunds" not in read(repo, "docs/plan/personas.md")
    data["scope"]["open_questions"][-1]["text"] = "Who approves refunds?"
    refused(repo, data, capsys, "rule 6: scope.open_questions Q2: no (verify) mark")


# --- rule 7: render ----------------------------------------------------------------------------


def test_ac2_render_writes_personas_md(repo: Path, capsys) -> None:
    """REQ-050 AC2: rule 7, one `### P<n> <name>` block with its `Goal:` and `Source:` lines."""
    code, out = render(repo, two_personas(), capsys)
    assert code == 0, out
    assert "created docs/plan/personas.md" in out
    assert read(repo, "docs/plan/personas.md") == (
        "# Personas\n\n"
        "Drafted by `plan_intake.py render` (SPEC-0043 rule 7); the person owns it.\n\n"
        f"### P1 {OWNER}\n\nGoal: Sees every order\nSource: `{PRD}:8`\n\n"
        f"### P2 {CLERK}\n\nGoal: Packs each order\nGoal: Finds late orders\nSource: `{SOW}:8`\n"
    )


def test_ac2_render_writes_the_persona_and_story_lines_before_the_criteria(
    repo: Path, capsys
) -> None:
    """REQ-050 AC2: rule 7, `Persona: P<n> <name>` and `Story: <story>` in each block."""
    assert render(repo, two_personas(), capsys)[0] == 0
    proposed = read(repo, "docs/plan/requirements-proposed.md")
    block = proposed[proposed.index(f"### R1 {TITLE}") : proposed.index("### R2")]
    assert block.startswith(f"### R1 {TITLE}\n\nPersona: P1 {OWNER}\nStory: {STORY}\n\nCriteria:")
    assert f"\nPersona: P2 {CLERK}\nStory: As {CLERK}, I want late orders flagged" in proposed


def test_ac2_render_refuses_an_existing_personas_md(repo: Path, capsys) -> None:
    """REQ-050 AC2: rule 7, all or nothing: personas.md is one of the new files."""
    write(repo, "docs/plan/personas.md", "the person's file\n")
    code, out = render(repo, two_personas(), capsys)
    assert code == 1 and "rule 7: docs/plan/personas.md already exists" in out, out
    assert not (repo / "docs/plan/scope.md").exists()


# --- rules 9 and 10: check_plan.py -------------------------------------------------------------


def trace_rows(out: str) -> dict[str, list[str]]:
    rows = [line for line in out.splitlines() if line.startswith("| docs/")]
    return {
        cells[0]: cells[1:]
        for cells in ([c.strip() for c in row.strip("|").split("|")] for row in rows)
    }


def test_ac3_the_trace_has_a_persona_column(repo: Path, capsys) -> None:
    """REQ-050 AC3: rule 9, the persona after the requirement, `none` where it has none."""
    assert render(repo, two_personas(), capsys)[0] == 0
    proposed = read(repo, "docs/plan/requirements-proposed.md")
    write(
        repo, "docs/plan/requirements-proposed.md", proposed.replace(f"Persona: P2 {CLERK}\n", "")
    )
    code = check_plan.main(["--root", str(repo), "--trace"])
    out = capsys.readouterr().out
    assert code == 0, out
    head = "| Location | Requirement | Persona | Spec rule | Brief | Pull request | Test |"
    assert head in out
    rows = trace_rows(out)
    assert rows[f"{SOW}:8"][:2] == ["R1, R2", "P1"]
    assert rows[f"{PRD}:8"][:2] == ["R1, R2, REQ-101", "P1"]  # REQ-101 of requirements.md
    write(repo, "docs/plan/requirements-proposed.md", f"### R9 Other\n\nSource: `{SOW}:8`\n")
    write(repo, "docs/plan/personas.md", "# Personas\n")
    check_plan.main(["--root", str(repo), "--trace"])
    assert trace_rows(capsys.readouterr().out)[f"{SOW}:8"][:2] == ["R9", "none"]


def test_ac3_check_plan_fails_a_persona_that_personas_md_does_not_list(repo: Path, capsys) -> None:
    """REQ-050 AC3: rule 10 with amendment 164 item 2, naming the requirement and the key."""
    assert render(repo, two_personas(), capsys)[0] == 0
    assert check_plan.main(["--root", str(repo)]) == 0, capsys.readouterr().out
    capsys.readouterr()
    personas = read(repo, "docs/plan/personas.md")
    write(repo, "docs/plan/personas.md", personas[: personas.index("### P2")])
    code = check_plan.main(["--root", str(repo)])
    out = capsys.readouterr().out
    assert code == 1, out
    line = (
        "FAIL plan: rule 10: docs/plan/requirements-proposed.md: R2:"
        " Persona: P2 names no persona of docs/plan/personas.md"
    )
    assert line in out and "R1:" not in out
    no_text(out)
    (repo / "docs/plan/personas.md").unlink()
    check_plan.main(["--root", str(repo)])
    out = capsys.readouterr().out
    assert "R1: Persona: P1 names no persona" in out and "R2: Persona: P2" in out


def test_ac3_a_requirement_block_without_a_persona_line_is_not_failed(repo: Path, capsys) -> None:
    """REQ-050 AC3: rule 10, only a `Persona:` that names nothing fails; a block drafted before
    personas has none and its trace cell is `none` (rule 9)."""
    assert render(repo, proposals(), capsys)[0] == 0
    proposed = read(repo, "docs/plan/requirements-proposed.md")
    write(
        repo, "docs/plan/requirements-proposed.md", proposed.replace(f"Persona: P1 {OWNER}\n", "")
    )
    (repo / "docs/plan/personas.md").unlink()
    assert check_plan.main(["--root", str(repo)]) == 0, capsys.readouterr().out
