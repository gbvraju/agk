"""Tests of the product glossary and its `glossary` step (SPEC-0073 rule 8; REQ-080 AC5 and AC6;
brief #1951, ADR-0812).

`glossary.py --write` writes `docs/glossary.md` from `kit/templates/glossary.md` once and refuses a
second time; the step fails a table missing or with other columns, a row with no term or meaning,
a term twice (case-folded, trimmed, against every synonym of another row), more rows than
`[quality] glossary_terms` and a refused cap, each naming `SPEC-0073 rule 8` (or the setting), the
path class and the row number, never a term; aliases in `In code` are never rows; no glossary runs
nothing; and `run_gates.py` runs the step after the product steps only where the file exists.
Review checklist item 1 asks for a term against the glossary within its word count. Fixtures in
`tmp_path` only: invented data, no network.
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

import pytest

KIT_ROOT = Path(__file__).resolve().parents[2]
AGK = KIT_ROOT / "scripts" / "agk"
sys.path.insert(0, str(AGK))

import run_gates  # noqa: E402
from gates import glossary  # noqa: E402

PLANTED = "INVENTEDPLANTEDTERM"
HEAD = "| Term | Meaning | In code | Synonyms |\n| --- | --- | --- | --- |\n"


def _rows(n: int, start: int = 0) -> str:
    return "".join(f"| term{i} | a thing of example.com | `Term{i}` | |\n" for i in range(start, n))


def _root(tmp_path: Path, body: str | None, quality: str = "") -> Path:
    (tmp_path / "agk.toml").write_text('mode = "init"\n' + quality, encoding="utf-8")
    if body is not None:
        (tmp_path / "docs").mkdir(exist_ok=True)
        (tmp_path / "docs" / "glossary.md").write_text("# Glossary\n\n" + body, encoding="utf-8")
    return tmp_path


def _failures(root: Path) -> list[tuple[str, str]]:
    return glossary.check(root, {})


def test_write_writes_the_template_once_and_refuses_a_second_time(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """REQ-080 AC5."""
    assert glossary.main(["--root", str(tmp_path), "--write"]) == 0
    template = (KIT_ROOT / "kit" / "templates" / "glossary.md").read_text(encoding="utf-8")
    assert (tmp_path / "docs" / "glossary.md").read_text(encoding="utf-8") == template
    assert "ok glossary: wrote docs/glossary.md" in capsys.readouterr().out
    (tmp_path / "docs" / "glossary.md").write_text("kept\n", encoding="utf-8")
    assert glossary.main(["--root", str(tmp_path), "--write"]) == 1
    out = capsys.readouterr().out
    assert out == "FAIL glossary: the glossary exists (path class: docs/glossary.md)\n"
    assert (tmp_path / "docs" / "glossary.md").read_text(encoding="utf-8") == "kept\n"


def test_the_template_is_one_empty_table_that_passes(tmp_path: Path) -> None:
    """REQ-080 AC5: an empty table passes (0 rows); the header keeps the steward's notes."""
    text = (KIT_ROOT / "kit" / "templates" / "glossary.md").read_text(encoding="utf-8")
    assert HEAD.splitlines()[0] in text and "Term:" in text
    root = _root(tmp_path, None)
    (root / "docs").mkdir()
    (root / "docs" / "glossary.md").write_text(text, encoding="utf-8")
    assert _failures(root) == []


def test_distinct_rows_with_empty_code_and_synonym_cells_pass(tmp_path: Path) -> None:
    """REQ-080 AC5."""
    body = HEAD + "| order | a request of example.com | | |\n"
    body += "| basket | items held | `Cart` | trolley |\n"
    assert _failures(_root(tmp_path, body)) == []


@pytest.mark.parametrize(
    ("body", "row"),
    [
        (HEAD + f"| {PLANTED} | one | | |\n| {PLANTED.lower()}  | two | | |\n", 2),
        (HEAD + f"| first | one | | {PLANTED} |\n| {PLANTED} | two | | |\n", 2),
        (HEAD + f"| {PLANTED} | one | | |\n| other | two | | {PLANTED.lower()} |\n", 2),
    ],
)
def test_a_term_twice_fails_naming_the_row_and_never_the_term(
    tmp_path: Path, body: str, row: int
) -> None:
    """REQ-080 AC5: compared case-folded and trimmed, and against another row's synonyms."""
    found = _failures(_root(tmp_path, body))
    assert found == [(f"{glossary.TWICE} (row {row})", glossary.RECORD)]
    assert all(PLANTED.lower() not in rule.lower() for rule, _ in found)


@pytest.mark.parametrize(
    "body",
    [
        "no table here\n",
        "| Term | Meaning |\n| --- | --- |\n| a | b |\n",
        HEAD + "| a | b | | |\n\ntext\n\n" + HEAD + "| c | d | | |\n",
    ],
)
def test_a_missing_table_other_columns_or_two_tables_fail(tmp_path: Path, body: str) -> None:
    """REQ-080 AC5: one table of the four columns."""
    assert _failures(_root(tmp_path, body)) == [(glossary.FORM, glossary.RECORD)]


@pytest.mark.parametrize(
    ("line", "rule"),
    [
        (f"|  | {PLANTED} | | |\n", "EMPTY"),
        (f"| {PLANTED} |  | | |\n", "EMPTY"),
        (f"| {PLANTED} | one | | | extra |\n", "CELLS"),
    ],
)
def test_a_row_without_term_or_meaning_or_with_other_cells_fails(
    tmp_path: Path, line: str, rule: str
) -> None:
    """REQ-080 AC5."""
    found = _failures(_root(tmp_path, HEAD + "| ok | fine | | |\n" + line))
    assert found == [(f"{getattr(glossary, rule)} (row 2)", glossary.RECORD)]
    assert PLANTED not in found[0][0]


def test_escaped_pipes_crlf_and_aliases_are_text_not_rows(tmp_path: Path) -> None:
    """REQ-080 AC5: an `In code` cell of several aliases is one row."""
    body = HEAD + "| pipe | a \\| b | `A`, `B`, `C` | |\n" + _rows(39)
    root = _root(tmp_path, body.replace("\n", "\r\n"))
    assert _failures(root) == []


def test_the_cap_is_forty_by_default(tmp_path: Path) -> None:
    """REQ-080 AC5: 40 rows pass, 41 fail naming the setting."""
    assert _failures(_root(tmp_path, HEAD + _rows(40))) == []
    found = _failures(_root(tmp_path, HEAD + _rows(41)))
    assert found == [(glossary.CAP, glossary.RECORD)]
    assert "quality.glossary_terms" in glossary.CAP


def test_a_set_cap_is_read(tmp_path: Path) -> None:
    """REQ-080 AC5: the bounds 10 and 200."""
    assert _failures(_root(tmp_path, HEAD + _rows(10), "[quality]\nglossary_terms = 10\n")) == []
    over = _failures(_root(tmp_path, HEAD + _rows(11), "[quality]\nglossary_terms = 10\n"))
    assert over == [(glossary.CAP, glossary.RECORD)]
    assert _failures(_root(tmp_path, HEAD + _rows(41), "[quality]\nglossary_terms = 200\n")) == []


@pytest.mark.parametrize("value", ["9", "201", "true", '"40"'])
def test_a_refused_cap_fails_naming_the_setting_never_the_value(tmp_path: Path, value: str) -> None:
    """REQ-080 AC5 and AC7."""
    root = _root(tmp_path, HEAD + _rows(1), f"[quality]\nglossary_terms = {value}\n")
    assert _failures(root) == [(glossary.REFUSED, glossary.RECORD)]
    assert "setting: quality.glossary_terms" in glossary.REFUSED and value not in glossary.REFUSED


def test_other_quality_keys_are_not_read(tmp_path: Path) -> None:
    """REQ-080 AC7: a refused `grill` is not this step's."""
    assert _failures(_root(tmp_path, HEAD + _rows(1), '[quality]\ngrill = "x"\n')) == []


def test_no_glossary_applies_nothing_and_prints_nothing(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """REQ-080 AC5: the kit's own repository and every project today are unchanged."""
    root = _root(tmp_path, None)
    assert not glossary.applies(root)
    assert glossary.main(["--root", str(root)]) == 0
    assert capsys.readouterr().out == ""


def test_the_runner_runs_the_step_after_the_product_steps_only_where_the_file_exists(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """REQ-080 AC5: `QUALITY_STEPS` after `PRODUCT_STEPS`; a failure names the row."""
    assert run_gates.QUALITY_STEPS == ("glossary",)
    shutil.copytree(KIT_ROOT / "config" / "playbooks", tmp_path / "config" / "playbooks")
    root = _root(tmp_path, None)
    assert run_gates.main(["--root", str(root)]) == 0
    before = capsys.readouterr().out
    assert "glossary" not in before
    _root(tmp_path, HEAD + f"| {PLANTED} | one | | |\n| {PLANTED} | two | | |\n")
    assert run_gates.main(["--root", str(root)]) == 1
    out = capsys.readouterr().out
    assert f"FAIL gates: glossary: {glossary.TWICE} (row 2) (path class: docs/glossary.md)" in out
    assert PLANTED not in out
    _root(tmp_path, HEAD + _rows(2))
    assert run_gates.main(["--root", str(root)]) == 0
    assert "ok glossary\n" in capsys.readouterr().out


def test_checklist_item_one_asks_for_a_term_within_its_word_count() -> None:
    """REQ-080 AC6: item 1 keeps its kind and at most its 18 words (the brief said 19)."""
    lines = (KIT_ROOT / "config" / "review-checklist.md").read_text(encoding="utf-8").splitlines()
    item = next(line for line in lines if line.startswith("1. "))
    assert item.startswith("1. `wrong-assumption`:") and "docs/glossary.md" in item
    assert len(item[3:].split()) <= 18
