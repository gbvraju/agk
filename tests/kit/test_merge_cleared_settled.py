"""The merger lifts the router's approval hold for a settled amendment only with the setting on.

Brief #1957 (ADR-0813) answer 3, amendment 252 (SPEC-0039 rule 5): with `[steward]
settle_amendments = true` on the checkout read, a pull request labelled `agk:approve` whose every
open approval ask names an amendment that a steward's settled line (by an account in
`spec_approvers`, `Who: AGK steward`) settles after the ask is not held as `spec approval`; a
spec approval ask, an unsettled amendment or the setting off still holds. Unit by unit, files
only; invented logins, no network.
"""

from __future__ import annotations

import sys
from pathlib import Path

from test_amendment_class import project

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts" / "agk"
sys.path.insert(0, str(SCRIPTS))

import check_amendments as ca  # noqa: E402
import merge_cleared  # noqa: E402

HEAD = "a" * 40
LABELLED = {"labels": [{"name": "agk:approve"}], "body": ""}


def at(cid: int, login: str, body: str, when: str) -> dict:
    return {"id": cid, "user": {"login": login}, "body": body, "created_at": when}


def asked(line: str = "Maintainer answer: amendment 900 approved") -> dict:
    return at(4, "boss", f"Owner needed: post:\n\n`{line}`", "2026-11-25T10:05:00Z")


def settled(number: int = 900, login: str = "owner") -> dict:
    line = ca.SETTLED_FORM.format(number, "pins.py:41", "correction", "SPEC-0072 rule 4")
    return at(6, login, f"{line}\n\n{ca.WHO}", "2026-11-25T10:20:00Z")


def held(root: Path | None, comments: list[dict]) -> bool:
    return merge_cleared.unapproved(LABELLED, comments, HEAD, ["owner"], root, 7)


def test_req066_the_merger_holds_without_the_setting_and_merges_with_it(tmp_path):
    assert held(project(tmp_path, on=False), [asked(), settled()])
    assert held(None, [asked(), settled()])
    assert not held(project(tmp_path, on=True), [asked(), settled()])


def test_req066_an_unsettled_or_spec_ask_still_holds(tmp_path):
    root = project(tmp_path, on=True)
    assert held(root, [asked()])
    assert held(root, [asked(), settled(number=901)])
    assert held(root, [asked(), settled(login="stranger")])
    assert held(root, [asked("Approve: SPEC-0072"), settled()])
    assert held(root, [settled(), asked()])  # a line before the ask settles nothing


def test_req066_the_shared_reading_names_the_settled_amendments():
    comments = [asked(), settled(), settled(number=900)]
    assert ca.settled_keys(comments, ["owner"]) == {"amendment 900"}
    assert ca.asked_keys(comments) == {"amendment 900"}
