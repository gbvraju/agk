"""`session.py plan --what-if DIR`: how a wave of unfiled briefs would split (amendment 141 item 6).

REQ-057 AC12. Saved brief files are judged with the same function as the plan, against the open
work; capacity is read from nothing; nothing is posted or recorded. A `gh` stub serves saved JSON;
invented briefs only; no network."""

from __future__ import annotations

from pathlib import Path

import pytest
from test_conductor_guard_launch import SESSION, allowed, denied, run_hook, tmp  # noqa: F401
from test_conductor_guard_launch import project as guarded  # noqa: F401 - the fixture
from test_session import REPO, Stub, issue, listing
from test_session_flow import PULLS, brief, flow, pr
from test_session_plan import changed, free, labelled, plan, read_only

ROOT = Path(__file__).resolve().parents[2]


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
def wave(tmp_path) -> Path:
    folder = tmp_path / "wave"
    folder.mkdir()
    return folder


def save(folder: Path, **files: str) -> Path:
    for name, body in files.items():
        (folder / f"{name}.md").write_text(body, encoding="utf-8")
    return folder


def open_work(stub: Stub, pulls: list[dict] | None = None, briefs: dict[int, str] | None = None):
    stub.serve(PULLS, pulls or [])
    listing(stub, [issue(n, brief(t)) for n, t in (briefs or {}).items()])
    free(stub, *(briefs or {}))


def lines(proj, stub, folder: Path) -> list[str]:
    out = plan(proj, stub, "--what-if", str(folder))
    assert out.returncode == 0, out.stdout + out.stderr
    return out.stdout.splitlines()


def test_ac12_two_briefs_with_nothing_shared_can_start_together(proj, stub, wave):
    """REQ-057 AC12: item 6, the exact lines."""
    open_work(stub)
    save(wave, a=brief("a.py"), b=brief("b.py"))
    assert lines(proj, stub, wave) == [
        "What-if: 2 of 2 can start together.",
        "File in this order: a.md, b.md",
    ]


def test_ac12_a_saved_brief_waits_for_an_open_pull_request(proj, stub, wave):
    """REQ-057 AC12: item 6, the holder and the file that holds it back."""
    open_work(stub, [labelled(20, 90, "agk:review")])
    changed(stub, 20, ("modified", "a.py"))
    save(wave, a=brief("a.py"), b=brief("b.py"))
    assert lines(proj, stub, wave) == [
        "What-if: 1 of 2 can start together.",
        "a.md waits for #20 (it changes a.py)",
        "File in this order: a.md, b.md",
    ]


def test_ac12_a_saved_brief_waits_for_an_earlier_saved_brief(proj, stub, wave):
    """REQ-057 AC12: item 6, the holder is the file; same function as the plan's waves."""
    open_work(stub)
    save(wave, a=brief("x.py"), b=brief("x.py"))
    assert lines(proj, stub, wave) == [
        "What-if: 1 of 2 can start together.",
        "b.md waits for a.md (both touch x.py)",
        "File in this order: a.md, b.md",
    ]


def test_ac12_a_filed_ready_brief_goes_first(proj, stub, wave):
    """REQ-057 AC12: item 6, "with the open work": a filed brief is judged before a saved one."""
    open_work(stub, briefs={5: "x.py"})
    save(wave, a=brief("x.py"))
    assert lines(proj, stub, wave)[:2] == [
        "What-if: 0 of 1 can start together.",
        "a.md waits for #5 (both touch x.py)",
    ]


def test_ac12_order_is_priority_then_file_name(proj, stub, wave):
    """REQ-057 AC12: item 6, the earlier in that order starts and the other waits."""
    open_work(stub)
    save(wave, a=brief("x.py"), z=brief("x.py", priority=1))
    assert lines(proj, stub, wave) == [
        "What-if: 1 of 2 can start together.",
        "a.md waits for z.md (both touch x.py)",
        "File in this order: z.md, a.md",
    ]


def test_ac12_a_brief_that_fails_the_shape_is_named_and_not_filed(proj, stub, wave):
    """REQ-057 AC12: item 6, `MALFORMED: <file> <rule>`."""
    open_work(stub)
    save(wave, a=brief("a.py"), bad="no shape at all\n")
    found = lines(proj, stub, wave)
    assert found[0] == "What-if: 1 of 2 can start together."
    assert found[1].startswith("MALFORMED: bad.md rule ")
    assert found[-1] == "File in this order: a.md"


def test_ac12_capacity_is_read_from_nothing(proj, stub, wave):
    """REQ-057 AC12: item 6, overlap only: a full house of builders does not lower the count."""
    flow(proj, "max_builders = 1\nreviews_in_flight = 1\n")
    open_work(stub, [labelled(20, 90, "agk:review")])
    changed(stub, 20, ("modified", "z.py"))
    save(wave, a=brief("a.py"), b=brief("b.py"))
    assert lines(proj, stub, wave)[0] == "What-if: 2 of 2 can start together."


def test_ac12_only_saved_markdown_files_are_read(proj, stub, wave):
    """REQ-057 AC12: item 6, `*.md`, one brief each, not below the folder."""
    open_work(stub)
    save(wave, a=brief("a.py"))
    (wave / "note.txt").write_text("no\n", encoding="utf-8")
    (wave / "below").mkdir()
    (wave / "below" / "b.md").write_text(brief("b.py"), encoding="utf-8")
    assert lines(proj, stub, wave)[0] == "What-if: 1 of 1 can start together."


def test_ac12_an_empty_folder_files_nothing(proj, stub, wave):
    """REQ-057 AC12: item 6, the two lines still print."""
    open_work(stub)
    assert lines(proj, stub, wave) == [
        "What-if: 0 of 0 can start together.",
        "File in this order: none",
    ]


def test_ac12_it_posts_nothing_and_records_nothing(proj, stub, wave):
    """REQ-057 AC12: item 6, GET only, no record of a hold."""
    open_work(stub, [labelled(20, 90, "agk:review")])
    changed(stub, 20, ("modified", "a.py"))
    save(wave, a=brief("a.py"))
    lines(proj, stub, wave)
    read_only(stub)
    assert not (proj.root / "docs" / "runs" / "holds.jsonl").exists()


def test_ac12_a_folder_that_cannot_be_read_is_refused_without_its_name(proj, stub, tmp_path):
    """REQ-057 AC12: principle 8, the rule and never the value."""
    open_work(stub)
    out = plan(proj, stub, "--what-if", str(tmp_path / "absent-folder-name"))
    assert out.returncode == 2
    assert "rule 4 of SPEC-0050" in out.stdout and "absent-folder-name" not in out.stdout


@pytest.mark.parametrize(
    "extra", [("--what-if",), ("--what-if", "d", "--json"), ("--what-if", "d", "--record")]
)
def test_ac12_any_other_form_is_a_usage_error(proj, stub, extra):
    """REQ-057 AC12: item 6, `--what-if` stands alone and posts and records nothing."""
    open_work(stub)
    assert plan(proj, stub, *extra).returncode == 2


def test_ac12_the_guard_lets_the_conductor_run_it_on_a_scratch_folder(guarded, tmp):  # noqa: F811
    """REQ-057 AC12: item 6, `Q-772-10`: the conductor's filing step, on its scratch folder only."""
    scratch = tmp / "agk-conductor-1"
    assert allowed(run_hook(f"python3 {SESSION} plan --what-if {scratch}", guarded, tmp))
    assert denied(run_hook(f"python3 {SESSION} plan --what-if {tmp}", guarded, tmp))
    assert denied(run_hook(f"python3 {SESSION} plan --what-if /etc", guarded, tmp))
    assert denied(run_hook(f"python3 {SESSION} plan --what-if {scratch} --json", guarded, tmp))
    assert denied(run_hook(f"python3 {SESSION} plan --record", guarded, tmp))
    assert denied(run_hook(f"python3 {SESSION} plan --what-if {scratch}", guarded, tmp, shadow=True))


def test_ac12_the_conductor_files_a_wave_in_that_order():
    """REQ-057 AC12: item 6, the conductor's filing step."""
    text = (ROOT / ".claude" / "agents" / "conductor.md").read_text(encoding="utf-8")
    assert "plan --what-if" in text


def test_ac12_the_usage_names_the_new_forms():
    """REQ-057 AC12, AC13: the usage line."""
    import session

    assert "session.py plan [--json] [--record] | plan --what-if DIR" in session.USAGE
