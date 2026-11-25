"""The router reads the steward's settled line as an approval only with the setting on.

Brief #1957 (ADR-0813) answers 3 and 7: `Answer: amendment <n> settled (...)` by an account in
`spec_approvers`, carrying `Who: AGK steward`, closes the approval ask of amendment <n> when the
facts say `[steward] settle_amendments` is on; otherwise it approves nothing and the ask stays.
`Maintainer answer: amendment <n> approved` keeps working. Saved facts only; invented data.
"""

from __future__ import annotations

import sys
from pathlib import Path

from test_route import HEAD, facts  # noqa: F401

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts" / "agk"
sys.path.insert(0, str(SCRIPTS))

import check_amendments as ca  # noqa: E402
import route  # noqa: E402

FILES = [{"filename": "docs/runs/proposed-spec-amendments-900.md"}]
PUSHED = {"commit": {"committer": {"date": "2026-11-25T10:00:00Z"}}}


def at(cid: int, login: str, body: str, when: str) -> dict:
    return {"id": cid, "user": {"login": login}, "body": body, "created_at": when}


def asked(number: int = 900) -> dict:
    line = f"`Maintainer answer: amendment {number} approved`"
    return at(4, "boss", f"Owner needed: post:\n\n{line}", "2026-11-25T10:05:00Z")


def cleared() -> dict:
    return at(5, "boss", f"Verdict: cleared {HEAD[:7]}", "2026-11-25T10:10:00Z")


def settled(number: int = 900, login: str = "maintainer", who: bool = True) -> dict:
    line = ca.SETTLED_FORM.format(number, "pins.py:41", "correction", "SPEC-0072 rule 4")
    return at(6, login, line + (f"\n\n{ca.WHO}" if who else ""), "2026-11-25T10:20:00Z")


def state(comments: list[dict], on: bool | None) -> str:
    extra = {} if on is None else {"settle": on}
    return route.decide(facts(comments=comments, commit=PUSHED, files=FILES, **extra))


def test_req066_a_settled_line_closes_the_ask_with_the_setting_on():
    assert state([asked(), cleared(), settled()], True) == "agk:merge-ready"


def test_req066_the_same_line_approves_nothing_with_the_setting_off():
    assert state([asked(), cleared(), settled()], False) == "agk:approve"
    assert state([asked(), cleared(), settled()], None) == "agk:approve"


def test_req066_only_a_spec_approver_with_the_steward_marker_settles():
    assert state([asked(), cleared(), settled(login="stranger")], True) == "agk:approve"
    assert state([asked(), cleared(), settled(who=False)], True) == "agk:approve"


def test_req066_a_settled_line_for_another_amendment_closes_nothing():
    assert state([asked(), cleared(), settled(number=901)], True) == "agk:approve"


def test_req066_the_owner_line_still_approves():
    answer = at(
        6, "maintainer", "Maintainer answer: amendment 900 approved", "2026-11-25T10:20:00Z"
    )
    for on in (True, False):
        assert state([asked(), cleared(), answer], on) == "agk:merge-ready"


def test_req066_the_facts_carry_the_setting(tmp_path):
    (tmp_path / "agk.toml").write_text('default_branch = "main"\n', encoding="utf-8")
    assert route.settle_setting(tmp_path) is False
