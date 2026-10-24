"""Tests of the measured clearance of a covered final commit (SPEC-0021 rule 7; REQ-028).

`merged_head_cleared` and the facts' optional `head_cleared` are `yes` when the merged head is the
covered commit of the latest verdict by a listed author, read from the commit record alone. A
change to `docs/requirements.md` cannot be confirmed from a patch, so it reads `unknown`. The
report's At risk line is not printed for a head that is `yes`. No network, no model.
"""

from __future__ import annotations

import json
import shutil

import pytest
from test_metrics import FIXTURES, rows_of

ADR = "docs/adr/0001-x.md"
REQS = "docs/requirements.md"
REVIEWED = "abc1234"
HEAD = "d" * 40
PATCH = "@@ -3,1 +3,1 @@\n context\n-- Status: Proposed\n+- Status: Accepted\n more"


def fix_list(*finals: str, sha: str = REVIEWED, extra: str = "") -> str:
    return "\n".join([f"Verdict: fix list {sha}", "", "reviewed.", extra, *finals]) + "\n"


FINAL = f"Final: {ADR} Proposed -> Accepted"


def comment(body: str, login: str = "reviewer", at: int = 0) -> dict:
    return {"body": body, "created_at": f"2026-10-06T10:{at:02d}:00Z", "user": {"login": login}}


def commit(parent: str = REVIEWED + "0" * 33, files=None) -> dict:
    files = [{"filename": ADR, "status": "modified", "patch": PATCH}] if files is None else files
    return {"parents": [{"sha": parent}], "files": files}


class Src:
    def __init__(self, record):
        self.record, self.asked = record, []

    def get(self, name, endpoint, until=None):
        self.asked.append(name)
        return self.record if name == f"commit-{HEAD}" else None


def head_cleared(comments, record, authors=("reviewer",)):
    import metrics

    src = Src(record)
    return metrics.merged_head_cleared(src, HEAD, comments, list(authors)), src


def test_ac1_the_covered_commit_is_a_cleared_head_without_a_cleared_verdict():
    """REQ-028 AC1: rule 7 (the head is the one commit after the reviewed sha)."""
    state, _ = head_cleared([comment(fix_list(FINAL))], commit())
    assert state == "yes"


@pytest.mark.parametrize(
    "variant",
    ["two commits", "extra line", "other file", "other value", "added file", "numbered"],
)
def test_ac2_a_head_that_is_not_exactly_the_covered_commit_is_no(variant):
    """REQ-028 AC2: rules 1 to 3 and 7 (each refusal reads `no`)."""
    body, record = fix_list(FINAL), commit()
    if variant == "two commits":
        record = commit(parent="e" * 40)
    elif variant == "extra line":
        record = commit(files=[{"filename": ADR, "status": "modified", "patch": PATCH + "\n+x"}])
    elif variant == "other file":
        both = [{"filename": ADR, "status": "modified", "patch": PATCH}]
        record = commit(files=both + [{"filename": "a.md", "status": "modified", "patch": "+x"}])
    elif variant == "other value":
        patch = PATCH.replace("Accepted", "Superseded")
        record = commit(files=[{"filename": ADR, "status": "modified", "patch": patch}])
    elif variant == "added file":
        record = commit(files=[{"filename": ADR, "status": "added", "patch": PATCH}])
    else:
        body = fix_list(FINAL, extra="1. an item")
    state, _ = head_cleared([comment(body)], record)
    assert state == "no"


def test_ac1_a_blank_context_line_in_the_patch_still_reads_yes():
    """REQ-028 AC1: rule 7 (an empty line is not a changed line: `ln[:1]` of "" is "")."""
    patch = "@@ -3,4 +3,4 @@\n context\n\n-- Status: Proposed\n+- Status: Accepted\n\n more"
    record = commit(files=[{"filename": ADR, "status": "modified", "patch": patch}])
    state, _ = head_cleared([comment(fix_list(FINAL))], record)
    assert state == "yes"


def test_ac4_a_covered_fix_list_by_an_unlisted_author_clears_nothing():
    """REQ-028 AC4: rule 5 (a stranger's `Final:` lines are ignored)."""
    state, src = head_cleared([comment(fix_list(FINAL), login="stranger")], commit())
    assert state == "unknown" and src.asked == []  # no verdict by a listed author at all


def test_ac1_a_cleared_verdict_that_names_the_head_needs_no_commit_record():
    """REQ-028 AC1: rule 7 (as before; the commit record is read only when it is needed)."""
    cleared = comment(f"Verdict: cleared {HEAD}", at=1)
    state, src = head_cleared([comment(fix_list(FINAL)), cleared], commit())
    assert state == "yes" and src.asked == []


def test_ac2_a_later_verdict_replaces_the_covered_fix_list():
    """REQ-028 AC2: rule 3 (the covered fix list must be the latest verdict)."""
    later = comment("Verdict: fix list abc1234\n", at=1)
    state, _ = head_cleared([comment(fix_list(FINAL)), later], commit())
    assert state == "no"


def test_ac7_a_change_to_the_requirements_file_reads_unknown_with_no_extra_read():
    """REQ-028 AC7: rule 7 and the ruling (the section cannot be read from the patch)."""
    final = f"Final: {REQS} REQ-001 planned -> done"
    patch = PATCH.replace("Proposed", "planned").replace("Accepted", "done")
    record = commit(files=[{"filename": REQS, "status": "modified", "patch": patch}])
    state, src = head_cleared([comment(fix_list(final))], record)
    assert state == "unknown" and src.asked == [f"commit-{HEAD}"]


def test_ac7_a_commit_record_that_cannot_be_read_is_unknown():
    """REQ-028 AC7: rule 7 (unknown is not no)."""
    assert head_cleared([comment(fix_list(FINAL))], None)[0] == "unknown"
    assert head_cleared([comment(fix_list(FINAL))], {"parents": []})[0] == "unknown"


def test_ac1_the_metrics_table_reads_the_covered_commit_as_cleared(repo, tmp_path):
    """REQ-028 AC1: rule 7 (the recorded pull request, through the command line)."""
    api = tmp_path / "api"
    shutil.copytree(FIXTURES / "cleared-other-commit", api)
    (api / "comments-103.json").write_text(json.dumps([comment(fix_list(FINAL))]), encoding="utf-8")
    pull = json.loads((api / "pull-103.json").read_text(encoding="utf-8"))
    pull["head"]["sha"] = HEAD
    (api / "pull-103.json").write_text(json.dumps(pull), encoding="utf-8")
    (api / f"commit-{HEAD}.json").write_text(json.dumps(commit()), encoding="utf-8")
    assert rows_of(repo, api)[103]["merged_head_cleared"] == "yes"
    (api / f"commit-{HEAD}.json").unlink()
    assert rows_of(repo, api)[103]["merged_head_cleared"] == "unknown"


def facts_record(comments, record, merged=True):
    import facts

    class Recorded(Src):
        def get(self, name, endpoint, until=None):
            if name == "comments-7":
                return comments
            return [] if name in ("files-7", "commits-7") else super().get(name, endpoint, until)

    item = {"number": 7, "head": {"sha": HEAD}, "created_at": "2026-10-06T09:00:00Z"}
    item |= {"state": "closed" if merged else "open", "title": "t", "body": ""}
    item["merged_at"] = "2026-10-07T09:00:00Z" if merged else None
    return facts.pull_record(Recorded(record), item, ["reviewer"])


def test_ac7_the_facts_carry_head_cleared_for_a_merged_pull_request():
    """REQ-028 AC7: rule 7 (an optional field; the schema number stays 1)."""
    import facts

    done = facts_record([comment(fix_list(FINAL))], commit())
    assert done["head_cleared"] == "yes" and facts.SCHEMA == 1
    assert facts_record([], commit())["head_cleared"] == "unknown"


def entry(head_cleared=None, cleared=False, verdicts=None):
    kinds = [{"kind": "cleared", "sha": HEAD[:7] if cleared else "1234567", "at": None}]
    p = {"verdicts": kinds if verdicts is None else verdicts, "head": HEAD}
    return p | ({} if head_cleared is None else {"head_cleared": head_cleared})


def test_ac7_the_at_risk_line_is_not_printed_for_a_cleared_head_and_is_as_before_otherwise():
    """REQ-028 AC7: rule 7 (`yes` skips the line; `no`, `unknown` and absent read as before)."""
    import product_report as pr

    assert pr.cleared_state(entry("yes")) is None
    for value in ("no", "unknown", None):
        assert pr.cleared_state(entry(value)) == "not-cleared", value
    assert pr.cleared_state(entry("yes", verdicts=[])) is None
    assert pr.cleared_state(entry(None, verdicts=[])) == "no-verdict"
    assert pr.cleared_state(entry(None, cleared=True)) is None


def test_ac7_the_facts_carry_head_cleared_for_an_open_pull_request_too():
    """REQ-037 AC7: rule 8 (an open pull request as a merged one; a closed one carries none)."""
    cleared = comment(f"Verdict: cleared {HEAD[:9]}", at=1)
    assert facts_record([cleared], commit(), merged=False)["head_cleared"] == "yes"
    assert facts_record([comment(fix_list(FINAL))], commit(), merged=False)["head_cleared"] == "yes"
    assert facts_record([], commit(), merged=False)["head_cleared"] == "no"  # no verdict yet
    assert facts_record(None, commit(), merged=False)["head_cleared"] == "unknown"  # unreadable
    other = comment("Verdict: cleared 1234567", at=1)
    assert facts_record([other], commit(), merged=False)["head_cleared"] == "no"
    import facts

    assert facts.SCHEMA == 1
