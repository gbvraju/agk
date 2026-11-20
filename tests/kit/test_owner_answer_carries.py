"""An owner's answer stays answered (brief #1616, ADR-0685; REQ-066).

A `Maintainer answer: Q-<id>` or `Answer: Q-<id>` by an answerer closes every open owner item that
names that id, an `Owner needed:` keyed `owner-needed` included (its first line or its body). An
`accept <old>` closes the items when OLD is the current head, or when every first-parent step from
OLD to the head is a light merge of the default branch (`session_plan.light_merge`), read through
the `carried` check the callers with a checkout pass. A read that fails is no carry. The replays use
invented logins and shas; the git trees live in `tmp_path`; no network.
"""

from __future__ import annotations

import inspect
import os
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "agk"))

import conductor  # noqa: E402
import route  # noqa: E402
import session  # noqa: E402
import steward_owner  # noqa: E402

NOW = datetime(2026, 11, 20, 15, 0, tzinfo=UTC)
LISTED = {"conductor-example"}
ANSWERERS = {"conductor-example", "owner-example"}
PLAIN = {"minutes": 30, "rest": None, "offset": 0}
HEAD = "c" * 40
OLD = "b" * 40
GIT_ENV = {
    "GIT_AUTHOR_NAME": "Example",
    "GIT_AUTHOR_EMAIL": "example@example.com",
    "GIT_COMMITTER_NAME": "Example",
    "GIT_COMMITTER_EMAIL": "example@example.com",
}
LINES = "".join(f"# line {i}\n" for i in range(1, 6))
SCRIPT = "scripts/agk/example.py"


def at(cid: int, login: str, body: str, minutes: float) -> dict:
    when = (NOW - timedelta(minutes=minutes)).strftime("%Y-%m-%dT%H:%M:%SZ")
    return {"id": cid, "user": {"login": login}, "body": body, "created_at": when}


def pull(head: str = HEAD, labels: tuple = ()) -> dict:
    return {
        "number": 7,
        "user": {"login": "builder-example"},
        "created_at": "2026-11-20T08:00:00Z",
        "head": {"sha": head},
        "labels": [{"name": n} for n in labels],
    }


def items(comments: list, head: str = HEAD, carried=None) -> dict:
    return session.open_owner_items(pull(head), comments, LISTED, ANSWERERS, carried=carried)


# --- answer 1: a Q id answer closes every item that names it ------------------------------------


def test_1616_replay_1572_an_answer_closes_the_owner_needed_that_names_it():
    """REQ-066: #1572 was parked again after `Maintainer answer: Q-1567-1`: now nothing is open."""
    said = [
        at(1, "conductor-example", "Owner needed: Q-1567-1 decides whether the take counts", 70),
        at(2, "owner-example", "Maintainer answer: Q-1567-1 a take older than the ask ends", 40),
    ]
    assert items(said) == {}
    assert session.owner_step(pull(), said, PLAIN, NOW, LISTED, ANSWERERS) is None


def test_1616_replay_1609_no_second_park_after_the_unpark():
    """REQ-066: #1609 was unparked for Q-1586-4 and parked for `owner-needed` 28 seconds later."""
    said = [
        at(1, "conductor-example", "Owner needed: the scope\n\nIt waits on Q-1586-4.", 90),
        at(2, "builder-example", "Question: Q-1586-4 for the maintainers: which scope?", 80),
        at(3, "conductor-example", "Parked-by: wait Q-1586-4", 45),
        at(4, "owner-example", "Maintainer answer: Q-1586-4 the narrow scope", 10),
    ]
    parked = pull(labels=("agk:parked",))
    assert session.owner_step(parked, said, PLAIN, NOW, LISTED, ANSWERERS) == (
        "unpark",
        "Q-1586-4",
    )
    after = [*said, at(5, "conductor-example", "Unparked-by: answer Q-1586-4", 9)]
    assert session.owner_step(pull(), after, PLAIN, NOW, LISTED, ANSWERERS) is None


def test_1616_an_answer_to_another_id_closes_nothing():
    """REQ-066: brief #1534 answer 3 holds: `Answer: Q-7-2` leaves the ask for Q-7-1."""
    said = [
        at(1, "conductor-example", "Owner needed: Q-7-1 decides the runtime", 70),
        at(2, "owner-example", "Answer: Q-7-2 the north", 40),
    ]
    assert set(items(said)) == {"owner-needed"}


def test_1616_a_q_id_named_only_in_the_body_is_closed_by_its_answer():
    """REQ-066: edge 5."""
    said = [
        at(1, "conductor-example", "Owner needed: one ruling\n\nSee Q-7-3 above.", 70),
        at(2, "owner-example", "Answer: Q-7-3 yes", 40),
    ]
    assert items(said) == {}


def test_1616_an_answer_by_someone_not_an_answerer_closes_nothing():
    said = [
        at(1, "conductor-example", "Owner needed: Q-7-1 decides the runtime", 70),
        at(2, "builder-example", "Maintainer answer: Q-7-1 yes", 40),
    ]
    assert set(items(said)) == {"owner-needed"}


def test_1616_an_owner_needed_posted_after_the_answer_is_open_again():
    """REQ-066: edge 4, for an answer and for an accept."""
    said = [
        at(1, "conductor-example", "Owner needed: Q-7-1 decides the runtime", 70),
        at(2, "owner-example", "Maintainer answer: Q-7-1 yes", 40),
        at(3, "conductor-example", "Owner needed: Q-7-1 again, for the new scope", 20),
    ]
    assert set(items(said)) == {"owner-needed"}
    accepted = [
        at(1, "owner-example", f"Maintainer answer: accept {HEAD}", 50),
        at(2, "conductor-example", "Owner needed: accept the evidence", 20),
    ]
    assert set(items(accepted, carried=lambda old, head: True)) == {"owner-needed"}


def test_1616_a_correction_keeps_todays_rule():
    """REQ-066: edge 6: a `Correction:` closes the Q id items of its body, nothing more."""
    said = [
        at(1, "builder-example", "Question: Q-7-1 for the maintainers: which runtime?", 80),
        at(2, "conductor-example", "Owner needed: accept the evidence", 70),
        at(3, "owner-example", "Correction: Q-7-1 is withdrawn", 40),
    ]
    assert set(items(said)) == {"owner-needed"}


# --- answer 2: an accept carries over light merges ----------------------------------------------


def accept_ask() -> list:
    return [
        at(1, "conductor-example", "Owner needed: accept the evidence of the head", 90),
        at(2, "owner-example", f"Maintainer answer: accept {OLD}", 60),
    ]


def test_1616_an_accept_carries_only_when_the_check_holds():
    """REQ-066: answer 2: exact head, a carried head, and no check at all (today's rule)."""
    assert items(accept_ask(), head=OLD) == {}
    assert set(items(accept_ask())) == {"owner-needed"}
    asked: list = []

    def carried(old, head):
        asked.append((old, head))
        return True

    assert items(accept_ask(), carried=carried) == {}
    assert asked == [(OLD, HEAD)]
    assert set(items(accept_ask(), carried=lambda old, head: False)) == {"owner-needed"}


def test_1616_a_check_that_raises_is_no_carry():
    """REQ-066: answer 2: a read that fails is False."""

    def broken(old, head):
        raise OSError("unreadable")

    assert set(items(accept_ask(), carried=broken)) == {"owner-needed"}


def test_1616_owner_apply_hands_the_check_to_every_step(monkeypatch):
    """REQ-066: answer 2: the fresh read decides with the caller's check."""
    said = [*accept_ask(), at(3, "conductor-example", "Parked-by: wait owner-needed", 30)]
    parked = pull(labels=("agk:parked",))
    monkeypatch.setattr(session, "owner_read", lambda repo, n: (parked, list(said)))
    monkeypatch.setattr(session, "owner_own", lambda *a, **k: False)
    writes: list = []
    monkeypatch.setattr(session, "unpark_pull", lambda *a, **k: writes.append(a) or True)
    found = session.owner_apply("example/agk", 7, PLAIN, LISTED, ANSWERERS, NOW)
    assert found is None and writes == []
    found = session.owner_apply(
        "example/agk", 7, PLAIN, LISTED, ANSWERERS, NOW, carried=lambda o, h: (o, h) == (OLD, HEAD)
    )
    assert found == ("unpark", "owner-needed") and len(writes) == 1


def test_1616_every_caller_with_a_checkout_passes_the_check():
    """REQ-066: answer 2: the conductor's two passes, the steward, `watch` and the router."""
    for function in (conductor.owner_pass, steward_owner.unpark, steward_owner.park,
                     session.owner_park, route.owner_unpark):  # fmt: skip
        text = inspect.getsource(function)
        assert "owner_apply(" in text and "carried=" in text, function.__name__
    text = inspect.getsource(conductor)
    assert text.count("carried=session.carried_check(") >= 2


def test_1616_the_merger_evidence_accept_stays_exact():
    """REQ-066: answer 3 and the maintainer answer to Q-1616-1: no carry in the merger."""
    import merge_cleared

    assert "carried" not in inspect.getsource(merge_cleared.answered)


# --- the git-backed check -----------------------------------------------------------------------


def git(root: Path, *args: str) -> str:
    return subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
        ["git", *args], cwd=root, capture_output=True, text=True, check=True,
        env={**os.environ, **GIT_ENV},
    ).stdout.strip()  # fmt: skip


def commit(root: Path, files: dict, message: str) -> str:
    for name, text in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", message)
    return git(root, "rev-parse", "HEAD")


def edit(line: int, word: str, text: str = LINES) -> str:
    return text.replace(f"line {line}\n", f"{word}\n")


def merge_main(root: Path, head: str) -> str:
    git(root, "checkout", "-q", "--detach", head)
    git(root, "merge", "-q", "--no-ff", "--no-edit", "main")
    sha = git(root, "rev-parse", "HEAD")
    git(root, "checkout", "-q", "main")
    git(root, "update-ref", "refs/remotes/origin/main", "main")
    return sha


def tree(tmp_path: Path, head_files: dict, main_files: dict) -> tuple[Path, str]:
    """The saved tree of #1576: a branch and main each change the shared base: (root, head)."""
    root = tmp_path / "work"
    root.mkdir(parents=True)
    git(root, "init", "-q", "-b", "main")
    commit(root, {"agk.toml": LINES, SCRIPT: LINES, "docs/example.md": "a\n"}, "base")
    git(root, "checkout", "-q", "-b", "feature")
    head = commit(root, {**head_files, "docs/feature.md": "the feature\n"}, "feature")
    git(root, "checkout", "-q", "main")
    commit(root, main_files, "main")
    return root, head


def carries(root: Path, old: str, head: str) -> bool:
    return session.carried_check(root)(old, head)


def test_1616_replay_1576_an_accept_of_the_pre_merge_head_carries_to_its_light_merge(tmp_path):
    """REQ-066: #1576: the accept of 3e545b21 and the merge of main e5ec9668 parked it again."""
    root, head = tree(tmp_path, {"agk.toml": edit(1, "branch")}, {"agk.toml": edit(5, "main")})
    merged = merge_main(root, head)
    assert carries(root, head, merged)
    said = [
        at(1, "conductor-example", "Owner needed: accept the evidence", 90),
        at(2, "owner-example", f"Maintainer answer: accept {head}", 60),
    ]
    assert items(said, head=merged, carried=session.carried_check(root)) == {}
    assert set(items(said, head=merged)) == {"owner-needed"}


def test_1616_two_merges_of_main_in_a_row_carry_step_by_step(tmp_path):
    """REQ-066: edge 3."""
    root, head = tree(tmp_path, {"agk.toml": edit(1, "branch")}, {"agk.toml": edit(5, "main")})
    first = merge_main(root, head)
    commit(root, {"agk.toml": edit(3, "again", edit(5, "main"))}, "main again")
    second = merge_main(root, first)
    assert carries(root, head, second) and carries(root, first, second)


@pytest.mark.parametrize("case", ["own-file", "conflict", "unreadable", "not-ancestor"])
def test_1616_no_carry_when_the_merge_adds_anything_or_cannot_be_read(tmp_path, case):
    """REQ-066: edges 1 and 2, and answer 2's failed read."""
    head_files, main_files = {"agk.toml": edit(1, "branch")}, {"agk.toml": edit(5, "main")}
    if case == "own-file":
        head_files[SCRIPT], main_files[SCRIPT] = edit(1, "branch"), edit(5, "main")
    if case == "conflict":
        main_files = {"agk.toml": edit(1, "main")}
    root, head = tree(tmp_path, head_files, main_files)
    if case == "conflict":
        git(root, "checkout", "-q", "--detach", head)
        git(root, "merge", "-q", "-s", "ours", "--no-edit", "main")
        merged = git(root, "rev-parse", "HEAD")
        git(root, "checkout", "-q", "main")
        git(root, "update-ref", "refs/remotes/origin/main", "main")
    else:
        merged = merge_main(root, head)
    old = head
    if case == "unreadable":
        old, merged = "d" * 40, "e" * 40
    if case == "not-ancestor":
        old = git(root, "rev-parse", "main")
    assert not carries(root, old, merged)
    assert not carries(tmp_path / "nowhere", head, merged)
