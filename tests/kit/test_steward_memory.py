"""Tests of scripts/agk/steward.py, the steward's memory (SPEC-0059 rules 8, 14 and 18; brief #1320,
ADR-0557; REQ-066 AC1 and AC7).

A recorded `gh` double counts each call and answers from an invented in-memory issue store; no
network, no model, invented data only (example.com).
"""

from __future__ import annotations

import re
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "agk"))

import steward  # noqa: E402

NOW = datetime(2026, 11, 15, 10, 30, tzinfo=UTC)
ISSUES = re.compile(r"repos/\{owner\}/\{repo\}/issues(?:/(\d+))?(/comments)?(?:\?(.*))?$")


def stamp(minutes: int) -> str:
    return (NOW - timedelta(minutes=minutes)).strftime("%Y-%m-%dT%H:%M:%SZ")


class GitHub:
    """The recorded double: each call is counted; issues and comments live in memory."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []
        self.issues: dict[int, dict] = {}
        self.next_id = 100
        self.clock = 0  # minutes before NOW at which a posted comment is created

    def add_issue(self, labels=("agk-steward",), state="open") -> int:
        number = len(self.issues) + 1
        self.issues[number] = {"number": number, "labels": list(labels), "state": state, "c": []}
        return number

    def comment(self, number: int, body: str, minutes: int = 120) -> dict:
        self.next_id += 1
        item = {"id": self.next_id, "body": body, "created_at": stamp(minutes)}
        item["updated_at"] = item["created_at"]
        self.issues[number]["c"].append(item)
        return item

    def view(self, issue: dict) -> dict:
        labels = [{"name": n} for n in issue["labels"]]
        return {"number": issue["number"], "comments": len(issue["c"]), "labels": labels}

    def __call__(self, method: str, endpoint: str, fields: dict | None = None):
        self.calls.append((method, endpoint))
        found = ISSUES.match(endpoint)
        assert found, endpoint
        number, comments, query = found.group(1), found.group(2), found.group(3) or ""
        if method == "GET" and number is None:
            return [
                self.view(i)
                for i in self.issues.values()
                if i["state"] == "open" and "agk-steward" in i["labels"]
            ]
        if method == "GET":
            since = re.search(r"since=([^&]+)", query)
            page = int((re.search(r"(?:^|&)page=(\d+)", query) or [0, 1])[1])
            items = [
                c for c in self.issues[int(number)]["c"] if not since or c["updated_at"] >= since[1]
            ]
            return items[(page - 1) * 100 : page * 100]
        if method == "POST" and number is None:
            new = self.add_issue(tuple(fields["labels"]))
            return self.view(self.issues[new])
        if method == "POST" and comments:
            return self.comment(int(number), fields["body"], minutes=self.clock)
        if method == "PATCH":
            self.issues[int(number)]["state"] = fields["state"]
            return {}
        raise AssertionError((method, endpoint))

    def counted(self) -> int:
        return len(self.calls)


@pytest.fixture
def root(tmp_path, monkeypatch):
    monkeypatch.setenv("AGK_STEWARD_CACHE", str(tmp_path / "cache.json"))
    (tmp_path / "agk.toml").write_text('default_branch = "main"\n', encoding="utf-8")
    return tmp_path


def test_req066_the_parser_reads_each_kind_and_names_an_unknown_one():
    """REQ-066 AC7: rule 8, each entry kind is read; another first word is named, not read."""
    for kind in steward.KINDS:
        assert steward.entry_kind(f"{kind}: a note.\n\nWho: AGK steward") == kind
    assert steward.entry_kind("Started: steward s1 2026-11-15T10:00Z") == "Started"
    assert steward.entry_kind("Remark: something") is None
    comments = [
        {"id": 1, "body": "Term: a widget is a part.", "created_at": stamp(30)},
        {"id": 2, "body": "Term: a gadget is a tool.", "created_at": stamp(20)},
        {"id": 3, "body": "Remark: x", "created_at": stamp(10)},
        {"id": 4, "body": "Gap: no source for totals.", "created_at": stamp(5)},
    ]
    memory = steward.read_memory(comments)
    assert [e["id"] for e in memory["newest"]["Term"]] == [2, 1]
    assert [e["id"] for e in memory["newest"]["Gap"]] == [4]
    assert memory["unknown"] == [3]
    lines = steward.summary(memory)
    assert any("unknown first word" in line and "3" in line for line in lines)


def test_req066_a_first_start_creates_the_memory_issue_and_posts_its_marker(root):
    """REQ-066 AC7: rule 8, one issue labelled `agk-steward` is created when none is open."""
    gh = GitHub()
    code, lines = steward.start(root, "s1", gh, NOW)
    assert code == 0
    assert [m for m, _ in gh.calls] == ["GET", "POST", "POST"]
    issue = gh.issues[1]
    assert issue["labels"] == ["agk-steward"]
    assert issue["c"][-1]["body"].startswith("Started: steward s1 2026-11-15T10:30Z")
    assert issue["c"][-1]["body"].rstrip().endswith("Who: AGK steward")


def test_req066_a_quiet_start_reads_the_memory_first_within_five_calls(root):
    """REQ-066 AC1: rule 18, a quiet start makes at most 5 counted calls, memory read first, and
    a changed memory is read with `since=` from the last comment seen."""
    gh = GitHub()
    number = gh.add_issue()
    gh.comment(number, "Decision: Q-1-1 Friday (evidence: docs/sources/a.md:3)", minutes=200)
    steward.start(root, "s1", gh, NOW)
    steward.end(root, "s1", gh, NOW)
    gh.calls.clear()
    code, _ = steward.start(root, "s2", gh, NOW + timedelta(minutes=5))
    assert code == 0 and gh.counted() <= 5
    assert gh.calls[0] == (
        "GET",
        "repos/{owner}/{repo}/issues?labels=agk-steward&state=open&per_page=10",
    )
    gh.comment(number, "Term: a widget is a part.", minutes=0)
    gh.calls.clear()
    steward.start(root, "s3", gh, NOW + timedelta(minutes=9))
    reads = [e for m, e in gh.calls if m == "GET" and "/comments" in e]
    assert reads and all("since=" in e for e in reads)
    assert gh.counted() <= 5
    assert not any(m in ("PUT", "DELETE") for m, _ in gh.calls)


def test_req066_a_live_start_marker_makes_a_second_start_write_nothing(root):
    """REQ-066 AC1: rule 2, a `Started: steward` newer than 60 minutes with no `Ended:` after it."""
    gh = GitHub()
    number = gh.add_issue()
    gh.comment(number, "Started: steward s1 " + stamp(20)[:-4] + "Z", minutes=20)
    code, lines = steward.start(root, "s2", gh, NOW)
    assert code == 1
    assert any("already running" in line for line in lines)
    assert all(m == "GET" for m, _ in gh.calls)
    gh.comment(number, "Ended: steward s1", minutes=10)
    assert steward.start(root, "s2", gh, NOW)[0] == 0


def test_req066_an_old_marker_is_not_live(root):
    """REQ-066 AC1: rule 2, a marker older than 60 minutes does not stop a start."""
    gh = GitHub()
    number = gh.add_issue()
    gh.comment(number, "Started: steward s1 " + stamp(61)[:-4] + "Z", minutes=61)
    assert steward.start(root, "s2", gh, NOW)[0] == 0


def test_req066_at_500_comments_a_new_issue_carries_the_open_owner_questions(root):
    """REQ-066 AC7: rule 8, the roll-over links the old issue, carries the open questions."""
    gh = GitHub()
    old = gh.add_issue()
    gh.comment(old, "Owner question: Q-7-1 Should the report go out on Friday?", minutes=300)
    gh.comment(old, "Owner question: Q-7-2 Should the export keep two columns?", minutes=299)
    gh.comment(old, "Decision: Q-7-2 keep two columns (evidence: the owner's answer)", minutes=298)
    for n in range(497):
        gh.comment(old, f"Term: word{n} means thing{n}.", minutes=200)
    code, _ = steward.start(root, "s1", gh, NOW)
    assert code == 0
    assert gh.issues[old]["state"] == "closed"
    new = max(gh.issues)
    first = gh.issues[new]["c"][0]["body"]
    assert f"#{old}" in first and "Q-7-1" in first and "Q-7-2" not in first
    assert gh.issues[new]["labels"] == ["agk-steward"]


def test_req066_a_record_is_one_comment_with_a_known_first_word(root):
    """REQ-066 AC7: rule 8, each record is one comment; an unknown kind or a secret is refused."""
    gh = GitHub()
    gh.add_issue()
    assert steward.record(root, "Term", "a widget is a part.", gh)[0] == 0
    body = gh.issues[1]["c"][-1]["body"]
    assert body.startswith("Term: a widget is a part.") and "Who: AGK steward" in body
    code, lines = steward.record(root, "Remark", "x", gh)
    assert code == 2 and "kind" in lines[0]
    secret = "Gap: mail ada@example.org about the key AKIA" + "ABCDEFGHIJKLMNOP"
    code, lines = steward.record(root, "Gap", secret, gh)
    assert code == 2 and "AKIA" not in " ".join(lines) and "ada@" not in " ".join(lines)
    assert len(gh.issues[1]["c"]) == 1


def test_req066_personal_mode_writes_the_sidecar_file_and_posts_nothing(root):
    """REQ-066 AC7: rule 14, the memory is `docs/runs/steward/memory.md`; no call is made."""
    (root / "agk.toml").write_text('[personal]\nforge = "files"\n', encoding="utf-8")
    gh = GitHub()
    assert steward.start(root, "s1", gh, NOW)[0] == 0
    assert steward.record(root, "Term", "a widget is a part.", gh)[0] == 0
    assert gh.calls == []
    text = (root / "docs" / "runs" / "steward" / "memory.md").read_text(encoding="utf-8")
    assert "Started: steward s1" in text and "Term: a widget is a part." in text
    memory = steward.read_memory(steward.personal_entries(root))
    assert memory["newest"]["Term"][0]["body"].startswith("Term: a widget")


# --- refresh: what changed since the checkpoint (brief #1702, ADR-0708) --------------------------

PULLS = re.compile(r"repos/\{owner\}/\{repo\}/pulls\?(.*)$")
COMMENT = re.compile(r"repos/\{owner\}/\{repo\}/issues/comments/(\d+)$")


class Forge(GitHub):
    """The double with pull requests: an open listing and a closed listing, newest updated first."""

    def __init__(self) -> None:
        super().__init__()
        self.pulls: list[dict] = []

    def pull(self, number, minutes=5, state="open", merged=True, labels=(), head="a" * 40):
        when = stamp(minutes)
        item = {"number": number, "state": state, "updated_at": when, "head": {"sha": head}}
        item["labels"] = [{"name": n} for n in labels]
        item["closed_at"] = when if state == "closed" else None
        item["merged_at"] = when if state == "closed" and merged else None
        self.pulls.append(item)
        return item

    def __call__(self, method, endpoint, fields=None):
        if edited := COMMENT.match(endpoint):  # brief #1741: a beat edits its own marker
            self.calls.append((method, endpoint))
            for issue in self.issues.values():
                for item in issue["c"]:
                    if item["id"] == int(edited[1]):
                        item["body"], item["updated_at"] = fields["body"], stamp(self.clock)
                        return dict(item)
            return None
        found = PULLS.match(endpoint)
        if not found:
            return super().__call__(method, endpoint, fields)
        self.calls.append((method, endpoint))
        state = re.search(r"state=(\w+)", found[1])[1]
        items = [p for p in self.pulls if p["state"] == state]
        return sorted(items, key=lambda p: p["updated_at"], reverse=True)[:100]


def started(root, gh, minutes=60):
    """A start `minutes` before NOW: the checkpoint is then; the calls are cleared."""
    gh.clock = minutes
    assert steward.start(root, "s1", gh, NOW - timedelta(minutes=minutes))[0] == 0
    gh.calls.clear()
    gh.clock = 0


def test_req066_refresh_makes_three_calls_and_prints_only_what_changed(root):
    """REQ-066 AC1: brief #1702 Measured, 2 new comments, 1 merged and 1 changed open pull request
    since the checkpoint make exactly 3 calls and 4 lines, a `Decision:` first; then the checkpoint
    moves, so a second refresh prints nothing new."""
    gh = Forge()
    number = gh.add_issue()
    gh.comment(number, "Term: a widget is a part.", minutes=200)
    gh.pull(7, minutes=200)  # unchanged since the checkpoint
    gh.pull(5, minutes=300, state="closed")  # closed before it
    started(root, gh)
    gh.comment(number, "Lesson: read the memory before a list.", minutes=30)
    gh.comment(number, "Decision: Q-9-1 class technical (evidence: the owner)", minutes=20)
    gh.pull(8, minutes=10, labels=("agk:ci-red",), head="b" * 40)
    gh.pull(6, minutes=15, state="closed")
    code, lines = steward.refresh(root, "s1", gh, NOW)
    assert code == 0 and gets(gh) == 3
    comments = [e for m, e in gh.calls if "/comments" in e and m == "GET"]
    assert len(comments) == 1 and "since=" in comments[0]
    assert any("pulls?state=open" in e for _, e in gh.calls)
    assert any("pulls?state=closed&sort=updated&direction=desc" in e for _, e in gh.calls)
    assert len(lines) == 4
    assert lines[0].split()[1] == "Decision" and "Q-9-1" in lines[0]
    assert lines[1].split()[1] == "Lesson"
    assert lines[2] == "#8 " + "b" * 12 + " agk:ci-red"
    assert lines[3] == "#6 merged " + stamp(15)
    gh.calls.clear()
    code, lines = steward.refresh(root, "s1", gh, NOW + timedelta(minutes=1))
    assert code == 0 and gets(gh) == 3
    assert lines == ["refresh: nothing new since " + NOW.strftime("%Y-%m-%dT%H:%M:%SZ")]
    assert [m for m, _ in gh.calls if m != "GET"] == ["PATCH"]  # the beat, brief #1741


def test_req066_refresh_without_a_checkpoint_is_refused_naming_the_setting(root):
    """REQ-066 AC1: brief #1702 answer 5, no `start` in this clone: refused, no call; `--since`
    takes a UTC time instead."""
    gh = Forge()
    number = gh.add_issue()
    code, lines = steward.refresh(root, "s1", gh, NOW)
    assert code == 2 and gh.calls == []
    assert lines == [
        "refresh: no checkpoint (setting: AGK_STEWARD_CACHE); run start, or pass --since <UTC time>"
    ]
    gh.comment(number, "Gap: no source for totals.", minutes=5)
    code, lines = steward.refresh(root, "s1", gh, NOW, since="2026-11-15T10:00Z")
    assert code == 0 and any("Gap" in line for line in lines)
    assert steward.refresh(root, "s1", gh, NOW, since="yesterday")[0] == 2


def test_req066_refresh_prints_an_edited_comment_as_edited(root):
    """REQ-066 AC1: brief #1702 answer 5, an edited old comment comes back with `since=`."""
    gh = Forge()
    number = gh.add_issue()
    old = gh.comment(number, "Risk: the export is slow.", minutes=200)
    started(root, gh)
    old["body"], old["updated_at"] = "Risk: the export is slow on Fridays.", stamp(5)
    code, lines = steward.refresh(root, "s1", gh, NOW)
    assert code == 0 and lines == [f"{old['id']} edited Risk Risk: the export is slow on Fridays."]


def test_req066_a_failed_refresh_call_leaves_the_checkpoint(root, monkeypatch):
    """REQ-066 AC1: brief #1702 answer 5, a failed call raises Unreadable (exit 4) and the
    checkpoint is not moved."""
    gh = Forge()
    number = gh.add_issue()
    started(root, gh)
    before = steward.load_cache(root)["checkpoint"]
    gh.comment(number, "Term: a gadget is a tool.", minutes=5)

    def broken(method, endpoint, fields=None):
        return None if "state=closed" in endpoint else gh(method, endpoint, fields)

    with pytest.raises(steward.Unreadable):
        steward.refresh(root, "s1", broken, NOW)
    assert steward.load_cache(root)["checkpoint"] == before
    monkeypatch.setattr(steward, "gh_api", broken)
    monkeypatch.setattr(steward, "repo_root", lambda: root)
    assert steward.main(["refresh", "--session", "s1"]) == 4


def test_req066_refresh_says_when_more_closed_than_one_page(root):
    """REQ-066 AC1: brief #1702 answer 5, more than 100 closed since the checkpoint."""
    gh = Forge()
    gh.add_issue()
    started(root, gh, minutes=300)
    for n in range(101):
        gh.pull(100 + n, minutes=200, state="closed", merged=False)
    code, lines = steward.refresh(root, "s1", gh, NOW)
    assert code == 0 and gets(gh) == 3
    assert lines[-1].startswith("more closed since ") and lines[-1].endswith(": not listed")
    assert sum(line.startswith("#") and " closed " in line for line in lines) == 100


def test_req066_refresh_reads_a_rolled_over_memory_from_its_first_comment(root, monkeypatch):
    """REQ-066 AC1: brief #1702 answer 5, another clone's start rolled the memory over since the
    checkpoint: the new issue is read from its first comment."""
    gh = Forge()
    old = gh.add_issue()
    for n in range(497):
        gh.comment(old, f"Term: word{n} means thing{n}.", minutes=300)
    started(root, gh)
    gh.comment(old, "Term: one more.", minutes=40)
    gh.comment(old, "Ended: steward s1", minutes=35)
    mine = steward.load_cache(root)
    monkeypatch.setenv("AGK_STEWARD_CACHE", str(root / "other.json"))
    gh.clock = 30
    assert steward.start(root, "s3", gh, NOW - timedelta(minutes=30))[0] == 0
    monkeypatch.setenv("AGK_STEWARD_CACHE", str(root / "cache.json"))
    assert steward.load_cache(root) == mine
    gh.calls.clear()
    code, lines = steward.refresh(root, "s1", gh, NOW)
    new = max(gh.issues)
    assert code == 0 and new != old and gh.issues[old]["state"] == "closed"
    assert any("Term: one more." in line for line in lines)
    assert any("Memory continued from" in line for line in lines)
    assert any("Started: steward s3" in line for line in lines)
    assert steward.load_cache(root)["issue"] == new


def test_req066_refresh_in_personal_mode_reads_the_sidecar_file_only(root):
    """REQ-066 AC1: brief #1702 answer 4, personal mode reads the entries after the checkpoint
    and reads no pull request: no call."""
    (root / "agk.toml").write_text('[personal]\nforge = "files"\n', encoding="utf-8")
    gh = Forge()
    assert steward.start(root, "s1", gh, NOW - timedelta(minutes=10))[0] == 0
    assert steward.record(root, "Term", "a widget is a part.", gh)[0] == 0
    code, lines = steward.refresh(root, "s1", gh, NOW)
    assert code == 0 and gh.calls == []
    assert any("Term: a widget is a part." in line for line in lines)
    assert lines[-1] == "pull requests: not read in personal mode"
    assert steward.refresh(root, "s1", gh, NOW)[1][0].startswith("refresh: nothing new since ")


def test_req066_refresh_keeps_its_checkpoint_in_the_cache_setting(root, tmp_path, monkeypatch):
    """REQ-066 AC1: brief #1702 answer 4, `AGK_STEWARD_CACHE` holds the checkpoint; the steward
    started by the conductor runs the same command."""
    monkeypatch.setenv("AGK_STEWARD_START", "conductor")
    gh = Forge()
    gh.add_issue()
    started(root, gh)
    held = steward.load_cache(root)["checkpoint"]
    assert held["at"] == (NOW - timedelta(minutes=60)).strftime("%Y-%m-%dT%H:%M:%SZ")
    assert (tmp_path / "cache.json").is_file()
    assert steward.refresh(root, "s1", gh, NOW)[0] == 0 and gets(gh) == 3


# --- one live run at a time, and a run's work survives the next start (brief #1741, ADR-0726) ----

Beating = Forge  # the double edits a comment too (brief #1741)


def hm(minutes: int) -> str:
    return (NOW - timedelta(minutes=minutes)).strftime("%Y-%m-%dT%H:%MZ")


def gets(gh) -> int:
    return sum(m == "GET" for m, _ in gh.calls)


def test_req066_brief_1741_a_start_under_a_live_runs_own_name_is_refused(root):
    """REQ-066 AC1: brief #1741 answer 1 and 7(a), a live `Started:` of the same name refuses the
    start, names the run and its start time, and writes nothing."""
    gh = Beating()
    number = gh.add_issue()
    gh.comment(number, f"Started: steward st-day {hm(20)}\n\nWho: AGK steward", minutes=20)
    code, lines = steward.start(root, "st-day", gh, NOW)
    assert code == 1
    assert lines[-1] == f"steward already running: st-day since {hm(20)}; this start writes nothing"
    assert all(m == "GET" for m, _ in gh.calls) and len(gh.issues[number]["c"]) == 1


def test_req066_brief_1741_a_beat_keeps_a_run_live_past_sixty_minutes(root):
    """REQ-066 AC1: brief #1741 answer 2 and 7(b), a run 70 minutes old whose newest beat is 5
    minutes old (65 minutes after its start) is live: the start is refused."""
    gh = Beating()
    number = gh.add_issue()
    body = f"Started: steward st-day {hm(70)} beat {hm(5)}\n\nWho: AGK steward"
    gh.comment(number, body, minutes=70)
    code, lines = steward.start(root, "st-chat", gh, NOW)
    assert code == 1 and lines[-1].startswith(f"steward already running: st-day since {hm(70)}")


def test_req066_brief_1741_refresh_and_record_beat_on_the_runs_own_marker(root, monkeypatch):
    """REQ-066 AC1: brief #1741 answer 2, `refresh` and `record` edit the run's own `Started:`
    comment in place (one PATCH, no new comment); the beat is not printed as a change."""
    gh = Beating()
    number = gh.add_issue()
    started(root, gh)
    marker = gh.issues[number]["c"][-1]
    code, lines = steward.refresh(root, "s1", gh, NOW)
    assert code == 0 and gets(gh) == 3
    assert [m for m, _ in gh.calls].count("PATCH") == 1
    assert gh.calls[-1] == ("PATCH", f"repos/{{owner}}/{{repo}}/issues/comments/{marker['id']}")
    assert marker["body"].startswith(f"Started: steward s1 {hm(60)} beat {hm(0)}")
    assert marker["body"].rstrip().endswith("Who: AGK steward")
    assert len(gh.issues[number]["c"]) == 1 and lines[0].startswith("refresh: nothing new")
    monkeypatch.setattr(steward, "gh_api", gh)
    monkeypatch.setattr(steward, "repo_root", lambda: root)
    gh.calls.clear()
    assert steward.main(["record", "--kind", "Term", "--text", "a widget is a part."]) == 0
    assert [m for m, _ in gh.calls] == ["POST", "PATCH"]
    assert len(gh.issues[number]["c"]) == 2


def test_req066_brief_1741_a_run_with_no_beat_for_61_minutes_is_named_and_the_start_proceeds(root):
    """REQ-066 AC1: brief #1741 answer 2 and 7(c), no beat for 61 minutes: the next start names
    the previous run and starts."""
    gh = Beating()
    number = gh.add_issue()
    gh.comment(number, f"Started: steward st-day {hm(90)} beat {hm(61)}", minutes=90)
    code, lines = steward.start(root, "st-day", gh, NOW)
    assert code == 0
    assert f"previous run st-day ended without Ended (last beat {hm(61)})" in lines
    assert gh.issues[number]["c"][-1]["body"].startswith(f"Started: steward st-day {hm(0)}")


def test_req066_brief_1741_record_and_end_need_a_live_start_in_this_clone(root, monkeypatch):
    """REQ-066 AC1: brief #1741 answer 3 and 7(d), `record` and `end` after an `Ended:` with no new
    start are refused naming `steward.py start`; after `start` they write."""
    gh = Beating()
    number = gh.add_issue()
    monkeypatch.setattr(steward, "gh_api", gh)
    monkeypatch.setattr(steward, "repo_root", lambda: root)
    record = ["record", "--kind", "Note", "--text", "the export runs on Fridays."]
    assert steward.main(record) == 2 and gh.calls == []
    assert steward.main(["end", "--session", "s1"]) == 2 and gh.calls == []
    assert steward.main(["start", "--session", "s1"]) == 0
    assert steward.main(record) == 0
    assert steward.main(["end", "--session", "s1"]) == 0
    count = len(gh.issues[number]["c"])
    gh.calls.clear()
    assert steward.main(record) == 2 and gh.calls == []
    assert len(gh.issues[number]["c"]) == count
    assert "steward.py start" in steward.no_start(root)
    assert steward.main(["start", "--session", "s1"]) == 0 and steward.main(record) == 0


def test_req066_brief_1741_another_clones_end_stops_this_clones_writes(root, monkeypatch):
    """REQ-066 AC1: brief #1741 answer 3, an `Ended:` of the run read into the cache refuses."""
    gh = Beating()
    number = gh.add_issue()
    started(root, gh, minutes=10)
    gh.comment(number, "Ended: steward s1 calls not shown; tokens not shown", minutes=5)
    assert steward.refresh(root, "s1", gh, NOW)[0] == 0
    assert "steward.py start" in steward.no_start(root)


UNKNOWN_TODAY = [
    "Note: the chat steward resumed after the scheduled run ended.",
    "Owner list: three items for the owner today.\n1. #9001 waits on a ruling.",
    "Morning list for the owner: two items.\n1. #9002 is ready.",
    "Draft brief: F-st-day-28A The export keeps two columns\nSentence: the export keeps two.",
    "Filed: F-st-day-27A as #9003",
]


def fixture_today():
    """Invented stand-ins for the 51 comments read as unknown on 2026-11-22, and one other word."""
    bodies = [UNKNOWN_TODAY[n % len(UNKNOWN_TODAY)] for n in range(50)] + ["Remark: other"]
    return [
        {"id": n, "body": f"{b}\n\nWho: AGK steward", "created_at": stamp(200 - n)}
        for n, b in enumerate(bodies, 1)
    ]


def test_req066_brief_1741_the_kinds_the_runs_write_are_read_as_memory():
    """REQ-066 AC7: brief #1741 answer 4 and 7(e), `Note:`, `Owner list:`, `Morning list for the
    owner:`, `Draft brief:` and `Filed:` are kinds; any other first word is still unknown."""
    for kind in ("Note", "Owner list", "Morning list for the owner", "Draft brief", "Filed"):
        assert kind in steward.KINDS
        assert steward.entry_kind(f"{kind}: some text.") == kind
    memory = steward.read_memory(fixture_today())
    assert memory["unknown"] == [51]
    assert {"Note", "Owner list", "Morning list for the owner", "Draft brief", "Filed"} <= set(
        memory["newest"]
    )


def test_req066_brief_1741_the_summary_carries_the_owner_list_note_and_unfiled_drafts():
    """REQ-066 AC7: brief #1741 answer 4, the newest owner list's first line, every line of the
    newest note and of each `Draft brief:` not yet followed by a `Filed:` naming it."""
    comments = [
        {"id": 1, "body": "Draft brief: F-s-1 Old one\nSentence: filed.", "created_at": stamp(90)},
        {
            "id": 2,
            "body": "Draft brief: F-s-2 Kept\nSentence: still open.",
            "created_at": stamp(80),
        },
        {"id": 3, "body": "Filed: F-s-1 as #9003\n\nWho: AGK steward", "created_at": stamp(70)},
        {"id": 4, "body": "Owner list: old list.\n1. done", "created_at": stamp(60)},
        {"id": 5, "body": "Owner list: new list.\n1. #9001 waits", "created_at": stamp(50)},
        {"id": 6, "body": "Note: older note.", "created_at": stamp(40)},
        {
            "id": 7,
            "body": "Note: newest note.\nsecond line\n\nWho: AGK steward",
            "created_at": stamp(30),
        },
    ]
    lines = steward.summary(steward.read_memory(comments))
    assert "Owner list: new list." in lines and "1. #9001 waits" not in lines
    assert not any("old list" in line for line in lines)
    assert "Note: newest note." in lines and "second line" in lines
    assert "Draft brief: F-s-2 Kept" in lines and "Sentence: still open." in lines
    assert not any("F-s-1 Old one" in line or "Sentence: filed." in line for line in lines)
    assert not any(line.startswith("Who:") for line in lines)


def test_req066_brief_1741_a_draft_keeps_its_text_and_a_triage_draft_names_it(root):
    """REQ-066 AC7: brief #1741 answer 5 and 7(f), a `Draft brief:` is stored under its id; a
    `Triage:` that says `draft for the owner` and names no recorded draft id is refused."""
    gh = Beating()
    number = gh.add_issue()
    started(root, gh)
    triage = "F-s1-3 kit brief: the export is slow, draft for the owner"
    code, lines = steward.record(root, "Triage", triage, gh)
    assert code == 2 and "Draft brief" in lines[0]
    code, lines = steward.record(root, "Draft brief", "The export is slow\nSentence: x.", gh)
    assert code == 2 and "F-" in lines[0]
    text = "F-s1-3 The export is slow\nSentence: the export is quick.\nModes: github x; local x"
    assert steward.record(root, "Draft brief", text, gh)[0] == 0
    assert gh.issues[number]["c"][-1]["body"].startswith("Draft brief: " + text)
    assert steward.record(root, "Triage", triage, gh)[0] == 0
    assert steward.record(root, "Triage", "F-s1-4 kit brief: file it now", gh)[0] == 0


def test_req066_brief_1741_a_roll_over_carries_every_unfiled_draft(root):
    """REQ-066 AC7: brief #1741 7(g), the new memory issue carries every `Draft brief:` not yet
    filed, beside the open owner questions."""
    gh = Beating()
    old = gh.add_issue()
    gh.comment(old, "Owner question: Q-7-1 Should the report go out on Friday?", minutes=300)
    gh.comment(old, "Draft brief: F-s-1 Filed one\nSentence: gone.", minutes=299)
    gh.comment(old, "Draft brief: F-s-2 Kept one\nSentence: kept.", minutes=298)
    gh.comment(old, "Filed: F-s-1 as #9003", minutes=297)
    for n in range(496):
        gh.comment(old, f"Term: word{n} means thing{n}.", minutes=200)
    assert steward.start(root, "s1", gh, NOW)[0] == 0
    new = max(gh.issues)
    bodies = [c["body"] for c in gh.issues[new]["c"]]
    assert "Q-7-1" in bodies[0]
    assert any(b.startswith("Draft brief: F-s-2 Kept one\nSentence: kept.") for b in bodies)
    assert not any("F-s-1" in b for b in bodies)
    assert bodies[-1].startswith("Started: steward s1")


@pytest.mark.parametrize(
    "toml",
    [
        "[steward]\nauto_file = 0\n",
        "[steward]\nauto_file = 3\n",
        "[steward]\nauto_file = false\n",
        'review_mode = "solo"\n',
        'review_mode = "team"\n',
        'pr_mode = "strict"\n',
        'pr_mode = "flow"\n',
        'execution = "hosted"\n',
        'execution = "hybrid"\n',
        'execution = "pool"\n',
        'execution = "local"\n',
    ],
)
def test_req066_brief_1741_settings_do_not_change_the_refusal(root, toml):
    """REQ-066 AC1: brief #1741 answer 6, `[steward] auto_file`, `review_mode`, `pr_mode` and
    `execution` are not read: a live run refuses the start under each value."""
    (root / "agk.toml").write_text('default_branch = "main"\n' + toml, encoding="utf-8")
    gh = Beating()
    number = gh.add_issue()
    gh.comment(number, f"Started: steward s1 {hm(10)}", minutes=10)
    assert steward.start(root, "s1", gh, NOW)[0] == 1
    assert len(gh.issues[number]["c"]) == 1


def test_req066_brief_1741_a_start_by_the_conductor_is_refused_and_listed_as_stuck(
    root, monkeypatch
):
    """REQ-066 AC1: brief #1741 answer 6, `AGK_STEWARD_START=conductor` is refused as any other
    while a run is live, and listed as stuck, never silent (SPEC-0059 rule 2)."""
    monkeypatch.setenv("AGK_STEWARD_START", "conductor")
    gh = Beating()
    number = gh.add_issue()
    gh.comment(number, f"Started: steward st-day {hm(10)}", minutes=10)
    code, lines = steward.start(root, "st-sup", gh, NOW)
    assert code == 1 and len(gh.issues[number]["c"]) == 1
    assert "stuck: steward st-sup not started (steward already running: st-day)" in lines


def test_req066_brief_1741_a_malformed_beat_is_read_as_the_start_time_alone(root):
    """REQ-066 AC1: brief #1741 answer 6, a malformed `beat` time never makes a run live forever."""
    gh = Beating()
    number = gh.add_issue()
    gh.comment(number, f"Started: steward s1 {hm(70)} beat 2026-13-99T99:99Z", minutes=70)
    code, lines = steward.start(root, "s2", gh, NOW)
    assert code == 0 and f"previous run s1 ended without Ended (last beat {hm(70)})" in lines
    gh.comment(number, f"Started: steward s3 {hm(10)} beat soon", minutes=0)
    assert steward.start(root, "s4", gh, NOW)[0] == 1


def test_req066_brief_1741_personal_mode_beats_the_sidecar_file_with_no_call(root, monkeypatch):
    """REQ-066 AC1: brief #1741 answer 2 and 6, with `[personal]` the beat edits the `Started:`
    line of the sidecar memory file; no GitHub call; a same-name start is refused."""
    (root / "agk.toml").write_text('[personal]\nforge = "files"\n', encoding="utf-8")
    gh = Beating()
    assert steward.start(root, "s1", gh, NOW - timedelta(minutes=50))[0] == 0
    assert steward.record(root, "Term", "a widget is a part.", gh)[0] == 0
    assert steward.refresh(root, "s1", gh, NOW)[0] == 0
    text = (root / "docs" / "runs" / "steward" / "memory.md").read_text(encoding="utf-8")
    assert f"Started: steward s1 {hm(50)} beat {hm(0)}" in text
    assert "Term: a widget is a part." in text
    code, lines = steward.start(root, "s1", gh, NOW + timedelta(minutes=55))
    assert code == 1 and "already running: s1" in lines[-1]
    assert gh.calls == []
