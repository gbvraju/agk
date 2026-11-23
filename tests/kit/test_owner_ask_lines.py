"""Every wait on the owner names the one line that ends it (brief #1784, ADR-0747; REQ-037).

`session.closing_line(key, pr, comments)` is the one source of the line that closes each kind of
owner item, and `session.py ask-lines --pr N` prints it for each open item. The tests feed each
line back into `open_owner_items`, which is the contract that stops a free-text ask returning:
#1762's `Size accepted.` closed nothing. `conductor.py check-verdict --pr N` refuses an `Owner
needed:` that holds no such line. Invented logins; the shas are the recorded ones; no network.
"""

from __future__ import annotations

import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "agk"))

import conductor  # noqa: E402
import route  # noqa: E402
import session  # noqa: E402

NOW = datetime(2026, 11, 23, 1, 0, tzinfo=UTC)
LISTED = {"conductor-example"}
ANSWERERS = {"conductor-example", "owner-example"}
HEAD_1762 = "4a3ef2375e606bf5d854663c2f7678f9560973fb"
ACCEPT_1762 = f"Maintainer answer: accept {HEAD_1762}"
REFUSED = "refused: an Owner needed: names no line that closes it (setting: Owner needed:)"


def at(cid: int, login: str, body: str, minutes: float) -> dict:
    when = (NOW - timedelta(minutes=minutes)).strftime("%Y-%m-%dT%H:%M:%SZ")
    return {"id": cid, "user": {"login": login}, "body": body, "created_at": when}


def pull(head: str = HEAD_1762, labels: tuple = (), number: int = 1762) -> dict:
    return {
        "number": number,
        "user": {"login": "builder-example"},
        "created_at": "2026-11-22T08:00:00Z",
        "head": {"sha": head},
        "labels": [{"name": n} for n in labels],
        "draft": False,
    }


def items(pr: dict, comments: list) -> dict:
    return session.open_owner_items(pr, comments, LISTED, ANSWERERS)


def answered(pr: dict, comments: list, key: str) -> dict:
    """The items after the owner posts `closing_line(key)` as a new comment."""
    line = session.closing_line(key, pr, comments)
    return items(pr, [*comments, at(99, "owner-example", line, 0)])


SIZE_ASK_1762 = at(
    1,
    "conductor-example",
    "Owner needed: the change is larger than the standing size limit; say so in a comment here "
    "(for example `Size accepted`).",
    250,
)


# --- answer 1: one line per kind, and that line closes its item ----------------------------------


def test_1784_a_question_id_item_is_closed_by_its_line():
    """REQ-037: a `Question:` for the maintainers is closed by `Maintainer answer: Q-<id> ...`."""
    said = [at(1, "builder-example", "Question: Q-7-1 for the maintainers: which runtime?", 90)]
    assert set(items(pull(), said)) == {"Q-7-1"}
    assert session.closing_line("Q-7-1", pull(), said) == "Maintainer answer: Q-7-1 <your answer>"
    assert answered(pull(), said, "Q-7-1") == {}


def test_1784_a_not_blocking_item_is_closed_by_its_question_line():
    """REQ-037: an `nb:<Q-id>` item takes the same answer line as its question."""
    assert session.closing_line("nb:Q-7-1", pull(), []) == "Maintainer answer: Q-7-1 <your answer>"


def test_1784_an_owner_needed_item_is_closed_by_the_accept_of_the_head():
    """REQ-037: #1762: the size ask is closed by the accept of the full head sha, nothing else."""
    said = [SIZE_ASK_1762, at(2, "owner-example", "Size accepted.", 12)]
    assert set(items(pull(), said)) == {"owner-needed"}  # the free word closed nothing
    assert session.closing_line("owner-needed", pull(), said) == ACCEPT_1762
    assert answered(pull(), said, "owner-needed") == {}


def test_1784_an_approval_item_names_the_offered_approval_line():
    """REQ-037: the router's `agk:approve` names the approval line the comments offer, the form
    `route.APPROVAL_LINE` reads, which the router's own answer reader takes as the approval."""
    said = [at(1, "conductor-example", 'Approval: SPEC-0042 x Draft -> Approved, waiting for a '
                'person: post "Approve: SPEC-0042"', 30)]  # fmt: skip
    line = session.closing_line("approve", pull(labels=("agk:approve",)), said)
    assert line == "Approve: SPEC-0042"
    assert route.APPROVAL_LINE.fullmatch(line) and route.APPROVAL_ANSWER.match(line)


def test_1784_a_merge_item_names_the_owners_merge_command():
    """REQ-037: an `owner-merge` item names `merge_cleared.OWNER_COMMAND` of the number."""
    line = session.closing_line("owner-merge", pull(), [])
    assert line == "python3 scripts/agk/merge_cleared.py --pr 1762 --owner"


# --- ask-lines -----------------------------------------------------------------------------------


@pytest.fixture
def reads(monkeypatch):
    def make(pr: dict, comments: list):
        monkeypatch.setattr(session, "repo_name", lambda root: "o/r")
        monkeypatch.setattr(session, "owner_read", lambda repo, number: (pr, comments))
        monkeypatch.setattr(session, "owner_people", lambda root, pr: (LISTED, ANSWERERS))
        monkeypatch.setattr(session, "carried_check", lambda root: None)

    return make


def test_1784_ask_lines_on_1762_prints_the_accept_line(reads, capsys, tmp_path):
    """REQ-037: brief #1784 Measured: #1762's recorded size ask prints its accept line."""
    reads(pull(), [SIZE_ASK_1762, at(2, "owner-example", "Size accepted.", 12)])
    assert session.ask_lines(tmp_path, 1762) == 0
    assert capsys.readouterr().out.splitlines() == [f"owner-needed: {ACCEPT_1762}"]


def test_1784_ask_lines_prints_one_line_per_item_and_none_without_any(reads, capsys, tmp_path):
    """REQ-037: edge case 8: two items open at once give one line each; none gives `none`."""
    said = [SIZE_ASK_1762, at(2, "builder-example", "Question: Q-7-2 for the maintainers: x", 5)]
    reads(pull(), said)
    session.ask_lines(tmp_path, 1762)
    assert capsys.readouterr().out.splitlines() == [
        f"owner-needed: {ACCEPT_1762}",
        "Q-7-2: Maintainer answer: Q-7-2 <your answer>",
    ]
    reads(pull(), [])
    session.ask_lines(tmp_path, 1762)
    assert capsys.readouterr().out.strip() == "none"


def test_1784_ask_lines_is_a_command_of_session_py():
    """REQ-037: the command is named in the usage and parsed."""
    assert "ask-lines" in session.COMMANDS and "session.py ask-lines --pr N" in session.USAGE


def test_1784_an_old_head_accept_closes_nothing_and_the_new_sha_is_printed():
    """REQ-037: edge case 8: the head moves after a size ask; the old accept closes nothing."""
    new = "5" * 40
    said = [SIZE_ASK_1762, at(2, "owner-example", ACCEPT_1762, 5)]
    assert set(items(pull(head=new), said)) == {"owner-needed"}
    assert session.closing_line("owner-needed", pull(head=new), said).endswith(new)


# --- answer 2: the conductor's ask must carry its line -------------------------------------------


@pytest.fixture
def ask_reads(monkeypatch):
    def make(comments: list = ()):
        pr = pull()
        monkeypatch.setattr(conductor, "read_one", lambda endpoint, what: pr)
        monkeypatch.setattr(conductor, "read", lambda endpoint, what: list(comments))
        monkeypatch.setattr(conductor, "size_ask_problem", lambda *a: None)
        monkeypatch.setattr(session, "owner_people", lambda root, pr: (LISTED, ANSWERERS))

    return make


def test_1784_an_owner_needed_without_its_closing_line_is_refused(ask_reads):
    """REQ-037: #1762's free-text size ask is refused, naming the setting."""
    ask_reads()
    assert conductor.full_problem("o/r", 1762, SIZE_ASK_1762["body"]) == REFUSED


def test_1784_an_owner_needed_with_its_closing_line_passes(ask_reads):
    """REQ-037: the ask that ends with the `ask-lines` line, on its own line, passes."""
    ask_reads()
    body = f"Owner needed: the size is above the standing ruling.\n\n{ACCEPT_1762}\n"
    assert conductor.full_problem("o/r", 1762, body) is None
    asked = "Owner needed: Q-7-3 decides the runtime.\n\nMaintainer answer: Q-7-3 <your answer>\n"
    ask_reads([at(1, "builder-example", "Question: Q-7-3 for the maintainers: which?", 9)])
    assert conductor.full_problem("o/r", 1762, asked) is None


def test_1784_an_approval_ask_with_its_approval_line_passes(ask_reads):
    """REQ-037: an approval ask carries its code-formed approval line."""
    ask_reads()
    body = (
        "Owner needed: amendment 218 needs your yes.\n\nMaintainer answer: amendment 218 approved\n"
    )
    assert conductor.full_problem("o/r", 1762, body) is None


def test_1784_the_conductor_role_file_names_the_line_and_the_check():
    """REQ-037: answer 2: the role file has every ask end with the `ask-lines` line."""
    text = (Path(__file__).resolve().parents[2] / ".claude/agents/conductor.md").read_text()
    assert "session.py ask-lines --pr <n>" in text and "never a free-text example" in text


def test_1784_the_builder_role_file_names_the_not_blocking_form():
    """REQ-037: answer 3: the one form of a question that does not block."""
    text = (Path(__file__).resolve().parents[2] / ".claude/agents/builder.md").read_text()
    assert "Question: Q-<id> for the maintainers (not blocking): <text>" in text


# --- answer 7, personal mode (Q-1784-1, answered by the steward) --------------------------------


def test_1784_personal_mode_reads_the_sidecars_records_and_posts_nothing(
    monkeypatch, capsys, tmp_path
):
    """REQ-037: Q-1784-1: in a sidecar, `ask-lines` reads `forge/pulls/<n>.json` and
    `forge/comments-<n>.json` and prints the same lines; a plain answer line in a sidecar closes
    nothing (only what `reviewers.derived_only` derives answers); nothing is read from GitHub."""
    import json

    forge = tmp_path / "forge"
    forge.mkdir()
    (forge / "pulls").mkdir()
    (forge / "pulls" / "3.json").write_text(json.dumps(pull(number=3)), encoding="utf-8")
    said = [SIZE_ASK_1762, at(2, "owner-example", ACCEPT_1762, 5)]
    (forge / "comments-3.json").write_text(json.dumps(said), encoding="utf-8")
    monkeypatch.setattr(session, "personal_table", lambda root: {"forge": "files"})
    monkeypatch.setattr(session, "owner_people", lambda root, pr: (LISTED, ANSWERERS))
    monkeypatch.setattr(session, "agent_apps", lambda root: [])
    monkeypatch.setattr(session, "solo_person", lambda root: None)
    monkeypatch.setattr(session, "gh", lambda *a, **k: pytest.fail("no GitHub read"))
    assert session.ask_lines(tmp_path, 3) == 0
    assert capsys.readouterr().out.splitlines() == [f"owner-needed: {ACCEPT_1762}"]
    (forge / "comments-3.json").unlink()
    session.ask_lines(tmp_path, 3)
    assert capsys.readouterr().out.strip() == "none"
