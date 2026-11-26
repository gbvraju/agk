"""The conductor reads the Tells sent to it (brief #1970, ADR-0823; REQ-037).

`conductor.tell_lines` gives `watch` and `sweep` their Tells: `watch` wakes on a new
`Tell: <conductor id>` by a listed author on the open `agk-conductor` issue, from the delta read or
one `since` GET; `sweep` prints each unread one once as `TELL <id> reply-to <steward|none>: <line>`.
The GitHub responses are recorded copies with invented logins and names; no network.
"""

from __future__ import annotations

import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

KIT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KIT_ROOT / "scripts" / "agk"))

import conductor  # noqa: E402

REPO = "example/kit"
ISSUE = 204
STEWARD_ISSUE = 300
NOW = datetime(2026, 11, 26, 4, 30, tzinfo=UTC)
ME = "conductor-long"


def stamp(minutes: float) -> str:
    return (NOW - timedelta(minutes=minutes)).strftime("%Y-%m-%dT%H:%M:%SZ")


def said(cid: int, text: str, minutes: float, who: str = "owner", issue: int = ISSUE) -> dict:
    return {
        "id": cid,
        "user": {"login": who},
        "body": f"{text}\n\nWho: AGK steward\n",
        "created_at": stamp(minutes),
        "updated_at": stamp(minutes),
        "issue_url": f"https://api.github.example.com/repos/{REPO}/issues/{issue}",
    }


@pytest.fixture
def gh(monkeypatch, tmp_path):
    """Recorded GitHub: `comments` of the agk-conductor issue, `steward` notes, the GETs made."""

    class Gh:
        comments: list[dict] = []
        steward: list[dict] = []
        gets: list[str] = []
        broken = False
        no_issue = False
        authors = ["@owner"]
        name: str | None = ME

    def pages(endpoint):
        Gh.gets.append(endpoint)
        if endpoint.startswith(f"repos/{REPO}/issues/{ISSUE}/comments"):
            return None if Gh.broken else list(Gh.comments)
        if endpoint.startswith(f"repos/{REPO}/issues?state=open&labels=agk-conductor"):
            return [] if Gh.no_issue else [{"number": ISSUE, "labels": [{"name": "agk-conductor"}]}]
        if endpoint.startswith(f"repos/{REPO}/issues?labels=agk-steward"):
            return [{"number": STEWARD_ISSUE}]
        if endpoint.startswith(f"repos/{REPO}/issues/{STEWARD_ISSUE}/comments"):
            return list(Gh.steward)
        return []

    monkeypatch.setattr(conductor.session, "pages", pages)
    monkeypatch.setattr(conductor.session, "repo_name", lambda root: REPO)
    monkeypatch.setattr(conductor.session, "verdict_authors", lambda root: Gh.authors)
    monkeypatch.setattr(conductor.session, "inbox_mark", lambda root, me: tmp_path / f"in-{me}")
    monkeypatch.setattr(conductor, "own_name", lambda root: Gh.name)
    monkeypatch.setattr(conductor.common, "personal_table", lambda root: None)
    monkeypatch.setattr(conductor, "tell_now", lambda: NOW)
    monkeypatch.delenv("AGK_ROLE", raising=False)
    monkeypatch.delenv("AGK_SESSION", raising=False)
    monkeypatch.setattr(conductor, "TELL_ROOT", ["root"])
    conductor.TELL_ISSUE.clear()
    return Gh


def sweep_tells(root="root") -> list[str]:
    return conductor.tell_lines(root, REPO)


def watch_tells(since_minutes: float, delta: list | None = None) -> list[str]:
    return conductor.tell_lines("root", REPO, NOW - timedelta(minutes=since_minutes), delta)


def test_1970_watch_wakes_on_a_new_tell_in_full_with_one_since_get(gh):
    """REQ-037: brief #1970 answer 2; `full` reads only the comments since `since`."""
    gh.comments = [
        said(1, "Tell: conductor-long merge #21 on restart", 2),
        said(2, "Tell: cb22 merge the default branch", 2),
        said(3, "Tell: conductor-long an old one", 30),
        said(4, "Tell: conductor-long by a stranger", 1, who="stranger"),
    ]
    assert watch_tells(10) == [f"{ISSUE} Tell: conductor-long merge #21 on restart"]
    reads = [g for g in gh.gets if g.startswith(f"repos/{REPO}/issues/{ISSUE}/comments")]
    assert reads == [f"repos/{REPO}/issues/{ISSUE}/comments?since={stamp(10)}"]


def test_1970_watch_wakes_from_the_delta_read_without_another_get(gh):
    """REQ-037: brief #1970 answer 2; `delta` takes the Tells from the read already made."""
    delta = [
        said(5, "Tell: conductor-long asks for a builder", 1),
        said(6, "Tell: conductor-long on another issue", 1, issue=999),
    ]
    assert watch_tells(10, delta) == [f"{ISSUE} Tell: conductor-long asks for a builder"]
    assert not [g for g in gh.gets if f"issues/{ISSUE}/comments" in g]


def test_1970_watch_once_ends_on_a_tell(gh, monkeypatch, capsys):
    """REQ-037: brief #1970 test: `watch --once` wakes on a new Tell to the lease name."""
    gh.comments = [said(7, "Tell: conductor-long re-review #30", 1)]
    for name in ("green_lines", "start_lines"):
        monkeypatch.setattr(conductor, name, lambda *a, **k: [])
    monkeypatch.setattr(conductor, "held_lines", lambda *a: [])
    monkeypatch.setattr(conductor, "sweep_late", lambda *a: [])
    monkeypatch.setattr(conductor, "renew_lease", lambda root: 0)
    monkeypatch.setattr(conductor, "spec_approvers", lambda root: [])
    monkeypatch.setattr(conductor.session, "github_reads", lambda root: "full")
    monkeypatch.setattr(conductor.session, "flow_int", lambda *a: 60)
    assert conductor.watch("root", NOW - timedelta(minutes=5), once=True) == 0
    assert capsys.readouterr().out.splitlines() == [f"{ISSUE} Tell: conductor-long re-review #30"]


def test_1970_sweep_prints_each_unread_tell_once_with_the_live_steward(gh):
    """REQ-037: brief #1970 answer 3; the mark moves as `inbox` moves it."""
    gh.steward = [said(50, "Started: steward st-agk-day 2026-11-26T04:00Z", 30, issue=300)]
    gh.comments = [
        said(10, "Tell: conductor-long merge #21 on restart", 40),
        said(11, "Tell: someone-else stop", 30),
        said(12, "Tell: conductor-long information only", 20),
    ]
    assert sweep_tells() == [
        "TELL 10 reply-to st-agk-day: Tell: conductor-long merge #21 on restart",
        "TELL 12 reply-to st-agk-day: Tell: conductor-long information only",
    ]
    assert sweep_tells() == []
    gh.comments.append(said(13, "Tell: conductor-long one more", 5))
    assert sweep_tells() == ["TELL 13 reply-to st-agk-day: Tell: conductor-long one more"]


def test_1970_sweep_says_reply_to_none_without_a_live_steward(gh):
    """REQ-037: brief #1970 answer 3 and Q-CT-1: no live `Started: steward` marker."""
    gh.steward = [said(51, "Started: steward st-old 2026-11-26T01:00Z", 200, issue=300)]
    gh.comments = [said(14, "Tell: conductor-long merge #21", 5)]
    assert sweep_tells() == ["TELL 14 reply-to none: Tell: conductor-long merge #21"]


def test_1970_the_conductor_id_is_the_lease_else_its_session(gh, monkeypatch):
    """REQ-037: brief #1970 answer 1; neither prints the one name line and reads no Tell."""
    gh.comments = [said(15, "Tell: conductor-x restart cb22", 5)]
    gh.name = None
    assert sweep_tells() == ["TELL: no conductor name (lease)"]
    assert watch_tells(10) == []
    monkeypatch.setenv("AGK_SESSION", "conductor-x")
    assert sweep_tells() == ["TELL: no conductor name (lease)"]
    monkeypatch.setenv("AGK_ROLE", "conductor")
    assert sweep_tells() == ["TELL 15 reply-to none: Tell: conductor-x restart cb22"]


def test_1970_no_listed_author_prints_the_author_line_never_a_login(gh):
    """REQ-037: brief #1970 answer 5: `@REPLACE-ME` lists nobody."""
    gh.authors = []
    gh.comments = [said(16, "Tell: conductor-long merge #21", 5)]
    assert sweep_tells() == ["TELL: no listed author (verdict_authors)"]
    assert watch_tells(10) == []


def test_1970_a_failed_read_prints_its_line_and_the_other_sweep_lines(gh):
    """REQ-037: brief #1970 answer 3: a failed read is one line; the rest of sweep still prints."""
    gh.broken = True
    assert sweep_tells() == [f"TELL: the comments of #{ISSUE} cannot be read"]
    assert watch_tells(10) == []

    conductor.TELL_ISSUE.clear()
    gh.no_issue = True  # no agk-conductor issue: no Tell to read, no line, the sweep unchanged
    assert sweep_tells() == [] and watch_tells(10) == []
    source = Path(conductor.__file__).read_text(encoding="utf-8")
    sweep_body = source.split("\ndef sweep(root)", 1)[1].split("\ndef ", 1)[0]
    assert "lines += tell_lines(root, repo)" in sweep_body


def test_1970_personal_mode_prints_no_tell_line(gh, monkeypatch):
    """REQ-037: brief #1970 answer 5: `forge = "files"` has no agk-conductor issue."""
    monkeypatch.setattr(conductor.common, "personal_table", lambda root: {"forge": "files"})
    gh.comments = [said(17, "Tell: conductor-long merge #21", 5)]
    assert sweep_tells() == [] and watch_tells(10) == [] and gh.gets == []


def test_1970_the_words_the_conductor_wakes_on_are_a_closed_list():
    """REQ-037: brief #1970 answer 8: a new kind addressed to the conductor fails here first."""
    assert set(conductor.WAKES + conductor.TELLS) == {
        "Question:",
        "Report:",
        "Answer:",
        "Maintainer answer:",
        "Approve:",
        "Tell:",
    }


def test_1970_the_role_file_says_act_or_answer():
    """REQ-037: brief #1970 answer 4: the conductor acts on each TELL line or answers why not."""
    text = (KIT_ROOT / ".claude" / "agents" / "conductor.md").read_text(encoding="utf-8")
    paragraph = next((p for p in text.split("\n\n") if p.startswith("Tells to you")), "")
    for part in (
        "`TELL <comment id>",
        "reply-to",
        "not done:",
        "already done:",
        "acted|answered|noted",
        "Needs you",
        "never a verdict",
    ):
        assert part in paragraph, part
