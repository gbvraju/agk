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
    assert code == 0 and gh.counted() == 3
    comments = [e for _, e in gh.calls if "/comments" in e]
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
    assert code == 0 and gh.counted() == 3
    assert lines == ["refresh: nothing new since " + NOW.strftime("%Y-%m-%dT%H:%M:%SZ")]
    assert not any(m != "GET" for m, _ in gh.calls)


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
    assert code == 0 and gh.counted() == 3
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
    assert steward.refresh(root, "s1", gh, NOW)[0] == 0 and gh.counted() == 3
