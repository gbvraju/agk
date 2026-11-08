"""merge_cleared.py build (b): the re-checks, the evidence, the hold list and the pinned merge.

Brief #531, ADR-0265, REQ-046 (SPEC-0039 rules 2, 4, 5, 6 first sentence, 8 and 9). Every test runs
on a git repository in `tmp_path` and a fake `gh` that answers from saved responses and records its
argument lists; the merge call is answered by the fake, never by GitHub. No network; invented
logins, addresses at example.com.
"""

from __future__ import annotations

import json
import os
import socket
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path

import pytest
from test_merge_cleared_verdict import (
    AUTO_ISSUE,
    BUILDER,
    CONDUCTOR,
    GREEN_RUNS,
    HEAD,
    HIDDEN,
    MERGE12,
    OLD,
    ON,
    OWNER,
    REPO,
    SCRIPT,
    SCRIPTS,
    SHA12,
    calls,
    cleared,
    comment,
    evidence,
    fake_gh,
    merge_call,
    merge_cleared_run,
    one_line,
    repo,
    toml,
    world,
)

sys.path.insert(0, str(SCRIPTS))

import lock  # noqa: E402
import merge_cleared  # noqa: E402

PULL = world()["pull"]
APPROVERS = f'version: 1\nspec_approvers: ["@{OWNER}"]\n'
LOCAL = toml(ON, local=True)
MERGED = f"merge-cleared #7 {SHA12}: merged {MERGE12}"


def pull(**fields: object) -> dict:
    return {**PULL, **fields}


def held(proc, reason: str) -> str:
    line = one_line(proc)
    assert line.startswith(f"merge-cleared #7 {SHA12}: held: "), line
    assert reason in line, line
    assert proc.returncode == 3, line
    return line


def no_merge(made: list[list[str]]) -> None:
    assert [c for c in made if "PUT" in c] == [], made


def bare(sha: str = HEAD, at: int = 5) -> dict:
    """A cleared verdict with no evidence lines."""
    return cleared(sha, at=at, extra="")


# --- rule 4: evidence in local mode -------------------------------------------------------------


def test_local_mode_merges_with_evidence_that_agrees_for_the_head(tmp_path):
    """REQ-046 AC3: SPEC-0039 rule 4 (`Local evidence:` and `Evidence check: agrees`)."""
    proc, made = merge_cleared_run(tmp_path, LOCAL, [cleared()])
    assert one_line(proc) == MERGED and proc.returncode == 0
    assert not any("check-runs" in a for c in made for a in c), "local mode reads no CI"


def test_the_open_record_issue_is_local_mode_too(tmp_path):
    """REQ-046 AC3: SPEC-0039 rule 4 (the one open local-mode record issue)."""
    record = {"number": 40, "title": "Local mode since 2026-11-01", "body": "Actions is blocked."}
    proc, made = merge_cleared_run(tmp_path / "a", toml(ON), [cleared()], issues=[record])
    assert one_line(proc) == MERGED
    assert not any("check-runs" in a for c in made for a in c)
    proc, made = merge_cleared_run(tmp_path / "b", toml(ON), [bare()], issues=[record])
    held(proc, "rule 4")
    no_merge(made)


@pytest.mark.parametrize(
    ("name", "extra"),
    [
        ("no evidence at all", ""),
        ("a check for another head", evidence(HEAD).replace(f"head {SHA12}", f"head {OLD[:12]}")),
        ("a line for another head", evidence(OLD).replace(f"head {OLD[:12]}", f"head {SHA12}", 1)),
        ("a check with no line", f"Evidence check: agrees, head {SHA12}\n"),
        ("a line with no check", f"Local evidence: {HEAD} proof ok\n"),
        ("a short line sha", evidence(HEAD).replace(f"evidence: {HEAD}", f"evidence: {HEAD[:7]}")),
    ],
)
def test_local_mode_holds_without_evidence_for_the_head(tmp_path, name, extra):
    """REQ-046 AC3: SPEC-0039 rule 4 (evidence for another head, or none, holds)."""
    proc, made = merge_cleared_run(tmp_path, LOCAL, [cleared(extra=extra)])
    line = held(proc, "rule 4")
    assert HEAD not in line and OLD[:12] not in line, name
    no_merge(made)


def answer(body: str, login: str = OWNER, at: int = 8) -> dict:
    return comment(body, login, at)


ACCEPT = f"Maintainer answer: accept {HEAD}"


@pytest.mark.parametrize(
    ("name", "later", "merges"),
    [
        ("no answer", [], False),
        ("a spec approver accepts for the head", [answer(ACCEPT)], True),
        ("the exact line with more lines below", [answer(f"{ACCEPT}\n\nThe proof is fine.")], True),
        ("the short head", [answer(ACCEPT.replace(HEAD, SHA12))], False),
        ("another account accepts", [answer(ACCEPT, BUILDER)], False),
        ("an answer before the verdict", [answer(ACCEPT, at=2)], False),
        ("an answer for another head", [answer(ACCEPT.replace(HEAD, OLD))], False),
        ("an answer that does not accept", [answer(f"Maintainer answer: no, for {HEAD}")], False),
        (
            "the word on a later line only",
            [answer(f"Maintainer answer: {HEAD}\n\naccepted")],
            False,
        ),
        ("I can't accept", [answer(f"Maintainer answer: I can't accept {HEAD}")], False),
        ("I don't accept", [answer(f"Maintainer answer: I don't accept {HEAD}")], False),
        ("I won't accept", [answer(f"Maintainer answer: I won't accept {HEAD}")], False),
        ("refuse to accept", [answer(f"Maintainer answer: refuse to accept {HEAD}")], False),
        ("accepted, a free sentence", [answer(f"Maintainer answer: accepted for {HEAD}")], False),
        ("text after the sha", [answer(f"{ACCEPT} unless the proof fails")], False),
        ("upper case", [answer(f"Maintainer answer: ACCEPT {HEAD}")], False),
        ("a space before", [answer(f" {ACCEPT}")], False),
        ("an upper-case sha", [answer(ACCEPT.replace(HEAD, HEAD.upper()))], False),
    ],
)
def test_an_evidence_check_that_differs_merges_only_with_a_spec_approvers_answer(
    tmp_path, name, later, merges
):
    """REQ-046 AC3: SPEC-0039 rule 4 (`differs` and the one exact `Maintainer answer: accept
    <head>` first line by a spec approver after the verdict; the fix list on cb0a7ef, item 2)."""
    verdict = cleared(extra=evidence(HEAD, "differs"))
    proc, made = merge_cleared_run(tmp_path, LOCAL, [verdict, *later], reviewers_yaml=APPROVERS)
    if merges:
        assert one_line(proc) == MERGED, name
    else:
        held(proc, "evidence differs")
        no_merge(made)


def test_a_reviewers_file_that_cannot_be_parsed_is_refused_naming_the_setting(tmp_path):
    """REQ-046 AC2: SPEC-0039 rules 2 and 3 (a malformed config/reviewers.yaml never empties
    conductor_accounts; the fix list on cb0a7ef, item 1)."""
    broken = f'version: 1\nconductor_accounts: ["@{CONDUCTOR}"]\n  : {HIDDEN}\n'
    for sub, login in (("a", BUILDER), ("b", CONDUCTOR)):
        proc, made = merge_cleared_run(
            tmp_path / sub, toml(ON), [cleared(login=login)], reviewers_yaml=broken
        )
        line = one_line(proc)
        assert line.startswith(f"merge-cleared #7 {SHA12}: refused: "), line
        assert "config/reviewers.yaml" in line and HIDDEN not in line and login not in line
        assert proc.returncode == 1
        no_merge(made)


# --- rule 4: evidence in CI mode ----------------------------------------------------------------


def run(name: str, conclusion: str | None, status: str = "completed", rid: int = 20) -> dict:
    return {"id": rid, "name": name, "status": status, "conclusion": conclusion}


def test_ci_mode_merges_when_every_required_check_ended_success(tmp_path):
    """REQ-046 AC3: SPEC-0039 rule 4 (CI mode)."""
    proc, made = merge_cleared_run(tmp_path, toml(ON), [bare()])
    assert one_line(proc) == MERGED and proc.returncode == 0
    reads = [c for c in made if any("check-runs" in a for a in c)]
    assert reads == [
        ["api", "--method", "GET", f"repos/{REPO}/commits/{HEAD}/check-runs?per_page=100&page=1"]
    ]


@pytest.mark.parametrize(
    ("name", "runs", "reason"),
    [
        ("one failed", [GREEN_RUNS[0], run("governance", "failure")], "red"),
        ("one cancelled", [GREEN_RUNS[0], run("governance", "cancelled")], "red"),
        ("one neutral", [GREEN_RUNS[0], run("governance", "neutral")], "red"),
        ("one missing", [GREEN_RUNS[0]], "missing"),
        ("none at all", [], "missing"),
        ("one running", [GREEN_RUNS[0], run("governance", None, "in_progress")], "pending"),
        ("one queued", [GREEN_RUNS[0], run("governance", None, "queued")], "pending"),
    ],
)
def test_ci_mode_holds_a_red_missing_or_pending_required_check(tmp_path, name, runs, reason):
    """REQ-046 AC3: SPEC-0039 rule 4 (red or missing holds; pending is `checks pending`)."""
    proc, made = merge_cleared_run(tmp_path, toml(ON), [bare()], runs=runs)
    held(proc, reason)
    no_merge(made)


def test_the_latest_run_of_a_check_decides(tmp_path):
    """REQ-046 AC3: SPEC-0039 rule 4 (a latest run on the head)."""
    rerun = [run("governance", "failure", rid=5), *GREEN_RUNS]
    proc, _ = merge_cleared_run(tmp_path / "a", toml(ON), [bare()], runs=rerun)
    assert one_line(proc) == MERGED
    later_red = [*GREEN_RUNS, run("governance", "failure", rid=30)]
    proc, _ = merge_cleared_run(tmp_path / "b", toml(ON), [bare()], runs=later_red)
    held(proc, "red")


def test_a_check_that_is_not_required_never_decides(tmp_path):
    """REQ-046 AC3: SPEC-0039 rule 4 (only `required_checks`)."""
    runs = [*GREEN_RUNS, run("lint-extra", "failure", rid=40)]
    proc, _ = merge_cleared_run(tmp_path, toml(ON), [bare()], runs=runs)
    assert one_line(proc) == MERGED


def test_required_checks_are_read_from_the_default_branch_and_a_bad_value_is_refused(tmp_path):
    """REQ-046 AC3: SPEC-0039 rule 4 (the setting named, never its value)."""
    only = f'required_checks = ["governance"]\n{toml(ON)}'
    proc, _ = merge_cleared_run(tmp_path / "a", only, [bare()], runs=[GREEN_RUNS[1]])
    assert one_line(proc) == MERGED
    bad = f'required_checks = "{HIDDEN}"\n{toml(ON)}'
    proc, made = merge_cleared_run(tmp_path / "b", bad, [bare()])
    line = one_line(proc)
    assert "refused" in line and "required_checks" in line and HIDDEN not in line
    assert proc.returncode == 1 and made == []


# --- rule 5: the hold list ----------------------------------------------------------------------


def patch(name: str, text: str, previous: str | None = None) -> dict:
    item = {"filename": name, "status": "modified", "patch": text}
    if previous:
        item.update(status="renamed", previous_filename=previous)
    return item


@pytest.mark.parametrize(
    ("name", "files"),
    [
        ("agk.toml version", [patch("agk.toml", '-version = "0.63.0"\n+version = "0.64.0"')]),
        (
            "kit_version",
            [patch("kit/manifest.json", '-  "kit_version": "1",\n+  "kit_version": "2",')],
        ),
        ("agk.toml with no patch", [{"filename": "agk.toml", "status": "modified"}]),
    ],
)
def test_a_release_is_held(tmp_path, name, files):
    """REQ-046 AC4: SPEC-0039 rule 5 (`release`)."""
    proc, made = merge_cleared_run(tmp_path, toml(ON), [bare()], files=files)
    held(proc, "release (rule 5)")
    no_merge(made)


def test_other_changes_to_agk_toml_are_not_a_release(tmp_path):
    """REQ-046 AC4: SPEC-0039 rule 5 (only `version` and `kit_version`)."""
    files = [
        patch("agk.toml", '@@ -9 +9 @@\n-stall_hours = 4\n+stall_hours = 5\n version_note = "x"')
    ]
    proc, _ = merge_cleared_run(tmp_path, toml(ON), [bare()], files=files)
    assert one_line(proc) == MERGED


APPROVAL = pull(body="Brief: #500\nApproval: SPEC-0042 docs/specs/0042-x.md Draft -> Approved\n")


@pytest.mark.parametrize(
    ("name", "extra", "merges"),
    [
        ("no approve line", [], False),
        ("the approver names the head", [comment(f"Approve: {HEAD} SPEC-0042", OWNER, 7)], True),
        ("a short head", [comment(f"Approve: {SHA12} SPEC-0042", OWNER, 7)], True),
        ("another head", [comment(f"Approve: {OLD} SPEC-0042", OWNER, 7)], False),
        ("another spec", [comment(f"Approve: {HEAD} SPEC-0041", OWNER, 7)], False),
        ("another account", [comment(f"Approve: {HEAD} SPEC-0042", BUILDER, 7)], False),
        ("the short form with no sha", [comment("Approve: SPEC-0042", OWNER, 7)], False),
    ],
)  # fmt: skip
def test_an_approval_line_needs_a_spec_approvers_approve_for_the_head(
    tmp_path, name, extra, merges
):
    """REQ-046 AC4: SPEC-0039 rule 5 (`spec approval`)."""
    proc, made = merge_cleared_run(
        tmp_path, toml(ON), [bare(), *extra], pull=APPROVAL, reviewers_yaml=APPROVERS
    )
    if merges:
        assert one_line(proc) == MERGED, name
    else:
        held(proc, "spec approval (rule 5)")
        no_merge(made)


def test_the_approve_label_is_held(tmp_path):
    """REQ-046 AC4: SPEC-0039 rule 5 (`agk:approve`)."""
    labelled = pull(labels=[{"name": "agk:approve"}])
    proc, made = merge_cleared_run(tmp_path, toml(ON), [bare()], pull=labelled)
    held(proc, "spec approval (rule 5)")
    no_merge(made)


@pytest.mark.parametrize(
    ("path", "previous", "klass"),
    [
        ("constitution/principles.md", None, "constitution/"),
        ("config/reviewers.yaml", None, "config/reviewers.yaml"),
        ("kit/templates/ruleset.json", None, "kit/templates/ruleset.json"),
        ("scripts/agk/ruleset.py", None, "scripts/agk/ruleset.py"),
        (".github/workflows/governance.yml", None, ".github/workflows/"),
        ("docs/principles.md", "constitution/principles.md", "constitution/"),
    ],
)
def test_each_protected_class_is_held_by_its_name(tmp_path, path, previous, klass):
    """REQ-046 AC4: SPEC-0039 rule 5 (`protected class <class>`)."""
    files = [patch("scripts/agk/example.py", "+x"), patch(path, "+x", previous)]
    proc, made = merge_cleared_run(tmp_path, toml(ON), [bare()], files=files)
    held(proc, f"protected class {klass} (rule 5)")
    no_merge(made)


def test_other_config_files_are_not_held(tmp_path):
    """REQ-046 AC4: SPEC-0039 rule 5 (only the listed classes)."""
    files = [patch("config/session-rules.md", "+x"), patch(".github/CODEOWNERS", "+x")]
    proc, _ = merge_cleared_run(tmp_path, toml(ON), [bare()], files=files)
    assert one_line(proc) == MERGED


def test_the_files_are_read_page_by_page(tmp_path):
    """REQ-046 AC4: SPEC-0039 rule 5 (a protected file on the second page)."""
    files = [patch(f"docs/x{i}.md", "+x") for i in range(120)]
    files.append(patch("constitution/principles.md", "+x"))
    proc, made = merge_cleared_run(tmp_path, toml(ON), [bare()], files=files)
    held(proc, "protected class constitution/")
    assert len([c for c in made if any("/files" in a for a in c)]) == 2


@pytest.mark.parametrize(
    ("name", "fields", "reason"),
    [
        ("the hold label", {"labels": [{"name": "agk:hold"}]}, "hold label (rule 5)"),
        ("a draft", {"draft": True}, "draft (rule 5)"),
        ("a dirty state", {"mergeable_state": "dirty"}, "conflict (rule 5)"),
        ("an unknown state", {"mergeable_state": "unknown"}, "conflict (rule 5)"),
        ("no state", {"mergeable_state": None}, "conflict (rule 5)"),
    ],
)
def test_a_label_a_draft_or_a_conflict_is_held(tmp_path, name, fields, reason):
    """REQ-046 AC4: SPEC-0039 rule 5 (`hold label`, `draft`, `conflict`)."""
    proc, made = merge_cleared_run(tmp_path, toml(ON), [bare()], pull=pull(**fields))
    held(proc, reason)
    no_merge(made)


DEPENDS = pull(body="Brief: #500\nDepends-on: #12\n")


def a_pull(state: str, merged: str | None) -> dict:
    return {"number": 12, "state": state, "pull_request": {}, "pull": {"merged_at": merged}}


def a_brief(reason: str) -> dict:
    return {"number": 12, "state": "closed", "state_reason": reason}


@pytest.mark.parametrize(
    ("name", "item", "merges"),
    [
        ("an open pull request", a_pull("open", None), False),
        ("a closed, unmerged pull request", a_pull("closed", None), False),
        ("a merged pull request", a_pull("closed", "2026-11-04T09:00:00Z"), True),
        ("an open brief", {"number": 12, "state": "open"}, False),
        ("a brief closed as not planned", a_brief("not_planned"), False),
        ("a brief closed as completed", a_brief("completed"), True),
    ],
)
def test_depends_on_holds_until_merged_or_completed(tmp_path, name, item, merges):
    """REQ-046 AC4: SPEC-0039 rule 5 (`depends-on`, Q-S0039-8)."""
    proc, made = merge_cleared_run(tmp_path, toml(ON), [bare()], pull=DEPENDS, items={"12": item})
    if merges:
        assert one_line(proc) == MERGED, name
    else:
        held(proc, "depends-on (rule 5)")
        no_merge(made)


RED = {"number": 90, "title": "The default branch is red", "body": "Priority: 0\n"}


def test_the_red_branch_issue_holds_everything(tmp_path):
    """REQ-046 AC4: SPEC-0039 rule 5 (the default branch red; exit 3)."""
    proc, made = merge_cleared_run(tmp_path, toml(ON), [bare()], issues=[RED])
    held(proc, "the default branch is red (rule 5)")
    no_merge(made)


def test_an_issue_of_another_title_or_a_pull_request_of_that_title_is_not_red(tmp_path):
    """REQ-046 AC4: SPEC-0039 rule 5 (the one issue of that title)."""
    others = [
        {"number": 91, "title": "The default branch is green"},
        {**RED, "pull_request": {}},
        AUTO_ISSUE,
    ]
    proc, _ = merge_cleared_run(tmp_path, toml(ON), [bare()], issues=others)
    assert one_line(proc) == MERGED


def test_a_paused_kit_holds_everything_and_reads_nothing(tmp_path):
    """REQ-046 AC4: SPEC-0039 rule 5 (`paused = true` on the default branch; exit 3)."""
    proc, made = merge_cleared_run(tmp_path, f"paused = true\n{toml(ON)}", [bare()])
    held(proc, "paused (rule 5")
    assert made == []


def test_a_head_that_pauses_while_the_default_branch_does_not_changes_nothing(tmp_path):
    """REQ-046 AC4: SPEC-0039 rule 5 (paused is read from the default branch)."""
    proc, _ = merge_cleared_run(
        tmp_path, toml(ON), [bare()], head_toml=f"paused = true\n{toml(ON)}"
    )
    assert one_line(proc) == MERGED


@pytest.mark.parametrize(
    ("name", "count", "listed"),
    [
        ("fewer files read than changed", 5, 3),
        ("no count of changed files", None, 1),
        ("a count that is not a number", "1", 1),
        ("more files read than changed", 1, 2),
    ],
)
def test_the_files_read_must_be_every_changed_file(tmp_path, name, count, listed):
    """REQ-046 AC4: SPEC-0039 rules 2 and 5 (a partial file list is never a pass; the fix list on
    cb0a7ef, item 4)."""
    files = [patch(f"docs/x{i}.md", "+x") for i in range(listed)]
    the_pull = pull(changed_files=count) if count is not None else pull()
    proc, made = merge_cleared_run(
        tmp_path, toml(ON), [bare()], pull=the_pull, files=files, changed=False
    )
    held(proc, "files not all read (rule 5)")
    no_merge(made)


def test_a_protected_file_past_the_3000_file_limit_is_held(tmp_path):
    """REQ-046 AC4: SPEC-0039 rule 5 (the list-files endpoint stops at 3,000 files; the fix list on
    cb0a7ef, item 4)."""
    files = [patch(f"docs/x{i}.md", "+x") for i in range(3000)]
    files.append(patch("constitution/principles.md", "+x"))
    proc, made = merge_cleared_run(tmp_path, toml(ON), [bare()], files=files)
    held(proc, "files not all read (rule 5)")
    no_merge(made)
    assert len([c for c in made if any("/files" in a for a in c)]) == 31


def test_an_unreadable_hold_list_read_is_never_a_pass(tmp_path):
    """REQ-046 AC4: SPEC-0039 rule 2 (a failed read is never an empty list)."""
    root = repo(tmp_path, toml(ON))
    bin_dir, log = fake_gh(tmp_path, comments=[bare()], files={"message": "Not Found"})
    proc = run_script(root, bin_dir)
    assert proc.returncode == 4 and "GitHub cannot be read" in one_line(proc)
    no_merge(calls(log))


# --- rules 2, 6 and 9: the pinned merge, one line, the lock -------------------------------------


def run_script(root: Path, bin_dir: Path):
    env = {k: v for k, v in os.environ.items() if k not in ("GITHUB_BASE_REF", "AGK_BASE", "CI")}
    env["PATH"] = f"{bin_dir}{os.pathsep}{env['PATH']}"
    temp = bin_dir.parent / "temp"
    temp.mkdir(exist_ok=True)
    env["TMPDIR"] = env["TEMP"] = env["TMP"] = str(temp)
    return subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, str(SCRIPT), "--pr", "7", "--sha", HEAD],
        cwd=root,
        capture_output=True,
        text=True,
        env=env,
    )


def test_a_merge_is_one_pinned_put_and_one_line(tmp_path):
    """REQ-046 AC5: SPEC-0039 rules 2 and 6 (`sha=` and `merge_method=squash`, one line)."""
    proc, made = merge_cleared_run(tmp_path, toml(ON), [cleared()])
    assert proc.stdout == MERGED + "\n" and proc.returncode == 0
    writes = [c for c in made if c[2] != "GET"]
    record = ["api", "--method", "POST", f"repos/{REPO}/issues/41/comments"]
    assert writes[0] == merge_call() and [c[:4] for c in writes[1:]] == [record]
    assert made[-2:] == writes, "the merge, then the record line of build (c), are the last calls"


def test_every_call_is_a_rest_get_but_the_merge_and_nothing_tags_approves_or_pushes(tmp_path):
    """REQ-046 AC5: SPEC-0039 rule 8 (no tag, approve, edit, push or head command)."""
    proc, made = merge_cleared_run(
        tmp_path, LOCAL, [cleared()], pull=DEPENDS, items={"12": a_brief("completed")}
    )
    assert proc.returncode == 0
    for argv in made:
        assert argv[:2] == ["api", "--method"] and argv[2] in ("GET", "PUT", "POST"), argv
        if argv[2] == "POST":  # build (c): the one record line (SPEC-0039 rule 7)
            assert argv[3] == f"repos/{REPO}/issues/41/comments", argv
        assert argv[3].startswith(f"repos/{REPO}/"), argv
        assert "--jq" not in argv and "graphql" not in " ".join(argv)
        for word in ("/reviews", "/git/refs", "/git/tags", "/releases", "/contents", "/labels"):
            assert word not in argv[3], argv


def test_a_moved_head_at_the_merge_is_refused_with_exit_3(tmp_path):
    """REQ-046 AC5: SPEC-0039 rule 6 (a saved 409: GitHub refuses a head that moved)."""
    root = repo(tmp_path, toml(ON))
    bin_dir, log = fake_gh(tmp_path, comments=[bare()], merge={"http": 409})
    proc = run_script(root, bin_dir)
    line = one_line(proc)
    assert (
        line.startswith(f"merge-cleared #7 {SHA12}: refused: head moved") and proc.returncode == 3
    )
    assert [c for c in calls(log) if "PUT" in c] == [merge_call()], "one merge call, no retry"


def test_a_405_with_the_head_moved_since_reads_head_moved(monkeypatch):
    """REQ-046 AC5: SPEC-0039 rule 6 (a 405 for a moved head)."""
    heads = iter([OLD])
    monkeypatch.setattr(
        merge_cleared, "write_once", lambda argv, env=None: (1, "", "gh: x (HTTP 405)")
    )
    monkeypatch.setattr(merge_cleared, "current_head", lambda repo, number: next(heads))
    with pytest.raises(merge_cleared.Refused) as err:
        merge_cleared.merge_pull(REPO, 7, HEAD)
    assert str(err.value).startswith("head moved") and err.value.code == 3


def test_a_405_with_the_same_head_is_not_mergeable(monkeypatch):
    """REQ-046 AC5: SPEC-0039 rule 6 (a 405 that is not a moved head says so)."""
    monkeypatch.setattr(
        merge_cleared, "write_once", lambda argv, env=None: (1, "", "gh: x (HTTP 405)")
    )
    monkeypatch.setattr(merge_cleared, "current_head", lambda repo, number: HEAD)
    with pytest.raises(merge_cleared.Refused) as err:
        merge_cleared.merge_pull(REPO, 7, HEAD)
    assert "not mergeable" in str(err.value) and "head moved" not in str(err.value)
    assert err.value.code == 3


@pytest.mark.parametrize(
    ("answer", "code", "words"),
    [
        ({"http": 502}, 3, "GitHub cannot be reached"),
        ({"http": 403}, 1, "GitHub refused the merge"),
        ({"http": 422}, 1, "GitHub refused the merge"),
        ({"merged": False, "message": "no"}, 1, "GitHub did not report a merge"),
        ({"sha": "nope", "merged": True}, 1, "GitHub did not report a merge"),
    ],
)
def test_other_merge_answers_are_refusals_and_never_retried(tmp_path, answer, code, words):
    """REQ-046 AC5: SPEC-0039 rule 2 (exit 3 for what a later pass may clear, else 1)."""
    root = repo(tmp_path, toml(ON))
    bin_dir, log = fake_gh(tmp_path, comments=[bare()], merge=answer)
    proc = run_script(root, bin_dir)
    line = one_line(proc)
    assert line.startswith(f"merge-cleared #7 {SHA12}: refused: ") and words in line, line
    assert proc.returncode == code
    assert len([c for c in calls(log) if "PUT" in c]) == 1


def test_a_second_run_waits_on_the_merge_cleared_lock(tmp_path):
    """REQ-046 AC5: SPEC-0039 rule 9 (the named lock `merge-cleared`; Q-S0039-2)."""
    locks = tmp_path / "locks"
    main = f'lock_dir = "{locks.as_posix()}"\n{toml(ON)}'
    root = repo(tmp_path, main)
    bin_dir, log = fake_gh(tmp_path, comments=[bare()])
    held_dir = lock.lock_folder(root, "merge-cleared")
    assert held_dir == locks / "agk-lock-merge-cleared"
    token = uuid.uuid4().hex
    owner = {
        "session": "first-run",
        "pid": os.getpid(),
        "host": socket.gethostname(),
        "started": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "token": token,
    }
    taken = lock.take(held_dir, "merge-cleared", owner, 120, None)
    assert taken is not None
    env = {k: v for k, v in os.environ.items() if k not in ("GITHUB_BASE_REF", "AGK_BASE", "CI")}
    env["PATH"] = f"{bin_dir}{os.pathsep}{env['PATH']}"
    second = subprocess.Popen(  # nosec B603 - fixed argument list, no shell
        [sys.executable, str(SCRIPT), "--pr", "7", "--sha", HEAD],
        cwd=root,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env,
    )
    try:
        time.sleep(2.0)
        assert second.poll() is None, "the second run waits while the lock is held"
        assert [c for c in calls(log) if "PUT" in c] == []
    finally:
        lock.clear_if_same(taken, token)
    out, err = second.communicate(timeout=60)
    assert out == MERGED + "\n", out + err
    assert "lock merge-cleared: waiting" in err, "the wait is said on stderr, not in the one line"
    assert not held_dir.exists(), "the run releases the lock"


def test_the_merge_call_is_the_same_on_a_fake_windows_platform(monkeypatch):
    """REQ-046 AC5: SPEC-0039 rule 2 (the same argument list, no shell, no `--jq`)."""
    seen: list[tuple[list[str], dict]] = []

    def fake_run(argv, **kwargs):
        seen.append((list(argv), kwargs))
        return subprocess.CompletedProcess(argv, 0, json.dumps(world()["merge"]), "")

    monkeypatch.setattr(merge_cleared.subprocess, "run", fake_run)
    for platform in ("linux", "win32"):
        monkeypatch.setattr(sys, "platform", platform)
        assert merge_cleared.merge_pull(REPO, 7, HEAD) == world()["merge"]["sha"]
    assert seen[0][0] == seen[1][0] == ["gh", *merge_call()]
    assert all(not kwargs.get("shell") for _, kwargs in seen)


def test_the_script_runs_once_with_no_timer_and_no_head_command():
    """REQ-046 AC5: SPEC-0039 rules 8 and 9 (no loop on a timer, nothing from a pull request)."""
    text = SCRIPT.read_text(encoding="utf-8")
    for word in (
        "Timer(",
        "sched.",
        "ScheduleWakeup",
        "while True:\n        merge",
        "git push",
    ):
        assert word not in text, word
    # build (c) (brief #551): `make` runs only in the governance run on the merged default branch
    assert text.count('"make"') == 1, "make appears once"
    run_body = text.split("def governance_argv(", 1)[1].split("\ndef ", 1)[0]
    assert '"make"' in run_body, "only the governance run names make"
    assert text.count('--method", "PUT"') <= 1 and '"PUT"' in text


# --- rule 9: review-queue lists `cleared, not merged` -------------------------------------------


REVIEWERS = "version: 1\nverdict_authors: [boss]\n"


def queue_world(tmp_path: Path, flow: str, verdict_line: str) -> list[str]:
    """`session.py review-queue` with one open pull request whose last verdict is VERDICT_LINE."""
    from test_session import STUB  # the stub that test_session_review.py serves from

    root = tmp_path / "q"
    root.mkdir()
    git_env = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.com",
               "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@example.com"}  # fmt: skip

    def git(*args: str) -> None:
        subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
            ["git", *args], cwd=root, check=True, capture_output=True, env=git_env
        )

    git("init", "-q", "-b", "main")
    (root / "agk.toml").write_text(toml(flow), encoding="utf-8")
    (root / "config").mkdir()
    (root / "config" / "reviewers.yaml").write_text(REVIEWERS, encoding="utf-8")
    git("add", "-A")
    git("commit", "-q", "-m", "main")
    git("update-ref", "refs/remotes/origin/main", "HEAD")
    git("remote", "add", "origin", f"https://github.com/{REPO}.git")
    stub = tmp_path / "stub"
    stub.mkdir()
    bin_dir = tmp_path / "qbin"
    bin_dir.mkdir()
    (bin_dir / "gh").write_text(STUB, encoding="utf-8")
    (bin_dir / "gh").chmod(0o755)

    def serve(endpoint: str, data: object) -> None:
        name = endpoint.replace("/", "__") + ".GET"
        (stub / f"{name}.json").write_text(json.dumps(data), encoding="utf-8")

    open_pull = {**PULL, "user": {"login": "builder"}}
    serve(f"repos/{REPO}/pulls", [open_pull])
    serve(f"repos/{REPO}/issues/7/comments", [
        {"id": 3, "user": {"login": "boss"}, "body": verdict_line + "\n\nok",
         "created_at": "2026-11-04T10:00:00Z"}])  # fmt: skip
    serve(f"repos/{REPO}/commits/{HEAD}/check-runs", {"total_count": 2, "check_runs": GREEN_RUNS})
    serve(f"repos/{REPO}/commits/{HEAD}/status", {"state": "success", "statuses": []})
    serve(f"repos/{REPO}/issues", [])
    env = {k: v for k, v in os.environ.items() if k not in ("GITHUB_BASE_REF", "AGK_BASE", "CI")}
    env.update(PATH=f"{bin_dir}{os.pathsep}{env['PATH']}", GH_STUB_DIR=str(stub))
    proc = subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, str(SCRIPTS / "session.py"), "review-queue", "--all"],
        cwd=root, capture_output=True, text=True, env=env, timeout=60,
    )  # fmt: skip
    assert proc.returncode == 0, proc.stdout + proc.stderr
    return proc.stdout.splitlines()


def test_review_queue_lists_a_cleared_unmerged_pull_request_with_auto_merge_on(tmp_path):
    """REQ-046 AC5: SPEC-0039 rule 9 (`cleared, not merged`, retried by the next pass)."""
    lines = queue_world(tmp_path, ON, f"Verdict: cleared {HEAD}")
    assert lines == [f"#7 {HEAD[:7]} cleared, not merged"]


@pytest.mark.parametrize(
    ("flow", "line"),
    [
        ("auto_merge = false\n", f"Verdict: cleared {HEAD}"),
        ("", f"Verdict: cleared {HEAD}"),
        (ON, f"Verdict: cleared {HEAD[:7]}"),
        (ON, f"Verdict: fix list {HEAD}"),
    ],
)
def test_review_queue_is_unchanged_without_the_setting_or_an_exact_cleared_verdict(
    tmp_path, flow, line
):
    """REQ-046 AC5: SPEC-0039 rule 9 (only with `auto_merge = true` and the full head)."""
    lines = queue_world(tmp_path, flow, line)
    assert lines == ["empty", f"#7 {HEAD[:7]} skip: verdict on this head (comment 3)"]


def test_conductor_accounts_do_not_change_what_a_listed_verdict_author_counts_for(tmp_path):
    """REQ-046 AC2: SPEC-0039 rule 3 holds after build (b) (a listed author merges)."""
    yaml = f'version: 1\nspec_approvers: ["@{OWNER}"]\nconductor_accounts: ["@{CONDUCTOR}"]\n'
    proc, _ = merge_cleared_run(tmp_path, toml(ON), [cleared(login=CONDUCTOR)], reviewers_yaml=yaml)
    assert one_line(proc) == MERGED
