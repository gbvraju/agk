"""A kit brief names what already exists (brief #2052, ADR-0850; REQ-037).

Answer 1: with `kit/agk-kit.mk` under the root, a brief has one line `Existing:` before its
Answers line, as items naming `<path>:<line>` with `not enough: <text>`, or `Existing: none:` with a
backquoted search command and a match count; each break is a study problem, warned before
`[flow] brief_study_fails_from` and failed from it. Answer 2: `brief_study.code_matches` finds the
scripts, functions and settings the brief names, and the study warns on each one `Existing:` leaves
out. Answer 3: a tree without the marker reads no line and searches no code. Each case is a stub
root in `tmp_path`, the day fixed by the test. Invented data only (example.com); no network.
"""

from __future__ import annotations

import socket
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts" / "agk"
sys.path.insert(0, str(SCRIPTS))

import brief_study  # noqa: E402
import check_brief  # noqa: E402
import steward_owner  # noqa: E402
from test_check_brief_study import STUDIED, tree  # noqa: E402

DAY = "2026-12-14"
BEFORE, AFTER = "2026-12-13", "2026-12-15"
ITEM = "- `scripts/agk/tool.py:1` (`main`): the tool; not enough: partial, it reads no line.\n"
EXISTING = "Existing:\n" + ITEM + "\n"
NONE = "Existing: none: `grep -rn probe scripts/` gives 0 matches\n"
PLACEHOLDER = "Existing: none: (verify) for the person to state\n"


def with_line(line: str, body: str = STUDIED) -> str:
    return body.replace("Answers:\n", line + "Answers:\n", 1)


def kit(tmp_path: Path, marker: bool = True) -> Path:
    root = tree(tmp_path)
    (root / "agk.toml").write_text(
        f'[flow]\nbrief_study_fails_from = "{DAY}"\nassign = "next"\n', "utf-8"
    )
    (root / "scripts" / "agk" / "config.py").write_text('KEYS = ("max_builders",)\n', "utf-8")
    (root / "scripts" / "agk" / "probe.py").write_text(
        "import os\n\n\ndef probe_line():\n    return 1\n", "utf-8"
    )
    if marker:
        (root / "kit").mkdir()
        (root / "kit" / "agk-kit.mk").write_text("# the kit\n", encoding="utf-8")
    return root


def result(root: Path, body: str, today: str):
    return brief_study.study_result(body, root, today=today, briefs=[])


def existing(lines: list[str]) -> list[str]:
    return [x for x in lines if "Existing" in x]


@pytest.mark.parametrize("line", [EXISTING, NONE, "Existing: none: `rg -n x` 1 match\n"])
def test_req037_each_form_of_the_line_passes_before_and_after_the_day(tmp_path, line):
    """REQ-037: answer 1, both forms."""
    root = kit(tmp_path)
    for today in (BEFORE, AFTER):
        failures, warnings = result(root, with_line(line), today)
        assert failures == []
        assert [w for w in existing(warnings) if "leaves out" not in w] == []


BREAKS = {
    "missing": STUDIED,
    "twice": with_line(EXISTING + NONE),
    "after answers": STUDIED.replace("Size: M\n", "Size: M\n" + NONE),
    "no reference": with_line("Existing:\n- the tool; not enough: partial\n\n"),
    "no reason": with_line("Existing:\n- `scripts/agk/tool.py:1` the tool\n\n"),
    "no file": with_line("Existing:\n- `scripts/agk/gone.py:1`; not enough: gone\n\n"),
    "a folder": with_line("Existing:\n- `scripts/agk/:1`; not enough: a folder\n\n"),
    "a glob": with_line("Existing:\n- `scripts/agk/*.py:1`; not enough: a glob\n\n"),
    "past the end": with_line("Existing:\n- `scripts/agk/tool.py:99`; not enough: x\n\n"),
    "no items": with_line("Existing:\n\n"),
    "none without command": with_line("Existing: none: searched, 0 matches\n"),
    "none without count": with_line("Existing: none: `grep -rn probe scripts/`\n"),
}


@pytest.mark.parametrize("name", sorted(BREAKS))
def test_req037_each_break_is_one_problem_warned_before_and_failed_from_the_day(tmp_path, name):
    """REQ-037: answers 1 and 5."""
    root = kit(tmp_path)
    failures, warnings = result(root, BREAKS[name], BEFORE)
    assert failures == []
    found = [w for w in existing(warnings) if "leaves out" not in w and "more code" not in w]
    assert len(found) == 1 and found[0].startswith("study: ")
    failures, _ = result(root, BREAKS[name], AFTER)
    assert existing(failures) == found


def test_req037_a_problem_names_the_path_class_never_the_path(tmp_path):
    """REQ-037: answer 1 (the refusal names the class, never the brief's text)."""
    failures, _ = result(kit(tmp_path), BREAKS["no file"], AFTER)
    assert any("scripts/agk/" in f and "gone.py" not in f for f in existing(failures))


def test_req037_a_brief_filed_before_the_day_is_never_failed(tmp_path):
    """REQ-037: answer 5 (judged by created_at)."""
    root = kit(tmp_path)
    failures, warnings = brief_study.study_result(
        STUDIED, root, today=AFTER, briefs=[], filed=f"{BEFORE}T08:00:00Z"
    )
    assert failures == [] and existing(warnings)


def test_req037_the_placeholder_warns_on_any_day_and_never_fails(tmp_path):
    """REQ-037: answer 1 (the render's placeholder)."""
    root = kit(tmp_path)
    for today in (BEFORE, AFTER):
        failures, warnings = result(root, with_line(PLACEHOLDER), today)
        assert failures == []
        assert "study: the Existing line is the render's placeholder" in warnings


def test_req037_a_priority_0_brief_is_not_held_to_the_line(tmp_path):
    """REQ-037: answer 1 (`held`)."""
    body = STUDIED.replace("Priority: 1\n", "Priority: 0\n")
    failures, warnings = result(kit(tmp_path), body, AFTER)
    assert failures == [] and [w for w in existing(warnings) if "leaves out" not in w] == []


@pytest.mark.parametrize("body", [STUDIED, *BREAKS.values(), with_line(PLACEHOLDER)])
def test_req037_a_project_tree_reads_no_line_and_searches_no_code(tmp_path, body):
    """REQ-037: answer 3 (no kit marker: no Existing line at all)."""
    root = kit(tmp_path, marker=False)
    for today in (BEFORE, AFTER):
        failures, warnings = result(root, body, today)
        assert existing(failures + warnings) == []
    assert brief_study.code_matches(body, root) == []


SEARCHED = (
    'Sentence: "A team can run `probe.py`, `probe.probe_line` and `[flow] assign`."\n'
    "Answers:\n1. Uses `probe_line()`, `flow.max_builders`, `nowhere.missing` and `none`.\n"
)


def test_req037_code_matches_finds_a_script_a_def_and_a_setting(tmp_path):
    """REQ-037: answer 2 (the three term classes; a name no file defines is left out)."""
    root = kit(tmp_path)
    body = STUDIED.replace(STUDIED.split("Size:")[0], SEARCHED)
    found = brief_study.code_matches(body, root)
    assert ("scripts/agk/probe.py", 1, "probe.py") in found
    assert ("scripts/agk/probe.py", 4, "probe.probe_line") in found
    assert ("scripts/agk/probe.py", 4, "probe_line()") in found
    assert ("agk.toml", 3, "[flow] assign") in found
    assert ("scripts/agk/config.py", 1, "flow.max_builders") in found
    assert not any("nowhere" in term or term == "none" for _, _, term in found)


def test_req037_a_named_path_silences_its_warning(tmp_path):
    """REQ-037: answer 2 (named by its path or its file name)."""
    root = kit(tmp_path)
    body = STUDIED.replace(STUDIED.split("Size:")[0], SEARCHED)
    _, warnings = result(root, with_line(EXISTING, body), BEFORE)
    left = [w for w in warnings if "leaves out" in w]
    assert (
        "study: Existing leaves out scripts/agk/probe.py:4, which defines probe.probe_line" in left
    )
    assert not any("tool.py" in w for w in left)
    named = EXISTING.replace(
        "\n\n",
        "\n- `scripts/agk/probe.py:1`, `agk.toml:3`, `scripts/agk/config.py:1`; not enough: x\n\n",
    )
    _, warnings = result(root, with_line(named, body), BEFORE)
    assert [w for w in warnings if "leaves out" in w] == []


def test_req037_under_none_every_match_is_left_out(tmp_path):
    """REQ-037: answer 2 (`none:` names nothing)."""
    body = with_line("Existing: none: `grep -rn tool.py scripts/` gives 0 matches\n")
    _, warnings = result(kit(tmp_path), body, BEFORE)
    assert (
        "study: Existing leaves out scripts/agk/tool.py:1, which defines scripts/agk/tool.py"
        in warnings
    )


def test_req037_eleven_matches_give_ten_warnings_and_one_count_line(tmp_path):
    """REQ-037: answer 2 (`CODE_WARNINGS`)."""
    root = kit(tmp_path)
    names = [f"stub_{n}" for n in range(11)]
    (root / "scripts" / "agk" / "stubs.py").write_text(
        "".join(f"def {n}():\n    return 0\n" for n in names), "utf-8"
    )
    body = with_line(NONE).replace(
        "1. one\n", "1. " + " ".join(f"`stubs.{n}`" for n in names) + "\n"
    )
    _, warnings = result(root, body, BEFORE)
    left = [w for w in warnings if "leaves out" in w]
    assert len(left) == brief_study.CODE_WARNINGS == 10
    assert any("more code matches not warned" in w for w in warnings)


def test_req037_the_cli_prints_each_code_match(tmp_path):
    """REQ-037: answer 2 (`brief_study.py FILE --root DIR`)."""
    root = kit(tmp_path)
    (tmp_path / "brief.md").write_text(with_line(EXISTING), encoding="utf-8")
    run = subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, str(SCRIPTS / "brief_study.py"), str(tmp_path / "brief.md"), "--root",
         str(root)],
        capture_output=True, text=True, check=False,
    )  # fmt: skip
    assert run.returncode == 0, run.stderr
    assert "code scripts/agk/tool.py:1: scripts/agk/tool.py" in run.stdout


def test_req037_the_search_makes_no_network_call(tmp_path, monkeypatch):
    """REQ-037: answer 6 (file-only)."""

    def refuse(*_args, **_kwargs):
        raise AssertionError("no network")

    monkeypatch.setattr(socket, "socket", refuse)
    monkeypatch.setattr(socket, "create_connection", refuse)
    body = STUDIED.replace(STUDIED.split("Size:")[0], SEARCHED)
    assert brief_study.code_matches(body, kit(tmp_path))
    assert result(kit(tmp_path / "again"), body, AFTER)[0]


def test_req037_every_writer_reports_the_same_existing_problem(tmp_path, monkeypatch):
    """REQ-037: answer 7 (the check, the steward's refusal and the plan's shape agree)."""
    root = kit(tmp_path)
    (root / "config").mkdir()
    (root / "config" / "neutrality.txt").write_text("", "utf-8")
    body = BREAKS["no file"]
    problem = existing(brief_study.study_failures(body, root, None, AFTER))
    assert len(problem) == 1
    failures, _ = check_brief.brief_result(body, root, today=AFTER)
    assert existing(failures) == problem
    monkeypatch.setattr(check_brief, "utc_day", lambda: AFTER)  # the steward's day, fixed
    refused = steward_owner.brief_refusal(root, body, None) or ""
    assert problem[0] in refused
    assert check_brief.KIT_MAKE == brief_study.KIT_MAKE
