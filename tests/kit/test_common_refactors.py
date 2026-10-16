"""The three behaviour-preserving changes of SPEC-0009 rule 17 and the helpers they add.

The `legacy_*` functions are the code of the scripts before the change; the tests show that the
new code gives equal results on this repository and on the fixtures, and test the new helpers.
"""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path

import common
import drift_audit
import pytest

ROOT = Path(__file__).resolve().parents[2]


# --- the code as it was before the change ------------------------------------------------------


def legacy_parse_requirements(text: str) -> list[dict]:
    reqs: list[dict] = []
    for n, line in enumerate(text.splitlines(), 1):
        header = common.REQ_HEADER.match(line)
        if header:
            reqs.append({"id": header.group(1), "status": None, "status_count": 0, "line": n})
            continue
        status = common.STATUS_LINE.match(line)
        if status and reqs:
            reqs[-1]["status"] = status.group(1)
            reqs[-1]["status_count"] += 1
    return reqs


def legacy_find_markers(root, dirs, patterns=("test_*.py",), exclude=()):
    found: dict[str, set[str]] = {}
    skip = tuple(
        e.strip("/") + "/"
        for e in exclude
        if not any(d.strip("/").startswith(e.strip("/")) for d in dirs)
    )
    for d in dirs:
        base = root / d
        if not base.is_dir():
            continue
        paths = {p for pattern in patterns for p in base.rglob(pattern)}
        for path in sorted(paths):
            rel = path.relative_to(root).as_posix()
            if not path.is_file() or "__pycache__" in path.parts or rel.startswith(skip):
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue
            for req in set(common.REQ_ID.findall(text)):
                found.setdefault(req, set()).add(rel)
    return {k: sorted(v) for k, v in found.items()}


def legacy_d4_register(root, today):
    text = drift_audit.read(root, drift_audit.REGISTER)
    if text is None:
        return []
    found, in_open = [], False
    for number, line in enumerate(text.splitlines(), 1):
        if line.startswith("## "):
            in_open = line.strip() == "## Open"
        elif in_open and line.startswith("- "):
            parts = line[2:].split(" | ")
            due = drift_audit.DUE.fullmatch(parts[-2]) if len(parts) >= 4 else None
            when = drift_audit.parse_date(due.group(1)) if due else None
            fields = [parts[0], " | ".join(parts[1:-2]), parts[-1]] if len(parts) >= 4 else []
            F = drift_audit.Finding
            reg = drift_audit.REGISTER
            if when is None or not all(f.strip() for f in fields):
                found.append(F("D4", f"{reg}:{number}", "malformed register line"))
            elif when < today:
                found.append(F("D4", parts[0], f"register line is overdue since {when}"))
    return found


# --- rule 17 (a): parse_requirements ----------------------------------------------------------


def test_ac2_parse_requirements_old_fields_are_unchanged_on_this_repository():
    """REQ-018 AC2: SPEC-0009 rule 17 (a)."""
    path = ROOT / "docs" / "requirements.md"
    if not path.is_file():
        pytest.skip("no requirements file")
    text = path.read_text(encoding="utf-8")
    old = legacy_parse_requirements(text)
    new = common.parse_requirements(text)
    assert [{k: r[k] for k in old[0]} for r in new] == old
    assert all(r["title"] for r in new)


def test_ac2_parse_requirements_reads_the_title_and_the_acceptance_line():
    """REQ-018 AC2: rule 17 (a); the title is the text after the em dash."""
    text = (
        "# R\n\n### REQ-901 — First thing\n\n- Acceptance: AC1 a; AC2 b\n- Status: done\n\n"
        "### REQ-902 — Second\n\n- Status: planned\n\n### REQ-903\n\n- Acceptance:\n"
    )
    first, second, third = common.parse_requirements(text)
    assert (first["title"], first["acceptance"], first["status"]) == (
        "First thing",
        "AC1 a; AC2 b",
        "done",
    )
    assert (second["title"], second["acceptance"]) == ("Second", None)
    assert (third["title"], third["acceptance"]) == (None, "")


# --- rule 17 (b): parse_acceptance, find_ac_markers --------------------------------------------


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("AC1 one; AC2 two", [("AC1", "one"), ("AC2", "two")]),
        ("AC1 one;", [("AC1", "one")]),
        ("AC1 given a, when b; then c; AC2 d", [("AC1", "given a, when b; then c"), ("AC2", "d")]),
        ("no marker here", []),
        ("see AC1 inside", []),
        ("AC1 x;AC2 y", [("AC1", "x;AC2 y")]),
        ("AC10 ten; AC2 two", [("AC10", "ten"), ("AC2", "two")]),
        ("", []),
    ],
)
def test_ac2_parse_acceptance_grammar(text, expected):
    """REQ-018 AC2: SPEC-0009 rule 8 (the grammar) through rule 17 (b)."""
    assert common.parse_acceptance(text) == expected


def marked(text: str) -> str:
    """Test data: `@` stands for `REQ-`, so that no line of this file is itself a marker."""
    return text.replace("@", "REQ-")


def write(root: Path, rel: str, text: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_ac2_find_ac_markers_reads_runs_of_requirements_in_any_language(tmp_path):
    """REQ-018 AC2: rule 9 (marker grammar); REQ-016 AC1: a non-Python tree."""
    write(
        tmp_path,
        "tests/test_a.py",
        marked('"""@909 AC2"""\n# @901 @902 AC2\n# @903/@904 AC1, @905\n@906, @907 AC3\n'),
    )
    write(tmp_path, "pkg/x_test.go", marked("// @910 AC1\nfunc TestX() {}\n"))
    got = common.find_ac_markers(tmp_path, ["tests", "pkg"], ["test_*.py", "*_test.go"])
    summary = [(m["file"], m["line"], m["req"], m["ac"]) for m in got]
    assert summary == [
        ("pkg/x_test.go", 1, "REQ-910", "AC1"),
        ("tests/test_a.py", 1, "REQ-909", "AC2"),
        ("tests/test_a.py", 2, "REQ-901", "AC2"),
        ("tests/test_a.py", 2, "REQ-902", "AC2"),
        ("tests/test_a.py", 3, "REQ-903", "AC1"),
        ("tests/test_a.py", 3, "REQ-904", "AC1"),
        ("tests/test_a.py", 3, "REQ-905", None),
        ("tests/test_a.py", 4, "REQ-906", "AC3"),
        ("tests/test_a.py", 4, "REQ-907", "AC3"),
    ]
    assert set(got[0]) == {"req", "ac", "file", "line"}


def test_ac2_find_ac_markers_one_ac_per_run_and_skipped_directories(tmp_path):
    """REQ-018 AC2: rule 9; `AC1 AC2` is one run, and the six directories are skipped."""
    write(tmp_path, "tests/test_b.py", marked("# @901 AC1 AC2\n# @902 AC1 @903 AC2\n"))
    for skipped in (".git", "node_modules", "vendor", "target", "__pycache__", ".venv"):
        write(tmp_path, f"tests/{skipped}/test_hidden.py", marked("# @999 AC1\n"))
    got = common.find_ac_markers(tmp_path, ["tests"])
    assert [(m["line"], m["req"], m["ac"]) for m in got] == [
        (1, "REQ-901", "AC1"),
        (2, "REQ-902", "AC1"),
        (2, "REQ-903", "AC2"),
    ]


def test_ac2_find_ac_markers_keeps_the_adopt_mode_exclusion(tmp_path):
    """REQ-018 AC2: rule 9 keeps the `tests/kit` exclusion of find_markers."""
    write(tmp_path, "tests/kit/test_k.py", marked("# @901 AC1\n"))
    write(tmp_path, "tests/test_p.py", marked("# @902 AC1\n"))
    got = common.find_ac_markers(tmp_path, ["tests"], exclude=["tests/kit"])
    assert [m["req"] for m in got] == ["REQ-902"]


# --- find_markers keeps its signature and result ------------------------------------------------


def test_ac2_find_markers_is_unchanged_on_this_repository_and_on_a_tree(tmp_path):
    """REQ-018 AC2: rule 17 (b): `find_markers` keeps its signature and result."""
    for root, dirs, patterns in (
        (ROOT, ["tests"], ("test_*.py",)),
        (ROOT, ["tests/kit"], ("test_*.py", "*.json")),
    ):
        assert common.find_markers(root, dirs, patterns) == legacy_find_markers(
            root, dirs, patterns
        )
    write(tmp_path, "tests/test_a.py", "# REQ-901 REQ-902\n")
    write(tmp_path, "tests/kit/test_b.py", "# REQ-903\n")
    write(tmp_path, "tests/__pycache__/test_c.py", "# REQ-904\n")
    for exclude in ((), ("tests/kit",)):
        assert common.find_markers(tmp_path, ["tests"], exclude=exclude) == legacy_find_markers(
            tmp_path, ["tests"], exclude=exclude
        )


# --- rule 17 (c): register_lines --------------------------------------------------------------

REGISTER = (
    "# R\n\n## Open\n\n"
    "- docs/adr/0001-x.md 2026-10-01 | text one | (due 2026-12-31) | open\n"
    "- docs/adr/0002-x.md 2026-10-01 | has | a pipe | (due 2026-01-02) | open\n"
    "- docs/adr/0003-x.md 2026-10-01 | no date | open\n"
    "- docs/adr/0004-x.md 2026-10-01 | bad | (due 2026-13-45) | open\n"
    "- docs/adr/0005-x.md 2026-10-01 |  | (due 2026-12-31) | open\n\n"
    "## Closed (not findings)\n\n| a | b | c |\n| --- | --- | --- |\n| x | y | z |\n"
)


def test_ac2_register_lines_parses_the_open_lines():
    """REQ-018 AC2: rule 17 (c)."""
    lines = drift_audit.register_lines(REGISTER)
    assert [(i["number"], i["well_formed"]) for i in lines] == [
        (5, True),
        (6, True),
        (7, False),
        (8, False),
        (9, False),
    ]
    assert lines[0]["source"] == "docs/adr/0001-x.md 2026-10-01"
    assert lines[0]["text"] == "text one"
    assert lines[0]["due"] == date(2026, 12, 31)
    assert lines[1]["text"] == "has | a pipe"
    assert drift_audit.register_lines("# nothing\n") == []


@pytest.mark.parametrize("today", [date(2026, 10, 15), date(2027, 6, 1)])
def test_ac2_d4_register_is_unchanged_on_this_repository_and_a_fixture(tmp_path, today):
    """REQ-018 AC2: rule 17 (c): `d4_register` gives the findings it gave before."""
    assert drift_audit.d4_register(ROOT, today) == legacy_d4_register(ROOT, today)
    write(tmp_path, "docs/runs/residuals.md", REGISTER)
    got = drift_audit.d4_register(tmp_path, today)
    assert got == legacy_d4_register(tmp_path, today)
    assert any("malformed" in f.sentence for f in got)


def test_ac2_nothing_in_the_new_code_names_a_language():
    """REQ-018 AC2: the new helpers read no language: no test pattern is hard-coded in common."""
    source = (ROOT / "scripts" / "agk" / "common.py").read_text(encoding="utf-8")
    assert not re.search(r"\.(go|rs|ts|java)\b", source)
