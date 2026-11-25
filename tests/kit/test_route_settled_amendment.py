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
DIGEST = "0123456789abcdef"  # the amendment's text at the head, as `amendment_settles` reads it
PUSHED = {"commit": {"committer": {"date": "2026-11-25T10:00:00Z"}}}


def at(cid: int, login: str, body: str, when: str) -> dict:
    return {"id": cid, "user": {"login": login}, "body": body, "created_at": when}


def asked(number: int = 900) -> dict:
    line = f"`Maintainer answer: amendment {number} approved`"
    return at(4, "boss", f"Owner needed: post:\n\n{line}", "2026-11-25T10:05:00Z")


def cleared() -> dict:
    return at(5, "boss", f"Verdict: cleared {HEAD[:7]}", "2026-11-25T10:10:00Z")


def settled(
    number: int = 900, login: str = "maintainer", who: bool = True, text: str = DIGEST
) -> dict:
    line = ca.SETTLED_FORM.format(number, "pins.py:41", "correction", "SPEC-0072 rule 4")
    line += f"\nText: {text}"
    return at(6, login, line + (f"\n\n{ca.WHO}" if who else ""), "2026-11-25T10:20:00Z")


def state(comments: list[dict], on: bool | None, settles: dict | None = None) -> str:
    extra = {} if on is None else {"settle": on}
    held = {"amendment 900": DIGEST} if settles is None else settles
    f = facts(comments=comments, commit=PUSHED, files=FILES, settles=held, **extra)
    return route.decide(f)


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


def test_req066_a_behaviour_or_edited_amendment_is_not_settled():
    """Fix list items 2 and 4: only an amendment settleable at the head, with the line's digest."""
    assert state([asked(), cleared(), settled()], True, settles={}) == "agk:approve"
    assert state([asked(), cleared(), settled(text="f" * 16)], True) == "agk:approve"


def test_req066_a_settled_line_leaves_other_asks_and_questions_open():
    """Fix list item 1: its own approval only; a question or a plain ask stays open."""
    question = at(3, "builder", "Question: Q-1957-9 for the maintainers: x", "2026-11-25T10:06:00Z")
    assert state([asked(), question, cleared(), settled()], True) == "agk:question"
    plain = at(7, "boss", "Owner needed: a size ruling", "2026-11-25T10:07:00Z")
    assert state([asked(), plain, cleared(), settled()], True) == "agk:question"
    with_id = at(
        4,
        "boss",
        "Owner needed: Q-1957-8 and\n\n`Maintainer answer: amendment 900 approved`",
        "2026-11-25T10:05:00Z",
    )
    assert state([with_id, cleared(), settled()], True) == "agk:question"
    two = at(
        4,
        "boss",
        "Owner needed: post:\n\n`Maintainer answer: amendment 900 approved`\n"
        "`Maintainer answer: amendment 901 approved`",
        "2026-11-25T10:05:00Z",
    )
    files = [*FILES, {"filename": "docs/runs/proposed-spec-amendments-901.md"}]
    f = facts(
        comments=[two, cleared(), settled()],
        commit=PUSHED,
        files=files,
        settle=True,
        settles={"amendment 900": DIGEST},
    )
    assert route.decide(f) == "agk:approve"


def test_req066_the_router_reads_the_amendment_at_the_head(tmp_path, monkeypatch):
    """Fix list item 2: one GET of each changed amendment at the head, only with the setting on."""
    import base64

    from test_amendment_class import CORRECTION, amendment, project

    root = project(tmp_path, on=True)
    text = amendment(CORRECTION)
    calls = []

    def fake(path: str):
        calls.append(path)
        return {"content": base64.b64encode(text.encode()).decode()}

    monkeypatch.setattr(route, "gh", fake)
    files = [{"filename": "docs/runs/proposed-spec-amendments-900.md", "status": "added"}]
    assert route.amendment_settles("o/r", files, HEAD, root) == {"amendment 900": ca.digest(text)}
    assert calls == [f"repos/o/r/contents/docs/runs/proposed-spec-amendments-900.md?ref={HEAD}"]
    project(tmp_path, on=False)
    assert route.amendment_settles("o/r", files, HEAD, root) == {}
