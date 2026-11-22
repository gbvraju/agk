"""The one-yes approval: the steward asks about one pinned pull request head and, on the person's
clear yes, writes the exact line the kit needs (SPEC-0062 rules 13, 14 and 16; brief #1690,
ADR-0661 build (a), ADR-0703; REQ-069).

A recorded `gh` double stands in for GitHub (each call kept); no network, no model, invented data
only (example.com).
"""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "agk"))

import steward_owner  # noqa: E402

NOW = datetime(2026, 11, 22, 4, 0, tzinfo=UTC)
REPO = "acme/widgets"
HEAD = "a" * 40
MOVED = "b" * 40
LINK = "https://example.com/acme/widgets/pull/7"
ASK = "The login page is built and every check passed. Shall I approve it? I recommend yes."
AT = "2026-11-22T04:05Z"
SOLO = 'review_mode = "solo"\n'


class GitHub:
    """`session.gh` recorded: one pull request #7 at a head, open or closed."""

    def __init__(self, head: str = HEAD, state: str = "open") -> None:
        self.head, self.state, self.calls, self.bodies = head, state, [], []

    def __call__(self, endpoint: str, *extra: str, method: str = "GET"):
        self.calls.append((method, endpoint, extra))
        if method == "GET" and endpoint.endswith("/pulls/7"):
            return {"number": 7, "state": self.state, "head": {"sha": self.head}, "html_url": LINK}
        if method == "POST" and endpoint.endswith("/issues/7/comments"):
            field = extra[1]
            if field.startswith("body=@"):
                self.bodies.append(Path(field[6:]).read_text(encoding="utf-8"))
            else:
                self.bodies.append(field.split("=", 1)[1])
            return {"id": 9, "html_url": f"{LINK}#issuecomment-9"}
        raise AssertionError((method, endpoint))


@pytest.fixture
def root(tmp_path, monkeypatch):
    (tmp_path / "agk.toml").write_text(SOLO, encoding="utf-8")
    monkeypatch.setenv("AGK_STEWARD_CACHE", str(tmp_path / "state" / "memory.json"))
    monkeypatch.delenv("AGK_STEWARD_START", raising=False)
    monkeypatch.setenv("AGK_SESSION", "s1")
    monkeypatch.setattr(steward_owner.session, "repo_name", lambda root: REPO)
    records: list = []
    monkeypatch.setattr(
        steward_owner.steward,
        "record",
        lambda r, kind, text, gh: records.append((kind, text)) or (0, ["recorded"]),
    )
    gh = GitHub()
    monkeypatch.setattr(steward_owner.session, "gh", gh)
    return tmp_path, records, gh


def write(base: Path, name: str, text: str) -> Path:
    path = base / name
    path.write_bytes(text.encode("utf-8"))
    return path


def ask(base: Path, line: str, qid: str = "Q-7-1", minutes: float = 5) -> tuple[int, list[str]]:
    return steward_owner.ask_target(
        base, qid, "pr:7", ASK, write(base, f"line-{qid}.txt", line + "\n"),
        NOW - timedelta(minutes=minutes),
    )  # fmt: skip


def approve(base: Path, words: str = "Yes, go ahead.", qid: str = "Q-7-1", by=None):
    said = write(base, "said.txt", words + "\r\n")
    return steward_owner.approve(base, qid, said, AT, by, NOW)


def test_req069_the_ask_pins_the_head_and_posts_only_todays_question(root):
    """REQ-069 AC7: rule 13, the ask reads the head once, records it with its link and posts the
    one `Question:` line, nothing else."""
    base, records, gh = root
    code, lines = ask(base, f"Maintainer answer: accept {HEAD}")
    assert code == 0 and lines[0] == f"ask the person: {ASK}"
    assert gh.calls[0][:2] == ("GET", f"repos/{REPO}/pulls/7")
    assert gh.bodies == [f"Question: Q-7-1 for the maintainers: {ASK}\n\nWho: AGK steward"]
    kind, text = records[0]
    assert kind == "Owner question" and HEAD in text and LINK in text


def test_req069_a_yes_posts_the_maintainer_answer_with_its_three_closing_lines(root):
    """REQ-069 AC7: rule 13, the evidence accept on a yes, posted from a file, then a Decision."""
    base, records, gh = root
    ask(base, f"Maintainer answer: accept {HEAD}")
    code, lines = approve(base, "Yes, go ahead. Ünïcode ok")  # not a yes: words after the yes
    assert code == 1 and gh.bodies[1:] == []
    code, lines = approve(base)
    assert code == 0, lines
    body = gh.bodies[-1]
    assert gh.calls[-1][2][1].startswith("body=@")
    asked = (NOW - timedelta(minutes=5)).strftime("%Y-%m-%dT%H:%MZ")
    assert body.splitlines() == [
        f"Maintainer answer: accept {HEAD}",
        f'Owner said ({AT}): "Yes, go ahead."',
        f'Asked ({asked}): "{ASK}" {LINK}',
        "Who: ProductOwner",
    ]
    assert "\r" not in body
    assert records[-1][0] == "Decision" and "Q-7-1" in records[-1][1]
    assert approve(base)[0] == 2  # answered: the ask is closed, a second yes posts nothing


@pytest.mark.parametrize(
    "line",
    ["Maintainer answer: Q-7-1 wait a week", "Maintainer answer: amendment 194 approved"],
)
def test_req069_each_maintainer_answer_form_is_posted(root, line):
    """REQ-069 AC7: rule 13, an owner question's answer and an amendment's approval."""
    base, _, gh = root
    assert ask(base, line)[0] == 0
    assert approve(base, "Approved")[0] == 0
    assert gh.bodies[-1].splitlines()[0] == line


@pytest.mark.parametrize(
    "line",
    [f"Approve: {HEAD} SPEC-0062", f"Approve: design 1.2 {HEAD}"],
)
def test_req069_an_approve_form_is_printed_ready_to_paste_and_never_posted(root, line):
    """REQ-069 AC7: rule 13, item 3: an `Approve:` is printed with its lines, never posted."""
    base, records, gh = root
    ask(base, line)
    code, lines = approve(base)
    assert code == 0 and len(gh.bodies) == 1  # only the question
    assert lines[0].startswith("paste on #7") and line in lines and "Who: ProductOwner" in lines
    assert any(x.startswith("Owner said (") for x in lines)


def test_req069_a_confirmation_is_printed_with_the_quotes_before_shown(root):
    """REQ-069 AC7: session rule 29, the `Confirmed:` text printed with the two quote lines
    standing before `Shown:`, and never posted."""
    base, _, gh = root
    text = (
        f"Confirmed: #7 {HEAD}\nVerdict: clear {HEAD}\nShown: the login page\n"
        "confirmed by boss in a session at 2026-11-22T04:04Z"
    )
    ask(base, text)
    code, lines = approve(base)
    assert code == 0 and len(gh.bodies) == 1
    shown = lines.index("Shown: the login page")
    assert lines[shown - 2].startswith("Owner said") and lines[shown - 1].startswith("Asked")
    assert lines[-1] == "Who: ProductOwner"


@pytest.mark.parametrize(
    ("words", "why"),
    [
        ("Yes but change the colour.", "rule 14"),
        ("Yes?", "rule 14"),
        ("ok?", "rule 14"),
        ("👍", "not a yes"),
        ("Yes if the totals match.", "rule 14"),
    ],
)
def test_req069_a_condition_a_question_or_an_emoji_posts_nothing(root, words, why):
    """REQ-069 AC7: rule 14's backstop; a change is a new decision, asked again."""
    base, _, gh = root
    ask(base, f"Maintainer answer: accept {HEAD}")
    code, lines = approve(base, words)
    assert code in (1, 2) and why in lines[0] and len(gh.bodies) == 1


def test_req069_not_yet_is_recorded_and_posts_nothing(root):
    """REQ-069 AC7: rule 14, 'not yet' is a Decision note, nothing posted."""
    base, records, gh = root
    ask(base, f"Maintainer answer: accept {HEAD}")
    code, _ = approve(base, "Not yet.")
    assert code == 1 and len(gh.bodies) == 1 and records[-1][0] == "Decision"


def test_req069_a_moved_head_or_a_closed_target_is_refused(root):
    """REQ-069 AC7: rule 13, a new head never inherits a yes; a closed target takes none."""
    base, _, gh = root
    ask(base, f"Maintainer answer: accept {HEAD}")
    gh.head = MOVED
    code, lines = approve(base)
    assert code == 2 and "head moved" in lines[0] and MOVED not in lines[0]
    gh.head, gh.state = HEAD, "closed"
    code, lines = approve(base)
    assert code == 2 and "closed" in lines[0] and len(gh.bodies) == 1


def test_req069_a_stale_ask_is_refused_by_the_age_setting(root):
    """REQ-069 AC7: Q-1690-2, four times `[flow] owner_wait_minutes`, 24 hours when unset or 0."""
    base, _, gh = root
    ask(base, f"Maintainer answer: accept {HEAD}", minutes=24 * 60 + 1)
    code, lines = approve(base)
    assert code == 2 and "owner_wait_minutes" in lines[0]
    (base / "agk.toml").write_text(SOLO + "[flow]\nowner_wait_minutes = 30\n", encoding="utf-8")
    ask(base, f"Maintainer answer: accept {HEAD}", minutes=121)
    assert approve(base)[0] == 2
    ask(base, f"Maintainer answer: accept {HEAD}", minutes=119)
    assert approve(base)[0] == 0
    (base / "agk.toml").write_text(SOLO + "[flow]\nowner_wait_minutes = 0\n", encoding="utf-8")
    ask(base, f"Maintainer answer: accept {HEAD}", minutes=60)
    assert approve(base)[0] == 0
    (base / "agk.toml").write_text(SOLO + '[flow]\nowner_wait_minutes = "x"\n', encoding="utf-8")
    ask(base, f"Maintainer answer: accept {HEAD}")
    code, lines = approve(base)
    assert code == 2 and "owner_wait_minutes" in lines[0] and '"x"' not in lines[0]


def test_req069_only_the_latest_open_ask_takes_a_yes(root):
    """REQ-069 AC7: two asks pending on one pull request: the newer stands, the older is closed;
    a yes to an older ask after another question is refused."""
    base, _, gh = root
    ask(base, f"Maintainer answer: accept {HEAD}", "Q-7-1", minutes=6)
    ask(base, "Maintainer answer: Q-7-2 wait", "Q-7-2", minutes=5)
    code, lines = approve(base, qid="Q-7-1")
    assert code == 2 and "latest open" in lines[0]
    assert approve(base, qid="Q-9-9")[0] == 2
    assert approve(base, qid="Q-7-2")[0] == 0


def test_req069_the_forms_it_never_writes_and_a_wrong_head_are_refused_at_the_ask(root):
    """REQ-069 AC7: decision 9, no `Merge:`, `Verdict:`, `Final:` or `Correction:`; a line that
    names another head; a target that is not a pull request; nothing posted."""
    base, _, gh = root
    for line in (
        f"Merge: #7 {HEAD}",
        f"Verdict: clear {HEAD}",
        "Final: docs/adr/0001-x.md Proposed -> Accepted",
        "Correction: none",
        f"Maintainer answer: accept {MOVED}",
        "Maintainer answer: Q-8-1 another question",
        "Hello there",
    ):
        code, lines = ask(base, line)
        assert code == 2 and "setting: --line" in lines[0], line
    code, lines = steward_owner.ask_target(
        base, "Q-7-1", "spec:SPEC-0062", ASK, write(base, "l.txt", "Approve: SPEC-0062\n"), NOW
    )
    assert code == 2 and "--target" in lines[0]
    assert gh.bodies == []


def test_req069_a_supervisor_started_steward_and_a_guard_match_are_refused(root, monkeypatch):
    """REQ-069 AC7: rule 13, `AGK_STEWARD_START=conductor` and the data guard, naming the class."""
    base, _, gh = root
    ask(base, f"Maintainer answer: accept {HEAD}")
    monkeypatch.setenv("AGK_STEWARD_START", "conductor")
    code, lines = approve(base)
    assert code == 2 and "AGK_STEWARD_START" in lines[0]
    monkeypatch.delenv("AGK_STEWARD_START")
    code, lines = approve(base, "Yes, call me on +44 7700 900123")
    assert code == 2 and "PHONE" in lines[0] and "[guard]" in lines[0] and len(gh.bodies) == 1
    assert "7700" not in lines[0]


def test_req069_an_unreadable_ask_state_is_refused_and_posts_nothing(root):
    """REQ-069 AC7: the steward's ask state unreadable: refused, nothing posted."""
    base, _, gh = root
    ask(base, f"Maintainer answer: accept {HEAD}")
    steward_owner.asks_file(base).write_text("{not json", encoding="utf-8")
    code, lines = approve(base)
    assert code == 2 and "cannot be read" in lines[0] and len(gh.bodies) == 1


def test_req069_team_mode_counts_only_a_spec_approvers_yes_and_never_prints_confirmed(
    root, monkeypatch
):
    """REQ-069 AC7: team mode, `spec_approvers` (yes_of) and no `Confirmed:`."""
    base, _, gh = root
    (base / "agk.toml").write_text('review_mode = "team"\n', encoding="utf-8")
    monkeypatch.setattr("reviewers.spec_approvers", lambda r: ["lead"])
    ask(base, f"Maintainer answer: accept {HEAD}")
    code, lines = approve(base, by="someone")
    assert code == 2 and "spec_approvers" in lines[0]
    assert approve(base, by="lead")[0] == 0
    code, lines = ask(base, f"Confirmed: #7 {HEAD}\nShown: x\nconfirmed by lead")
    assert code == 2 and "review_mode" in lines[0]


def test_req069_personal_mode_prints_the_confirm_command_and_posts_nothing(root):
    """REQ-069 AC7: rule 16, personal mode: nothing read or posted, the terminal command printed,
    the Decision to the sidecar memory."""
    base, records, gh = root
    (base / "agk.toml").write_text(SOLO + '[personal]\nforge = "files"\n', encoding="utf-8")
    line = write(base, "l.txt", "Maintainer answer: Q-7-1 go\n")
    for wrong in ("rec-3", "pr:7", "SPEC-62", "REQ-0690"):
        code, lines = steward_owner.ask_target(base, "Q-7-1", wrong, ASK, line, NOW)
        assert code == 2 and "--target" in lines[0], wrong
    code, lines = steward_owner.ask_target(base, "Q-7-1", "SPEC-0062", ASK, line, NOW)
    assert code == 0
    code, lines = approve(base)
    assert code == 0 and "python3 scripts/agk/personal.py confirm SPEC-0062" in lines
    assert gh.calls == [] and records[-1][0] == "Decision"


def test_req069_the_cli_takes_target_and_approve(root, monkeypatch, capsys):
    """REQ-069 AC7: `ask --target --qid --file --line` and `approve --ask --said --at`."""
    base, _, gh = root
    monkeypatch.setattr(steward_owner, "repo_root", lambda: base)
    question = write(base, "q.txt", ASK + "\n")
    line = write(base, "line.txt", f"Maintainer answer: accept {HEAD}\n")
    argv = ["ask", "--target", "pr:7", "--qid", "Q-7-1", "--file", str(question)]
    assert steward_owner.main([*argv, "--line", str(line)]) == 0
    said = write(base, "said.txt", "Yes\n")
    at = datetime.now(UTC).strftime("%Y-%m-%dT%H:%MZ")
    assert steward_owner.main(["approve", "--ask", "Q-7-1", "--said", str(said), "--at", at]) == 0
    assert gh.bodies[-1].startswith(f"Maintainer answer: accept {HEAD}\n")
    assert steward_owner.main(["approve", "--ask", "Q-7-1", "--said", str(said), "--at", "x"]) == 2


def test_req069_an_ask_ends_with_its_session(root, monkeypatch):
    """REQ-069 AC7: rule 13, "an ask ends when the session ends": the ask keeps its session's id
    (`AGK_SESSION`, else the memory's newest `Started: steward <id>`), and a yes in another
    session, or after that session's `Ended:`, is refused; with no session the ask is refused."""
    base, _, gh = root
    ask(base, f"Maintainer answer: accept {HEAD}")
    monkeypatch.setenv("AGK_SESSION", "s2")
    code, lines = approve(base)
    assert code == 2 and "another session" in lines[0] and len(gh.bodies) == 1
    monkeypatch.delenv("AGK_SESSION")
    cache = base / "state" / "memory.json"
    started = {"body": "Started: steward s1 2026-11-22T03:00Z"}
    cache.write_text(json.dumps({"comments": [started, {"body": "Ended: steward s1"}]}))
    assert approve(base)[0] == 2 and len(gh.bodies) == 1
    cache.write_text(json.dumps({"comments": [started]}))
    assert approve(base)[0] == 0
    cache.write_text("{}")
    code, lines = ask(base, f"Maintainer answer: accept {HEAD}")
    assert code == 2 and "AGK_SESSION" in lines[0] and len(gh.bodies) == 2


@pytest.mark.parametrize("line", [f"Approve: {HEAD} SPEC-0062", f"Confirmed: #7 {HEAD}\nShown: x"])
def test_req069_a_stored_ask_edited_to_an_approval_is_printed_never_posted(root, line):
    """REQ-069 AC7: session rule 29, the form is read again at the yes from the stored line, so
    an ask state edited to an `Approve:` or `Confirmed:` line is printed, never posted."""
    base, _, gh = root
    ask(base, f"Maintainer answer: accept {HEAD}")
    state = json.loads(steward_owner.asks_file(base).read_text(encoding="utf-8"))
    state[-1]["line"] = line
    steward_owner.asks_file(base).write_text(json.dumps(state), encoding="utf-8")
    code, lines = approve(base)
    assert code == 0 and lines[0].startswith("paste on #7") and len(gh.bodies) == 1
    state[-1]["line"], state[-1]["open"] = f"Merge: #7 {HEAD}", True
    steward_owner.asks_file(base).write_text(json.dumps(state), encoding="utf-8")
    code, lines = approve(base)
    assert code == 2 and "setting: --line" in lines[0] and len(gh.bodies) == 1


def test_req069_an_unwritable_memory_is_refused_before_the_post(root, monkeypatch):
    """REQ-069 AC7: answer 5, the `Decision:` is written first; when it cannot be, nothing is
    posted and the ask stays open."""
    base, _, gh = root
    ask(base, f"Maintainer answer: accept {HEAD}")
    monkeypatch.setattr(steward_owner.steward, "record", lambda *a: (2, ["refused: memory"]))
    code, lines = approve(base)
    assert code == 2 and lines == ["refused: memory"] and len(gh.bodies) == 1
    code, _ = approve(base, "Not yet.")
    assert code == 2 and len(gh.bodies) == 1


def test_req069_a_reply_before_the_ask_or_in_the_future_is_refused(root):
    """REQ-069 AC7: `--at` lies between the ask and now."""
    base, _, gh = root
    ask(base, f"Maintainer answer: accept {HEAD}")
    said = write(base, "said.txt", "Yes\n")
    for when, why in (("2026-11-22T03:50Z", "older than the ask"), ("2026-11-22T04:01Z", "future")):
        code, lines = steward_owner.approve(base, "Q-7-1", said, when, None, NOW)
        assert code == 2 and why in lines[0] and "--at" in lines[0], when
    assert steward_owner.approve(base, "Q-7-1", said, "2026-11-22T04:00Z", None, NOW)[0] == 0
    assert len(gh.bodies) == 2


SETTINGS = [
    ("env", "CLAUDE_CODE_REMOTE", "true"),
    ("reviewers", "agent_apps: [claude]\n", None),
    ("toml", 'pr_mode = "flow"\n[flow]\nauto_merge = true\n', None),
    ("toml", 'pr_mode = "strict"\n[flow]\nauto_merge = false\n', None),
    ("toml", '[kit]\nlayout = "plugin"\n', None),
    ("toml", '[kit]\nlayout = "installed"\n', None),
]


@pytest.mark.parametrize(("where", "text", "value"), SETTINGS)
def test_req069_the_other_settings_leave_the_approval_unchanged(
    root, monkeypatch, where, text, value
):
    """REQ-069 AC7: answer 4, a cloud session, `agent_apps`, `pr_mode`, `[flow] auto_merge` and
    `[kit] layout` change nothing: the `Maintainer answer:` is posted and an `Approve:` printed."""
    base, _, gh = root
    if where == "env":
        monkeypatch.setenv(text, value)
    elif where == "reviewers":
        (base / "config").mkdir()
        (base / "config" / "reviewers.yaml").write_text(text, encoding="utf-8")
    else:
        (base / "agk.toml").write_text(SOLO + text, encoding="utf-8")
    ask(base, f"Maintainer answer: accept {HEAD}")
    assert approve(base)[0] == 0 and gh.bodies[-1].startswith(f"Maintainer answer: accept {HEAD}")
    ask(base, f"Approve: {HEAD} SPEC-0062")
    code, lines = approve(base)
    assert code == 0 and lines[0].startswith("paste on #7") and len(gh.bodies) == 3
