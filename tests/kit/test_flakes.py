"""The flake ledger (brief #435, ADR-0234).

`docs/runs/flakes.md` holds one table, `test | owner | strikes | status | expires | issue`.
`scripts/agk/flakes.py [--today DATE] [--json]` reads it and lists each quarantined entry past its
expiry (`expired`), each entry with two strikes or more and no issue (`brief due`) and each
malformed row with its line number; it exits 0 when nothing is listed and 1 otherwise. It reads one
file, uses no network and blocks nothing: it is not a governance step.

REQ-016 (managed flakes: a flaky test is recorded, owned and due, never retried away).
"""

from __future__ import annotations

import json
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
from pathlib import Path

import flakes

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "agk" / "flakes.py"
LEDGER = "docs/runs/flakes.md"
HEADER = "| test | owner | strikes | status | expires | issue |"
HEAD = HEADER + "\n| --- | --- | --- | --- | --- | --- |\n"
TODAY = "2031-05-10"


def ledger(*rows: str, before: str = "# Flake ledger\n\n") -> str:
    return before + HEAD + "".join(f"{r}\n" for r in rows)


def run(repo, *args: str):
    proc = subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, str(SCRIPT), *args],
        cwd=repo.root,
        capture_output=True,
        text=True,
    )
    return proc.returncode, proc.stdout.splitlines()


def with_ledger(repo, text: str):
    repo.commit({LEDGER: text}, "ledger")
    return repo


# --- answer 4: the six cases the brief names first ------------------------------------------------


def test_an_expired_quarantine_is_listed_as_expired(repo):
    """REQ-016: answer 2, first bullet; a quarantine past its expiry is listed, exit 1."""
    with_ledger(
        repo,
        ledger(
            "| tests/test_upload.py::test_retries | builder-a1 | 1 | quarantined "
            "| 2031-05-09 | #12 |"
        ),
    )
    code, out = run(repo, "--today", TODAY)
    assert code == 1, out
    assert out[0] == (
        "expired: line 5: tests/test_upload.py::test_retries "
        "(owner builder-a1; quarantined until 2031-05-09)"
    )
    assert out[-1] == f"flakes: 1 listed (1 expired, 0 brief due, 0 malformed) in {LEDGER}"


def test_a_quarantine_that_expires_today_is_not_yet_expired(repo):
    """REQ-016: answer 2: `past its expiry` is a date before today, never today itself."""
    with_ledger(
        repo, ledger("| tests/test_a.py::test_x | conductor | 1 | quarantined | 2031-05-10 | #3 |")
    )
    code, out = run(repo, "--today", TODAY)
    assert code == 0, out
    assert out == [f"flakes: nothing due (1 entry) in {LEDGER}"]


def test_two_strikes_and_no_issue_is_a_brief_due(repo):
    """REQ-016: answer 2, second bullet; a watched test with two strikes and no issue."""
    with_ledger(repo, ledger("| tests/test_b.py::test_y | builder-a1 | 2 | watch |  |  |"))
    code, out = run(repo, "--today", TODAY)
    assert code == 1, out
    assert out[0] == (
        "brief due: line 5: tests/test_b.py::test_y (owner builder-a1; 2 strikes, no issue)"
    )
    assert out[-1] == f"flakes: 1 listed (0 expired, 1 brief due, 0 malformed) in {LEDGER}"


def test_three_strikes_and_no_issue_is_a_brief_due_too(repo):
    """REQ-016: answer 2: two strikes `or more`."""
    with_ledger(repo, ledger("| tests/test_b.py::test_y | builder-a1 | 3 | watch |  |  |"))
    code, out = run(repo, "--today", TODAY)
    assert code == 1 and out[0].startswith("brief due: line 5: tests/test_b.py::test_y "), out


def test_two_strikes_with_an_issue_is_not_listed(repo):
    """REQ-016: answer 2: an entry that names its issue is already a brief; nothing is due."""
    with_ledger(repo, ledger("| tests/test_b.py::test_y | builder-a1 | 2 | watch |  | #44 |"))
    code, out = run(repo, "--today", TODAY)
    assert code == 0, out
    assert out == [f"flakes: nothing due (1 entry) in {LEDGER}"]


def test_one_strike_and_no_issue_is_only_watched(repo):
    """REQ-016: answer 2: one strike is recorded and watched, not yet due."""
    with_ledger(repo, ledger("| tests/test_b.py::test_y | builder-a1 | 1 | watch |  |  |"))
    assert run(repo, "--today", TODAY)[0] == 0


def test_an_expired_quarantine_with_two_strikes_and_no_issue_is_listed_twice(repo):
    """REQ-016: answer 2: the two lists are independent; one entry can be in both."""
    with_ledger(
        repo, ledger("| tests/test_c.py::test_z | conductor | 2 | quarantined | 2031-01-01 |  |")
    )
    code, out = run(repo, "--today", TODAY)
    assert code == 1
    assert [ln.split(":")[0] for ln in out[:-1]] == ["expired", "brief due"]
    assert out[-1] == f"flakes: 2 listed (1 expired, 1 brief due, 0 malformed) in {LEDGER}"


def test_a_malformed_row_is_listed_with_its_line_number(repo):
    """REQ-016: answer 2, third bullet; the message names the column, never the value."""
    with_ledger(
        repo,
        ledger(
            "| tests/test_ok.py::test_ok | builder-a1 | 0 | watch |  |  |",
            "| tests/test_d.py::test_w | builder-a1 | two | watch |  |  |",
        ),
    )
    code, out = run(repo, "--today", TODAY)
    assert code == 1, out
    assert out[0] == "malformed: line 6: strikes is not a whole number"
    assert "two" not in out[0].split(":", 2)[2]
    assert out[-1] == f"flakes: 1 listed (0 expired, 0 brief due, 1 malformed) in {LEDGER}"


def test_an_empty_ledger_lists_nothing(repo):
    """REQ-016: answer 4: the header alone is a valid, empty ledger."""
    with_ledger(repo, ledger())
    code, out = run(repo, "--today", TODAY)
    assert code == 0
    assert out == [f"flakes: nothing due (0 entries) in {LEDGER}"]


def test_no_file_lists_nothing_and_says_so(repo):
    """REQ-016: answer 4: a project without the ledger has recorded no flake; exit 0."""
    repo.commit({"README.md": "x\n"}, "base")
    code, out = run(repo, "--today", TODAY)
    assert code == 0
    assert out == [f"flakes: no ledger at {LEDGER}; nothing due"]


# --- each malformed shape, by column --------------------------------------------------------------


def malformed(repo, row: str) -> list[str]:
    with_ledger(repo, ledger(row))
    code, out = run(repo, "--today", TODAY)
    assert code == 1, out
    return [ln for ln in out if ln.startswith("malformed: ")]


def test_a_row_with_the_wrong_number_of_cells_is_malformed(repo):
    """REQ-016: answer 1: six cells, in the order of the header."""
    assert malformed(repo, "| tests/test_a.py::t | builder-a1 | 1 | watch |  |") == [
        "malformed: line 5: 5 cells, the header has 6"
    ]


def test_an_empty_test_or_owner_is_malformed(repo):
    """REQ-016: answer 1: every entry names its test and its owner."""
    assert malformed(repo, "|  | builder-a1 | 1 | watch |  |  |") == [
        "malformed: line 5: test is empty"
    ]


def test_an_owner_is_one_role_or_session_id(repo):
    """REQ-016: answer 1: owners are roles or session ids, one word each."""
    assert malformed(repo, "| tests/test_a.py::t | a person | 1 | watch |  |  |") == [
        "malformed: line 5: owner is not one role or session id"
    ]
    assert malformed(repo, "| tests/test_a.py::t |  | 1 | watch |  |  |") == [
        "malformed: line 5: owner is empty"
    ]


def test_an_unknown_status_is_malformed(repo):
    """REQ-016: answer 1: status is watch or quarantined."""
    assert malformed(repo, "| tests/test_a.py::t | builder-a1 | 1 | skipped |  |  |") == [
        "malformed: line 5: status is not watch or quarantined"
    ]


def test_a_quarantine_without_an_expiry_is_malformed(repo):
    """REQ-016: answer 3: a quarantine always names its expiry."""
    assert malformed(repo, "| tests/test_a.py::t | builder-a1 | 1 | quarantined |  | #2 |") == [
        "malformed: line 5: expires is empty for a quarantine"
    ]


def test_an_expiry_that_is_not_a_date_is_malformed(repo):
    """REQ-016: answer 1: expires is YYYY-MM-DD, a real date."""
    assert malformed(
        repo, "| tests/test_a.py::t | builder-a1 | 1 | quarantined | 2031-02-30 | #2 |"
    ) == ["malformed: line 5: expires is not a YYYY-MM-DD date"]
    assert malformed(repo, "| tests/test_a.py::t | builder-a1 | 1 | watch | soon |  |") == [
        "malformed: line 5: expires is not a YYYY-MM-DD date"
    ]


def test_an_issue_is_a_number_or_a_link(repo):
    """REQ-016: answer 1: issue is empty, `#n` or a link."""
    assert malformed(repo, "| tests/test_a.py::t | builder-a1 | 2 | watch |  | later |") == [
        "malformed: line 5: issue is not #n or a link"
    ]
    with_ledger(
        repo,
        ledger("| tests/test_a.py::t | builder-a1 | 2 | watch |  | https://example.invalid/i/9 |"),
    )
    assert run(repo, "--today", TODAY)[0] == 0


def test_a_test_listed_twice_is_malformed(repo):
    """REQ-016: answer 1: one ledger, one row per test; the second row names the first."""
    with_ledger(
        repo,
        ledger(
            "| tests/test_a.py::t | builder-a1 | 1 | watch |  |  |",
            "| tests/test_a.py::t | conductor | 1 | watch |  |  |",
        ),
    )
    code, out = run(repo, "--today", TODAY)
    assert code == 1
    assert out[0] == "malformed: line 6: test is listed already on line 5"


def test_a_file_without_the_ledger_table_is_malformed(repo):
    """REQ-016: answer 1: a file at the ledger path holds the one table; without it, line 1."""
    with_ledger(repo, "# Flakes\n\nnothing here\n")
    code, out = run(repo, "--today", TODAY)
    assert code == 1
    assert out[0] == f"malformed: line 1: no ledger table (header: {HEADER[2:-2]})"


def test_a_header_without_its_separator_line_is_malformed(repo):
    """REQ-016: answer 1: a Markdown table has its separator line under the header."""
    with_ledger(repo, HEADER + "\n| a | b | 1 | watch |  |  |\n")
    code, out = run(repo, "--today", TODAY)
    assert code == 1
    assert out[0] == "malformed: line 2: no separator line under the header"


def test_a_second_ledger_table_is_malformed(repo):
    """REQ-016: answer 1: the file holds one table."""
    text = ledger("| tests/test_a.py::t | builder-a1 | 1 | watch |  |  |") + "\nmore\n\n" + HEAD
    with_ledger(repo, text)
    code, out = run(repo, "--today", TODAY)
    assert code == 1
    assert out[0] == "malformed: line 9: a second ledger table (the ledger holds one)"
    assert len(out) == 2, out  # its separator line is part of it, not a stray row


def test_rows_in_a_fenced_block_are_an_example_and_not_read(repo):
    """REQ-016: answer 1: the template's invented example sits in a fence, outside the ledger."""
    example = "```text\n" + HEAD + "| tests/test_x.py::t | builder-a1 | 5 | watch |  |  |\n```\n\n"
    with_ledger(repo, ledger(before="# Flake ledger\n\n" + example))
    code, out = run(repo, "--today", TODAY)
    assert code == 0, out


def test_the_table_ends_at_the_first_line_that_is_not_a_row(repo):
    """REQ-016: answer 1: prose after the table is not a row."""
    row = "| tests/test_a.py::t | builder-a1 | 1 | watch |  |  |"
    with_ledger(repo, ledger(row) + "\nA note.\n")
    assert run(repo, "--today", TODAY) == (0, [f"flakes: nothing due (1 entry) in {LEDGER}"])


def test_a_row_after_a_break_in_the_table_is_malformed_never_hidden(repo):
    """REQ-016: verdict on 5e4043d, finding 1: a row cut off from the table by a blank line or
    prose is listed as malformed with its line number, so an expired quarantine is never hidden."""
    row = "| tests/test_a.py::t | builder-a1 | 0 | watch |  |  |"
    late = "| tests/test_b.py::u | builder-a1 | 3 | quarantined | 2020-01-01 |  |"
    with_ledger(repo, ledger(row) + "\n" + late + "\n")
    code, out = run(repo, "--today", TODAY)
    assert code == 1, out
    assert out == [
        "malformed: line 7: a row outside the ledger table",
        f"flakes: 1 listed (0 expired, 0 brief due, 1 malformed) in {LEDGER}",
    ]
    with_ledger(repo, ledger(row) + "\nA note.\n" + late + "\n")
    code, out = run(repo, "--today", TODAY)
    assert code == 1 and out[0] == "malformed: line 8: a row outside the ledger table", out


def test_a_row_inside_a_fence_after_the_table_is_still_not_read(repo):
    """REQ-016: verdict on 5e4043d, finding 1: a fenced example below the ledger stays unread."""
    late = "| tests/test_b.py::u | builder-a1 | 3 | quarantined | 2020-01-01 |  |"
    with_ledger(repo, ledger() + "\n```text\n" + late + "\n```\n")
    assert run(repo, "--today", TODAY) == (0, [f"flakes: nothing due (0 entries) in {LEDGER}"])


def test_the_lines_are_in_file_order_and_the_reasons_stack(repo):
    """REQ-016: answer 2: each listed line in the order of the file; exit 1."""
    with_ledger(
        repo,
        ledger(
            "| tests/test_a.py::a | builder-a1 | 2 | watch |  |  |",
            "| tests/test_b.py::b | builder-a1 | x | watch |  |  |",
            "| tests/test_c.py::c | conductor | 0 | quarantined | 2030-12-31 | #1 |",
        ),
    )
    code, out = run(repo, "--today", TODAY)
    assert code == 1
    assert [ln.split(": line ")[1].split(":")[0] for ln in out[:-1]] == ["5", "6", "7"]


# --- the options ----------------------------------------------------------------------------------


def test_json_gives_the_same_lists(repo):
    """REQ-016: answer 2: `--json` gives the three lists and the counts."""
    with_ledger(
        repo,
        ledger(
            "| tests/test_a.py::a | builder-a1 | 2 | watch |  |  |",
            "| tests/test_b.py::b | builder-a1 | x | watch |  |  |",
            "| tests/test_c.py::c | conductor | 0 | quarantined | 2030-12-31 | #1 |",
        ),
    )
    proc = subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, str(SCRIPT), "--today", TODAY, "--json"],
        cwd=repo.root,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 1
    doc = json.loads(proc.stdout)
    assert doc == {
        "ledger": LEDGER,
        "present": True,
        "today": TODAY,
        "entries": 2,
        "expired": [
            {
                "line": 7,
                "test": "tests/test_c.py::c",
                "owner": "conductor",
                "expires": "2030-12-31",
            }
        ],
        "brief_due": [
            {"line": 5, "test": "tests/test_a.py::a", "owner": "builder-a1", "strikes": 2}
        ],
        "malformed": [{"line": 6, "reason": "strikes is not a whole number"}],
    }


def test_json_without_a_file(repo):
    """REQ-016: answer 4: no file is present false and three empty lists; exit 0."""
    repo.commit({"README.md": "x\n"}, "base")
    proc = subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, str(SCRIPT), "--json", "--today", TODAY],
        cwd=repo.root,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0
    doc = json.loads(proc.stdout)
    assert doc["present"] is False and doc["entries"] == 0
    assert doc["expired"] == doc["brief_due"] == doc["malformed"] == []


def test_a_bad_today_is_refused_naming_the_option(repo):
    """REQ-016: answer 2: `--today` is a YYYY-MM-DD date; the refusal names the option only."""
    with_ledger(repo, ledger())
    code, out = run(repo, "--today", "tomorrow")
    assert code == 2
    assert out == ["flakes: --today is not a YYYY-MM-DD date"]


def test_an_unknown_option_prints_the_usage(repo):
    """REQ-016: answer 2: the options are `--today DATE` and `--json`."""
    with_ledger(repo, ledger())
    code, out = run(repo, "--fix")
    assert code == 2
    assert out == ["usage: flakes.py [--today YYYY-MM-DD] [--json]"]


def test_today_defaults_to_the_utc_date(repo, monkeypatch):
    """REQ-016: principle 10: dates come from the UTC clock (`date -u`) when not given."""
    assert (
        flakes.utc_today()
        == subprocess.run(  # nosec B603 B607 - fixed argument list
            ["date", "-u", "+%Y-%m-%d"], capture_output=True, text=True, check=True
        ).stdout.strip()
    )
    with_ledger(
        repo,
        ledger(
            "| tests/test_a.py::old | conductor | 0 | quarantined | 2001-01-01 | #1 |",
            "| tests/test_a.py::new | conductor | 0 | quarantined | 2999-01-01 | #1 |",
        ),
    )
    code, out = run(repo)
    assert code == 1 and len(out) == 2 and "test_a.py::old" in out[0]


def test_the_ledger_is_found_from_a_subfolder(repo):
    """REQ-016: the ledger path is relative to the top of the repository."""
    with_ledger(repo, ledger("| tests/test_b.py::test_y | builder-a1 | 2 | watch |  |  |"))
    (repo.root / "src").mkdir()
    proc = subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, str(SCRIPT), "--today", TODAY],
        cwd=repo.root / "src",
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 1 and proc.stdout.startswith("brief due: line 5: ")


def test_an_unreadable_ledger_is_refused(repo):
    """REQ-016: a ledger that is not UTF-8 text cannot be read; exit 2, naming the path class."""
    repo.root.joinpath("docs/runs").mkdir(parents=True)
    repo.root.joinpath(LEDGER).write_bytes(b"\xff\xfe\x00")
    repo.commit({"README.md": "x\n"}, "base")
    code, out = run(repo, "--today", TODAY)
    assert code == 2
    assert out == [f"flakes: cannot read the ledger ({LEDGER})"]


# --- the template and the install (answer 1) ------------------------------------------------------


def test_the_template_parses_and_lists_nothing(repo):
    """REQ-016: answer 1: the installed ledger is valid and empty; its example row is fenced."""
    text = (ROOT / "kit" / "templates" / "flakes.md").read_text(encoding="utf-8")
    assert "{{" not in text  # no template variable: the file is installed as it is
    with_ledger(repo, text)
    code, out = run(repo, "--today", TODAY)
    assert (code, out) == (0, [f"flakes: nothing due (0 entries) in {LEDGER}"])
    report = flakes.read_ledger(text, TODAY)
    assert report.entries == 0 and not report.malformed
    assert HEAD.splitlines()[0] in text.splitlines()  # the header the brief names, in its order


def test_the_template_is_installed_when_absent_and_never_overwritten():
    """REQ-016: answer 1: a template of init and adopt, created only when absent."""
    manifest = json.loads((ROOT / "kit" / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["templates"][LEDGER] == "kit/templates/flakes.md"
    assert manifest["adopt"]["templates"][LEDGER] == "kit/templates/flakes.md"
    assert "scripts/agk/flakes.py" in manifest["verbatim"]
    import init

    assert LEDGER in init.CREATE_ONLY


def test_the_guide_says_how_to_strike_and_quarantine():
    """REQ-016: answer 3: the testing guide covers a strike, a quarantine and its expiry."""
    text = (ROOT / "docs" / "guides" / "testing.md").read_text(encoding="utf-8")
    section = text.split("## The flake ledger", 1)[1]
    for words in ("add a strike", "quarantine", "expires", "flakes.py", "not a governance step"):
        assert words in section, words
