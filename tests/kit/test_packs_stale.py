"""Tests of the stale pack lines and `update --check`'s notes (SPEC-0077 rule 8; REQ-084 AC6;
brief #2045, ADR-0848).

A pack in use whose `reviewed` or `as_of`, or a knowledge entry's access date, is older than
`[packs] stale_months` calendar months is one `warn packs:` line with its date and `(verify)`,
shown by doctor (team mode and on a sidecar) and the weekly reports, never failing. `update
--check` gives each newer tag's change note, `(no change notes)` or `(notes withheld: rule 6)`,
names a pack whose locked tag is gone `withdrawn (verify)` and an unreachable source `cannot
check`, and writes nothing. Fixtures in `tmp_path` only: invented packs (`example.com`), a fixed
`today`, stub tag listers and note readers, no network, no model.
"""

from __future__ import annotations

import datetime
import hashlib
import socket
import sys
from pathlib import Path

import pytest

KIT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KIT_ROOT / "scripts" / "agk"))

import check_packs  # noqa: E402
import doctor  # noqa: E402
import metrics  # noqa: E402
import packs  # noqa: E402
import personal  # noqa: E402

TODAY = datetime.date(2026, 11, 27)
PID = "zz-guide"
REL = f"config/packs/{PID}"
KNOW = "standards/zz.toml"
MANIFEST = """format = 1
id = "{pid}"
version = "1.2.0"
publisher = "Example Org"
tier = "curated"
licence = "MIT"
source = "{source}"
kit = ">=0.60.0,<1.0.0"
as_of = "{as_of}"
reviewed = "{reviewed} by maintainers"
kinds = ["standards"]

[permissions]

[files]
"{know}" = "{sha}"
"""
FRESH = "2026-11-01"


def entries(*dates: str | None) -> str:
    """A knowledge file: one `[[rules]]` entry per date (None: `basis = "expected"`)."""
    out = []
    for n, d in enumerate(dates):
        tail = f'source = "https://example.com/r{n} (accessed {d})"' if d else 'basis = "expected"'
        out.append(f'[[rules]]\nid = "r{n}"\ntext = "Invented rule {n}."\n{tail}\n')
    return "\n".join(out)


def pack(
    root: Path,
    pid: str = PID,
    as_of: str = FRESH,
    reviewed: str = FRESH,
    items: tuple[str | None, ...] = (FRESH,),
    source: str = "https://example.com/packs/zz-guide.git",
) -> dict:
    folder = root / "config" / "packs" / pid
    (folder / "standards").mkdir(parents=True, exist_ok=True)
    know = entries(*items)
    (folder / KNOW).write_text(know, encoding="utf-8")
    sha = hashlib.sha256(know.encode()).hexdigest()
    text = MANIFEST.format(
        pid=pid, source=source, as_of=as_of, reviewed=reviewed, know=KNOW, sha=sha
    )
    (folder / check_packs.MANIFEST).write_text(text, encoding="utf-8")
    assert check_packs.problems(folder) == []
    digest = check_packs.digest(folder / check_packs.MANIFEST)
    return {"id": pid, "version": "1.2.0", "sha256": digest}


def project(root: Path, used: list[dict], extra: str = "", top: str = "") -> Path:
    use = ", ".join(
        f'{{ id = "{u["id"]}", version = "{u["version"]}", sha256 = "{u["sha256"]}" }}'
        for u in used
    )
    (root / "agk.toml").write_text(
        f'review_mode = "solo"\n{top}[packs]\nuse = [{use}]\n{extra}', encoding="utf-8"
    )
    return root


@pytest.fixture
def no_socket(monkeypatch):
    def refuse(*args, **kwargs):
        raise AssertionError("a socket was opened")

    monkeypatch.setattr(socket, "socket", refuse)
    monkeypatch.setattr(socket, "create_connection", refuse)


# --- answer 1: the lines --------------------------------------------------------------------------


def test_ac6_a_reviewed_date_thirteen_months_old_is_one_line_with_its_date(tmp_path, no_socket):
    """REQ-084 AC6: SPEC-0077 rule 8 (the date and `(verify)`; the pack id, never a value)."""
    root = project(tmp_path, [pack(tmp_path, reviewed="2025-10-03")])
    assert packs.stale(root, TODAY) == [
        f"warn packs: {PID} reviewed 2025-10-03 is older than [packs] stale_months (verify)"
    ]


def test_ac6_as_of_and_items_give_their_own_lines_in_use_order(tmp_path):
    """REQ-084 AC6: SPEC-0077 rule 8 (reviewed, as_of, then items with the count and oldest)."""
    one = pack(tmp_path, "zz-one", as_of="2024-01-15", items=("2025-01-02", "2024-06-30", FRESH))
    two = pack(tmp_path, "zz-two", reviewed="2023-05-05", as_of="2023-05-01")
    root = project(tmp_path, [two, one])
    lines = packs.stale(root, TODAY)
    assert lines == [
        "warn packs: zz-two reviewed 2023-05-05 is older than [packs] stale_months (verify)",
        "warn packs: zz-two as_of 2023-05-01 is older than [packs] stale_months (verify)",
        "warn packs: zz-one as_of 2024-01-15 is older than [packs] stale_months (verify)",
        "warn packs: zz-one 2 items accessed before [packs] stale_months, oldest 2024-06-30"
        " (verify)",
    ]
    assert "example.com" not in "\n".join(lines) and "maintainers" not in "\n".join(lines)


def test_ac6_one_old_item_is_named_in_the_singular(tmp_path):
    """REQ-084 AC6: SPEC-0077 rule 8 (one line for the items of a pack, however many)."""
    root = project(tmp_path, [pack(tmp_path, items=("2020-02-02",))])
    assert packs.stale(root, TODAY) == [
        f"warn packs: {PID} 1 item accessed before [packs] stale_months, oldest 2020-02-02 (verify)"
    ]


@pytest.mark.parametrize(
    ("date", "warned"),
    [
        ("2025-11-30", False),  # 12 months back, same month: at, not over
        ("2025-11-01", False),
        ("2025-10-31", True),  # 13 months back
        ("2027-01-01", False),  # after today
    ],
)
def test_ac6_the_count_is_over_not_at_and_a_future_date_is_quiet(tmp_path, date, warned):
    """REQ-084 AC6: SPEC-0077 rule 8 (`check_domains.stale`'s month count, the day ignored)."""
    root = project(tmp_path, [pack(tmp_path, reviewed=date)])
    assert bool(packs.stale(root, TODAY)) is warned


def test_ac6_expected_entries_and_fresh_packs_give_no_line(tmp_path):
    """REQ-084 AC6: SPEC-0077 rule 8 (`basis = "expected"` has no access date)."""
    root = project(tmp_path, [pack(tmp_path, items=(None, FRESH))])
    assert packs.stale(root, TODAY) == []


# --- answer 5: the settings -----------------------------------------------------------------------


@pytest.mark.parametrize(
    ("setting", "date", "warned"),
    [
        ("", "2025-10-03", True),  # absent: 12
        ("stale_months = 1\n", "2026-09-30", True),  # the month before last
        ("stale_months = 1\n", "2026-10-30", False),  # last month: at, not over
        ("stale_months = 60\n", "2021-11-01", False),  # five years: at
        ("stale_months = 60\n", "2021-10-31", True),  # over five years
    ],
)
def test_ac6_stale_months_sets_the_age(tmp_path, setting, date, warned):
    """REQ-084 AC6: SPEC-0077 rules 8 and 12 (`[packs] stale_months`, default 12)."""
    root = project(tmp_path, [pack(tmp_path, reviewed=date)], extra=setting)
    assert bool(packs.stale(root, TODAY)) is warned


@pytest.mark.parametrize("value", ["0", "61", "true", '"12"', "12.0"])
def test_ac6_a_refused_stale_months_shows_no_line_and_unknown_in_the_report(tmp_path, value):
    """REQ-084 AC6: SPEC-0077 rule 12 (refused as today; doctor quiet, the report `unknown`)."""
    root = project(tmp_path, [pack(tmp_path, reviewed="2020-01-01")], f"stale_months = {value}\n")
    with pytest.raises(packs.Refused, match=r"\(setting: packs\.stale_months\)"):
        packs.stale(root, TODAY)
    assert doctor.pack_stale_lines(root) == []
    assert packs.report_lines(root, TODAY) == ["packs: stale unknown (setting: packs.stale_months)"]
    assert doctor.packs_settings_result(root).status == "fail"


def test_ac6_no_table_or_no_pack_in_use_is_none_stale(tmp_path):
    """REQ-084 AC6: SPEC-0077 rule 8 (`agk-core` has no dates; never 0, never a line)."""
    (tmp_path / "agk.toml").write_text('review_mode = "team"\n', encoding="utf-8")
    assert packs.stale(tmp_path, TODAY) == []
    assert packs.report_lines(tmp_path, TODAY) == ["packs: none stale"]
    project(tmp_path, [])
    assert packs.report_lines(tmp_path, TODAY) == ["packs: none stale"]
    assert packs.stale(KIT_ROOT, TODAY) == []


def test_ac6_domain_stale_months_is_never_read_for_packs(tmp_path):
    """REQ-084 AC6: SPEC-0077 rule 8 (`[domain] stale_months` is the domain packs' own)."""
    used = pack(tmp_path, reviewed="2024-01-01")
    root = project(tmp_path, [used], "stale_months = 60\n", top="[domain]\nstale_months = 1\n")
    assert packs.stale(root, TODAY) == []


def test_ac6_a_top_level_stale_months_leaves_the_default(tmp_path):
    """REQ-084 AC6: SPEC-0077 rule 12 (a misplaced key is doctor's line; 12 holds here)."""
    root = project(tmp_path, [pack(tmp_path, reviewed="2025-10-03")], top="stale_months = 60\n")
    assert len(packs.stale(root, TODAY)) == 1


def test_ac6_a_pack_that_fails_its_check_gives_no_line(tmp_path):
    """REQ-084 AC6: SPEC-0077 rule 8 (the `playbooks` step names the pack, not this line)."""
    used = pack(tmp_path, reviewed="2020-01-01")
    root = project(tmp_path, [used])
    (root / REL / KNOW).write_text("changed = true\n", encoding="utf-8")
    assert doctor.pack_stale_lines(root) == []
    assert packs.report_lines(root, TODAY)[0].startswith("packs: stale unknown (")


# --- answer 2 and 8: where they show, never failing -----------------------------------------------


def test_ac6_doctor_shows_the_lines_and_never_a_fail(tmp_path, monkeypatch):
    """REQ-084 AC6: SPEC-0077 rule 8 (doctor's warn lines; no FAIL line)."""
    root = project(tmp_path, [pack(tmp_path, reviewed="2020-01-01")])
    monkeypatch.setattr(packs, "_today", lambda: TODAY)
    lines = doctor.pack_stale_lines(root)
    assert lines == packs.stale(root, TODAY) and len(lines) == 1
    assert all(ln.startswith("warn packs: ") and "FAIL" not in ln for ln in lines)


def test_ac6_doctor_main_appends_the_lines_beside_the_floor_lines():
    """REQ-084 AC6: SPEC-0077 rule 8 (wired in `doctor.main` and on a sidecar)."""
    import inspect

    main = inspect.getsource(doctor.main)
    assert "skills += pack_stale_lines(root.resolve())" in main
    assert "pack_stale_lines(root)" in inspect.getsource(doctor.personal_line)


def test_ac6_on_a_sidecar_doctor_adds_the_lines_and_keeps_its_exit(tmp_path, monkeypatch):
    """REQ-084 AC6: SPEC-0077 rule 8 (personal mode: the sidecar's packs, nothing posted)."""
    used = pack(tmp_path, reviewed="2020-01-01")
    top = '[personal]\nforge = "files"\n'
    root = project(tmp_path, [used], top=top)
    monkeypatch.setattr(packs, "_today", lambda: TODAY)
    found = doctor.personal_line(root)
    assert found is not None
    code, text = found
    (tmp_path / "fresh").mkdir()
    fresh = project(tmp_path / "fresh", [], top=top)
    assert code == doctor.personal_line(fresh)[0]
    assert f"warn packs: {PID} reviewed 2020-01-01" in text


def test_ac6_the_weekly_report_shows_the_lines_and_keeps_its_result(tmp_path, monkeypatch):
    """REQ-084 AC6: SPEC-0077 rule 8 (`metrics.report` with `--today`, no other read)."""
    root = project(tmp_path, [pack(tmp_path, reviewed="2020-01-01")])

    class Src:
        def get(self, name, path, older=None):
            return []

    ctx = metrics.Context(Src(), root, [])
    body, incomplete = metrics.report(ctx, TODAY, [])
    assert f"warn packs: {PID} reviewed 2020-01-01 is older than" in body
    assert incomplete is False
    (root / "agk.toml").write_text('review_mode = "solo"\n', encoding="utf-8")
    body, incomplete = metrics.report(ctx, TODAY, [])
    assert "packs: none stale" in body.splitlines() and incomplete is False


def test_ac6_the_sidecar_report_adds_the_lines_before_its_caution(tmp_path, monkeypatch):
    """REQ-084 AC6: SPEC-0077 rule 8 (`personal.py report` on the sidecar's packs)."""
    side = project(tmp_path, [pack(tmp_path, reviewed="2020-01-01")])
    monkeypatch.setattr(personal, "read_events", lambda sidecar: ([], 0))
    monkeypatch.setattr(personal, "ungated", lambda clone, sidecar: [])
    lines = personal.report(tmp_path, side, "2026-W48", today=TODAY).splitlines()
    assert lines[-1] == personal.CAUTION
    assert lines[-2].startswith(f"warn packs: {PID} reviewed 2020-01-01")


# --- answers 3 and 4: update --check --------------------------------------------------------------


def locked(tmp_path: Path, source: str = "https://example.com/packs/zz-guide.git") -> Path:
    used = pack(tmp_path, source=source)
    root = project(tmp_path, [used])
    (root / packs.LOCK).write_text(packs.lock_text([packs.lock_entry(root / REL)]))
    return root


def said(tmp_path: Path) -> Path:
    path = tmp_path / "said.txt"
    path.write_text("yes", encoding="utf-8")
    return path


def record(root, text):
    return 0, ["recorded"]


def snapshot(root: Path) -> dict[str, bytes]:
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob("*") if p.is_file()}


NOTES = {
    "1.3.0": "Adds two invented rules.\nA second line that is never shown.",
    "v1.4.0": None,  # a lightweight tag
    "1.5.0": "token = ghp_" + "a1B2c3D4e5F6g7H8i9J0k1L2m3N4o5P6q7R8",
    "1.6.0": "x" * 200 + "\x1b[31m",
}


def test_ac6_update_check_gives_each_newer_tag_its_note_and_writes_nothing(tmp_path):
    """REQ-084 AC6: SPEC-0077 rule 8 (`Q-PI-1`: the annotated tag's first line, cut, scanned)."""
    root = locked(tmp_path)
    yes = said(tmp_path)
    before = snapshot(root)
    asked = []

    def note(source, tag):
        asked.append(tag)
        return NOTES[tag]

    code, lines = packs.update_check(
        root,
        yes,
        "T",
        tags=lambda s: ["1.1.0", "1.2.0", "main", *NOTES],
        notes=note,
        record=record,
    )
    assert code == 0
    assert lines[1:] == [
        f"{PID} 1.2.0 -> 1.3.0: Adds two invented rules.",
        f"{PID} 1.2.0 -> v1.4.0: (no change notes)",
        f"{PID} 1.2.0 -> 1.5.0: (notes withheld: rule 6)",
        f"{PID} 1.2.0 -> 1.6.0: " + "x" * 120,
    ]
    assert asked == ["1.3.0", "v1.4.0", "1.5.0", "1.6.0"]
    assert snapshot(root) == before


def test_ac6_no_newer_tag_is_one_line(tmp_path):
    """REQ-084 AC6: SPEC-0077 rule 8 (the locked tag present, nothing newer)."""
    root = locked(tmp_path)
    code, lines = packs.update_check(
        root, said(tmp_path), "T", tags=lambda s: ["v1.2.0"], notes=None, record=record
    )
    assert (code, lines[-1]) == (0, f"{PID} 1.2.0: no newer tag")


def test_ac6_a_locked_tag_the_source_no_longer_has_is_withdrawn(tmp_path):
    """REQ-084 AC6: SPEC-0077 rule 8 (`Q-PI-2`: the source answered and the tag is gone)."""
    root = locked(tmp_path)
    code, lines = packs.update_check(
        root, said(tmp_path), "T", tags=lambda s: ["1.1.0"], notes=None, record=record
    )
    assert code == 0 and lines[1:] == [f"{PID} 1.2.0: withdrawn (verify)"]


def test_ac6_an_unreachable_source_is_cannot_check_never_withdrawn(tmp_path):
    """REQ-084 AC6: SPEC-0077 rule 8 (`Q-PI-2`: no answer is not a withdrawal)."""
    root = locked(tmp_path)
    code, lines = packs.update_check(
        root, said(tmp_path), "T", tags=lambda s: None, notes=None, record=record
    )
    assert (code, lines[1:]) == (4, [f"{PID}: cannot check (source: git)"])


def test_ac6_a_folder_source_gives_its_version_without_notes(tmp_path):
    """REQ-084 AC6: SPEC-0077 rule 8 (`Q-PI-1`: a folder has no notes; a missing one is named)."""
    root = locked(tmp_path, source="outside/zz-guide")
    newer = root / "outside" / PID
    newer.mkdir(parents=True)
    (newer / check_packs.MANIFEST).write_text('version = "1.4.0"\n', encoding="utf-8")
    code, lines = packs.update_check(root, said(tmp_path), "T", record=record)
    assert (code, lines[1:]) == (0, [f"{PID} 1.2.0 -> 1.4.0: (no change notes)"])
    (newer / check_packs.MANIFEST).unlink()
    code, lines = packs.update_check(root, said(tmp_path), "T", record=record)
    assert (code, lines[1:]) == (4, [f"{PID}: cannot check (source: folder)"])


def test_ac6_a_withdrawn_pack_still_verifies_offline(tmp_path, no_socket):
    """REQ-084 AC6: SPEC-0077 rule 8 (the lock and the project's copy are all a read needs)."""
    root = locked(tmp_path)
    assert packs.check(root) == []
    assert [layer for layer, _ in packs.files(root, "standards") if layer == PID] == [PID]


def test_ac6_the_note_reader_reads_only_an_https_source_and_an_exact_tag(tmp_path):
    """REQ-084 AC6: SPEC-0077 rules 4 and 8 (nothing runs for a source or tag out of form)."""
    assert packs.tag_note("--upload-pack=touch x;", "1.2.0") is None
    assert packs.tag_note("https://example.com/x.git", "--exec=x") is None
    assert packs.tag_note("file:///etc", "1.2.0") is None


@pytest.mark.parametrize(
    ("raw", "shown"),
    [
        ("Fixes a rule.\nmore", "Fixes a rule."),
        ("", "(no change notes)"),
        ("\x07\x1b", "(no change notes)"),
        ("tab\there", "tabhere"),
    ],
)
def test_ac6_a_note_is_cut_and_cleaned_as_data(raw, shown):
    """REQ-084 AC6: SPEC-0077 rule 8 (the first line, control characters dropped, 120 at most)."""
    assert packs.note_text(raw) == shown
