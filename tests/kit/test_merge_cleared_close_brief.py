"""merge_cleared.py after a merge: a brief closes only when it is really finished.

Brief #992, ADR-0424, REQ-046. A brief with no `Builds:` line closes only when the merged pull
request's body carries the line `Finishes: #<brief>` of its own; a brief with a `Builds:` line
closes when every listed build is named by a merged pull request's title, as before. Saved REST
replies, a fake `gh_api`, no network; invented data only.
"""

from __future__ import annotations

import sys

from test_merge_cleared_after import comment_of, issue, merged_ref, saved_gh
from test_merge_cleared_verdict import REPO, SCRIPTS

sys.path.insert(0, str(SCRIPTS))

import merge_cleared  # noqa: E402

SHA = "c0ffee0123456789abcdef0123456789abcdef01"
BRIEF = 7
PULL = 70
ENDPOINT = f"repos/{REPO}/issues/{BRIEF}"
BUILDS = "Builds: (a) the reader; (b) the writer\n"


def after(monkeypatch, replies: dict, body: str, title: str = "Example (brief #7)"):
    """One run of the step after the record line; the writes it made."""
    writes: list[list[str]] = []
    monkeypatch.setattr(merge_cleared, "gh_api", saved_gh(replies, writes))
    monkeypatch.setattr(merge_cleared.time, "sleep", lambda _s: None)
    merge_cleared.close_after_merge(REPO, PULL, SHA, body, title)
    return writes


def closed(writes: list[list[str]]) -> bool:
    targets = [w[w.index("--method") + 2] for w in writes]
    return (
        targets == [f"{ENDPOINT}/comments", ENDPOINT]
        and comment_of(writes[0]) == f"All builds merged; last #{PULL} {SHA[:12]}"
        and "state=closed" in writes[1]
        and "state_reason=completed" in writes[1]
    )


def test_a_brief_with_no_builds_line_and_brief_alone_stays_open(monkeypatch):
    """REQ-046: brief #992 answers 1 and 4 (a): `Brief: #7` alone leaves the brief open."""
    replies = {ENDPOINT: issue(BRIEF, body="Sentence: an example brief.\n")}
    writes = after(monkeypatch, replies, f"Brief: #{BRIEF}\nAdvances: REQ-046\n")
    assert writes == []


def test_a_brief_with_no_builds_line_and_finishes_closes(monkeypatch):
    """REQ-046: brief #992 answers 1, 3 and 4 (b): `Finishes: #7` on its own line closes it."""
    replies = {ENDPOINT: issue(BRIEF, body="Sentence: an example brief.\n")}
    body = f"Brief: #{BRIEF}\nFinishes: #{BRIEF}\nAdvances: REQ-046\n"
    assert closed(after(monkeypatch, replies, body))


def test_finishes_is_read_as_a_whole_stripped_line(monkeypatch):
    """REQ-046: brief #992 answer 1 (a whole stripped line, as `brief_of` reads `Brief: #n`)."""
    replies = {ENDPOINT: issue(BRIEF, body="Sentence: an example brief.\n")}
    body = f"Brief: #{BRIEF}\n  Finishes: #{BRIEF}  \n"
    assert closed(after(monkeypatch, replies, body))


def test_finishes_of_another_brief_does_not_close(monkeypatch):
    """REQ-046: brief #992 answer 1 (`Finishes:` must name this brief)."""
    replies = {ENDPOINT: issue(BRIEF, body="Sentence: an example brief.\n")}
    writes = after(monkeypatch, replies, f"Brief: #{BRIEF}\nFinishes: #77\n")
    assert writes == []


def test_a_builds_brief_with_only_build_a_merged_stays_open(monkeypatch):
    """REQ-046: brief #992 answers 2 and 4 (c): build (b) unmerged, the brief stays open."""
    replies = {ENDPOINT: issue(BRIEF, body=BUILDS), f"{ENDPOINT}/timeline": []}
    title = f"Example reader (brief #{BRIEF} build (a))"
    writes = after(monkeypatch, replies, f"Brief: #{BRIEF}\n", title)
    assert writes == []


def test_a_builds_brief_with_both_builds_merged_closes(monkeypatch):
    """REQ-046: brief #992 answers 2 and 4 (d): every listed build merged closes it as today."""
    replies = {
        ENDPOINT: issue(BRIEF, body=BUILDS),
        f"{ENDPOINT}/timeline": [merged_ref(5, f"Example reader (brief #{BRIEF} build (a))")],
    }
    title = f"Example writer (brief #{BRIEF} build (b))"
    assert closed(after(monkeypatch, replies, f"Brief: #{BRIEF}\n", title))


def test_finishes_inside_a_sentence_does_not_close(monkeypatch):
    """REQ-046: brief #992 answer 4 (e): `Finishes: #7` inside a sentence is not the line."""
    replies = {ENDPOINT: issue(BRIEF, body="Sentence: an example brief.\n")}
    body = f"Brief: #{BRIEF}\nBuild (b) comes later, so no Finishes: #{BRIEF} here.\n"
    assert after(monkeypatch, replies, body) == []


def test_a_brief_like_846_stays_open_after_its_first_build(monkeypatch):
    """REQ-046: brief #992 Measured (two builds named in a sentence, not a `Builds:` line, and a
    first build whose body has no `Finishes:` line: the brief stays open)."""
    text = "6. Two builds: (a) answers 1 to 3 and (b) answers 4 and 5.\n"
    replies = {ENDPOINT: issue(BRIEF, body=text)}
    body = f"Brief: #{BRIEF}\nBuild (b) and the closing lines come later, so no `Finishes:` here.\n"
    assert after(monkeypatch, replies, body, f"Example (brief #{BRIEF} build (a))") == []
