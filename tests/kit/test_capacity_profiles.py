"""The capacity table and its profiles (SPEC-0034 rules 1 and 15, SPEC-0006 rule 5; REQ-041).

Brief #842 build (b), amendment 149 items 1 to 3 and 7 to 10 (ADR-0409). The machine's figures
are read through functions the tests replace, so no test depends on the machine that runs it. A
`gh` stub serves saved JSON copies; invented briefs only; no network."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from test_session import ISSUES, REPO, Stub, comment, issue, listing
from test_session_flow import DAY, PULLS, brief, files, flow
from test_session_plan import GIB, four_ready, labelled, planned


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
    """A machine of 32 GiB, 8 cores at a load of 2 and a 100 GiB disk with 60 GiB free."""
    import session_plan

    figures = {"total": 32 * GIB, "cpu": (6.0, 8), "disk": (60 * GIB, 100 * GIB)}
    monkeypatch.setattr(session_plan, "total_memory", lambda: figures["total"])
    monkeypatch.setattr(session_plan, "cpu_figures", lambda: figures["cpu"])
    monkeypatch.setattr(session_plan, "disk_figures", lambda root: figures["disk"])
    return figures


def capacity(proj, stub, monkeypatch, capsys, memory, toml: str) -> tuple[dict, list[str]]:
    four_ready(stub)
    flow(proj, toml)
    code, out = planned(proj, stub, monkeypatch, capsys, memory, "--json")
    assert code == 0, out
    got = json.loads(out)
    code, words = planned(proj, stub, monkeypatch, capsys, memory)
    return got, words.splitlines()


# --- item 1: the table, refused naming the setting ---------------------------------------------


def settings(tmp_path: Path, text: str):
    import config

    (tmp_path / "agk.toml").write_text(text, encoding="utf-8")
    return config.capacity_settings(tmp_path)


def test_no_capacity_table_is_none_and_a_table_without_profile_is_auto(tmp_path):
    """REQ-041: amendment 149 items 1 and 10 (no table: as today; omitted profile: auto)."""
    assert settings(tmp_path, "[flow]\nmax_builders = 3\n") is None
    got = settings(tmp_path, "[capacity]\nmax_builders = 4\n")
    assert got == {"profile": "auto", "max_builders": 4, "review_minutes": 15}


@pytest.mark.parametrize(
    ("text", "key"),
    [
        ("colour = 3", "colour"),
        ('profile = "huge"', "profile"),
        ("max_builders = 0", "max_builders"),
        ("builder_cpus = 2.5", "builder_cpus"),
        ('builder_disk_gb = "40"', "builder_disk_gb"),
        ("review_minutes = true", "review_minutes"),
    ],
)
def test_an_unknown_key_or_a_wrong_value_is_refused_naming_the_setting(tmp_path, text, key):
    """REQ-041: amendment 149 item 1 (`setting: capacity.<key>`, never the value)."""
    import config

    with pytest.raises(config.CapacitySettingError) as err:
        settings(tmp_path, f"[capacity]\n{text}\n")
    assert f"setting: capacity.{key}" in str(err.value)
    assert text.split(" = ")[1] not in str(err.value).replace(f"capacity.{key}", "")


def test_a_personal_project_reads_small_when_no_table_sets_the_profile(tmp_path):
    """REQ-041: amendment 149 item 10 (`forge = "files"` reads `small`, Q-842-7)."""
    sidecar = '[personal]\nforge = "files"\n'
    assert settings(tmp_path, sidecar) == {"profile": "small", "review_minutes": 15}
    got = settings(tmp_path, sidecar + '[capacity]\nprofile = "full"\n')
    assert got["profile"] == "full"


def test_a_refused_table_stops_the_plan_naming_the_setting(proj, stub, monkeypatch, capsys):
    """REQ-041: amendment 149 item 1 (the plan refuses, naming the setting)."""
    four_ready(stub)
    flow(proj, 'max_builders = 3\n[capacity]\nprofile = "turbo"')
    code, out = planned(proj, stub, monkeypatch, capsys, 8 * GIB)
    err = capsys.readouterr().err
    assert code != 0 and "setting: capacity.profile" in out + err and "turbo" not in out + err


# --- items 3 and 7: the ceilings and the line that says them -----------------------------------


def test_with_no_table_the_plan_is_as_today_and_says_profile_none(
    proj, stub, monkeypatch, capsys, machine
):
    """REQ-041: amendment 149 items 7 and 10 (`Capacity: <n> of <ceiling> (none; ...)`)."""
    got, lines = capacity(proj, stub, monkeypatch, capsys, 8 * GIB, "max_builders = 3")
    cap = got["capacity"]
    assert cap["profile"] == "none" and cap["ceiling"] == 3 and cap["slots"] == 3
    assert "cpu" not in cap and "disk" not in cap and "memory" not in cap
    assert "Capacity: 3 of 3 (none; limit: max_builders 3)." in lines


def test_the_smaller_of_two_tables_is_the_ceiling_and_reviews_follow_it(
    proj, stub, monkeypatch, capsys, machine
):
    """REQ-041: amendment 149 items 1 and 3 (smaller value wins; `reviews_in_flight` follows)."""
    got, lines = capacity(
        proj, stub, monkeypatch, capsys, 8 * GIB, 'max_builders = 9\n[capacity]\nmax_builders = 2'
    )
    cap = got["capacity"]
    assert cap["ceiling"] == 2 and cap["reviews_in_flight"] == 2 and cap["profile"] == "auto"
    assert [s["brief"] for s in got["start"]] == [5, 6]
    assert "Capacity: 2 of 2 (auto; limit: max_builders 2)." in lines


def test_full_measures_nothing_even_with_a_memory_setting(proj, stub, monkeypatch, capsys, machine):
    """REQ-041: amendment 149 item 2 (`full` uses every ceiling as given, measures nothing)."""
    toml = 'max_builders = 4\nbuilder_memory_gb = 8\n[capacity]\nprofile = "full"'
    got, lines = capacity(proj, stub, monkeypatch, capsys, 1 * GIB, toml)
    cap = got["capacity"]
    assert cap["slots"] == 4 and cap["limit"] == "max_builders" and "memory" not in cap
    assert "Capacity: 4 of 4 (full; limit: max_builders 4)." in lines


def test_balanced_keeps_a_quarter_of_memory_free(proj, stub, monkeypatch, capsys, machine):
    """REQ-041: amendment 149 item 2 (20 GiB available less 8 of 32 kept free, 4 each: 3)."""
    toml = 'max_builders = 9\n[capacity]\nprofile = "balanced"\nbuilder_memory_gb = 4'
    got, lines = capacity(proj, stub, monkeypatch, capsys, 20 * GIB, toml)
    cap = got["capacity"]
    assert cap["slots"] == 3 and cap["limit"] == "memory"
    assert cap["memory"] == {"available_bytes": 20 * GIB, "builders": 3}
    assert "Capacity: 3 of 9 (balanced; limit: memory 20 GB available)." in lines


def test_balanced_counts_cpu_and_disk_only_where_their_setting_is_set(
    proj, stub, monkeypatch, capsys, machine
):
    """REQ-041: amendment 149 item 2 (6 free of 8 cores less 2 kept, 2 each: 2; disk 60 GiB free
    less 25 kept, 10 each: 3; a figure without its per-builder setting is not counted)."""
    toml = 'max_builders = 9\n[capacity]\nprofile = "balanced"\nbuilder_cpus = 2'
    got, lines = capacity(proj, stub, monkeypatch, capsys, 20 * GIB, toml)
    cap = got["capacity"]
    assert cap["limit"] == "cpu" and cap["slots"] == 2
    assert cap["cpu"] == {"free_cores": 6.0, "builders": 2}
    assert "memory" not in cap and "disk" not in cap
    assert "Capacity: 2 of 9 (balanced; limit: cpu 6 cores free)." in lines
    toml = 'max_builders = 9\n[capacity]\nprofile = "balanced"\nbuilder_disk_gb = 10'
    got, lines = capacity(proj, stub, monkeypatch, capsys, 20 * GIB, toml)
    assert got["capacity"]["disk"] == {"free_bytes": 60 * GIB, "builders": 3}
    assert "Capacity: 3 of 9 (balanced; limit: disk 60 GB free)." in lines


def test_small_starts_at_most_two_and_keeps_half_free(proj, stub, monkeypatch, capsys, machine):
    """REQ-041: amendment 149 item 2 (`small`: at most 2; 20 GiB less 16 kept, 1 each: 4)."""
    toml = 'max_builders = 9\n[capacity]\nprofile = "small"\nbuilder_memory_gb = 1'
    got, lines = capacity(proj, stub, monkeypatch, capsys, 20 * GIB, toml)
    cap = got["capacity"]
    assert cap["slots"] == 2 and cap["limit"] == "small" and cap["ceiling"] == 2
    assert cap["memory"]["builders"] == 4
    assert "Capacity: 2 of 2 (small; limit: small 2)." in lines


def test_fixed_uses_max_builders_only(proj, stub, monkeypatch, capsys, machine):
    """REQ-041: amendment 149 item 2 (`fixed`: no other ceiling, no measured figure; a lower
    `reviews_in_flight` is not read, and reviews count against `max_builders`, Q-842-14)."""
    stub.serve(PULLS, [labelled(10, 1, "agk:review")])
    files(stub, 10, "z/10")
    toml = (
        "max_builders = 4\nreviews_in_flight = 1\nbuilder_memory_gb = 64\n"
        '[capacity]\nprofile = "fixed"'
    )
    got, lines = capacity(proj, stub, monkeypatch, capsys, 2 * GIB, toml)
    cap = got["capacity"]
    assert cap["reviews_in_flight"] == 4 and "memory" not in cap
    assert cap["limit"] == "max_builders" and cap["slots"] == 3
    assert "Capacity: 3 of 4 (fixed; limit: max_builders 4)." in lines


def test_a_figure_that_cannot_be_read_says_unknown_and_is_left_out(
    proj, stub, monkeypatch, capsys, machine
):
    """REQ-041: amendment 149 items 4 and 7 (`unknown`, never read as 0)."""
    machine["cpu"] = None
    toml = 'max_builders = 3\n[capacity]\nprofile = "balanced"\nbuilder_cpus = 1'
    got, lines = capacity(proj, stub, monkeypatch, capsys, 8 * GIB, toml)
    cap = got["capacity"]
    assert cap["cpu"] == "unknown" and cap["slots"] == 3 and cap["limit"] == "max_builders"
    assert "Capacity: 3 of 3 (balanced; limit: max_builders 3). Unknown: cpu." in lines


def test_start_zero_names_the_limit_and_its_figure(proj, stub, monkeypatch, capsys, machine):
    """REQ-041: amendment 149 item 7 (every `Start 0` names the limit and its figure)."""
    listing(stub, [issue(n, brief(f"d{n}/")) for n in (5, 6, 7)])
    stub.serve(f"{ISSUES}/5/comments", [comment(1, "x", f"taken: builder-a {DAY}")])
    stub.serve(f"{ISSUES}/6/comments", [comment(2, "y", f"taken: builder-b {DAY}")])
    stub.serve(f"{ISSUES}/7/comments", [])
    flow(proj, 'max_builders = 9\n[capacity]\nprofile = "small"')
    code, words = planned(proj, stub, monkeypatch, capsys, 8 * GIB)
    lines = words.splitlines()
    assert code == 0 and lines[0] == (
        "Start 0: the small profile runs at most 2 builders at once (2 running)."
    )
    assert "Capacity: 0 of 2 (small; limit: small 2)." in lines


def test_the_floor_of_one_stays_while_no_builder_runs(proj, stub, monkeypatch, capsys, machine):
    """REQ-041: amendment 149 item 4 (ADR-0223's floor: 30 GiB free less 25 kept, 50 each)."""
    machine["disk"] = (30 * GIB, 100 * GIB)
    toml = 'max_builders = 9\n[capacity]\nprofile = "balanced"\nbuilder_disk_gb = 50'
    got, lines = capacity(proj, stub, monkeypatch, capsys, 8 * GIB, toml)
    assert got["capacity"]["disk"] == {"free_bytes": 30 * GIB, "builders": 1}
    assert lines[0] == "Start 1: builder-a takes #5."
    assert "Capacity: 1 of 9 (balanced; limit: disk 30 GB free)." in lines


# --- item 9: the doctor's row ------------------------------------------------------------------


def test_doctor_prints_the_profile_ceilings_figures_and_a_suggestion(tmp_path, monkeypatch):
    """REQ-041: amendment 149 item 9 (a printed line that never fails the run)."""
    import common
    import doctor
    import session_plan

    monkeypatch.setattr(common, "available_memory", lambda: 12 * GIB)
    monkeypatch.setattr(session_plan, "total_memory", lambda: 16 * GIB)
    monkeypatch.setattr(session_plan, "cpu_figures", lambda: None)
    monkeypatch.setattr(session_plan, "disk_figures", lambda root: (40 * GIB, 80 * GIB))
    (tmp_path / "agk.toml").write_text(
        '[flow]\nmax_builders = 6\n[capacity]\nprofile = "balanced"\nbuilder_memory_gb = 2\n',
        encoding="utf-8",
    )
    res = doctor.capacity_result(tmp_path)
    assert res.status == "ok"
    assert res.message == (
        "profile balanced; max_builders 6, reviews_in_flight 6, builder_memory_gb 2; "
        "memory 12 GB available, cpu unknown, disk 40 GB free; suggested profile balanced"
    )
    (tmp_path / "agk.toml").write_text("[capacity]\nlimit = 9\n", encoding="utf-8")
    res = doctor.capacity_result(tmp_path)
    assert res.status == "fail" and "setting: capacity.limit" in res.message
    assert doctor.CHECKS["capacity"][0] == "warn"


@pytest.mark.parametrize(
    ("free", "profile"), [(4, "small"), (8, "balanced"), (31, "balanced"), (32, "full"), (None, None)]
)
def test_doctor_suggests_a_profile_by_free_memory(free, profile):
    """REQ-041: amendment 149 item 9 (`small` under 8 GB free, `balanced` under 32, `full`)."""
    import doctor

    assert doctor.suggested_profile(None if free is None else free * GIB) == profile
