"""The merger lifts the router's approval hold for a settled amendment only with the setting on.

Brief #1957 (ADR-0813) answer 3, amendment 252 (SPEC-0039 rule 5): with `[steward]
settle_amendments = true` on the checkout read, a pull request labelled `agk:approve` whose every
open approval ask names an amendment that a steward's settled line (by an account in
`spec_approvers`, `Who: AGK steward`) settles after the ask is not held as `spec approval`; a
spec approval ask, an unsettled amendment or the setting off still holds. Unit by unit, files
only; invented logins, no network.
"""

from __future__ import annotations

import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
from pathlib import Path

from test_amendment_class import CORRECTION, amendment, project

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts" / "agk"
sys.path.insert(0, str(SCRIPTS))

import check_amendments as ca  # noqa: E402
import merge_cleared  # noqa: E402

PATH = "docs/runs/proposed-spec-amendments-900.md"
LABELLED = {"labels": [{"name": "agk:approve"}], "body": ""}


def at(cid: int, login: str, body: str, when: str) -> dict:
    return {"id": cid, "user": {"login": login}, "body": body, "created_at": when}


def asked(line: str = "Maintainer answer: amendment 900 approved") -> dict:
    return at(4, "boss", f"Owner needed: post:\n\n`{line}`", "2026-11-25T10:05:00Z")


def git(root: Path, *args: str) -> str:
    return subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
        ["git", "-c", "user.name=t", "-c", "user.email=t@example.com", *args],
        cwd=root,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()


def checkout(tmp_path: Path, on: bool = True, text: str | None = None) -> tuple[Path, str]:
    """A git checkout whose head holds amendment 900 (TEXT, a correction by default)."""
    tmp_path.mkdir(parents=True, exist_ok=True)
    root = project(tmp_path, on=on)
    (root / "docs" / "runs").mkdir(parents=True, exist_ok=True)
    (root / PATH).write_text(text or amendment(CORRECTION), encoding="utf-8")
    git(root, "init", "-q")
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "x")
    return root, git(root, "rev-parse", "HEAD")


def settled(number: int = 900, login: str = "owner", text: str | None = None) -> dict:
    line = ca.SETTLED_FORM.format(number, "pins.py:41", "correction", "SPEC-0072 rule 4")
    line += f"\nText: {ca.digest(text or amendment(CORRECTION))}"
    return at(6, login, f"{line}\n\n{ca.WHO}", "2026-11-25T10:20:00Z")


def held(root: Path | None, comments: list[dict], sha: str = "") -> bool:
    return merge_cleared.unapproved(LABELLED, comments, sha, ["owner"], root, 7)


def test_req066_the_merger_holds_without_the_setting_and_merges_with_it(tmp_path):
    root, sha = checkout(tmp_path, on=False)
    assert held(root, [asked(), settled()], sha)
    assert held(None, [asked(), settled()], sha)
    project(root, on=True)
    assert not held(root, [asked(), settled()], sha)
    assert held(root, [asked(), settled()], "")  # no head to read the amendment at


def test_req066_an_unsettled_or_spec_ask_still_holds(tmp_path):
    root, sha = checkout(tmp_path)
    assert held(root, [asked()], sha)
    assert held(root, [asked(), settled(number=901)], sha)
    assert held(root, [asked(), settled(login="stranger")], sha)
    assert held(root, [asked("Approve: SPEC-0072"), settled()], sha)
    assert held(root, [settled(), asked()], sha)  # a line before the ask settles nothing
    plain = at(5, "boss", "Owner needed: a size ruling", "2026-11-25T10:06:00Z")
    assert held(root, [asked(), plain, settled()], sha)  # fix list item 1


def test_req066_a_behaviour_or_edited_amendment_at_the_head_holds(tmp_path):
    """Fix list items 2 and 4: the text at the head decides, by class and by digest."""
    behaviour = amendment("Adds a step.\n   Class: behaviour")
    root, sha = checkout(tmp_path, text=behaviour)
    assert held(root, [asked(), settled(text=behaviour)], sha)
    root, sha = checkout(tmp_path / "two")
    (root / PATH).write_text(amendment(CORRECTION, "Reuse it.\n   Class: implementation"), "utf-8")
    git(root, "commit", "-qam", "edit")
    assert held(root, [asked(), settled()], git(root, "rev-parse", "HEAD"))


def test_req066_the_shared_reading_names_the_settled_amendments():
    comments = [asked(), settled(), settled(number=900)]
    settles = {"amendment 900": ca.digest(amendment(CORRECTION))}
    assert ca.settled_keys(comments, ["owner"], settles) == {"amendment 900"}
    assert ca.settled_keys(comments, ["owner"], {}) == set()
    assert ca.asked_keys(comments) == {"amendment 900"}
