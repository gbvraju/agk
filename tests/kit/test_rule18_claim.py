"""Session rule 18 names the label that `session.py claim` adds (brief #1276, ADR-0547; REQ-050).

`claim` posts one `taken:` comment and adds the label `agk:taken` (brief #1251, ADR-0529), for a
brief and for a build alike. Rule 18 of `config/session-rules.md` names that label exactly when
`claim` adds it, so the rule and the planner cannot drift apart again. Read from the files; no
network.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RULES = ROOT / "config" / "session-rules.md"
SESSION = ROOT / "scripts" / "agk" / "session.py"


def rule(number: int) -> str:
    """The text of one numbered session rule."""
    text = RULES.read_text(encoding="utf-8")
    match = re.search(rf"^{number}\. (.*?)(?=^\d+\. |\Z)", text, re.M | re.S)
    assert match, f"session rule {number} is missing"
    return " ".join(match.group(1).split())


def taken_label() -> str | None:
    """The value of `TAKEN_LABEL` in session.py, else None."""
    tree = ast.parse(SESSION.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id == "TAKEN_LABEL" for t in node.targets
        ):
            return ast.literal_eval(node.value)
    return None


def claim_label_guards() -> list[list[str]] | None:
    """For each call in `claim` that names TAKEN_LABEL, the source of the `if` tests above it;
    None when `claim` names no label."""
    tree = ast.parse(SESSION.read_text(encoding="utf-8"))
    fn = next((n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "claim"), None)
    assert fn is not None, "session.py has no claim()"
    found: list[list[str]] = []

    def walk(node: ast.AST, tests: list[str]) -> None:
        if isinstance(node, (ast.FunctionDef, ast.Lambda)) and node is not fn:
            return  # an inner helper is not what claim itself does
        if isinstance(node, ast.Call) and any(
            isinstance(a, ast.Name) and a.id == "TAKEN_LABEL" for a in ast.walk(node)
        ):
            if not (isinstance(node.func, ast.Name) and node.func.id == "print"):
                found.append(list(tests))
        inner = tests + [ast.unparse(node.test)] if isinstance(node, ast.If) else tests
        for child in ast.iter_child_nodes(node):
            walk(child, inner)

    walk(fn, [])
    return found or None


def build_sentence(text: str) -> str:
    """The sentence of rule 18 on `claim --build X`."""
    found = [s for s in re.split(r"(?<=\.) ", text) if "--build X" in s]
    assert found, "rule 18 names no `claim --build X`"
    return " ".join(found)


def test_req050_claim_adds_the_taken_label():
    """REQ-050: the code side the rule is checked against."""
    assert taken_label() == "agk:taken"
    assert claim_label_guards(), "claim adds no label"


def test_req050_rule_18_names_the_label_exactly_when_claim_adds_it():
    """REQ-050: brief #1276 answer 1."""
    text = rule(18)
    label = taken_label()
    adds = claim_label_guards() is not None and label is not None
    assert (f"`{label}`" in text) is adds
    assert "posts one comment and nothing else" not in text
    if adds:
        wanted = f"which posts one comment and adds the label `{label}`, and nothing else"
        assert wanted in text


def test_req050_the_build_sentence_names_the_label_when_a_build_claim_adds_it():
    """REQ-050: brief #1276 answer 1; `claim --build` adds the label unless a `build` test
    guards it."""
    guards = claim_label_guards() or []
    build_adds = any(not any("build" in t for t in g) for g in guards)
    assert (f"`{taken_label()}`" in build_sentence(rule(18))) is build_adds


def test_req050_rule_18_keeps_its_other_words():
    """REQ-050: brief #1276 answer 1, no other word of the rule changes."""
    text = rule(18)
    for phrase in (
        "A session finds its next item with `python3 scripts/agk/session.py next --session ID`",
        "a builder takes a brief only with "
        "`python3 scripts/agk/session.py claim --session ID --brief N`",
        "or with `next --session ID --take`, which chooses and takes in one step",
        "which posts `taken: <id> <date> build (<x>)`",
        "and refuses a build that a live take holds",
    ):
        assert phrase in text, phrase
