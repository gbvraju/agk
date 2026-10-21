"""Tests of the verdict forms `metrics.verdicts` reads (SPEC-0007 rules 4 and 5, amendment 31).

`Verdict: cleared <sha>`, and `Verdict: fix list` and `Verdict: rejected` each optionally followed
by one space and a sha of 4 to 40 hex characters, which is recorded. Nothing else is a verdict.
`facts.py` reads the same function, so the sent-back count of the report follows. No network.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
from pathlib import Path

import pytest
from product_report import main as report_main
from test_facts import DROP, ENV_GIT, FACTS, FIXTURES, build_repo, no_gh_path

METRICS_FIXTURES = Path(__file__).parent / "fixtures" / "metrics"


def read(body: str) -> list[tuple[str, str]] | None:
    """`metrics.verdicts` on one comment (imported here, so a failure is the test's)."""
    from metrics import verdicts

    return verdicts([{"body": body, "created_at": "2026-10-06T10:00:00Z"}])


@pytest.mark.parametrize(
    ("first_line", "expected"),
    [
        ("Verdict: cleared 0066000", ("cleared", "0066000")),
        ("Verdict: fix list", ("fix", "")),
        ("Verdict: rejected", ("rejected", "")),
        ("Verdict: fix list c5ec2eb", ("fix", "c5ec2eb")),
        ("Verdict: rejected c5ec2eb", ("rejected", "c5ec2eb")),
        ("Verdict: fix list 4473", ("fix", "4473")),
        ("Verdict: fix list " + "a" * 40, ("fix", "a" * 40)),
        ("  Verdict: fix list c5ec2eb  ", ("fix", "c5ec2eb")),
    ],
)
def test_ac1_the_three_forms_with_and_without_a_sha_are_read_and_the_sha_is_recorded(
    first_line, expected
):
    """REQ-012 AC3: SPEC-0007 rule 4 (an optional sha of 4 to 40 hex characters; recorded)."""
    assert read(first_line + "\n\nnotes that are not read\n") == [expected]


@pytest.mark.parametrize(
    "first_line",
    [
        "Verdict on #92 (head 854eb19): fix list",
        "Verdict: fix list c5ec2eb extra",
        "Verdict: fix list c5e",
        "Verdict: fix list C5EC2EB",
        "Verdict: fix list  c5ec2eb",
        "Verdict: fix list c5ec2ez",
        "Verdict: fix list: c5ec2eb",
        "Verdict: fix list " + "a" * 41,
        "Verdict: rejected c5ec2eb.",
        "Verdict: cleared",
        "Verdict: cleared c5e",
        "Verdict: fix lists",
        "verdict: fix list",
        "Verdict: fix list, one item",
    ],
)
def test_ac1_nothing_else_is_a_verdict(first_line):
    """REQ-012 AC3: SPEC-0007 rule 4 (no `Verdict on #n` form, no trailing text, no other sha)."""
    assert read(first_line) == []


def pull_case(tmp_path: Path, comments: list[str]) -> Path:
    """The metrics fixture `fix-lists-cleared` (pull #102) with the given comments, oldest first."""
    case = tmp_path / "case"
    shutil.copytree(METRICS_FIXTURES / "fix-lists-cleared", case)
    body = [
        {"body": text, "created_at": f"2026-10-06T10:{i:02d}:00Z", "user": {"login": "r"}}
        for i, text in enumerate(comments)
    ]
    (case / "comments-102.json").write_text(json.dumps(body))
    return case


def record(repo, case: Path) -> dict[str, str]:
    from test_metrics import metrics, table

    proc = metrics(repo, case)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    return table(proc.stdout)[102]


def test_ac2_review_rounds_and_cost_class_count_fix_lists_that_carry_a_sha(repo, tmp_path):
    """REQ-012 AC3: SPEC-0007 rules 5 and 9 (two fix lists with a sha: 2 rounds, class M)."""
    case = pull_case(
        tmp_path,
        [
            "Verdict: fix list 0066abc\n\nitems",
            "plain comment",
            "Verdict: fix list 0066def",
            "Verdict: cleared 0066000",
        ],
    )
    row = record(repo, case)
    assert row["review_rounds"] == "2"
    assert row["cost_class"] == "M"
    assert row["merged_head_cleared"] == "yes"


def test_ac2_a_rejected_verdict_with_a_sha_is_counted_as_rejected(repo, tmp_path):
    """REQ-012 AC3: SPEC-0007 rule 4 (`rejected_verdicts` counts `Verdict: rejected <sha>`)."""
    row = record(
        repo, pull_case(tmp_path, ["Verdict: rejected 0066abc", "Verdict: cleared 0066000"])
    )
    assert (row["rejected"], row["rejected_verdicts"]) == ("yes", "1")


def test_ac2_the_other_forms_still_count_nothing(repo, tmp_path):
    """REQ-012 AC3: SPEC-0007 rule 5 (a `Verdict on #n` comment is not a round)."""
    row = record(
        repo,
        pull_case(
            tmp_path, ["Verdict on #102 (head 0066abc): fix list", "Verdict: cleared 0066000"]
        ),
    )
    assert row["review_rounds"] == "0"


def facts_and_report(tmp_path: Path, comments: list[str]) -> tuple[dict, str]:
    """Facts of the `ok` case with pull request #5 given `comments`, and the path of their file."""
    api = tmp_path / "api"
    shutil.copytree(FIXTURES / "ok" / "api", api)
    body = [
        {"id": i + 1, "body": text, "created_at": f"2026-10-06T10:{i:02d}:00Z"}
        for i, text in enumerate(comments)
    ]
    (api / "comments-5.json").write_text(json.dumps(body))
    root = build_repo("ok", tmp_path)
    meta = json.loads((FIXTURES / "ok" / "case.json").read_text())
    env = {k: v for k, v in os.environ.items() if k not in DROP} | ENV_GIT
    env["PATH"] = no_gh_path(tmp_path)
    args = ["--today", meta["today"], "--weeks", str(meta["weeks"]), *meta["args"]]
    proc = subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, str(FACTS), *args, "--api-dir", str(api), str(root)],
        capture_output=True,
        text=True,
        env=env,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    path = tmp_path / "facts.json"
    path.write_text(proc.stdout, encoding="utf-8")
    return json.loads(proc.stdout), str(path)


def test_ac3_the_facts_record_the_sha_of_a_fix_list_and_the_report_counts_it(tmp_path, capsys):
    """REQ-018 AC2: SPEC-0009 rule 14 (the same function), SPEC-0011 rule 10 (sent back 2 times)."""
    doc, path = facts_and_report(
        tmp_path,
        ["Verdict: fix list 05abcde", "Verdict: fix list 05abcdf", "Verdict: cleared 05ccccc"],
    )
    row = next(p for p in doc["pull_requests"] if p["number"] == 5)
    assert [(v["kind"], v["sha"]) for v in row["verdicts"]] == [
        ("fix", "05abcde"),
        ("fix", "05abcdf"),
        ("cleared", "05ccccc"),
    ]
    assert report_main(["--facts", path]) == 0
    out = capsys.readouterr().out
    assert "was sent back 2 times" in out


def test_ac3_a_fix_list_without_a_sha_is_as_before(tmp_path):
    """REQ-018 AC2: SPEC-0009 rule 14 (`sha` is `null` when the line carries none)."""
    doc, _ = facts_and_report(tmp_path, ["Verdict: fix list", "Verdict: cleared 05ccccc"])
    row = next(p for p in doc["pull_requests"] if p["number"] == 5)
    assert [(v["kind"], v["sha"]) for v in row["verdicts"]] == [
        ("fix", None),
        ("cleared", "05ccccc"),
    ]
