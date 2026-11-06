"""Fix-list items tagged by the rule they enforce (brief #647 answer 2, ADR-0310; REQ-037 AC5, AC6).

Each numbered item of a `Verdict: fix list <sha>` ends with `(rule: <file> <n>)` or `(rule: none)`.
`check_final_clearance.py` warns on an item without one, and fails on it from the date in
`rule_tags_from` of agk.toml; with no such setting it only warns. No network.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
CONFIG = "version: 1\nverdict_authors: [reviewer]\n"
AGENTS = ("conductor.md", "architect.md", "architect-review.md", "shadow.md")
TAGGED = (
    "Verdict: fix list 0066abc\n\nReviewed.\n\n"
    "1. Add the `Flow:` line. (rule: config/session-rules.md 27)\n"
    "2. Merge main in\n   and rerun prepush. (rule: none)\n"
    "3. Name the class. (rule: CLAUDE.md 3).\n"
)
UNTAGGED = "Verdict: fix list 0066abc\n\n1. Add the `Usage:` line.\n2. Fix it. (rule: none)\n"


def test_req037_fix_items_are_the_numbered_items_with_their_continuations():
    """REQ-037 AC5"""
    from common import fix_items

    items = fix_items(TAGGED)
    assert len(items) == 3
    assert items[1].endswith("and rerun prepush. (rule: none)")
    after = "Verdict: fix list 0066abc\n\n1. x (rule: none)\nFinal: docs/adr/0001-x.md A -> B\n"
    assert fix_items(after) == ["1. x (rule: none)"]  # an unindented line ends the item
    assert fix_items("Verdict: cleared 0066abc\n\n1. a note\n") == []
    assert fix_items("Report: 0066abc\n\n1. x\n") == []


@pytest.mark.parametrize(
    ("item", "tag"),
    [
        ("1. x (rule: config/session-rules.md 27)", "config/session-rules.md 27"),
        ("1. x (rule: docs/specs/0021-x.md 3a).", "docs/specs/0021-x.md 3a"),
        ("1. x (rule: none)", "none"),
        ("1. x", None),
        ("1. x (rule: session rule 27)", None),
        ("1. x (rule: none) and more", None),
        ("1. x (rule:)", None),
    ],
)
def test_req037_the_tag_ends_the_item(item, tag):
    """REQ-037 AC5: `(rule: <file> <n>)` or `(rule: none)`, last on the item, a period allowed."""
    from common import item_tag

    assert item_tag(item) == tag


def test_req037_the_protocol_asks_for_the_tag_in_every_copy():
    """REQ-037 AC5: item 8 of the review protocol, identical in the four agent files."""
    ask = "Each numbered item of a fix list ends with `(rule: <file> <n>)` or `(rule: none)`"
    for name in AGENTS:
        text = (ROOT / ".claude" / "agents" / name).read_text(encoding="utf-8")
        line = next(ln for ln in text.splitlines() if ln.startswith("8. **The verdict form**"))
        assert ask in line, name


def scenario(repo, toml: str | None) -> None:
    repo.commit({"README.md": "base\n"}, "base")
    repo.branch()
    files = {"config/reviewers.yaml": CONFIG}
    if toml is not None:
        files["agk.toml"] = toml
    repo.commit(files, "reviewed")


def comments(tmp_path: Path, body: str) -> Path:
    path = tmp_path / "comments.json"
    found = [{"body": body, "created_at": "2026-10-22T10:00:00Z", "user": {"login": "reviewer"}}]
    path.write_text(json.dumps(found), encoding="utf-8")
    return path


def test_req037_an_untagged_item_warns_before_the_date(repo, tmp_path):
    """REQ-037 AC6: before `rule_tags_from` the check passes with one warning."""
    scenario(repo, 'rule_tags_from = "2999-01-01"\n')
    out = repo.run("check_final_clearance.py", "--comments", str(comments(tmp_path, UNTAGGED)))
    assert out.returncode == 0, out.stdout + out.stderr
    assert "warning: 1 fix-list item names no rule" in out.stdout
    assert "(setting: rule_tags_from)" in out.stdout
    assert "ok final-clearance" in out.stdout


def test_req037_an_untagged_item_fails_from_the_date(repo, tmp_path):
    """REQ-037 AC6: from `rule_tags_from` on, an untagged item fails, naming the setting."""
    scenario(repo, 'rule_tags_from = "2026-01-01"\n')
    out = repo.run("check_final_clearance.py", "--comments", str(comments(tmp_path, UNTAGGED)))
    assert out.returncode == 1
    assert "1 fix-list item names no rule" in out.stdout + out.stderr
    assert "rule_tags_from" in out.stdout + out.stderr


def test_req037_with_no_setting_it_only_warns(repo, tmp_path):
    """REQ-037 AC6: a project without the setting is never failed by it."""
    scenario(repo, None)
    out = repo.run("check_final_clearance.py", "--comments", str(comments(tmp_path, UNTAGGED)))
    assert out.returncode == 0 and "warning: 1 fix-list item names no rule" in out.stdout


def test_req037_tagged_items_pass_silently_after_the_date(repo, tmp_path):
    """REQ-037 AC6"""
    scenario(repo, 'rule_tags_from = "2026-01-01"\n')
    out = repo.run("check_final_clearance.py", "--comments", str(comments(tmp_path, TAGGED)))
    assert out.returncode == 0 and "warning" not in out.stdout


@pytest.mark.parametrize("value", ['"soon"', "30", '"2026-13-01"'])
def test_req037_a_bad_setting_is_refused_naming_it(repo, tmp_path, value):
    """REQ-037 AC6: the refusal names the setting, never the value."""
    scenario(repo, f"rule_tags_from = {value}\n")
    out = repo.run("check_final_clearance.py", "--comments", str(comments(tmp_path, UNTAGGED)))
    assert out.returncode == 1
    text = out.stdout + out.stderr
    assert "rule_tags_from" in text and value.strip('"') not in text


def test_req037_this_repository_sets_the_date():
    """REQ-037 AC6: this repository warns for 30 days from the build, then fails."""
    import tomllib

    value = tomllib.loads((ROOT / "agk.toml").read_text(encoding="utf-8"))["rule_tags_from"]
    assert value == "2026-12-06"
