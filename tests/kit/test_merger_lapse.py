"""merge_cleared.py: cleared work merges when the conductor lapses (brief #1615, ADR-0684).

REQ-046, amendment 212 of SPEC-0039: in local mode the merger's sweep merges a cleared head once
the conductor's lease on the plan issue has been free for `[flow] conductor_lapse_minutes`, with
the verdict's local evidence and green GitHub checks for that head; the owner-only holds stay the
owner's. Saved answers only; no network, invented logins, example.com.
"""

from __future__ import annotations

import datetime
import sys
import tomllib
from pathlib import Path

import pytest
from test_merge_cleared_verdict import ON, comment, evidence, repo, toml
from test_merger_sweep import NOW, RECORD, a_pull, clearing, sha_of

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "agk"))

import merge_cleared  # noqa: E402

import config  # noqa: E402

AUTHOR = "conductor-two"
REFUSAL = "conductor_lapse_minutes of the flow table must be a whole number from 15 to 1440"
LAPSE = ON + "plan_issue = 661\nconductor_lapse_minutes = 30\n"
REPO = "example-owner/example-repo"


def at(minutes_ago: int) -> str:
    return (NOW - datetime.timedelta(minutes=minutes_ago)).strftime("%Y-%m-%dT%H:%M:%SZ")


def marker(word: str, minutes_ago: int, login: str = AUTHOR) -> dict:
    stamp = at(minutes_ago)
    return {**comment(f"Conductor: {word} {stamp} c1\n", login), "created_at": stamp}


def flow(extra: str = "") -> dict:
    return tomllib.loads(toml(LAPSE + extra, local=True))


def lapsed(monkeypatch, comments, data=None, unreadable=False) -> bool:
    def pages(endpoint, what, key=None):
        if unreadable:
            raise merge_cleared.Unreadable(what)
        assert endpoint == f"repos/{REPO}/issues/661/comments"
        return comments

    monkeypatch.setattr(merge_cleared, "read_pages", pages)
    return merge_cleared.lapsed(flow() if data is None else data, REPO, NOW, [AUTHOR])


# --- the setting ----------------------------------------------------------------------------


def test_the_setting_is_off_when_absent_and_a_whole_number_of_minutes_when_set():
    """REQ-046: brief #1615 answer 3 (absent means off; 15 to 1440 is the wait)."""
    assert merge_cleared.lapse_setting(tomllib.loads(toml(ON))) is None
    assert merge_cleared.lapse_setting(flow()) == 30
    for minutes in (15, 1440):
        data = tomllib.loads(toml(ON + f"conductor_lapse_minutes = {minutes}\n"))
        assert merge_cleared.lapse_setting(data) == minutes


@pytest.mark.parametrize("value", ["14", "1441", "0", '"30"', "true", "30.5", "-30"])
def test_a_bad_setting_is_refused_naming_the_setting_never_the_value(value):
    """REQ-046: brief #1615 answer 3 (anything else is refused)."""
    data = tomllib.loads(toml(ON + f"conductor_lapse_minutes = {value}\n"))
    with pytest.raises(merge_cleared.Refused) as err:
        merge_cleared.lapse_setting(data)
    assert str(err.value) == merge_cleared.LAPSE_REFUSAL  # one fixed line: no value in it
    assert str(err.value).startswith(REFUSAL)


def test_the_flow_table_knows_the_setting():
    """REQ-046: brief #1615 answer 3 (config.py's known keys of `[flow]`)."""
    assert "conductor_lapse_minutes" in config.TABLE_KEYS["flow"]


def test_this_repository_runs_solo_with_a_thirty_minute_lapse():
    """REQ-046, REQ-069: brief #1615 answer 1 (the owner's settings, by ADR-0684)."""
    data = tomllib.loads((ROOT / "agk.toml").read_text(encoding="utf-8"))
    assert data["review_mode"] == "solo" and data["execution"] == "local"
    assert data["flow"]["conductor_lapse_minutes"] == 30
    assert merge_cleared.lapse_setting(data) == 30


# --- the lapse --------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("comments", "expected"),
    [
        ([marker("released", 31)], True),
        ([marker("released", 29)], False),
        ([marker("active", 41)], True),  # the lease ended 31 minutes ago
        ([marker("active", 39)], False),  # it ended 29 minutes ago
        ([marker("active", 5)], False),  # held, stalled or not (`lease_stall` is not a lapse)
        ([marker("released", 90), marker("active", 3)], False),  # renewed
        ([], False),  # no lease was ever taken: nothing to measure
        ([marker("released", 90, login="builder-one")], False),  # not a listed verdict author
    ],
    ids=[
        "released",
        "released-young",
        "expired",
        "expired-young",
        "held",
        "renewed",
        "none",
        "unlisted",
    ],
)
def test_a_lapse_is_a_lease_free_for_the_setting_s_minutes(monkeypatch, comments, expected):
    """REQ-046: brief #1615 answer 1 (no holder for the minutes past the lease's end)."""
    assert lapsed(monkeypatch, comments) is expected


def test_unreadable_plan_issue_comments_are_never_a_lapse(monkeypatch):
    """REQ-046: brief #1615 answer 5 (counted as not lapsed)."""
    assert lapsed(monkeypatch, [marker("released", 90)], unreadable=True) is False


@pytest.mark.parametrize(
    "main",
    [
        toml(ON + "plan_issue = 661\n", local=True),
        toml(ON + "conductor_lapse_minutes = 30\n", local=True),
    ],
    ids=["setting-absent", "no-plan-issue"],
)
def test_no_setting_or_no_plan_issue_is_never_a_lapse(monkeypatch, main):
    """REQ-046: brief #1615 answer 3 (absent is off; no plan issue, no lease to read)."""
    assert lapsed(monkeypatch, [marker("released", 90)], tomllib.loads(main)) is False


# --- the sweep ------------------------------------------------------------------------------


class Sweep:
    def __init__(self, monkeypatch, plan, issues=(RECORD,), line="merged " + "ab" * 6):
        self.ran: list[tuple[int, str, bool]] = []

        def pages(endpoint, what, key=None):
            if "/pulls" in endpoint:
                return [a_pull(5)]
            return plan if "/issues/661/" in endpoint else list(issues)

        def guarded(root, number, sha, lapse=False):
            self.ran.append((number, sha, lapse))
            return f"merge-cleared #{number} {sha[:12]}: {line}", merge_cleared.EXIT_CLEARED

        monkeypatch.setattr(merge_cleared, "read_pages", pages)
        monkeypatch.setattr(merge_cleared, "read_comments", lambda r, n: clearing(n, 90))
        monkeypatch.setattr(merge_cleared, "guarded", guarded)
        monkeypatch.setattr(merge_cleared, "refresh_status", lambda *args: None)
        monkeypatch.setattr(merge_cleared, "clock", lambda: NOW)
        monkeypatch.setattr(merge_cleared, "repo_of", lambda root: REPO)
        monkeypatch.setattr(merge_cleared, "sweep_authors", lambda root: [AUTHOR])


def run_sweep(tmp_path, capsys, main=None) -> list[str]:
    root = repo(tmp_path, main or toml(LAPSE, local=True), origin="")
    assert merge_cleared.main(["--sweep"], root) == 0
    return capsys.readouterr().out.splitlines()


def test_a_lapse_merges_the_cleared_head_in_local_mode(tmp_path, monkeypatch, capsys):
    """REQ-046: brief #1615 `Measured:` (the sweep merges once the lease is free 30 minutes)."""
    world = Sweep(monkeypatch, [marker("released", 31)])
    lines = run_sweep(tmp_path, capsys)
    assert world.ran == [(5, sha_of(5), True)]
    assert lines[0].endswith(": merged " + "ab" * 6)


@pytest.mark.parametrize(
    "plan", [[marker("active", 5)], [marker("released", 10)], []], ids=["fresh", "young", "none"]
)
def test_no_lapse_keeps_the_conductor_s_merge(tmp_path, monkeypatch, capsys, plan):
    """REQ-046: brief #1615 answers 1 and 5 (a fresh or stalled lease merges nothing)."""
    world = Sweep(monkeypatch, plan)
    lines = run_sweep(tmp_path, capsys)
    assert world.ran == []
    assert lines[0].endswith("local mode: the conductor merges")


def test_the_open_record_issue_stops_a_lapse_merge(tmp_path, monkeypatch, capsys):
    """REQ-046: brief #1615 answer 5 (Actions blocked: no lapse merge)."""
    local = {"number": 42, "title": "Local mode since 2026-11-04", "labels": []}
    world = Sweep(monkeypatch, [marker("released", 90)], issues=(RECORD, local))
    run_sweep(tmp_path, capsys)
    assert world.ran == []


def test_an_owner_only_hold_names_the_owner_s_command(tmp_path, monkeypatch, capsys):
    """REQ-046: brief #1615 answer 2 (protected class and release stay the owner's)."""
    line = "held: protected class constitution/ (rule 5); would-be merge: pass"
    Sweep(monkeypatch, [marker("released", 90)], line=line)
    lines = run_sweep(tmp_path, capsys)
    unmerged = [x for x in lines if x.startswith("UNMERGED #5")]
    assert unmerged and unmerged[0].endswith(
        "the owner merges with python3 scripts/agk/merge_cleared.py --pr 5 --owner"
    )


# --- the gate -------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("main", "word"),
    [
        (toml(LAPSE, local=True), "on"),
        (toml(ON, local=True), "off"),
        (toml(LAPSE.replace(ON, ""), local=True), "off"),
        ('forge = "files"\n' + toml(LAPSE, local=True), "off"),
        ("paused = true\n" + toml(LAPSE, local=True), "off"),
        (toml(ON + "conductor_lapse_minutes = 5\n", local=True), "off"),
    ],
    ids=["lapse-rule", "no-setting", "auto-merge-off", "personal", "paused", "bad-setting"],
)
def test_the_gate_starts_the_sweep_where_the_lapse_rule_is_on(tmp_path, capsys, main, word):
    """REQ-046: brief #1615 answer 1 (the gate reads files only; the sweep reads the lease)."""
    root = repo(tmp_path, main, origin="")
    assert merge_cleared.main(["--sweep-gate"], root) == 0
    assert capsys.readouterr().out.strip() == word


def test_the_variable_is_not_offered_while_the_lapse_rule_is_on():
    """REQ-046: brief #1615 answer 3 (`AGK_MERGER = off` would stop the lapse sweep)."""
    assert merge_cleared.merger_variable_line(flow(), None, 96) is None
    off = tomllib.loads(toml(ON, local=True))
    assert merge_cleared.merger_variable_line(off, None, 96)[0] == "offer"


# --- the guarded command under a lapse ----------------------------------------------------------

HEAD = sha_of(5)


def checks(monkeypatch, names=("proof", "governance"), conclusion="success"):
    runs = [
        {"name": n, "status": "completed", "conclusion": conclusion, "id": i}
        for i, n in enumerate(names)
    ]

    def pages(endpoint, what, key=None):
        return runs if endpoint.endswith("/check-runs") else []

    monkeypatch.setattr(merge_cleared, "read_pages", pages)


def test_a_lapse_merge_needs_local_evidence_and_green_github_checks(monkeypatch):
    """REQ-046: brief #1615 answer 1 (`local_evidence` and `ci_evidence` both)."""
    verdict = comment(f"Verdict: cleared {HEAD}\n" + evidence(HEAD))
    required = ["proof", "governance"]
    checks(monkeypatch)
    merge_cleared.lapse_evidence(REPO, verdict, [verdict], HEAD, [], required)
    checks(monkeypatch, names=("proof",))
    with pytest.raises(merge_cleared.Held, match="a required check is missing"):
        merge_cleared.lapse_evidence(REPO, verdict, [verdict], HEAD, [], required)
    checks(monkeypatch, conclusion="failure")
    with pytest.raises(merge_cleared.Held, match="a required check is red"):
        merge_cleared.lapse_evidence(REPO, verdict, [verdict], HEAD, [], required)
    bare = comment(f"Verdict: cleared {HEAD}\n")
    checks(monkeypatch)
    with pytest.raises(merge_cleared.Held, match="no local evidence"):
        merge_cleared.lapse_evidence(REPO, bare, [bare], HEAD, [], required)


def test_a_lease_renewed_during_the_sweep_holds_under_the_lock(monkeypatch):
    """REQ-046: brief #1615 answer 5 (read again under `merge_lock`, and held)."""
    monkeypatch.setattr(merge_cleared, "read_pages", lambda e, w, k=None: [marker("active", 1)])
    monkeypatch.setattr(merge_cleared, "clock", lambda: NOW)
    with pytest.raises(merge_cleared.Held, match="conductor_lapse_minutes"):
        merge_cleared.lapse_recheck(flow(), REPO, [AUTHOR])
    monkeypatch.setattr(merge_cleared, "read_pages", lambda e, w, k=None: [marker("released", 60)])
    merge_cleared.lapse_recheck(flow(), REPO, [AUTHOR])


def test_the_record_line_says_the_sweep_merged_after_a_lapse(monkeypatch):
    """REQ-046: brief #1615 answer 1 (each lapse merge's record line says so)."""
    posted: list[list[str]] = []

    def write_once(args, env=None):
        posted.append(args)
        return 0, "", ""

    monkeypatch.setattr(merge_cleared, "write_once", write_once)
    verdict = {"id": 7, "html_url": "https://example.com/pull/5#issuecomment-7"}
    assert merge_cleared.post_record(REPO, 41, 5, "c" * 40, verdict, lapse=True)
    assert merge_cleared.post_record(REPO, 41, 5, "c" * 40, verdict)
    first, second = (next(x for x in a if x.startswith("body=")) for a in posted)
    assert first.endswith(" merged by the sweep after a conductor lapse")
    assert first.startswith("body=Auto merge: #5 " + "c" * 40)
    assert "lapse" not in second
