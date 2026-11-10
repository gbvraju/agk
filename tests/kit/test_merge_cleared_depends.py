"""merge_cleared.py reads `Depends-on: #n` only from a line of its own (brief #991, REQ-046).

SPEC-0039 rule 5's dependence hold, covered by ADR-0265. `dependence_unmet` reads a pull
request's `Depends-on: #n` only where a stripped line of the body is exactly that line, the same
reading as `check_pr_mode.py` (rule 5); a mention inside a sentence or backticks is no dependence.
The REST reads are replaced by a saved world of invented issues and pull requests. No network.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts" / "agk"
sys.path.insert(0, str(SCRIPTS))

import check_pr_mode  # noqa: E402
import merge_cleared  # noqa: E402

REPO = "example/agk"

# Invented records: #7 an open brief, #8 a merged pull request, #842 an open brief.
ISSUES = {
    7: {"number": 7, "state": "open", "state_reason": None},
    8: {"number": 8, "state": "closed", "pull_request": {"url": "https://example.com/8"}},
    842: {"number": 842, "state": "open", "state_reason": None},
}
PULLS = {8: {"number": 8, "merged_at": "2026-11-01T00:00:00Z"}}

SENTENCE = "Brief: #900\nNo `Depends-on:` line: the brief names `Depends-on: #842` later.\n"
OPEN_BRIEF = "Brief: #900\nDepends-on: #7\n"
MERGED_PULL = "Brief: #900\n  Depends-on: #8  \n"
CASES = [(SENTENCE, False), (OPEN_BRIEF, True), (MERGED_PULL, False)]


@pytest.fixture
def world(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    reads: list[str] = []

    def read_json(endpoint: str, kind: type, what: str) -> object:
        reads.append(endpoint)
        number = int(endpoint.rsplit("/", 1)[1])
        source = PULLS if "/pulls/" in endpoint else ISSUES
        return source[number]

    monkeypatch.setattr(merge_cleared, "read_json", read_json)
    return reads


def held(body: str) -> bool:
    return merge_cleared.dependence_unmet(REPO, {"number": 900, "body": body})


def record(number: int) -> dict:
    """The record `check_pr_mode.py` reads for NUMBER, as the workflow writes it."""
    item = ISSUES[number]
    if "pull_request" in item:
        return {"pull_request": True, "merged": bool(PULLS[number].get("merged_at"))}
    return {"pull_request": False, "state": item["state"], "state_reason": item["state_reason"]}


def mode_check_holds(body: str, tmp_path: Path) -> bool:
    path = tmp_path / "body.md"
    path.write_text(body, encoding="utf-8")
    named = check_pr_mode.depends_on(path)
    return any(check_pr_mode.unmet(record(n)) is not None for n in named)


def test_a_mention_inside_a_sentence_is_not_held(world: list[str]) -> None:
    """REQ-046: brief #991 answer 1, test (a)."""
    assert held(SENTENCE) is False
    assert world == []


def test_a_whole_line_naming_an_open_brief_is_held(world: list[str]) -> None:
    """REQ-046: brief #991 answer 2, test (b)."""
    assert held(OPEN_BRIEF) is True
    assert world == [f"repos/{REPO}/issues/7"]


def test_a_whole_line_naming_a_merged_pull_request_is_not_held(world: list[str]) -> None:
    """REQ-046: brief #991 answer 2, test (c)."""
    assert held(MERGED_PULL) is False
    assert world == [f"repos/{REPO}/issues/8", f"repos/{REPO}/pulls/8"]


@pytest.mark.parametrize(("body", "expected"), CASES)
def test_the_merge_and_the_mode_check_agree(
    world: list[str], tmp_path: Path, body: str, expected: bool
) -> None:
    """REQ-046: brief #991 answer 3, test (d)."""
    assert held(body) is expected
    assert mode_check_holds(body, tmp_path) is expected
