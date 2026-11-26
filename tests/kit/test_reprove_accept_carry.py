"""An owner's accept carries over a light merge; the conductor names a missing scanner (#2006).

REQ-057. ADR-0830: `merge_cleared.answered` counts a `Maintainer answer: accept <old>` for the
light re-prove's merge head when the head is the light merge of OLD, the accept follows a
`differs` verdict on OLD, and the verdict on the head carries the same `Differs:` lines; any
other difference, a builder push or a verdict with a numbered item between them needs a new
accept. The conductor's check refuses a `differs` verdict without `Differs:` lines and the lines
beside `agrees`, and its lease take in local mode without gitleaks prints one tools line and
marks the lease. Git repositories in `tmp_path` and recorded responses; invented data only, no
network.
"""

from __future__ import annotations

import os
import shutil
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from test_light_reprove import BOTTOM, TOP, commit, git, update_branch, world
from test_session import REPO, SCRIPTS, Stub, clean_env, comment

sys.path.insert(0, str(SCRIPTS))

import common  # noqa: E402
import conductor  # noqa: E402
import merge_cleared  # noqa: E402
import session_plan  # noqa: E402

OWNER = ["owner"]
DIFF = "Differs: tests/whole/whole (field: name)"
OTHER_DIFF = "Differs: tests/kit/kit (field: argv)"
THIRD = BOTTOM.replace("line 3", "main again")  # main's second change, its own line


def verdict(cid: int, head: str, check: str = "differs", lines: tuple[str, ...] = (DIFF,),
            first: str = "cleared", extra: str = "") -> dict:  # fmt: skip
    body = "\n".join(
        [
            f"Verdict: {first} {head}",
            f"Local evidence: {head[:12]} record",
            extra,
            f"Evidence check: {check}, head {head[:12]}",
            *lines,
        ]  # fmt: skip
    )
    return comment(cid, "boss", body, f"2026-11-26T10:{cid:02d}:00Z")


def accept(cid: int, head: str) -> dict:
    return comment(
        cid, "owner", f"Maintainer answer: accept {head}", f"2026-11-26T10:{cid:02d}:00Z"
    )


def light(root: Path):
    shared = list(session_plan.SHARED_INDEXES)
    return lambda old, new: session_plan.light_merge(root, old, new, "main", shared)


@pytest.fixture
def merged(tmp_path):
    """(the checkout, OLD, its light merge of main)."""
    root, head, main = world(tmp_path, {"agk.toml": TOP}, {"agk.toml": BOTTOM})
    return root, head, update_branch(root, head, main)


def evidence(root, comments, sha) -> str:
    try:
        merge_cleared.local_evidence(comments[-1], comments, sha, OWNER, light(root))
    except merge_cleared.Held as err:
        return str(err)
    return "ok"


def test_an_accept_on_old_carries_to_the_light_merge_with_the_same_lines(merged):
    root, old, new = merged
    comments = [verdict(1, old), accept(2, old), verdict(3, new)]
    assert evidence(root, comments, new) == "ok"


def test_without_the_carry_the_merge_head_is_held_as_before(merged):
    root, old, new = merged
    comments = [verdict(1, old), accept(2, old), verdict(3, new)]
    with pytest.raises(merge_cleared.Held, match=r"evidence differs \(rule 4\)"):
        merge_cleared.local_evidence(comments[-1], comments, new, OWNER)


@pytest.mark.parametrize(
    "lines", [(OTHER_DIFF,), (DIFF, OTHER_DIFF), ()], ids=["another", "more", "none"]
)
def test_another_set_of_lines_or_none_needs_a_new_accept(merged, lines):
    root, old, new = merged
    comments = [verdict(1, old), accept(2, old), verdict(3, new, lines=lines)]
    assert evidence(root, comments, new) == "evidence differs (rule 4)"


def test_a_verdict_on_old_posted_without_the_lines_carries_nothing(merged):
    root, old, new = merged
    comments = [verdict(1, old, lines=()), accept(2, old), verdict(3, new)]
    assert evidence(root, comments, new) == "evidence differs (rule 4)"


def test_an_accept_posted_before_the_verdict_on_old_is_not_counted(merged):
    root, old, new = merged
    comments = [accept(1, old), verdict(2, old), verdict(3, new)]
    assert evidence(root, comments, new) == "evidence differs (rule 4)"


def test_an_accept_by_another_account_is_not_counted(merged):
    root, old, new = merged
    other = comment(2, "someone", f"Maintainer answer: accept {old}", "2026-11-26T10:02:00Z")
    assert evidence(root, [verdict(1, old), other, verdict(3, new)], new) == (
        "evidence differs (rule 4)"
    )


def test_a_verdict_with_a_numbered_item_between_needs_a_new_accept(merged):
    root, old, new = merged
    fix = comment(
        4, "boss", f"Verdict: fix list {new}\n\n1. Record the head again.", "2026-11-26T10:04:00Z"
    )
    comments = [verdict(1, old), accept(2, old), fix, verdict(5, new)]
    assert evidence(root, comments, new) == "evidence differs (rule 4)"


def test_a_builder_push_after_old_carries_nothing(merged):
    root, old, _ = merged
    git(root, "checkout", "-q", old)
    pushed = commit(root, {"docs/feature.md": "the feature, changed\n"}, "push")
    git(root, "checkout", "-q", "main")
    new = update_branch(root, pushed, git(root, "rev-parse", "main"))
    comments = [verdict(1, old), accept(2, old), verdict(3, new)]
    assert evidence(root, comments, new) == "evidence differs (rule 4)"


def test_a_full_re_prove_head_carries_nothing(tmp_path):
    script = "scripts/agk/example.py"
    root, old, main = world(tmp_path, {script: TOP}, {script: BOTTOM})
    new = update_branch(root, old, main)
    comments = [verdict(1, old), accept(2, old), verdict(3, new)]
    assert evidence(root, comments, new) == "evidence differs (rule 4)"


def test_the_accept_carries_along_two_light_merges_with_the_same_lines(merged):
    root, old, first = merged
    second_main = commit(root, {"agk.toml": THIRD}, "main again")
    second = update_branch(root, first, second_main)
    chain = [verdict(1, old), accept(2, old), verdict(3, first), verdict(4, second)]
    assert evidence(root, chain, second) == "ok"
    broken = [verdict(1, old), accept(2, old), verdict(3, first, lines=()), verdict(4, second)]
    assert evidence(root, broken, second) == "evidence differs (rule 4)"


def test_an_agreeing_record_needs_no_accept(merged):
    root, _, new = merged
    assert evidence(root, [verdict(1, new, check="agrees", lines=())], new) == "ok"


def test_light_of_reads_the_fetched_default_branch_and_its_shared_indexes(merged):
    root, old, new = merged
    git(root, "update-ref", "refs/remotes/origin/main", "main")
    carry = merge_cleared.light_of(root)
    assert carry is not None and carry(old, new) and not carry(new, old)
    (root / "agk.toml").write_text('[flow]\nshared_indexes = "agk.toml"\n', encoding="utf-8")
    git(root, "commit", "-q", "-am", "a malformed list")
    git(root, "update-ref", "refs/remotes/origin/main", "main")
    assert merge_cleared.light_of(root) is None


# answer 3: the verdict's `Differs:` lines


def body(check: str, *lines: str) -> str:
    sha = "a" * 40
    return "\n".join(
        [f"Verdict: cleared {sha}", f"Evidence check: {check}, head {sha[:12]}", *lines]
    )


def test_a_differs_verdict_without_its_lines_is_refused_before_a_post():
    problem = conductor.form_problem(body("differs"))
    assert problem == common.DIFFERS_MISSING and "SPEC-0039 rule 4" in problem
    assert conductor.form_problem(body("differs", DIFF, OTHER_DIFF)) is None


def test_differs_lines_beside_an_agreeing_check_are_refused():
    assert conductor.form_problem(body("agrees", DIFF)) == common.DIFFERS_ALONE
    assert conductor.form_problem(body("agrees")) is None


def test_a_malformed_differs_line_is_refused_by_its_shape_never_its_value():
    problem = conductor.form_problem(body("differs", "Differs: something else"))
    assert problem == common.DIFFERS_SHAPE and "something else" not in problem


def test_the_lines_are_read_as_a_set():
    assert common.differs_lines(body("differs", OTHER_DIFF, DIFF)) == frozenset({DIFF, OTHER_DIFF})
    assert common.differs_lines(body("differs")) == frozenset()


# answer 1: the lease take names the missing scanner


TOOLS = conductor.TOOLS_LINE
assert TOOLS == (
    "lease: tools: gitleaks is missing; a light re-prove asks the builder for its record "
    "(tool: gitleaks)"
)
PLAN = f"repos/{REPO}/issues/61/comments"


def lease_world(repo, stub, execution: str) -> None:
    repo.git("remote", "add", "origin", f"https://github.com/{REPO}.git")
    repo.write(
        "config/reviewers.yaml", "version: 1\nverdict_authors: [boss]\nspec_approvers: [owner]\n"
    )
    repo.write("agk.toml", f'execution = "{execution}"\n[flow]\nplan_issue = 61\n')
    repo.git("add", "-A")
    repo.git("commit", "-q", "-m", "base")
    repo.git("update-ref", "refs/remotes/origin/main", "HEAD")
    stub.serve(f"repos/{REPO}/issues", [])


def take(repo, stub, tmp_path, scanner: bool, name: str = "c2"):
    tools = tmp_path / "tools"
    tools.mkdir(exist_ok=True)
    for tool, target in (("git", shutil.which("git")), ("python3", sys.executable)):
        if not (tools / tool).exists():
            (tools / tool).symlink_to(str(target))
    if scanner:
        fake = tools / "gitleaks"
        fake.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        fake.chmod(0o755)
    env = clean_env()
    env.update(PATH=f"{stub.bin}{os.pathsep}{tools}", GH_STUB_DIR=str(stub.dir))
    return subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, str(SCRIPTS / "conductor.py"), "lease", "--take", name],
        cwd=repo.root, capture_output=True, text=True, env=env, timeout=60,
    )  # fmt: skip


def written(stub) -> list[str]:
    calls = [c for c in stub.calls() if c[0] != "GET"]
    return [c[2][c[2].index("-f") + 1] for c in calls]


@pytest.fixture
def stub(tmp_path):
    return Stub(tmp_path)


def test_a_fresh_take_in_local_mode_without_gitleaks_says_so_and_marks_the_lease(
    repo, stub, tmp_path
):
    lease_world(repo, stub, "local")
    stub.serve(PLAN, [])
    out = take(repo, stub, tmp_path, scanner=False)
    assert out.returncode == 0, out.stderr
    lines = out.stdout.strip().splitlines()
    assert lines[0].startswith("lease: taken by c2 until ") and lines[1:] == [TOOLS]
    [text] = [w.splitlines()[0] for w in written(stub)]
    assert text.startswith("body=Conductor: active ") and text.endswith("; tools: gitleaks missing")
    marker = comment(5, "boss", text.removeprefix("body="))
    assert conductor.lease_comment([marker], ["boss"]) is not None


@pytest.mark.parametrize(("execution", "scanner"), [("local", True), ("hosted", False)])
def test_with_gitleaks_or_in_hosted_mode_the_take_is_as_before(
    repo, stub, tmp_path, execution, scanner
):
    lease_world(repo, stub, execution)
    stub.serve(PLAN, [])
    out = take(repo, stub, tmp_path, scanner=scanner)
    assert out.returncode == 0, out.stderr
    assert len(out.stdout.strip().splitlines()) == 1
    assert not written(stub)[0].splitlines()[0].endswith("missing")


def test_a_renew_prints_no_tools_line(repo, stub, tmp_path):
    lease_world(repo, stub, "local")
    stamp = (datetime.now(UTC) - timedelta(minutes=5)).strftime("%Y-%m-%dT%H:%M:%SZ")
    held = comment(
        5, "boss", f"Conductor: active {stamp} c2 since {stamp}; tools: gitleaks missing"
    )
    stub.serve(PLAN, [held])
    stub.serve(f"repos/{REPO}/issues/comments/5", {}, method="PATCH")
    out = take(repo, stub, tmp_path, scanner=False)
    assert out.returncode == 0, out.stderr
    assert TOOLS not in out.stdout
    assert written(stub)[0].splitlines()[0].endswith("; tools: gitleaks missing")  # the mark kept


def test_a_malformed_execution_is_named_and_the_take_still_succeeds(repo, stub, tmp_path):
    lease_world(repo, stub, "elsewhere")
    stub.serve(PLAN, [])
    out = take(repo, stub, tmp_path, scanner=False)
    assert out.returncode == 0, out.stderr
    assert "(setting: execution" in out.stdout and "elsewhere" not in out.stdout
