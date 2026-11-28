"""Tests of the steward's memory digest and the lesson's prevention (SPEC-0059 rules 8, 14, 18
and 20, SPEC-0063 rule 9; brief #2098, ADR-0873; REQ-066 AC1 and AC7).

A recorded `gh` double counts each call and answers from an invented in-memory issue store; no
network, no model, invented data only (example.com).
"""

from __future__ import annotations

import re
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

KIT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KIT / "scripts" / "agk"))

import steward  # noqa: E402

NOW = datetime(2026, 11, 28, 10, 30, tzinfo=UTC)
ROUTE = re.compile(
    r"repos/\{owner\}/\{repo\}/issues(?:/(comments/)?(\d+))?(/comments)?(?:\?(.*))?$"
)


def at(minutes: float) -> str:
    return (NOW - timedelta(minutes=minutes)).strftime("%Y-%m-%dT%H:%M:%SZ")


class GitHub:
    """The recorded double: issues with bodies, comments with their issue; each call is counted."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []
        self.issues: dict[int, dict] = {}
        self.next_id = 5000
        self.clock = 0.0  # minutes before NOW at which a posted comment is created

    def add_issue(self, body: str | None = None, labels=("agk-steward",), number=None) -> int:
        number = number or (max(self.issues, default=0) + 1)
        self.issues[number] = {"number": number, "labels": list(labels), "state": "open"}
        self.issues[number].update({"body": body, "c": []})
        return number

    def comment(self, number: int, body: str, minutes: float = 300) -> dict:
        self.next_id += 1
        item = {"id": self.next_id, "body": body, "created_at": at(minutes), "number": number}
        item["updated_at"] = item["created_at"]
        self.issues[number]["c"].append(item)
        return item

    def view(self, issue: dict) -> dict:
        labels = [{"name": n} for n in issue["labels"]]
        keys = ("number", "state", "body")
        return {**{k: issue[k] for k in keys}, "comments": len(issue["c"]), "labels": labels}

    def out(self, item: dict) -> dict:
        url = f"https://api.example.com/repos/o/r/issues/{item['number']}"
        return {**{k: v for k, v in item.items() if k != "number"}, "issue_url": url}

    def find(self, cid: int) -> dict | None:
        return next((c for i in self.issues.values() for c in i["c"] if c["id"] == cid), None)

    def __call__(self, method: str, endpoint: str, fields: dict | None = None):
        self.calls.append((method, endpoint))
        found = ROUTE.match(endpoint)
        assert found, endpoint
        by_id, number, comments, query = found[1], found[2], found[3], found[4] or ""
        if by_id:
            item = self.find(int(number))
            if item is None:
                return None
            if method == "PATCH":
                item.update(body=fields["body"], updated_at=at(self.clock))
            return self.out(item)
        if number is None and method == "GET":
            shown = [i for i in self.issues.values() if i["state"] == "open"]
            return [self.view(i) for i in shown if "agk-steward" in i["labels"]]
        if number is None and method == "POST":
            new = self.add_issue(fields.get("body"), tuple(fields["labels"]))
            return self.view(self.issues[new])
        issue = self.issues.get(int(number))
        if issue is None:
            return None
        if comments and method == "GET":
            since = re.search(r"since=([^&]+)", query)
            page = int((re.search(r"(?:^|&)page=(\d+)", query) or [0, 1])[1])
            items = [c for c in issue["c"] if not since or c["updated_at"] >= since[1]]
            return [self.out(c) for c in items[(page - 1) * 100 : page * 100]]
        if comments and method == "POST":
            return self.out(self.comment(int(number), fields["body"], minutes=self.clock))
        if method == "PATCH":
            issue.update(fields)
            return self.view(issue)
        if method == "GET":
            return self.view(issue)
        raise AssertionError((method, endpoint))

    def counted(self) -> int:
        return len(self.calls)


@pytest.fixture
def root(tmp_path, monkeypatch):
    monkeypatch.setenv("AGK_STEWARD_CACHE", str(tmp_path / "clone-a.json"))
    (tmp_path / "agk.toml").write_text('default_branch = "main"\n', encoding="utf-8")
    return tmp_path


def fresh_clone(monkeypatch, tmp_path, name: str) -> None:
    """Another clone: an empty cache, as every cloud start has."""
    monkeypatch.setenv("AGK_STEWARD_CACHE", str(tmp_path / f"{name}.json"))


def memory_fixture(gh: GitHub, number: int) -> None:
    """About #1944's shape: run markers, decisions, lessons, drafts of many lines, a daily."""
    for n in range(30):
        gh.comment(
            number, f"Decision: Q-9-{n} the export keeps column {n} (evidence: a.md:{n})", 900 - n
        )
    for n in range(5):
        body = f"Draft brief: F-s-{n} A draft of five days ago\n" + "\n".join(
            f"Line {k} of the draft body, carried at every start before." for k in range(48)
        )
        gh.comment(number, body, 800 - n)
    for n in range(35):
        gh.comment(number, f"Started: steward r{n} {at(700 - n)[:16]}Z", 700 - n)
        gh.comment(number, f"Ended: steward r{n} calls 4; tokens not shown", 699.5 - n)
    gh.comment(number, "Onboarded: the project on 2026-11-20 (evidence: docs/a.md)", 600)
    gh.comment(number, "Person: technical: a shop for example.com", 599)
    gh.comment(number, "Lesson: a time was guessed\nPrevent: brief #9001", 598)
    gh.comment(number, "Daily: 2026-11-27 four answers", 597)


def start(root, gh, session="s1", now=NOW):
    return steward.start(root, session, gh, now)


def run_once(root, gh, session="s1", now=NOW):
    """One pass: a start and its end, which writes the digest."""
    code, lines = start(root, gh, session, now)
    assert code == 0, lines
    assert steward.end(root, session, gh, now)[0] == 0
    return lines


def body_of(gh, number) -> str:
    return gh.issues[number]["body"] or ""


# --- answers 3, 4 and 10: the digest is read in three calls ---------------------------------------


def test_req066_a_cold_start_with_a_digest_makes_three_calls_and_prints_at_most_80_lines(
    root, tmp_path, monkeypatch
):
    """REQ-066 AC1: brief #2098 answers 4 and 10, a fresh clone reads the listing, one since page,
    and posts its `Started:`; it prints at most 80 lines and 10,000 characters."""
    gh = GitHub()
    number = gh.add_issue("Continues #1515.")
    memory_fixture(gh, number)
    run_once(root, gh, "s1", NOW - timedelta(minutes=30))
    assert body_of(gh, number).startswith("Memory in force (schema 1, through ")
    fresh_clone(monkeypatch, tmp_path, "clone-b")
    gh.calls.clear()
    code, lines = start(root, gh, "s2")
    assert code == 0
    assert [m for m, _ in gh.calls] == ["GET", "GET", "POST"]
    assert "since=" in gh.calls[1][1]
    assert len(lines) <= 80 and len("\n".join(lines)) <= 10000
    assert all(len(line) <= 200 for line in lines)
    assert not any("Line 7 of the draft body" in line for line in lines)
    assert any("F-s-4" in line for line in lines)


def test_req066_a_start_with_no_digest_reads_every_page_and_writes_one(root):
    """REQ-066 AC7: brief #2098 answer 5, a body that is no digest is rebuilt from every page."""
    gh = GitHub()
    number = gh.add_issue("Continues #1515.")
    for n in range(250):
        gh.comment(number, f"Term: word{n} means thing{n}.", 900 - n)
    code, lines = start(root, gh)
    assert code == 0
    pages = [e for m, e in gh.calls if m == "GET" and f"/{number}/comments" in e]
    assert len(pages) == 3 and not any("since=" in e for e in pages)
    assert "digest: rebuilt (missing)" in lines
    assert body_of(gh, number).startswith("Memory in force (schema 1")
    assert ("PATCH", f"repos/{{owner}}/{{repo}}/issues/{number}") in gh.calls


def test_req066_the_first_start_of_a_day_finds_a_changed_note_and_a_hand_edit(
    root, tmp_path, monkeypatch
):
    """REQ-066 AC7: brief #2098 answer 5, the daily check rebuilds and names the drift."""
    gh = GitHub()
    number = gh.add_issue()
    note = gh.comment(number, "Term: a widget is a part.", 900)
    gh.comment(number, "Gap: no source for the totals.", 899)
    run_once(root, gh, "s1", NOW - timedelta(days=1))
    note["body"] = "Term: a widget is a tool."  # changed with no newer updated_at: only a full read
    fresh_clone(monkeypatch, tmp_path, "clone-b")
    code, lines = start(root, gh)
    assert code == 0 and "digest: drift Term 1" in lines
    assert "a widget is a tool" in body_of(gh, number)
    steward.end(root, "s1", gh, NOW)
    gh.issues[number]["body"] = body_of(gh, number).replace("a widget", "a gizmo")
    fresh_clone(monkeypatch, tmp_path, "clone-c")
    code, lines = start(root, gh, "s3", NOW + timedelta(minutes=5))
    assert code == 0 and "digest: rebuilt (edited)" in lines


def test_req066_a_note_read_twice_is_folded_once_and_an_edit_is_folded_again(
    root, tmp_path, monkeypatch
):
    """REQ-066 AC7: brief #2098 answer 5, the fold is by comment id and `updated_at`."""
    gh = GitHub()
    number = gh.add_issue()
    note = gh.comment(number, "Risk: the import may double rows.", 30)
    run_once(root, gh, "s1", NOW - timedelta(minutes=20))
    note.update(body="Risk: the import may drop rows.", updated_at=at(1))
    fresh_clone(monkeypatch, tmp_path, "clone-b")
    assert start(root, gh)[0] == 0
    steward.end(root, "s1", gh, NOW)
    text = body_of(gh, number)
    assert text.count(f"{note['id']} ") == 1 and "drop rows" in text and "double rows" not in text


# --- answer 6: the roll-over carries what is in force ---------------------------------------------


def test_req066_a_roll_over_carries_what_is_in_force_and_links_the_new_issue(root):
    """REQ-066 AC7: brief #2098 answer 6, `Onboarded:`, `Person:`, a decision and an open lesson
    carry into the new issue's body, and the old issue says where the memory continues."""
    gh = GitHub()
    old = gh.add_issue()
    kept = [
        gh.comment(old, "Onboarded: the project on 2026-11-02", 990),
        gh.comment(old, "Person: business: a shop for example.com", 989),
        gh.comment(old, "Decision: Q-7-2 keep two columns (evidence: the owner's answer)", 988),
        gh.comment(old, "Lesson: a stale state was read\nPrevent: brief #9002", 987),
    ]
    gh.comment(old, "Owner question: Q-7-1 Should the report go out on Friday?", 986)
    for n in range(495):
        gh.comment(old, f"Term: word{n} means thing{n}.", 900)
    assert start(root, gh)[0] == 0
    new = max(gh.issues)
    assert new != old and gh.issues[old]["state"] == "closed"
    text = body_of(gh, new)
    assert text.startswith("Memory in force (schema 1")
    for item in kept:
        assert f"{item['id']} #{old} " in text
    assert f"Chain: #{old} and this issue" in text
    assert gh.issues[old]["c"][-1]["body"].startswith(f"Memory continued in #{new}")
    first = gh.issues[new]["c"][0]["body"]
    assert f"#{old}" in first and "Q-7-1" in first


def test_req066_review_mode_solo_asks_no_person_question_after_a_roll_over(root):
    """REQ-066 AC7: brief #2098 answer 8, the Person question reads the digest's `Person:`."""
    (root / "agk.toml").write_text('default_branch = "main"\nreview_mode = "solo"\n', "utf-8")
    gh = GitHub()
    old = gh.add_issue()
    gh.comment(old, "Person: technical: a shop for example.com", 990)
    for n in range(499):
        gh.comment(old, f"Term: word{n} means thing{n}.", 900)
    code, lines = start(root, gh)
    assert code == 0 and max(gh.issues) != old
    assert not any(line.startswith("ask: ") for line in lines)


# --- answers 1 and 2: a lesson names its prevention; a repeat is counted --------------------------


def started_memory(root, gh, *bodies) -> int:
    number = gh.add_issue()
    for n, body in enumerate(bodies):
        gh.comment(number, body, 500 - n)
    assert start(root, gh)[0] == 0
    return number


@pytest.mark.parametrize(
    "text",
    [
        "a guessed time\nPrevent: done check scripts/agk/check_x.py abc1234",
        "a guessed time\nPrevent: done tool scripts/agk/steward.py #2109",
        "a guessed time\nPrevent: done skill skills/agk-x/SKILL.md 0123abc",
        "a guessed time\nPrevent: brief #9003",
        "a guessed time\nPrevent: draft F-s-1",
    ],
)
def test_req066_each_prevention_form_is_recorded_in_the_kit(root, text):
    """REQ-066 AC7: brief #2098 answer 1, each form passes in the kit."""
    (root / "kit").mkdir()
    (root / "kit" / "manifest.json").write_text("{}", encoding="utf-8")
    gh = GitHub()
    number = started_memory(root, gh, "Draft brief: F-s-1 a draft\nSentence: x.")
    code, lines = steward.record(root, "Lesson", text, gh)
    assert code == 0, lines
    assert gh.issues[number]["c"][-1]["body"].startswith("Lesson: a guessed time\nPrevent: ")


@pytest.mark.parametrize(
    "text",
    [
        "x",
        "a guessed time\nPrevent: soon",
        "a guessed time\nPrevent: draft F-s-9",  # not a recorded draft
        "a guessed time\nPrevent: done check scripts/agk/check_x.py later",
    ],
)
def test_req066_a_lesson_without_a_known_prevention_is_refused_naming_the_line(root, text):
    """REQ-066 AC7: brief #2098 answer 1, refused naming `the Prevent: line of a Lesson`."""
    gh = GitHub()
    number = started_memory(root, gh)
    count = len(gh.issues[number]["c"])
    code, lines = steward.record(root, "Lesson", text, gh)
    assert code == 2 and "the Prevent: line of a Lesson" in lines[0]
    assert len(gh.issues[number]["c"]) == count


def test_req066_a_leading_lesson_word_is_written_once(root):
    """REQ-066 AC7: brief #2098 answer 1, `Lesson: Lesson:` is the kind written twice."""
    gh = GitHub()
    number = started_memory(root, gh)
    assert (
        steward.record(root, "Lesson", "Lesson: Lesson: a guess\nPrevent: brief #9004", gh)[0] == 0
    )
    assert gh.issues[number]["c"][-1]["body"].startswith("Lesson: a guess\n")


def test_req066_in_a_project_a_kit_prevention_needs_a_kit_defect(root):
    """REQ-066 AC7: brief #2098 answer 7, a project's lesson naming a kit path is a kit defect."""
    gh = GitHub()
    number = started_memory(root, gh)
    code, lines = steward.record(
        root, "Lesson", "a miss\nPrevent: done tool scripts/agk/steward.py abc1234", gh
    )
    assert code == 2 and "kit-defect" in lines[0] and "the Prevent: line" in lines[0]
    assert steward.record(root, "Lesson", "a miss\nPrevent: kit-defect #77", gh)[0] == 0
    assert gh.issues[number]["c"][-1]["body"].startswith("Lesson: a miss\nPrevent: kit-defect #77")


def test_req066_a_repeat_is_counted_and_never_edits_the_first_note(root, tmp_path, monkeypatch):
    """REQ-066 AC7: brief #2098 answer 2, `--repeat` writes a new note; the digest counts it; the
    start names it to the owner from the second sighting; the open brief gets one comment."""
    gh = GitHub()
    brief = gh.add_issue("A brief.", labels=("agk-brief",))
    number = started_memory(root, gh, f"Lesson: a time was guessed\nPrevent: brief #{brief}")
    first = gh.issues[number]["c"][0]
    original = first["body"]
    code, lines = steward.record(root, "Lesson", "guessed again", gh, repeat=first["id"])
    assert code == 0, lines
    assert gh.issues[number]["c"][-1]["body"].startswith(f"Lesson: repeat of {first['id']}: ")
    assert first["body"] == original
    assert gh.issues[brief]["c"][-1]["body"].startswith(
        f"Lesson repeat: {first['id']} seen 2 times"
    )
    steward.end(root, "s1", gh, NOW)
    assert f"{first['id']} #{number} " in body_of(gh, number)
    assert "seen 2" in body_of(gh, number)
    fresh_clone(monkeypatch, tmp_path, "clone-b")
    code, lines = start(root, gh, "s2", NOW + timedelta(minutes=5))
    assert f"owner: lesson {first['id']} seen 2 times; prevention brief #{brief}" in lines


def test_req066_a_repeat_of_an_unknown_id_or_a_held_prevention_is_refused(root):
    """REQ-066 AC7: brief #2098 answer 2, `--repeat` names a lesson of the digest; a repeat after a
    `done` prevention or a closed brief needs a new `Prevent:` line."""
    gh = GitHub()
    closed = gh.add_issue("A brief.", labels=("agk-brief",))
    gh.issues[closed]["state"] = "closed"
    number = started_memory(
        root,
        gh,
        "Lesson: a guess\nPrevent: done check scripts/agk/check_x.py abc1234",
        f"Lesson: a stale read\nPrevent: brief #{closed}",
        "Term: a widget is a part.",
    )
    done, gone, term = (c["id"] for c in gh.issues[number]["c"][:3])
    for target in (term, 1):
        code, lines = steward.record(root, "Lesson", "again", gh, repeat=target)
        assert code == 2 and "--repeat" in lines[0]
    for target in (done, gone):
        code, lines = steward.record(root, "Lesson", "again", gh, repeat=target)
        assert code == 2 and "the Prevent: line" in lines[0]
        text = "again\nPrevent: brief #9005"
        assert steward.record(root, "Lesson", text, gh, repeat=target)[0] == 0


def test_req066_the_same_prevention_warns_and_prevent_of_covers_an_old_lesson(root):
    """REQ-066 AC7: brief #2098 answer 2 and Q-S4-6, a warning, never a refusal; `--prevent-of`."""
    gh = GitHub()
    number = started_memory(root, gh, "Lesson: a guess\nPrevent: brief #9006", "Lesson: an old one")
    code, lines = steward.record(root, "Lesson", "another\nPrevent: brief #9006", gh)
    old_id = gh.issues[number]["c"][0]["id"]
    assert code == 0
    assert any(
        line.startswith(f"warning: lesson {old_id} names the same prevention") for line in lines
    )
    bare = gh.issues[number]["c"][1]["id"]
    steward.end(root, "s1", gh, NOW)
    assert "prevention none" in body_of(gh, number)
    assert start(root, gh, "s2", NOW + timedelta(minutes=2))[0] == 0
    text = "Prevent: brief #9007"
    assert steward.record(root, "Lesson", text, gh, prevent_of=bare)[0] == 0
    assert gh.issues[number]["c"][-1]["body"].startswith(f"Lesson: prevention of {bare}\n")
    steward.end(root, "s2", gh, NOW + timedelta(minutes=3))
    assert "prevention none" not in body_of(gh, number)


# --- answer 4: show and find ---------------------------------------------------------------------


def test_req066_show_makes_one_get_and_refuses_a_comment_off_the_memory(root):
    """REQ-066 AC1: brief #2098 answer 4, `show <id>` is one GET; `find` makes no call."""
    gh = GitHub()
    other = gh.add_issue("A brief.", labels=("agk-brief",))
    stray = gh.comment(other, "Gap: not memory.", 10)
    number = started_memory(root, gh, "Draft brief: F-s-1 a long draft\nSentence: the whole text.")
    note = gh.issues[number]["c"][0]
    gh.calls.clear()
    code, lines = steward.show(root, note["id"], gh)
    assert code == 0 and "Sentence: the whole text." in lines
    assert gh.calls == [("GET", f"repos/{{owner}}/{{repo}}/issues/comments/{note['id']}")]
    code, lines = steward.show(root, stray["id"], gh)
    assert code == 2 and "show" in lines[0] and "not memory" not in " ".join(lines)
    gh.calls.clear()
    code, lines = steward.find(root, "long draft")
    assert code == 0 and any(str(note["id"]) in line for line in lines) and gh.calls == []


# --- answer 8: settings and modes -----------------------------------------------------------------


def test_req066_personal_mode_writes_the_sidecar_digest_and_posts_nothing(root):
    """REQ-066 AC7: brief #2098 answer 8, `[personal]` keeps a digest file beside `memory.md`."""
    (root / "agk.toml").write_text('[personal]\nforge = "files"\n', encoding="utf-8")
    gh = GitHub()
    assert start(root, gh)[0] == 0
    assert steward.record(root, "Lesson", "a miss\nPrevent: kit-defect #77", gh)[0] == 0
    assert steward.end(root, "s1", gh, NOW)[0] == 0
    assert gh.calls == []
    digest = root / "docs" / "runs" / "steward" / "memory-digest.md"
    assert digest.read_text(encoding="utf-8").startswith("Memory in force (schema 1")
    code, lines = steward.show(root, 2, gh)
    assert code == 0 and "Prevent: kit-defect #77" in lines and gh.calls == []


def test_req066_team_mode_end_reads_the_body_before_it_writes_it(root, tmp_path, monkeypatch):
    """REQ-066 AC7: brief #2098 answers 8 and 9, a newer digest by another steward is folded."""
    (root / "agk.toml").write_text('default_branch = "main"\nreview_mode = "team"\n', "utf-8")
    gh = GitHub()
    number = gh.add_issue()
    mine = gh.comment(number, "Term: a widget is a part.", 50)
    assert start(root, gh, "s1", NOW - timedelta(minutes=40))[0] == 0
    gh.calls.clear()
    assert steward.end(root, "s1", gh, NOW - timedelta(minutes=39))[0] == 0
    methods = [m for m, e in gh.calls if e == f"repos/{{owner}}/{{repo}}/issues/{number}"]
    assert methods == ["GET", "PATCH"]
    assert f"{mine['id']} " in body_of(gh, number)


@pytest.mark.parametrize("key", ["digest", "digest_limit", "memory"])
def test_req066_no_new_steward_setting_is_read(root, key):
    """REQ-066 AC1: brief #2098 answer 8 and Q-S4-2, a new `[steward]` key stays refused."""
    from config import StewardSettingError, steward_settings

    (root / "agk.toml").write_text(f"[steward]\n{key} = 1\n", encoding="utf-8")
    with pytest.raises(StewardSettingError, match=rf"steward\.{key}\)"):
        steward_settings(root)


@pytest.mark.parametrize(
    "toml",
    [
        "[steward]\nauto_file = 2\nfix_briefs = true\n",
        'execution = "local"\n',
        'execution = "hosted"\n',
        '[kit]\nlayout = "plugin"\n',
    ],
)
def test_req066_the_digest_is_the_same_under_each_setting(root, toml, tmp_path, monkeypatch):
    """REQ-066 AC1: brief #2098 answer 8, the same three calls under each setting."""
    (root / "agk.toml").write_text('default_branch = "main"\n' + toml, encoding="utf-8")
    gh = GitHub()
    number = gh.add_issue()
    gh.comment(number, "Term: a widget is a part.", 50)
    run_once(root, gh, "s1", NOW - timedelta(minutes=30))
    fresh_clone(monkeypatch, tmp_path, "clone-b")
    gh.calls.clear()
    assert start(root, gh, "s2")[0] == 0
    assert [m for m, _ in gh.calls] == ["GET", "GET", "POST"]


def test_req066_an_unwritable_cache_costs_reads_never_a_note(root, tmp_path, monkeypatch):
    """REQ-066 AC1: brief #2098 answer 8, `AGK_STEWARD_CACHE` that cannot be written."""
    gh = GitHub()
    number = gh.add_issue()
    gh.comment(number, "Term: a widget is a part.", 50)
    (tmp_path / "a-file").write_text("not a folder", encoding="utf-8")
    monkeypatch.setenv("AGK_STEWARD_CACHE", str(tmp_path / "a-file" / "cache.json"))
    code, lines = start(root, gh)
    assert code == 0 and any("a widget" in line for line in lines)


# --- answer 11: the class stays closed ------------------------------------------------------------


def test_req066_the_summary_is_built_from_the_digest_only(root, monkeypatch):
    """REQ-066 AC7: brief #2098 answer 11, the start's summary reads the digest's notes alone."""
    gh = GitHub()
    number = gh.add_issue()
    memory_fixture(gh, number)
    seen = []
    real = steward.summary
    monkeypatch.setattr(steward, "summary", lambda memory: seen.append(memory) or real(memory))
    code, lines = start(root, gh)
    assert code == 0 and len(seen) == 1
    bodies = [c["body"] for c in seen[0]["comments"]]
    assert all("\nLine 1 of the draft body" not in b for b in bodies)
    assert all(len(line) <= 200 for line in lines) and len(lines) <= 80


def test_req066_no_kit_script_but_steward_writes_the_memory_body():
    """REQ-066 AC7: brief #2098 answer 11, only `steward.py` PATCHes an issue body."""
    patch = re.compile(r'"PATCH",\s*f?"\{ISSUES\}/\{[^}]+\}",\s*\{\s*"body"')
    writers = [
        path.name
        for path in sorted((KIT / "scripts" / "agk").glob("*.py"))
        if patch.search(path.read_text(encoding="utf-8"))
    ]
    assert writers == ["steward.py"]


def test_req066_the_agent_file_reads_the_digest_and_never_pages_the_memory():
    """REQ-066 AC7: brief #2098 answer 4, the role file's reading rule."""
    text = (KIT / ".claude" / "agents" / "steward.md").read_text(encoding="utf-8")
    assert (
        "never read the memory issue" in text and "`steward.py show <id>` fetches one note" in text
    )
    assert "a `Lesson:` with its `Prevent:`" in text


# --- answer 9 (Q-2098-2): a brief prevention is checked from the daily's issue read ---------------


def test_req066_the_daily_issue_read_gives_each_brief_prevention_its_state(root):
    """REQ-066 AC7: brief #2098 answer 9 (Q-2098-2), the issues `steward_daily` already lists
    mark a `Prevent: brief #<n>` open, closed or not an issue when the digest is written; no call
    is added, and a repeat of a lesson whose brief that read holds makes no GET of it."""
    import steward_daily

    gh = GitHub()
    number = started_memory(
        root,
        gh,
        "Lesson: a guess\nPrevent: brief #9011",
        "Lesson: a stale read\nPrevent: brief #9012",
        "Lesson: a wrong path\nPrevent: brief #9013",
    )
    gh.add_issue("A brief.", labels=("agk-brief",), number=9011)
    cache = steward.load_cache(root)
    listed = [
        {"number": 9011, "state": "open"},
        {"number": 9012, "state": "closed"},
        {"number": 9013, "state": "open", "pull_request": {}},
    ]

    def daily_gh(method, endpoint, fields=None):
        if method == "GET" and "issues?state=all" in endpoint:
            return listed
        if method == "GET":
            return []
        return gh(method, endpoint, fields)

    assert steward_daily.post_daily(cache, daily_gh, NOW)[0] == 0
    steward.save_cache(root, cache)
    steward.end(root, "s1", gh, NOW)
    text = body_of(gh, number)
    assert "prevention brief #9011 (open)" in text
    assert "prevention brief #9012 (closed)" in text
    assert "prevention brief #9013 (not an issue)" in text
    open_id, closed_id = (c["id"] for c in gh.issues[number]["c"][:2])
    assert start(root, gh, "s2", NOW + timedelta(minutes=2))[0] == 0
    gh.calls.clear()
    code, lines = steward.record(root, "Lesson", "again", gh, repeat=closed_id)
    assert code == 2 and "the Prevent: line" in lines[0] and gh.calls == []
    assert steward.record(root, "Lesson", "again", gh, repeat=open_id)[0] == 0
    assert not any(e.endswith("/issues/9011") for m, e in gh.calls if m == "GET")
    assert gh.issues[9011]["c"][-1]["body"].startswith(f"Lesson repeat: {open_id} seen 2 times")
