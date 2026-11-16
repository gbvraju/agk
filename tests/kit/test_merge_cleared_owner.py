"""A pull request reaches the default branch only tested as merged (brief #1358, ADR-0570; REQ-050).

The guarded merge holds a protected pull request for the owner (SPEC-0039 rule 5), and the owner
merged three of them with the GitHub button on 2026-11-15, each turning the default branch red. Now
a pull request held only for a protected class or a release still gets governance on its would-be
merge, and the line says `would-be merge: pass|fail`; `merge_cleared.py --pr <n> --owner` merges it
with the signed-in account of `spec_approvers` only when that run passes. Every test runs on a
checkout in `tmp_path` whose origin is a local bare repository, a fake `gh` answering from saved
responses and a fake `make`; no network, invented logins, addresses at example.com.
"""

from __future__ import annotations

import json
import os
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
from pathlib import Path

import pytest
from test_merge_cleared_after import makes, verdict, writes
from test_merge_cleared_verdict import (
    AUTO_ISSUE,
    BASE,
    GIT_ENV,
    HEAD,
    MERGE,
    MERGE12,
    ON,
    OWNER,
    REPO,
    SCRIPTS,
    SHA12,
    calls,
    cleared,
    fake_gh,
    git,
    merge_call,
    one_line,
    repo,
    run,
    toml,
    world,
)

sys.path.insert(0, str(SCRIPTS))

import conductor  # noqa: E402
import doctor as doctor_module  # noqa: E402
import merge_cleared  # noqa: E402

APPROVERS = f'version: 1\nspec_approvers: ["@{OWNER}"]\n'
PROTECTED = [{"filename": "scripts/agk/ruleset.py", "status": "modified", "patch": "+x"}]
RELEASE = [{"filename": "agk.toml", "status": "modified", "patch": '+version = "9.9.9"'}]
HELD = f"merge-cleared #7 {SHA12}: held: "
PASS = f"{HELD}protected class scripts/agk/ruleset.py (rule 5); would-be merge: pass"
FAIL = f"{HELD}protected class scripts/agk/ruleset.py (rule 5); would-be merge: fail"
MERGED = f"merge-cleared #7 {SHA12}: merged {MERGE12}"
PRE = f"AGK_BASE={MERGE}"  # the run before the merge: the fetched default branch is its base

OWNER_GH = """
import json, os, sys
args = sys.argv[1:]
if 'user' in args:  # the signed-in account (`gh api user`)
    with open(LOG, 'a', encoding='utf-8') as fh:
        fh.write(json.dumps(args) + '\\n')
    print(json.dumps({'login': LOGIN}))
    sys.exit(0)
os.execv(sys.executable, [sys.executable, REAL, *args])
"""


def checkout(tmp_path: Path, files=None, login: str = OWNER, **saved):
    """A protected pull request (FILES) cleared for HEAD in CI mode; (checkout, bin, gh log)."""
    root = repo(tmp_path, toml(ON), reviewers_yaml=APPROVERS)
    found = {"issues": [AUTO_ISSUE], "files": PROTECTED if files is None else files, **saved}
    bin_dir, log = fake_gh(tmp_path, comments=[verdict()], **found)
    real = bin_dir / "gh-saved"
    (bin_dir / "gh").rename(real)
    wrapper = bin_dir / "gh"
    wrapper.write_text(
        f"#!{sys.executable}\nLOG, LOGIN, REAL = {str(log)!r}, {login!r}, {str(real)!r}\n"
        + OWNER_GH,
        encoding="utf-8",
    )
    wrapper.chmod(0o755)
    return root, bin_dir, log


def pre_runs(tmp_path: Path) -> list[dict]:
    return [r for r in makes(tmp_path) if r["args"][-1] == PRE]


def merges(made: list[list[str]]) -> list[list[str]]:
    return [c for c in made if "PUT" in c]


def again(root: Path) -> None:
    """The next run reads the settings of the default branch as committed (the fetch of the run
    before moved `origin/main` to the remote's commit, which holds no agk.toml)."""
    git(root, "update-ref", "refs/remotes/origin/main", "main")


# --- answer 1: the check before a hand merge ------------------------------------------------------


def test_a_protected_pull_request_gets_the_would_be_merge_and_is_held(tmp_path):
    """REQ-050: brief #1358 answer 1 (pass: still held, nothing merged or posted)."""
    root, bin_dir, log = checkout(tmp_path)
    proc = run(root, bin_dir, "--pr", "7", "--sha", HEAD)
    assert one_line(proc) == PASS and proc.returncode == 3
    assert len(pre_runs(tmp_path)) == 1
    assert writes(calls(log)) == [], "nothing merged, recorded or posted"


def test_a_release_gets_the_would_be_merge_too(tmp_path):
    """REQ-050: brief #1358 answer 1 (a release is an owner-only hold)."""
    root, bin_dir, _ = checkout(tmp_path, files=RELEASE)
    proc = run(root, bin_dir, "--pr", "7", "--sha", HEAD)
    assert one_line(proc) == f"{HELD}release (rule 5); would-be merge: pass"


def test_a_failing_would_be_merge_is_reported_fail(tmp_path):
    """REQ-050: brief #1358 answers 1 and 4 (the merged result fails: `fail`, never merged)."""
    root, bin_dir, log = checkout(tmp_path, premerge_exit=2)
    proc = run(root, bin_dir, "--pr", "7", "--sha", HEAD)
    assert one_line(proc) == FAIL and proc.returncode == 3
    assert writes(calls(log)) == []


def test_another_hold_beside_the_owner_hold_is_reported_as_today(tmp_path):
    """REQ-050: brief #1358 answers 1 and 4 (not held only for the owner: no run, the old line)."""
    labelled = {**world()["pull"], "labels": [{"name": "agk:hold"}]}
    root, bin_dir, _ = checkout(tmp_path, pull=labelled)
    proc = run(root, bin_dir, "--pr", "7", "--sha", HEAD)
    assert one_line(proc) == f"{HELD}protected class scripts/agk/ruleset.py (rule 5)"
    assert pre_runs(tmp_path) == []


def test_a_conflict_holds_as_before(tmp_path):
    """REQ-050: brief #1358 answer 4 (a conflict holds as before, with or without --owner)."""
    dirty = {**world()["pull"], "mergeable_state": "dirty"}
    root, bin_dir, log = checkout(tmp_path, pull=dirty)
    proc = run(root, bin_dir, "--pr", "7", "--sha", HEAD)
    assert one_line(proc) == f"{HELD}protected class scripts/agk/ruleset.py (rule 5)"
    proc = run(root, bin_dir, "--pr", "7", "--owner")
    assert one_line(proc) == f"{HELD}conflict (rule 5)" and proc.returncode == 3
    assert merges(calls(log)) == [] and pre_runs(tmp_path) == []


def test_an_unprotected_pull_request_is_unchanged(tmp_path):
    """REQ-050: brief #1358 answer 4 (no owner hold: merged as before)."""
    files = [{"filename": "docs/example.md", "status": "modified", "patch": "+x"}]
    root, bin_dir, log = checkout(tmp_path, files=files)
    proc = run(root, bin_dir, "--pr", "7", "--sha", HEAD)
    assert one_line(proc) == MERGED
    assert merges(calls(log)) == [merge_call()]


# --- answer 2: the owner merges through the kit ----------------------------------------------------


def test_owner_merges_a_passing_protected_pull_request_with_the_signed_in_login(tmp_path):
    """REQ-050: brief #1358 answer 2 (the owner-only hold lifted for this one call)."""
    root, bin_dir, log = checkout(tmp_path)
    proc = run(root, bin_dir, "--pr", "7", "--owner")
    assert one_line(proc) == MERGED and proc.returncode == 0
    assert merges(calls(log)) == [merge_call()], "pinned to the head read from GitHub"
    tokens = (tmp_path / "gh-calls.jsonl.token").read_text(encoding="utf-8").splitlines()
    put = [json.loads(t) for t in tokens if json.loads(t)[0] == "PUT"]
    assert put == [["PUT", f"repos/{REPO}/pulls/7/merge", os.environ.get("GH_TOKEN")]]


def test_owner_never_merges_a_failing_would_be_merge(tmp_path):
    """REQ-050: brief #1358 answers 2 and 4 (refused with the hold's line)."""
    root, bin_dir, log = checkout(tmp_path, premerge_exit=2)
    proc = run(root, bin_dir, "--pr", "7", "--owner")
    line = one_line(proc)
    assert line == f"{HELD}the merge with the default branch fails governance (make governance)"
    assert proc.returncode == 3 and merges(calls(log)) == []


def test_owner_is_refused_for_a_login_outside_spec_approvers(tmp_path):
    """REQ-050: brief #1358 answers 2 and 4 (names the setting, never the login)."""
    root, bin_dir, log = checkout(tmp_path, login="builder-one")
    proc = run(root, bin_dir, "--pr", "7", "--owner")
    line = one_line(proc)
    assert line.startswith(f"merge-cleared #7 {SHA12}: refused: ") and proc.returncode == 1
    assert "spec_approvers" in line and "builder-one" not in line
    assert merges(calls(log)) == [] and pre_runs(tmp_path) == []


def test_owner_still_needs_the_clearing_verdict(tmp_path):
    """REQ-050: brief #1358 answer 2 (the same checks: no verdict for the head, no merge)."""
    root, bin_dir, log = checkout(tmp_path)
    saved = json.loads((tmp_path / "saved.json").read_text(encoding="utf-8"))
    saved["comments"] = []
    (tmp_path / "saved.json").write_text(json.dumps(saved), encoding="utf-8")
    proc = run(root, bin_dir, "--pr", "7", "--owner")
    assert one_line(proc).startswith(HELD) and merges(calls(log)) == []


@pytest.mark.parametrize("argv", [["--pr", "7", "--owner", "x"], ["--owner", "--pr", "7"]])
def test_owner_takes_exactly_its_one_form(argv):
    """REQ-050: brief #1358 answer 2 (`--pr <n> --owner`, nothing else)."""
    assert merge_cleared.owner_args(argv) is None
    assert merge_cleared.owner_args(["--pr", "7", "--owner"]) == 7


# --- answer 4: once per head ----------------------------------------------------------------------


def test_the_would_be_merge_runs_once_per_head_while_the_default_branch_stands(tmp_path):
    """REQ-050: brief #1358 answer 4 (the result is reused; a moved default branch runs again)."""
    root, bin_dir, _ = checkout(tmp_path)
    assert one_line(run(root, bin_dir, "--pr", "7", "--sha", HEAD)) == PASS
    again(root)
    assert one_line(run(root, bin_dir, "--pr", "7", "--sha", HEAD)) == PASS
    assert len(makes(tmp_path)) == 1, "the second pass reused the result"
    again(root)
    assert one_line(run(root, bin_dir, "--pr", "7", "--owner")) == MERGED
    ran = [r["args"][-1] for r in makes(tmp_path)]
    assert ran == [PRE, f"AGK_BASE={BASE}"], "reused before the merge; the run after it is new"
    bare = tmp_path / "remote" / "github.com" / f"{REPO}.git"
    git(bare, "update-ref", "refs/heads/main", BASE)  # the default branch moved
    again(root)
    run(root, bin_dir, "--pr", "7", "--sha", HEAD)
    assert len(makes(tmp_path)) == 3, "a moved default branch runs it again"


def test_a_failed_result_is_reused_and_never_merged(tmp_path):
    """REQ-050: brief #1358 answer 4 (a cached `fail` refuses --owner without a second run)."""
    root, bin_dir, log = checkout(tmp_path, premerge_exit=2)
    assert one_line(run(root, bin_dir, "--pr", "7", "--sha", HEAD)) == FAIL
    again(root)
    proc = run(root, bin_dir, "--pr", "7", "--owner")
    assert "fails governance" in one_line(proc) and merges(calls(log)) == []
    assert len(pre_runs(tmp_path)) == 1


# --- answer 5: a new script breaks a scan-all test on the merged result only ----------------------

SCAN_MAKE = """
import json, os, sys
args = sys.argv[1:]
tree = args[args.index('-C') + 1]
with open(LOG, 'a', encoding='utf-8') as fh:
    fh.write(json.dumps({'args': args}) + '\\n')
scan = os.path.join(tree, 'tests', 'scan_all.txt')  # the test that reads every script
scripts = os.path.join(tree, 'scripts')
bad = [n for n in sorted(os.listdir(scripts)) if os.path.isfile(scan) and
       '# scanned' not in open(os.path.join(scripts, n), encoding='utf-8').read()]
sys.exit(2 if bad else 0)
"""


def commit_files(bare: Path, parent: str | None, files: dict[str, str], message: str) -> str:
    """One commit in BARE whose tree holds FILES (path -> text), made with plumbing only."""
    env = {**os.environ, **GIT_ENV, "GIT_INDEX_FILE": str(bare / f"index-{message}")}

    def plumb(*args: str, data: str | None = None) -> str:
        return subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
            ["git", *args], cwd=bare, input=data, capture_output=True, text=True, check=True,
            env=env,
        ).stdout.strip()  # fmt: skip

    for path, text in files.items():
        blob = plumb("hash-object", "-w", "--stdin", data=text)
        plumb("update-index", "--add", "--cacheinfo", f"100644,{blob},{path}")
    tree = plumb("write-tree")
    return plumb("commit-tree", tree, *(["-p", parent] if parent else []), "-m", message)


def test_a_new_script_that_breaks_a_scan_all_test_only_when_merged_is_reported_fail(tmp_path):
    """REQ-050: brief #1358 answer 5 (each side green alone, the merge red: `fail`, no merge)."""
    root = repo(tmp_path, toml(ON), reviewers_yaml=APPROVERS)
    bare = tmp_path / "remote" / "github.com" / f"{REPO}.git"
    old = {"scripts/a.py": "# scanned\n"}
    base = commit_files(bare, None, old, "base")
    head = commit_files(bare, base, {**old, "scripts/new.py": "print(1)\n"}, "head")
    main = commit_files(bare, base, {**old, "tests/scan_all.txt": "every script\n"}, "main")
    git(bare, "update-ref", "refs/heads/main", main)
    git(bare, "update-ref", "refs/pull/7/head", head)
    pull = {**world()["pull"], "head": {"sha": head}}
    found = {"issues": [AUTO_ISSUE], "files": PROTECTED}
    bin_dir, log = fake_gh(tmp_path, pull=pull, comments=[cleared(head, extra="")], **found)
    (bin_dir / "make").write_text(
        f"#!{sys.executable}\nLOG = {str(tmp_path / 'make-calls.jsonl')!r}\n" + SCAN_MAKE,
        encoding="utf-8",
    )
    proc = run(root, bin_dir, "--pr", "7", "--sha", head)
    expected = f"merge-cleared #7 {head[:12]}: held: protected class scripts/agk/ruleset.py"
    assert one_line(proc) == f"{expected} (rule 5); would-be merge: fail"
    assert writes(calls(log)) == []
    assert [r["args"][-1] for r in makes(tmp_path)] == [f"AGK_BASE={main}"]


# --- answer 3: the conductor's owner text and doctor --------------------------------------------


def test_the_conductor_names_the_owner_command_for_an_owner_hold():
    """REQ-050: brief #1358 answers 2 and 3 (the `not queued:` line names `--owner`)."""
    line = conductor.kept_out_line(7, HEAD, "protected class constitution/ (rule 5)")
    assert line == (
        f"not queued: #7 {SHA12}: protected class constitution/ (rule 5); the owner merges with "
        "python3 scripts/agk/merge_cleared.py --pr 7 --owner"
    )
    assert conductor.kept_out_line(7, HEAD, "draft (rule 5)") == f"not queued: #7 {SHA12}: draft (rule 5)"


@pytest.mark.parametrize(
    ("config", "repo_data", "message"),
    [
        ({"flow": {}}, {"owner": {"type": "User"}}, "unavailable (user-owned repository)"),
        ({"flow": {"merge_queue": False}}, {"owner": {"type": "Organization"}}, "off"),
        ({"flow": {}, "execution": "local"}, {"owner": {"type": "User"}}, "off"),
        ({"flow": {"merge_queue": True}}, {"owner": {"type": "Organization"}}, "on"),
        ({"flow": {}}, None, "off"),
    ],
)
def test_doctor_says_when_the_merge_queue_is_unavailable(config, repo_data, message):
    """REQ-050: brief #1358 answer 3 (one line in CI mode; the kit changes no ruleset)."""
    result = doctor_module.merge_queue_result(config, repo_data)
    assert result.status == "ok" and result.message == message


def test_the_conductor_and_the_guide_name_the_owner_command():
    """REQ-050: brief #1358 answers 2 and 3."""
    root = SCRIPTS.parents[1]
    command = "merge_cleared.py --pr <n> --owner"
    for name in (".claude/agents/conductor.md", "docs/guides/getting-started.md"):
        text = (root / name).read_text(encoding="utf-8")
        assert command in text, name
        assert "would-be merge: pass" in text, name
