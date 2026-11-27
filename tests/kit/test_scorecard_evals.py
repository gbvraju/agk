"""The scorecard's one evals note (SPEC-0077 rule 10; REQ-084 AC7, AC8; brief #2043 build (h),
ADR-0847).

`scorecard.py` prints, after the `acceptance:` note, one `evals:` note with the last accepted eval
record's medians and cost, or `evals: no accepted record`; where the kit-only `eval_record.py` or
`evals/rubric.toml` is absent (a project) the note is absent and the output is today's. A note,
never a metric row. Saved invented trees, no network.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import scorecard

KIT = Path(__file__).resolve().parents[2]
TODAY = "2026-11-07"
NOTE = (
    "evals: 2026-11-20 accepted, medians booking-web problem 5, booking-web code 4;"
    " cost per accepted feature 2.00 usd"
)
RECORD = """# Eval record 2026-11-20

- Status: accepted
- Accepted: the person said "Yes" at 2026-11-20T10:00:00Z
- Kit: 0.66.0 at {sha}
- Rubric: {digest}
- Tolerance: 0
- Cost per accepted feature: 2.00 usd
- Compared with: none (first record)
- Regressions: none

| product | layer | run 1 | run 2 | run 3 | median |
| --- | --- | --- | --- | --- | --- |
| booking-web | problem | 5 | 5 | 5 | 5 |
| booking-web | code | 4 | 4 | 4 | 4 |
| booking-web | objective.tests_passed | 10 | 10 | 10 | 10 |
"""


def kit_tree(repo, accepted: bool) -> None:
    import hashlib

    rubric = (KIT / "evals" / "rubric.toml").read_text("utf-8")
    files = {"agk.toml": 'default_branch = "main"\n', "evals/rubric.toml": rubric}
    if accepted:
        digest = hashlib.sha256(rubric.encode("utf-8")).hexdigest()
        files["docs/runs/evals/2026-11-20.md"] = RECORD.format(sha="a" * 40, digest=digest)
    repo.commit(files)


def output(repo, tmp_path: Path) -> list[str]:
    api = tmp_path / "api"
    api.mkdir()
    (api / "pulls.json").write_text(json.dumps([]), "utf-8")
    proc = repo.run("scorecard.py", "--today", TODAY, "--api-dir", str(api))
    assert proc.returncode == 0, proc.stdout + proc.stderr
    return proc.stdout.splitlines()


def test_ac7_the_note_names_the_last_accepted_records_medians(repo, tmp_path):
    """REQ-084 AC7: SPEC-0077 rule 10 (answer 5: one note after the acceptance line)."""
    kit_tree(repo, accepted=True)
    lines = output(repo, tmp_path)
    assert NOTE in lines
    assert lines.index(NOTE) == next(i for i, x in enumerate(lines) if x.startswith("acceptance:")) + 1
    assert not any(x.startswith("| evals") for x in lines)  # a note, never a metric row


def test_ac7_no_accepted_record_says_so(repo, tmp_path):
    """REQ-084 AC7: SPEC-0077 rule 10 (answer 5: `evals: no accepted record`)."""
    kit_tree(repo, accepted=False)
    assert "evals: no accepted record" in output(repo, tmp_path)


def test_ac8_a_project_has_no_note_and_todays_output(repo, tmp_path, monkeypatch):
    """REQ-084 AC8: SPEC-0077 rule 12 (`Q-PH-7`: no `evals/`, or no `eval_record.py`)."""
    repo.commit({"agk.toml": 'default_branch = "main"\n'})
    assert not any(x.startswith("evals:") for x in output(repo, tmp_path))
    kit_tree(repo, accepted=True)
    monkeypatch.setitem(sys.modules, "eval_record", None)  # the script absent: ImportError
    assert scorecard.evals_note(repo.root) is None
