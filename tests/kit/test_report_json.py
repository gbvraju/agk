"""Tests of `product_report.py --json` and the report.json it writes (SPEC-0022 rules 1, 3, 4, 8).

The file is the structure the markdown is rendered from, written as JSON: the same facts and the
same run give the same bytes. No network, no model.
"""

from __future__ import annotations

import json
import os
import subprocess  # nosec B404 - fixed argument lists, no shell
import sys

import pytest
from test_product_report import CASES, GOLDEN, MASK, PR, SOURCE, main

GOLDEN_FILE = "report.json"


def run_json(facts, out, *extra, capsys):
    code = main(["--facts", str(facts), "--json", str(out), *extra])
    return code, capsys.readouterr().out


@pytest.mark.parametrize(("name", "facts"), CASES, ids=[name for name, _ in CASES])
def test_ac1_json_writes_the_structure_and_the_markdown_is_unchanged(name, facts, tmp_path, capsys):
    """REQ-029 AC1 and AC2: rules 1 and 2 (the file is the structure; the stdout is as before)."""
    import product_report as pr

    plain = main(["--facts", str(facts)])
    printed = capsys.readouterr().out
    out = tmp_path / "report.json"
    code, with_json = run_json(facts, out, capsys=capsys)
    assert (plain, code) == (0, 0) and with_json == printed
    document = json.loads(out.read_text(encoding="utf-8"))
    assert pr.render_markdown(document) == printed


@pytest.mark.parametrize(("name", "facts"), CASES, ids=[name for name, _ in CASES])
def test_ac1_the_file_is_utf8_two_space_indent_one_final_newline_in_the_order_of_the_table(
    name, facts, tmp_path, capsys
):
    """REQ-029 AC1 and AC5: rules 3 to 5 and 8 (key order of the table, no sorting)."""
    import product_report as pr

    out = tmp_path / "report.json"
    run_json(facts, out, capsys=capsys)
    raw = out.read_bytes()
    document = json.loads(raw)
    assert raw == (json.dumps(document, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
    assert list(document) == ["schema", "week", "opening", "sections", "counts", "notices"]
    entries = list(document["notices"])
    for key, section in document["sections"].items():
        entries += [i for g in section for i in g["items"]] if key == "needs_you" else section
    for entry in entries:
        order = [*pr.ITEM_KINDS[entry["kind"]], *pr.OPTIONAL_FIELDS.get(entry["kind"], ())]
        assert list(entry) == ["kind", *[f for f in order if f in entry], "links"], entry


@pytest.mark.parametrize(("name", "facts"), CASES, ids=[name for name, _ in CASES])
def test_ac5_two_runs_give_byte_identical_files(name, facts, tmp_path, capsys):
    """REQ-029 AC5: rule 8."""
    first, second = tmp_path / "one.json", tmp_path / "two.json"
    run_json(facts, first, capsys=capsys)
    run_json(facts, second, capsys=capsys)
    assert first.read_bytes() == second.read_bytes()


@pytest.mark.parametrize(("name", "facts"), CASES, ids=[name for name, _ in CASES])
def test_ac1_the_file_equals_its_golden(name, facts, tmp_path, capsys):
    """REQ-029 AC1: rules 3 to 5 (one report.json per golden facts; the pull request mask)."""
    out = tmp_path / "report.json"
    run_json(facts, out, capsys=capsys)
    text = out.read_text(encoding="utf-8")
    golden = GOLDEN / name / GOLDEN_FILE
    if os.environ.get("AGK_WRITE_GOLDENS") == "1":
        golden.parent.mkdir(parents=True, exist_ok=True)
        golden.write_text(text.replace(PR, MASK), encoding="utf-8")
    assert text == golden.read_text(encoding="utf-8").replace(MASK, PR)


def test_ac3_unknown_is_the_string_and_the_file_has_no_null(tmp_path, capsys):
    """REQ-029 AC3: rule 6 (facts that could not be read)."""
    from test_product_report import REPORT

    out = tmp_path / "report.json"
    run_json(REPORT / "dirty-unknown" / "facts.json", out, capsys=capsys)
    text = out.read_text(encoding="utf-8")
    assert '"unknown"' in text and "null" not in text


def test_ac1_json_is_refused_with_the_inbox_and_with_print_action(tmp_path):
    """REQ-029 AC1: rule 1 (a usage error; no file is written)."""
    from test_product_report import REPORT

    facts = REPORT / "kinds" / "facts.json"
    for flag in ("--inbox", "--print-action"):
        out = tmp_path / "report.json"
        with pytest.raises(SystemExit) as stop:
            main(["--facts", str(facts), flag, "--json", str(out)])
        assert stop.value.code == 2 and not out.exists()


def test_ac1_without_json_no_file_is_written(tmp_path, capsys):
    """REQ-029 AC1: rule 1 (the script behaves as before)."""
    from test_product_report import REPORT

    cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        main(["--facts", str(REPORT / "kinds" / "facts.json")])
    finally:
        os.chdir(cwd)
    capsys.readouterr()
    assert list(tmp_path.iterdir()) == []


def test_ac1_an_unwritable_json_path_is_refused_by_path_class(tmp_path, capsys):
    """REQ-029 AC1: rule 1 (a refusal names the option, not the path)."""
    from test_product_report import REPORT

    code = main(
        [
            "--facts",
            str(REPORT / "kinds" / "facts.json"),
            "--json",
            str(tmp_path / "missing" / "report.json"),
        ]
    )
    out = capsys.readouterr().out
    assert code == 1 and "option: --json" in out and str(tmp_path) not in out


def test_ac8_the_script_runs_json_in_an_empty_environment(tmp_path):
    """REQ-029 AC8: rule 10 (no environment, no HOME, no working copy)."""
    from test_product_report import REPORT

    out = tmp_path / "report.json"
    proc = subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, "-I", str(SOURCE), "--facts", str(REPORT / "kinds" / "facts.json")]
        + ["--json", str(out)],
        cwd=tmp_path,
        env={},
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr
    assert json.loads(out.read_text(encoding="utf-8"))["schema"] == 6
