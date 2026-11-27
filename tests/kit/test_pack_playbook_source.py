"""Tests of a pack playbook's provenance (SPEC-0077 rules 3 and 5; REQ-084; brief #2040, ADR-0844).

A pack's playbook carries rule 3's dated `source` or `basis = "expected"` on each top-level entry,
so `check_packs` (which requires it) and `playbook_format.problems` (which refused it) stop refusing
each other; the kit's and the project's own playbooks keep today's format. Fixtures in `tmp_path`
only: invented data (`example.com`), no network, no model.
"""

from __future__ import annotations

import re
import shutil
import sys
from pathlib import Path

import pytest

KIT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KIT_ROOT / "scripts" / "agk"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import check_packs  # noqa: E402
import check_playbooks  # noqa: E402
import packs  # noqa: E402
import playbook_format  # noqa: E402
from test_packs_resolver import clean, use, write_pack  # noqa: E402

SOURCE = 'source = "https://example.com/rows (accessed 2026-11-20)"'
EXPECTED = 'basis = "expected"'
PLUGIN = '[kit]\nlayout = "plugin"\n'
WEB = KIT_ROOT / "config/playbooks/web-app.toml"
SECTIONS = ("phases", "lanes", "gates", "claims", "discovery")


def marked(line: str | None, text: str | None = None) -> str:
    """The kit's web-app playbook with LINE on each top-level `[[...]]` entry (None: as it is)."""
    text = WEB.read_text(encoding="utf-8") if text is None else text
    if line is None:
        return text
    key = line.split(" ", 1)[0]
    blocks = re.split(r"(?m)^(?=\[)", text)
    return "".join(
        b.replace("]]\n", f"]]\n{line}\n", 1)
        if b.startswith("[[") and "." not in b.split("]]", 1)[0] and f"\n{key} = " not in b
        else b
        for b in blocks
    )


def tree(root: Path, playbook: str, extra: str = PLUGIN, pid: str = "zz-a") -> Path:
    root.mkdir(parents=True, exist_ok=True)
    clean(root)
    use(root, write_pack(root, pid, {"playbooks/web-app.toml": playbook}), extra=extra)
    return root / "config/packs" / pid / "playbooks/web-app.toml"


def lines(root: Path) -> list[str]:
    """The `FAIL playbooks:` lines of the step: `findings`, or the one line `run` prints."""
    try:
        return check_playbooks.findings(root)
    except packs.Refused as exc:
        return [str(exc)]


# --- answer 1: a pack playbook with provenance passes both checks -------------------------------


@pytest.mark.parametrize("line", [SOURCE, EXPECTED])
def test_a_sourced_pack_playbook_gives_no_line(tmp_path, line):
    """REQ-084: SPEC-0077 rule 3 (a dated source or expected on each entry: no line)."""
    path = tree(tmp_path, marked(line))
    assert check_packs.findings(tmp_path) == []
    assert playbook_format.problems(path, tmp_path) == []
    assert lines(tmp_path) == []


def test_measured_before_after_of_the_brief(tmp_path):
    """REQ-084: the brief's Measured line: 0 and 0 with provenance, 16 and 0 without."""
    for line, want in ((SOURCE, 0), (None, 16)):
        path = tree(tmp_path / str(want), marked(line))
        assert len(check_packs._knowledge(path)) == want
    assert playbook_format.problems(tree(tmp_path / "s", marked(SOURCE)), tmp_path / "s") == []


def test_a_pack_playbook_without_provenance_gives_check_packs_lines_only(tmp_path):
    """REQ-084: SPEC-0077 rule 3 (no provenance: the pack check's line, no format line)."""
    tree(tmp_path, marked(None))
    found = lines(tmp_path)
    assert found and all("rule 3: config/packs/zz-a:" in line for line in found)
    assert not [line for line in found if "outside the format" in line]


def test_a_bad_source_beside_expected_names_rule_3_the_file_and_the_key(tmp_path):
    """REQ-084: SPEC-0077 rule 3 (a source that is not a URL and a date, never its value)."""
    text = marked(EXPECTED).replace(EXPECTED, f'{EXPECTED}\nsource = "zz-not-a-url"', 1)
    path = tree(tmp_path, text)
    rel = "config/packs/zz-a/playbooks/web-app.toml"
    want = (
        f"SPEC-0077 rule 3: {rel}: an entry `source` is not a URL and an access date (key: source)"
    )
    assert playbook_format.problems(path, tmp_path) == [want]
    assert "zz-not-a-url" not in "".join(lines(tmp_path))


def test_a_bad_source_alone_is_refused_by_the_pack_check(tmp_path):
    """REQ-084: SPEC-0077 rule 3 (a source alone that is not dated: the pack check's line)."""
    tree(tmp_path, marked('source = "zz-not-a-url"'))
    assert lines(tmp_path) == [
        "packs: rule 3: config/packs/zz-a: an entry has neither a dated `source` nor "
        '`basis = "expected"` (key: source)'
    ]


def test_a_basis_of_the_wrong_type_is_refused(tmp_path):
    """REQ-084: SPEC-0077 rule 3 (a bool `basis` is not expected)."""
    tree(tmp_path, marked("basis = true"))
    assert lines(tmp_path) and all("(key: source)" in line for line in lines(tmp_path))
    found = playbook_format._provenance("x.toml", "phases", {"name": "a", "basis": True})
    assert found == ["SPEC-0077 rule 3: x.toml: an entry `basis` is not expected (key: basis)"]


def test_source_and_expected_together_are_accepted(tmp_path):
    """REQ-084: SPEC-0077 rule 3 (both keys, as SPEC-0048 rule 22 accepts)."""
    path = tree(tmp_path, marked(SOURCE, marked(EXPECTED)))
    assert playbook_format.problems(path, tmp_path) == []
    assert lines(tmp_path) == []


# --- answer 2: the kit's and the project's playbooks keep today's format ------------------------


def test_the_kits_playbooks_with_a_source_keep_todays_refusal(tmp_path):
    """REQ-084: SPEC-0048 rule 22 (a shipped playbook's entry carries no provenance)."""
    own = tmp_path / "config/playbooks/web-app.toml"
    own.parent.mkdir(parents=True)
    own.write_text(marked(SOURCE), encoding="utf-8")
    found = playbook_format.problems(own, tmp_path)
    for section in SECTIONS:
        assert f"rule 2 and rule 4: config/playbooks/web-app.toml: a [[{section}]] entry has a " \
            "key outside the format" in found  # fmt: skip


def test_the_projects_own_playbook_in_a_clean_project_keeps_todays_refusal(tmp_path):
    """REQ-084: SPEC-0077 rule 5 (the project's own layer is never a pack layer)."""
    tree(tmp_path, marked(SOURCE))
    own = tmp_path / "config/playbooks/web-app.toml"
    own.parent.mkdir(parents=True)
    own.write_text(marked(SOURCE), encoding="utf-8")
    assert [p for p in playbook_format.problems(own, tmp_path) if "outside the format" in p]


def test_a_copy_in_a_pack_folder_not_in_use_is_not_a_pack_layer(tmp_path):
    """REQ-084: SPEC-0077 rule 12 (a folder not in `use`: refused, and read as no pack)."""
    path = tree(tmp_path, marked(SOURCE))
    (tmp_path / "agk.toml").write_text(PLUGIN, encoding="utf-8")
    assert [p for p in playbook_format.problems(path, tmp_path) if "outside the format" in p]
    assert any("rule 12:" in line for line in check_packs.findings(tmp_path))


# --- answer 3: a measured claim proves its provenance with a dated source -----------------------


def test_a_measured_claim_with_a_dated_source_passes_the_pack_check(tmp_path):
    """REQ-084: SPEC-0077 rule 3, `Q-PS-1` (on a claim `basis` keeps its claim meaning)."""
    record = tmp_path / "docs/runs/zz-record.md"
    record.parent.mkdir(parents=True)
    record.write_text("measured\n", encoding="utf-8")
    record_line = 'record = "docs/runs/zz-record.md"'
    claim = f'[[claims]]\ntext = "zz"\nbasis = "measured"\n{record_line}\n{SOURCE}\n'
    path = tree(tmp_path, marked(EXPECTED) + "\n" + claim)
    assert check_packs.findings(tmp_path) == []
    assert playbook_format.problems(path, tmp_path) == []
    assert not check_packs._sourced({"basis": "measured"}, "claims")
    assert not check_packs._sourced({"basis": "measured", "source": SOURCE[10:-1]}, "phases")
    assert check_packs._sourced({"basis": "measured", "source": SOURCE[10:-1]}, "claims")


# --- answer 4: the settings ---------------------------------------------------------------------


def test_with_no_table_the_kit_tree_equals_the_snapshot():
    """REQ-084: SPEC-0077 rule 5 (no `[packs]` table: no file is a pack layer)."""
    assert check_playbooks.findings(KIT_ROOT, playbook_format.playbooks(KIT_ROOT)) == []
    assert all(
        playbook_format._pack_layer(p, KIT_ROOT) is None
        for p in playbook_format.playbooks(KIT_ROOT)
    )


def test_an_empty_use_reads_no_pack_layer(tmp_path):
    """REQ-084: SPEC-0077 rule 5 (`use = []`)."""
    path = tree(tmp_path, marked(SOURCE))
    (tmp_path / "agk.toml").write_text(PLUGIN + "[packs]\nuse = []\n", encoding="utf-8")
    assert playbook_format._pack_layer(path, tmp_path) is None


def test_two_packs_restating_one_playbook_are_each_a_pack_layer(tmp_path):
    """REQ-084: SPEC-0077 rule 5 (each pack's file is checked as its own layer)."""
    clean(tmp_path)
    text = marked(SOURCE)
    one = write_pack(tmp_path, "zz-a", {"playbooks/web-app.toml": text})
    two = write_pack(tmp_path, "zz-b", {"playbooks/web-app.toml": text})
    use(tmp_path, one, two, extra=PLUGIN)
    for pid in ("zz-a", "zz-b"):
        path = tmp_path / "config/packs" / pid / "playbooks/web-app.toml"
        assert playbook_format._pack_layer(path, tmp_path) == pid
    assert lines(tmp_path) == []


def test_the_installed_layout_reads_the_layer_from_the_resolver(tmp_path):
    """REQ-084: SPEC-0077 rule 5 (the installed layout: the project's playbook is `agk-core`)."""
    shutil.copytree(KIT_ROOT / "config/playbooks", tmp_path / "config/playbooks")
    path = tree(tmp_path, marked(SOURCE), extra="")
    assert playbook_format._pack_layer(path, tmp_path) == "zz-a"
    assert playbook_format.problems(path, tmp_path) == []
    own = tmp_path / "config/playbooks/web-app.toml"
    assert playbook_format._pack_layer(own, tmp_path) is None


def test_a_partial_copy_with_no_resolver_reads_no_pack_layer(tmp_path, monkeypatch):
    """REQ-084: SPEC-0077 rule 5 (no `packs.py`: today's format holds)."""
    path = tree(tmp_path, marked(SOURCE))
    monkeypatch.setattr(playbook_format, "resolver", lambda: None)
    assert playbook_format._pack_layer(path, tmp_path) is None
    assert [p for p in playbook_format.problems(path, tmp_path) if "outside the format" in p]


def test_a_refused_packs_table_reads_no_pack_layer(tmp_path):
    """REQ-084: SPEC-0077 rule 12 (a refused table: check_packs's line, no pack layer)."""
    path = tree(tmp_path, marked(SOURCE))
    (tmp_path / "agk.toml").write_text(PLUGIN + '[packs]\nuse = "zz"\n', encoding="utf-8")
    assert playbook_format._pack_layer(path, tmp_path) is None
    assert any(line.startswith("rule 12:") for line in check_packs.findings(tmp_path))


def test_a_derived_playbook_keeps_rule_22(tmp_path):
    """REQ-084: SPEC-0048 rule 22 (a derived playbook's gates, unchanged)."""
    record = tmp_path / playbook_format.RESEARCH / "zz-own.md"
    record.parent.mkdir(parents=True)
    record.write_text("research\n", encoding="utf-8")
    own = tmp_path / "config/playbooks/zz-own.toml"
    own.parent.mkdir(parents=True)
    text = marked(None).replace('work_type = "web-app"', 'work_type = "zz-own"')
    own.write_text(text, encoding="utf-8")
    found = playbook_format.problems(own, tmp_path)
    assert (
        "rule 22: config/playbooks/zz-own.toml: a gate has neither `source` nor "
        '`basis = "expected"`' in found
    )


def test_a_nested_table_with_provenance_is_still_refused(tmp_path):
    """REQ-084: `Q-PS-2` (a `[[testing.map]]` entry needs no provenance and takes none)."""
    text = marked(SOURCE).replace("[split]\n", f"[split]\n{SOURCE}\n", 1)
    path = tree(tmp_path, text)
    assert playbook_format._pack_layer(path, tmp_path) == "zz-a"
    found = playbook_format.problems(path, tmp_path)
    assert "rule 2 and rule 4: config/packs/zz-a/playbooks/web-app.toml: [split] has a key " \
        "outside the format" in found  # fmt: skip


# --- answer 7: the class stays closed -----------------------------------------------------------


@pytest.mark.parametrize("key", packs.PROVENANCE)
def test_no_key_the_pack_check_requires_is_refused_by_the_playbook_check(tmp_path, key):
    """REQ-084: SPEC-0077 rule 3 (every provenance key, on a playbook and a standards file)."""
    line = SOURCE if key == "source" else EXPECTED
    clean(tmp_path)
    standards = (KIT_ROOT / "config/standards.toml").read_text(encoding="utf-8")
    files = {
        "playbooks/web-app.toml": marked(line),
        "standards/standards.toml": marked(line, standards),
    }
    use(tmp_path, write_pack(tmp_path, "zz-a", files), extra=PLUGIN)
    assert check_packs.findings(tmp_path) == []
    assert lines(tmp_path) == []
    assert check_playbooks.standards_file(tmp_path)[1] == []
