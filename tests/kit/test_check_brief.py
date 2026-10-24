"""check_brief.py and the shape of a brief (SPEC-0030 rule 4; REQ-037 AC4)."""

from __future__ import annotations

import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts" / "agk"
GOOD = (
    'Sentence: "A team can run a thing."\n'
    "Answers (the maintainers'):\n1. one\n   wrapped\n2. two\n"
    "Depends-on: #3\nDepends-on: #4\nSize: M\n"
)


def check(tmp_path: Path, body: str | None, *extra: str):
    args = [str(tmp_path / "brief.md")] if body is not None else [str(tmp_path / "none.md")]
    if body is not None:
        (tmp_path / "brief.md").write_text(body, encoding="utf-8")
    return subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, str(SCRIPTS / "check_brief.py"), *args, *extra],
        cwd=tmp_path,
        capture_output=True,
        text=True,
    )


def test_ac4_a_good_body_passes(tmp_path):
    """REQ-037 AC4"""
    out = check(tmp_path, GOOD)
    assert out.returncode == 0 and out.stdout.strip() == "ok brief"


def test_ac4_depends_on_lines_are_optional_and_answers_may_be_plain(tmp_path):
    """REQ-037 AC4"""
    body = 'Sentence: "x"\nAnswers:\n1. a\nSize: S\n'
    assert check(tmp_path, body).stdout.strip() == "ok brief"


@pytest.mark.parametrize(
    ("body", "missing"),
    [
        (GOOD.replace('Sentence: "A team can run a thing."\n', ""), "Sentence"),
        (GOOD.replace('"A team can run a thing."', "no quotes"), "Sentence"),
        (GOOD.replace('"A team can run a thing."', '""'), "Sentence"),
        (GOOD.replace('"A team can run a thing."', '"' + "x" * 301 + '"'), "300"),
        (GOOD + 'Sentence: "second"\n', "Sentence"),
        (GOOD.replace("Answers (the maintainers'):\n", ""), "Answers"),
        (GOOD.replace("1. one\n   wrapped\n2. two\n", ""), "numbered"),
        (GOOD.replace("2. two", "3. two"), "numbered"),
        (GOOD.replace("1. one", "2. one"), "numbered"),
        (GOOD.replace("Depends-on: #4", "Depends-on: 4"), "Depends-on"),
        (GOOD.replace("Size: M\n", ""), "Size"),
        (GOOD.replace("Size: M", "Size: XL"), "Size"),
        (GOOD + "Size: S\n", "Size"),
        ("", "Sentence"),
    ],
)
def test_ac4_each_bad_shape_fails_naming_rule_4(tmp_path, body, missing):
    """REQ-037 AC4"""
    out = check(tmp_path, body)
    assert out.returncode == 1
    assert out.stdout.startswith("FAIL brief: rule 4: ") and missing in out.stdout


def test_ac4_a_failure_never_prints_the_sentence(tmp_path):
    """REQ-037 AC4"""
    out = check(tmp_path, GOOD.replace("Size: M\n", "").replace("run a thing", "UNIQUEWORDS"))
    assert out.returncode == 1 and "UNIQUEWORDS" not in out.stdout + out.stderr


def test_ac4_an_unreadable_file_and_a_bad_call_fail(tmp_path):
    """REQ-037 AC4"""
    out = check(tmp_path, None)
    assert out.returncode == 1 and out.stdout.startswith("FAIL brief: ")
    out = check(tmp_path, GOOD, "extra")
    assert out.returncode == 2 and out.stdout.startswith("usage: ")


def test_ac4_check_brief_makes_no_network_call():
    """REQ-037 AC4 and rule 5"""
    text = (SCRIPTS / "check_brief.py").read_text(encoding="utf-8")
    assert "subprocess" not in text and "urllib" not in text and '"gh"' not in text
