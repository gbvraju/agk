"""Kit-only tests of the shadow record and its counting script (SPEC-0023 rules 8, 9; REQ-030).

The maintainers paste the person's verdict and the shadow verdict of each pull request into one
record; `shadow_count.py FILE` reads that file only and totals the findings they marked. No network,
no model.
"""

from __future__ import annotations

import ast
import re
import subprocess
import sys

import pytest
from conftest import KIT_ROOT, clean_env

sys.path.insert(0, str(KIT_ROOT / "scripts" / "agk"))
import metrics  # noqa: E402

SCRIPT = KIT_ROOT / "scripts" / "agk" / "shadow_count.py"
TEMPLATE = KIT_ROOT / "kit" / "templates" / "playbook" / "shadow-record.md"
SHAPE = ("Read:", "Rules:", "Not proven:", "Lens:", "Gaps:", "Checklist:")
SHA = "0123456789abcdef0123456789abcdef01234567"


def verdict(first: str, shape=SHAPE) -> str:
    return "```text\n" + first + "\n\n" + "".join(f"{line} x\n" for line in shape) + "```\n"


def pull_request(n: int, findings: list[str], person_shape=SHAPE, shadow_shape=SHAPE) -> str:
    person = verdict(f"Verdict: cleared {SHA}", person_shape)
    shadow = verdict(f"Shadow verdict: cleared {SHA}", shadow_shape)
    return (
        f"## Pull request {n}\n\n### Person's verdict\n\n{person}\n"
        f"### Shadow verdict\n\n{shadow}\n"
        "### Findings\n\n" + "".join(f"{f}\n" for f in findings) + "\n"
    )


def count(tmp_path, body: str, *extra: str):
    record = tmp_path / "record.md"
    record.write_text(body, encoding="utf-8")
    return subprocess.run(
        [sys.executable, str(SCRIPT), str(record), *extra],
        capture_output=True,
        text=True,
        env=clean_env(),
        cwd=tmp_path,
        check=False,
    )


def test_ac7_the_template_has_the_instructions_the_two_verdicts_and_the_findings_shape():
    """REQ-030 AC7: rule 8 (the shape of the record)."""
    body = TEMPLATE.read_text(encoding="utf-8")
    lines = body.splitlines()
    heads = ["## Shadow session instructions", "## Pull request {{n}}"]
    heads += ["### Person's verdict", "### Shadow verdict", "### Findings"]
    positions = [lines.index(h) for h in heads]
    assert positions == sorted(positions)
    assert "- <by> <mark> <where>: <text>" in body
    assert "Shadow verdict: " in body and "catch" in body and "false" in body


def test_ac8_the_instructions_forbid_posting_and_reading_the_comments():
    """REQ-030 AC8: rule 8 (blind both ways) and rule 9 (the claims stay below the rate)."""
    body = " ".join(TEMPLATE.read_text(encoding="utf-8").split())
    for sentence in (
        "Post nothing on the pull request",
        "Do not read the pull request's comments",
        "never `Verdict:`",
        "second reader",
        "nothing more",
    ):
        assert sentence in body, sentence


def test_ac7_a_shadow_verdict_is_never_counted_as_a_verdict():
    """REQ-030 AC7: rule 8 (`metrics.VERDICT` does not match the shadow first line)."""
    for kind in ("cleared", "fix list", "rejected"):
        assert not metrics.VERDICT.fullmatch(f"Shadow verdict: {kind} {SHA}")
    assert metrics.VERDICT.fullmatch(f"Verdict: cleared {SHA}")


def test_ac7_the_counting_script_totals_each_case(tmp_path):
    """REQ-030 AC7: rule 8 (catches by both, person only, shadow only; false by each)."""
    body = (
        "# Shadow record\n\n"
        + pull_request(
            1,
            [
                "- both catch rule 3: the head was not read",
                "- person catch line 12: a stale claim",
                "- person catch rule 5: another",
                "- shadow catch scripts/x.py:40: a missing test",
                "- person false rule 2: wrong",
                "- shadow false rule 7: wrong",
                "- shadow false line 3: wrong again",
                "- both false rule 1: odd",
            ],
        )
        + pull_request(2, ["- both catch rule 1: also read"])
    )
    proc = count(tmp_path, body)
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.splitlines() == [
        "pull requests: 2",
        "catches: both=2 person-only=2 shadow-only=1",
        "false: both=1 person=1 shadow=2",
        "no where (count for nothing): 0",
        "unmarked (count for nothing): 0",
        "verdicts: 4, missing a line of the shape: 0",
    ]


def test_ac7_a_finding_with_no_where_counts_for_nothing(tmp_path):
    """REQ-030 AC7: rule 8 (the number of findings with no `<where>`)."""
    body = pull_request(
        1,
        [
            "- person catch: no rule or line",
            "- shadow false : none either",
            "- both catch rule 4: ok",
        ],
    )
    out = count(tmp_path, body).stdout.splitlines()
    assert out[1] == "catches: both=1 person-only=0 shadow-only=0"
    assert out[2] == "false: both=0 person=0 shadow=0"
    assert out[3] == "no where (count for nothing): 2"


def test_ac7_a_finding_without_a_mark_is_not_a_total(tmp_path):
    """REQ-030 AC7: rule 8 (only the findings the maintainers marked are totalled)."""
    body = pull_request(1, ["- person rule 3: unmarked", "- shadow maybe rule 2: bad mark"])
    out = count(tmp_path, body).stdout.splitlines()
    assert out[1] == "catches: both=0 person-only=0 shadow-only=0"
    assert out[4] == "unmarked (count for nothing): 2"


def test_ac7_other_bullets_and_the_instructions_are_not_findings(tmp_path):
    """REQ-030 AC7: rule 8 (only `- both|person|shadow ...` lines are read)."""
    body = (
        "- a bullet about catch and false\n- persons catch rule 1: not a finding\n"
        + pull_request(1, ["- both catch rule 1: yes"])
    )
    out = count(tmp_path, body).stdout.splitlines()
    assert out[1] == "catches: both=1 person-only=0 shadow-only=0"
    assert out[4] == "unmarked (count for nothing): 0"


def test_ac7_the_report_counts_verdicts_missing_a_line_of_the_shape(tmp_path):
    """REQ-030 AC7: SPEC-0023 rule 4 (the shape is reported here, no check fails)."""
    body = pull_request(1, [], person_shape=SHAPE[:4], shadow_shape=SHAPE[::-1]) + pull_request(
        2, []
    )
    proc = count(tmp_path, body)
    assert proc.returncode == 0
    assert proc.stdout.splitlines()[5] == "verdicts: 4, missing a line of the shape: 2"


def test_ac7_the_script_reads_the_one_file_and_nothing_else(tmp_path):
    """REQ-030 AC7: rule 8 (it reads that file only: a decoy beside it is never read)."""
    decoy = tmp_path / "shadow-review-4.md"
    decoy.write_text("- both catch rule 1: decoy\n", encoding="utf-8")
    proc = count(tmp_path, pull_request(1, ["- person catch rule 2: real"]))
    assert proc.stdout.splitlines()[1] == "catches: both=0 person-only=1 shadow-only=0"
    source = SCRIPT.read_text(encoding="utf-8")
    assert source.count(".read_text(") == 1
    for word in ("glob", "iterdir", "walk", "subprocess", "environ", "getenv"):
        assert word not in source, word


def test_ac7_the_script_imports_no_network_and_no_model():
    """REQ-030 AC7: rule 8 (no network, no model)."""
    tree = ast.parse(SCRIPT.read_text(encoding="utf-8"))
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported |= {a.name.split(".")[0] for a in node.names}
        elif isinstance(node, ast.ImportFrom):
            imported.add((node.module or "").split(".")[0])
    banned = {"socket", "ssl", "urllib", "http", "requests", "anthropic", "openai", "subprocess"}
    assert not imported & banned, imported & banned


@pytest.mark.parametrize("args", [[], ["a", "b"], ["--nope"]])
def test_ac7_usage_errors_exit_2_and_print_the_usage(tmp_path, args):
    """REQ-030 AC7: rule 8 (a bad call fails with the usage line)."""
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True,
        text=True,
        env=clean_env(),
        cwd=tmp_path,
        check=False,
    )
    assert proc.returncode == 2 and "usage: shadow_count.py FILE" in proc.stdout


def test_ac7_an_unreadable_file_exits_2_and_names_the_file_not_its_content(tmp_path):
    """REQ-030 AC7: principle 6 (the message names the path class, never a value)."""
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), str(tmp_path / "missing.md")],
        capture_output=True,
        text=True,
        env=clean_env(),
        cwd=tmp_path,
        check=False,
    )
    assert proc.returncode == 2 and re.search(r"cannot read the record", proc.stdout)
