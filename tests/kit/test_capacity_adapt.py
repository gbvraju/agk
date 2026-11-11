"""`auto` measures and adapts each pass (SPEC-0034 rule 15; REQ-041).

Brief #842 build (c), amendment 149 items 4 to 6 (ADR-0435). The machine's figures and the
evidence (governance run minutes, review minutes) are read through functions the tests replace,
so no test depends on the machine that runs it or on GitHub. Invented briefs only; no network."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from test_session import REPO, Stub, comment
from test_session_flow import flow
from test_session_plan import GIB, four_ready, planned

RECORD = "docs/runs/capacity-record.jsonl"


@pytest.fixture
def stub(tmp_path):
    return Stub(tmp_path)


@pytest.fixture
def proj(repo, stub):
    repo.git("remote", "add", "origin", f"https://github.com/{REPO}.git")
    repo.write("config/reviewers.yaml", "version: 1\nverdict_authors: [boss, second]\n")
    repo.write("config/protected-paths.txt", "config/\nscripts/agk/\n")
    return repo


@pytest.fixture
def machine(monkeypatch):
    """A machine of 32 GiB, 8 cores at a load of 2, a 100 GiB disk with 60 GiB free, and no
    evidence read unless a test gives it."""
    import session_plan

    figures = {"total": 32 * GIB, "cpu": (6.0, 8), "disk": (60 * GIB, 100 * GIB)}
    evidence: dict = {"runs": None, "reviews": None}
    monkeypatch.setattr(session_plan, "total_memory", lambda: figures["total"])
    monkeypatch.setattr(session_plan, "cpu_figures", lambda: figures["cpu"])
    monkeypatch.setattr(session_plan, "disk_figures", lambda root: figures["disk"])
    monkeypatch.setattr(session_plan, "check_runs", lambda repo: evidence["runs"])
    monkeypatch.setattr(session_plan, "review_times", lambda s, authors: evidence["reviews"])
    figures["evidence"] = evidence
    return figures


def history(proj, *counts: int) -> None:
    rows = [
        {"at": f"2026-11-10T0{i}:00:00Z", "count": n, "change": 0, "why": "no history"}
        for i, n in enumerate(counts)
    ]
    proj.write(RECORD, "".join(json.dumps(r) + "\n" for r in rows))


def run(proj, stub, monkeypatch, capsys, toml: str, memory: int = 20 * GIB, *extra: str):
    four_ready(stub)
    flow(proj, toml)
    code, out = planned(proj, stub, monkeypatch, capsys, memory, "--json", *extra)
    assert code == 0, out
    got = json.loads(out)
    code, words = planned(proj, stub, monkeypatch, capsys, memory)
    return got["capacity"], words.splitlines()


AUTO = "max_builders = 9\n[capacity]\n"


# --- item 4: measured each pass ----------------------------------------------------------------


def test_builders_run_is_here_or_cloud_and_refused_otherwise_naming_the_setting(tmp_path):
    """REQ-041: amendment 149 item 4 (`builders_run`, `here` by default, Q-842-3)."""
    import config

    path = tmp_path / "agk.toml"
    path.write_text('[capacity]\nbuilders_run = "cloud"\n', encoding="utf-8")
    assert config.capacity_settings(tmp_path)["builders_run"] == "cloud"
    path.write_text('[capacity]\nbuilders_run = "moon"\n', encoding="utf-8")
    with pytest.raises(config.CapacitySettingError) as err:
        config.capacity_settings(tmp_path)
    assert "setting: capacity.builders_run" in str(err.value) and "moon" not in str(err.value)


def test_auto_measures_memory_cores_and_disk_with_no_reserve(
    proj, stub, monkeypatch, capsys, machine
):
    """REQ-041: amendment 149 item 4 (20 GiB / 4 = 5, 6 cores / 2 = 3, 60 GiB / 10 = 6)."""
    toml = AUTO + "builder_memory_gb = 4\nbuilder_cpus = 2\nbuilder_disk_gb = 10"
    cap, lines = run(proj, stub, monkeypatch, capsys, toml)
    assert cap["memory"]["builders"] == 5 and cap["cpu"]["builders"] == 3
    assert cap["disk"]["builders"] == 6
    assert cap["limit"] == "cpu" and cap["slots"] == 3
    assert "Capacity: 3 of 9 (auto; limit: cpu 6 cores free)." in lines


def test_auto_in_the_cloud_measures_no_machine_figure_and_starts_read_unknown(
    proj, stub, monkeypatch, capsys, machine
):
    """REQ-041: amendment 149 items 4 and 6 (cloud: no machine figure; refused starts unknown,
    Q-842-8)."""
    toml = AUTO + 'builders_run = "cloud"\nbuilder_memory_gb = 64\nbuilder_cpus = 8'
    cap, lines = run(proj, stub, monkeypatch, capsys, toml, 1 * GIB)
    assert "memory" not in cap and "cpu" not in cap
    assert cap["slots"] == 9 and cap["adapt"]["conditions"]["starts"] == "unknown"
    assert "Capacity: 9 of 9 (auto; limit: max_builders 9)." in lines


# --- item 6: where the evidence lives ----------------------------------------------------------


def test_plan_alone_writes_nothing_and_record_appends_one_line_kept_out_of_git(
    proj, stub, monkeypatch, capsys, machine
):
    """REQ-041: amendment 149 item 6 (`plan --record`, a path kept out of git, Q-842-2)."""
    toml = AUTO + "builder_cpus = 2"
    run(proj, stub, monkeypatch, capsys, toml)
    assert not (Path(proj.root) / RECORD).exists()
    planned(proj, stub, monkeypatch, capsys, 20 * GIB, "--record")
    rows = (Path(proj.root) / RECORD).read_text(encoding="utf-8").splitlines()
    assert len(rows) == 1
    row = json.loads(rows[0])
    assert row["count"] == 3 and row["change"] == 0 and row["why"] == "no history"
    exclude = Path(proj.root) / ".git" / "info" / "exclude"
    assert RECORD in exclude.read_text(encoding="utf-8").splitlines()


def test_another_profile_records_no_capacity_line(proj, stub, monkeypatch, capsys, machine):
    """REQ-041: amendment 149 items 5 and 6 (only `auto` adapts)."""
    flow(proj, 'max_builders = 3\n[capacity]\nprofile = "full"')
    four_ready(stub)
    planned(proj, stub, monkeypatch, capsys, 20 * GIB, "--record")
    assert not (Path(proj.root) / RECORD).exists()


# --- item 5: adapted by evidence ---------------------------------------------------------------


def good(machine) -> None:
    machine["evidence"]["runs"] = [10.0] * 20
    machine["evidence"]["reviews"] = [5.0] * 10


def test_with_no_history_the_count_is_the_smallest_figure(proj, stub, monkeypatch, capsys, machine):
    """REQ-041: amendment 149 item 5 (no history: the smallest figure of item 4)."""
    good(machine)
    cap, lines = run(proj, stub, monkeypatch, capsys, AUTO + "builder_cpus = 2")
    assert cap["adapt"]["count"] == 3 and cap["adapt"]["why"] == "no history"
    assert "Adapt: 3 of 3 (no history)." in lines


def test_the_count_rises_by_one_while_every_readable_condition_holds(
    proj, stub, monkeypatch, capsys, machine
):
    """REQ-041: amendment 149 item 5 (rises by one, never above the smallest figure)."""
    good(machine)
    history(proj, 1)
    cap, lines = run(proj, stub, monkeypatch, capsys, AUTO + "builder_cpus = 2")
    assert cap["adapt"]["count"] == 2 and cap["adapt"]["change"] == 1
    assert cap["limit"] == "adapt" and cap["slots"] == 2
    assert "Capacity: 2 of 9 (auto; limit: adapt 2 rise)." in lines
    history(proj, 3)
    cap, _ = run(proj, stub, monkeypatch, capsys, AUTO + "builder_cpus = 2")
    assert cap["adapt"]["count"] == 3 and cap["adapt"]["change"] == 0


def test_reviews_over_review_minutes_drop_the_count_and_start_zero_names_it(
    proj, stub, monkeypatch, capsys, machine
):
    """REQ-041: amendment 149 items 5 and 7 (median of the last 10 reviews over 15 minutes)."""
    good(machine)
    machine["evidence"]["reviews"] = [40.0] * 10
    history(proj, 1)
    cap, lines = run(proj, stub, monkeypatch, capsys, AUTO + "builder_cpus = 2")
    adapt = cap["adapt"]
    assert (adapt["count"], adapt["change"], adapt["why"]) == (1, 0, "drop: reviews")
    assert adapt["conditions"]["reviews"] == "over"
    assert cap["slots"] == 1  # never below 1, and the floor while no builder runs
    history(proj, 3)
    cap, lines = run(proj, stub, monkeypatch, capsys, AUTO + "builder_cpus = 2")
    assert cap["adapt"]["count"] == 2 and cap["adapt"]["change"] == -1
    assert "Adapt: 2 of 3 (drop: reviews)." in lines


def test_memory_under_its_reserve_drops_the_count_and_slow_checks_do_not(
    proj, stub, monkeypatch, capsys, machine
):
    """REQ-041: amendment 149 item 5 (7 of 32 GiB available is under the 25 percent reserve,
    Q-842-5; the newest run over 1.5 times the median of 20 is not a reason to drop, Q-842-6)."""
    good(machine)
    machine["evidence"]["runs"] = [16.0] + [10.0] * 19
    history(proj, 3)
    toml = AUTO + "builder_cpus = 2\nbuilder_memory_gb = 1"
    cap, _ = run(proj, stub, monkeypatch, capsys, toml, 7 * GIB)
    adapt = cap["adapt"]
    assert adapt["conditions"]["checks"] == "over" and adapt["conditions"]["memory"] == "under"
    assert adapt["why"] == "drop: memory" and adapt["count"] == 2


def test_slow_checks_stop_the_rise_without_dropping(proj, stub, monkeypatch, capsys, machine):
    """REQ-041: amendment 149 item 5 (checks over their usual minutes only stop the rise)."""
    good(machine)
    machine["evidence"]["runs"] = [16.0] + [10.0] * 19
    history(proj, 2)
    cap, _ = run(proj, stub, monkeypatch, capsys, AUTO + "builder_cpus = 2")
    adapt = cap["adapt"]
    assert (adapt["count"], adapt["change"], adapt["why"]) == (2, 0, "held: checks")


def test_reviews_at_exactly_review_minutes_stop_the_rise_without_dropping(
    proj, stub, monkeypatch, capsys, machine
):
    """REQ-041: amendment 149 item 5 (at the limit is neither under nor over it)."""
    good(machine)
    machine["evidence"]["reviews"] = [15.0] * 10
    history(proj, 2)
    cap, _ = run(proj, stub, monkeypatch, capsys, AUTO + "builder_cpus = 2")
    adapt = cap["adapt"]
    assert adapt["conditions"]["reviews"] == "at"
    assert (adapt["count"], adapt["change"], adapt["why"]) == (2, 0, "held: reviews")


def test_memory_above_its_reserve_alone_never_raises_the_count(
    proj, stub, monkeypatch, capsys, machine
):
    """REQ-041: amendment 149 item 5 (the reserve is only a reason to drop; with checks and
    reviews unread the count stays)."""
    history(proj, 2)
    toml = AUTO + "builder_cpus = 2\nbuilder_memory_gb = 1"
    cap, _ = run(proj, stub, monkeypatch, capsys, toml)
    adapt = cap["adapt"]
    assert adapt["conditions"]["memory"] == "ok" and adapt["conditions"]["checks"] == "unknown"
    assert (adapt["count"], adapt["change"], adapt["why"]) == (2, 0, "nothing read")


def test_a_condition_that_cannot_be_read_counts_neither_way(
    proj, stub, monkeypatch, capsys, machine
):
    """REQ-041: amendment 149 item 5 (unreadable: left out; fewer than 20 runs: no usual)."""
    machine["evidence"]["runs"] = [10.0] * 19
    history(proj, 2)
    cap, _ = run(proj, stub, monkeypatch, capsys, AUTO + "builder_cpus = 2")
    adapt = cap["adapt"]
    assert adapt["conditions"] == {"starts": "unknown", "checks": "unknown", "reviews": "unknown"}
    assert adapt["count"] == 2 and adapt["change"] == 0 and adapt["why"] == "nothing read"


def test_the_last_twenty_changes_are_kept_in_the_output(proj, stub, monkeypatch, capsys, machine):
    """REQ-041: amendment 149 item 5 (the last 20 changes; a pass without a change is not one)."""
    good(machine)
    rows = [
        {"at": f"2026-11-10T00:{i:02d}:00Z", "count": 1 + i % 2, "change": 1 - 2 * (i % 2)}
        for i in range(25)
    ] + [{"at": "2026-11-10T01:00:00Z", "count": 1, "change": 0}]
    proj.write(RECORD, "".join(json.dumps(r) + "\n" for r in rows) + "not json\n")
    cap, _ = run(proj, stub, monkeypatch, capsys, AUTO + "builder_cpus = 2")
    changes = cap["adapt"]["changes"]
    assert len(changes) == 20 and all(c["change"] for c in changes)
    assert changes[-1]["change"] == 1 and changes[-1]["count"] == 2


# --- the evidence readers ----------------------------------------------------------------------


@pytest.mark.parametrize(
    ("runs", "want"),
    [
        (None, None),
        ([10.0] * 19, None),
        ([15.0] + [10.0] * 19, True),
        ([15.5] + [10.0] * 19, False),
    ],
)
def test_checks_hold_while_the_newest_run_is_within_its_usual_minutes(runs, want):
    """REQ-041: amendment 149 item 5 (usual: 1.5 times the median of the last 20, Q-842-6)."""
    import session_plan

    assert session_plan.checks_hold(runs) is want


def test_check_runs_reads_the_last_twenty_successful_governance_runs(monkeypatch):
    """REQ-041: amendment 149 item 5 (minutes from the run's start to its last update)."""
    import session_plan

    seen: list[str] = []
    runs = [
        {"run_started_at": "2026-11-10T00:00:00Z", "updated_at": "2026-11-10T00:12:30Z"},
        {"run_started_at": "bad", "updated_at": "2026-11-10T00:12:30Z"},
    ]
    monkeypatch.setattr(
        session_plan, "gh", lambda endpoint: seen.append(endpoint) or {"workflow_runs": runs}
    )
    assert session_plan.check_runs(REPO) == [12.5]
    assert "governance.yml/runs?status=success&per_page=20" in seen[0]
    monkeypatch.setattr(session_plan, "gh", lambda endpoint: None)  # no governance.yml: a 404
    assert session_plan.check_runs(REPO) is None
    assert session_plan.checks_hold(session_plan.check_runs(REPO)) is None


def test_review_times_run_from_the_asking_report_to_the_verdict_on_its_head(monkeypatch):
    """REQ-041: amendment 149 item 5 (a `Report:` that asks for a verdict to the `Verdict:` by a
    listed author that names its head; another author's verdict is not counted)."""
    import session_plan

    sha = "abc1234def5678"
    comments = {
        7: [
            comment(1, "me", f"Report: {sha[:7]} ready for review", "2026-11-10T00:00:00Z"),
            comment(2, "boss", f"Verdict: fix list {sha}", "2026-11-10T00:20:00Z"),
            comment(3, "me", "Report: fff0000 fix list applied", "2026-11-10T01:00:00Z"),
            comment(4, "stranger", "Verdict: cleared fff0000", "2026-11-10T01:01:00Z"),
            comment(5, "second", "Verdict: cleared fff0000aa", "2026-11-10T01:04:00Z"),
        ],
        8: None,
        9: [  # a short head that two reports name: the newest report is the one answered
            comment(6, "me", "Report: 9990000 ready for review", "2026-11-09T00:00:00Z"),
            comment(7, "me", "Report: 9990000aa merge of main", "2026-11-09T00:30:00Z"),
            comment(8, "boss", "Verdict: cleared 9990000", "2026-11-09T00:36:00Z"),
        ],
    }
    monkeypatch.setattr(
        session_plan, "pages", lambda endpoint: comments[int(endpoint.split("/")[-2])]
    )

    class S:
        repo = REPO
        prs = [
            {"number": 7, "user": {"login": "me"}, "updated_at": "2026-11-10T02:00:00Z"},
            {"number": 8, "user": {"login": "me"}, "updated_at": "2026-11-10T01:00:00Z"},
            {"number": 9, "user": {"login": "me"}, "updated_at": "2026-11-09T01:00:00Z"},
        ]

    assert session_plan.review_times(S, ["boss", "second"]) == [4.0, 20.0, 6.0]
    assert session_plan.review_state([4.0, 20.0, 30.0], 15) == "over"
    assert session_plan.review_state([4.0, 15.0, 30.0], 15) == "at"
    assert session_plan.review_state([4.0, 10.0, 30.0], 15) == "ok"
    assert session_plan.review_state([], 15) == "unknown"
    assert session_plan.review_state(None, 15) == "unknown"
