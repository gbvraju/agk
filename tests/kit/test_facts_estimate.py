"""Tests of the estimate in the facts (SPEC-0018 rule 5, REQ-025). No network, no model.

The `ok` fixture with its pull requests' bodies and commit dates changed in a temporary copy.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
from pathlib import Path

from test_facts import DROP, ENV_GIT, FACTS, FIXTURES, build_repo, no_gh_path

U = "unknown"


def facts_with(tmp_path: Path, body, authored) -> dict:
    """The facts of the `ok` case with pull request #5 given `body` and commits `authored`."""
    api = tmp_path / "api"
    shutil.copytree(FIXTURES / "ok" / "api", api)
    pulls = json.loads((api / "pulls.json").read_text())
    for pull in pulls:
        if pull["number"] == 5:
            pull["body"] = body
    (api / "pulls.json").write_text(json.dumps(pulls))
    if authored is None:
        (api / "commits-5.json").unlink(missing_ok=True)
    else:
        commits = [
            {"sha": f"{i:040d}", "commit": {"author": {"date": d}}} for i, d in enumerate(authored)
        ]
        (api / "commits-5.json").write_text(json.dumps(commits))
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
    return json.loads(proc.stdout)


def pull(doc: dict, number: int) -> dict:
    return next(p for p in doc["pull_requests"] if p["number"] == number)


def test_ac2_the_pull_request_row_carries_the_estimate_and_the_actual(tmp_path):
    """REQ-025 AC2, AC4: SPEC-0018 rule 5 (the three fields, read from the body and the commits)."""
    dates = ["2026-10-05T20:30:00Z", "2026-10-06T10:00:00Z"]
    doc = facts_with(tmp_path, "Size: M\nExpected: 2-4 hours\n", dates)
    row = pull(doc, 5)
    assert (row["estimated_size"], row["estimated_hours"]) == ("M", "2-4")
    assert row["state"] == "merged" and row["actual_hours"] == "60.5"  # to 2026-10-08T09:00:00Z
    assert doc["schema"] == 1


def test_ac3_a_body_without_the_lines_gives_unknown(tmp_path):
    """REQ-025 AC3: SPEC-0018 rule 5 (unknown, not a guess)."""
    row = pull(facts_with(tmp_path, "Advances: REQ-001\n", ["2026-10-06T10:00:00Z"]), 5)
    assert (row["estimated_size"], row["estimated_hours"]) == (U, U)


def test_ac4_commits_that_cannot_be_read_give_unknown_actual_hours(tmp_path):
    """REQ-025 AC4: SPEC-0018 rule 5 (no commits file in the recorded responses)."""
    row = pull(facts_with(tmp_path, "Size: M\nExpected: 2-4 hours\n", None), 5)
    assert row["actual_hours"] == U


def test_ac4_a_pull_request_that_is_not_merged_has_no_actual_hours(tmp_path):
    """REQ-025 AC4: SPEC-0018 rule 5 (`null`: nothing to measure, not an unknown)."""
    doc = facts_with(tmp_path, "Size: M\nExpected: 2-4 hours\n", ["2026-10-06T10:00:00Z"])
    rows = [p for p in doc["pull_requests"] if p["state"] != "merged"]
    assert rows and all(p["actual_hours"] is None for p in rows)
