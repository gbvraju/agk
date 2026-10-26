"""The shadow review in the facts (SPEC-0035 rules 4, 5 and 8; build (c) of REQ-042).

`facts.py` saves, in the optional section `shadow`, the counts of `shadow_rate.py` for the merged
pull requests of its window: the open issue labelled `agk-shadow`, the comments of that issue and
the comments of each merged pull request. What cannot be read is `unknown`, never zero. Saved
copies in `tmp_path`; no network, no model. REQ-042.
"""

from __future__ import annotations

import json
from pathlib import Path

import facts
import metrics
import pytest

SHA = "a1b2c3d4e5f60718293a4b5c6d7e8f9012345678"
SHA7 = SHA[:7]
AUTHORS = ["boss"]
WEEK = "2026-10-20T10:00:00Z"  # 2026-W43


def comment(cid: int, login: str, body: str) -> dict:
    return {"id": cid, "user": {"login": login}, "body": body, "created_at": WEEK}


def verdict(cid: int = 1, items: int = 3) -> dict:
    body = f"Verdict: fix list {SHA}\n\n" + "".join(
        f"{i}. finding {i}\n" for i in range(1, items + 1)
    )
    return comment(cid, "boss", body)


def shadow(cid: int = 5, pr: int = 7, items: int = 2) -> dict:
    body = f"Shadow: #{pr} {SHA} fix list\n\n" + "".join(
        f"S{i}. `a.py` line {i}\n" for i in range(1, items + 1)
    )
    return comment(cid, "boss", body)


def marks(cid: int, *lines: str) -> dict:
    return comment(cid, "builder", "Marks:\n" + "\n".join(lines) + "\n")


def pull(n: int = 7, merged: str | None = WEEK) -> dict:
    return {"number": n, "merged_at": merged, "user": {"login": "builder"}}


class Src:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.api = metrics.ApiDir(path)

    def write(self, name: str, value) -> None:
        (self.path / f"{name}.json").write_text(json.dumps(value), encoding="utf-8")

    def issue(self, number: int = 40, state: str = "open") -> None:
        self.write("issues-agk-shadow", [{"number": number, "state": state}])


@pytest.fixture
def src(tmp_path: Path) -> Src:
    return Src(tmp_path)


def kept(*pairs) -> dict:
    return {p["number"]: (p, comments) for p, comments in pairs}


def reviewed(src: Src, mark_lines: list[str] | None = None) -> dict:
    src.issue()
    src.write("comments-40", [shadow()])
    items = [verdict()] + ([marks(9, *mark_lines)] if mark_lines else [])
    return kept((pull(), items))


def test_the_counts_of_a_week_and_the_total_are_saved(src):
    """Rule 5: the facts carry the counts of rule 4 per ISO week of the merge and in total."""
    lines = [f"C{SHA7}-1 right", f"C{SHA7}-2 wrong", f"C{SHA7}-3 both", f"S{SHA7}-1 right"]
    lines += [f"S{SHA7}-2 wrong"]
    section = facts.shadow_section(src.api, reviewed(src, lines), AUTHORS)
    expected = {
        "heads": 1,
        "right_conductor_only": 1,
        "right_shadow_only": 1,
        "right_both": 1,
        "wrong_conductor": 1,
        "wrong_shadow": 1,
        "unmarked_heads": 0,
        "unmarked_findings": 0,
    }
    assert section == {
        "issue": 40,
        "unpaired": 0,
        "unread": 0,
        "weeks": {"2026-W43": expected},
        "total": expected,
    }


def test_a_head_without_marks_is_unmarked_never_zero_findings(src):
    section = facts.shadow_section(src.api, reviewed(src), AUTHORS)
    assert section["total"]["unmarked_heads"] == 1 and section["total"]["heads"] == 1
    assert section["total"]["right_conductor_only"] == 0


def test_no_open_shadow_issue_is_a_review_that_is_not_running(src):
    src.write("issues-agk-shadow", [])
    assert facts.shadow_section(src.api, kept((pull(), [verdict()])), AUTHORS) == {"issue": None}


def test_a_closed_shadow_issue_does_not_count_as_running(src):
    src.issue(state="closed")
    assert facts.shadow_section(src.api, {}, AUTHORS) == {"issue": None}


@pytest.mark.parametrize("case", ["no list", "two issues", "no comments", "no authors"])
def test_what_cannot_be_read_is_unknown(src, case):
    items = reviewed(src, [f"C{SHA7}-1 right"])
    authors = AUTHORS
    if case == "no list":
        (src.path / "issues-agk-shadow.json").unlink()
    elif case == "two issues":
        src.write(
            "issues-agk-shadow", [{"number": 40, "state": "open"}, {"number": 41, "state": "open"}]
        )
    elif case == "no comments":
        (src.path / "comments-40.json").unlink()
    else:
        authors = []
    assert facts.shadow_section(src.api, items, authors) == "unknown"


def test_a_refused_mark_is_unknown_not_a_guess(src):
    """Rule 3: a mark that names no finding is refused; the report then says `unknown`."""
    assert facts.shadow_section(src.api, reviewed(src, [f"C{SHA7}-9 right"]), AUTHORS) == "unknown"


def test_a_merged_pull_request_whose_comments_cannot_be_read_is_counted_unread(src):
    items = reviewed(src, [f"C{SHA7}-1 right"])
    items[8] = (pull(8), None)
    section = facts.shadow_section(src.api, items, AUTHORS)
    assert section["unread"] == 1 and section["total"]["right_conductor_only"] == 1


def test_a_shadow_comment_that_matches_no_verdict_is_unpaired(src):
    src.issue()
    src.write("comments-40", [shadow(pr=99)])
    section = facts.shadow_section(src.api, kept((pull(), [verdict()])), AUTHORS)
    assert section["unpaired"] == 1 and section["total"]["heads"] == 0


def test_pulls_section_keeps_the_comments_of_the_merged_pull_requests_only(src):
    """The one fetch of the comments of a merged pull request serves the flow and the shadow."""
    from datetime import date

    src.write("pulls-open", [])
    src.write(
        "pulls",
        [
            {**pull(7), "state": "closed", "closed_at": WEEK, "created_at": WEEK, "body": "x"},
            {
                **pull(8, None),
                "state": "closed",
                "closed_at": WEEK,
                "created_at": WEEK,
                "body": "x",
            },
        ],
    )
    src.write("comments-7", [verdict()])
    src.write("comments-8", [verdict()])
    keep: dict = {}
    facts.pulls_section(src.api, date(2026, 10, 26), 8, AUTHORS, None, None, keep)
    assert sorted(keep) == [7]
    assert keep[7][0]["number"] == 7 and keep[7][1] == [verdict()]


def test_the_facts_of_a_repository_without_saved_issues_say_unknown(tmp_path):
    from test_facts import document

    assert document("flow", tmp_path)["shadow"] == "unknown"
