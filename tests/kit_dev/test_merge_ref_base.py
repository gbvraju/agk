"""Kit-only tests: the base of a pull request run is the first parent of the merge ref (brief #180).

GitHub checks out `refs/pull/N/merge`, a merge of the current default branch and the pull request
head. `github.event.pull_request.base.sha` can be older than that first parent, and then every check
that diffs against the base counts what other pull requests merged in the meantime. A step of the
workflows sets `AGK_BASE` to `HEAD^1` when the checkout is a merge commit. No network, no model.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest
from conftest import KIT_ROOT, clean_env, git, make_repo
from test_changelog_flow import flow_kit, kit_hashes
from test_release_check import NEW, OLD, put, versions

SCRIPTS = KIT_ROOT / "scripts" / "agk"
WORKFLOWS = KIT_ROOT / ".github" / "workflows"
STEP = "Base of the merge ref"


def rev(root: Path, name: str) -> str:
    return subprocess.run(
        ["git", "rev-parse", name], cwd=root, capture_output=True, text=True, check=True
    ).stdout.strip()


def commit(root: Path, message: str) -> None:
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", message)


def merge_ref(root: Path, pr_work, main_work) -> tuple[str, str]:
    """Leave ROOT on a merge commit of `main` (after MAIN_WORK) and a PR branch (PR_WORK).

    Returns (the stale base: main before MAIN_WORK, the first parent of the merge commit).
    """
    stale = rev(root, "main")
    git(root, "switch", "-q", "-c", "pr")
    pr_work(root)
    commit(root, "the pull request")
    git(root, "switch", "-q", "main")
    main_work(root)
    commit(root, "merged meanwhile")
    git(root, "switch", "-q", "-c", "mergeref", "main")
    git(root, "merge", "-q", "--no-ff", "pr", "-m", "merge ref")
    first_parent = rev(root, "HEAD^1")
    assert first_parent == rev(root, "main") != stale
    return stale, first_parent


def run_check(root: Path, script: str, base: str, *args: str):
    env = {**clean_env(), "AGK_BASE": base}
    return subprocess.run(
        [sys.executable, str(SCRIPTS / script), *args],
        cwd=root,
        capture_output=True,
        text=True,
        env=env,
    )


def against_both(root: Path, script: str, stale: str, first_parent: str, needle: str) -> None:
    good = run_check(root, script, first_parent)
    assert good.returncode == 0, good.stdout
    bad = run_check(root, script, stale)
    assert bad.returncode == 1 and needle in bad.stdout, bad.stdout


# --- the checks, on a real merge commit ---------------------------------------------------------


@pytest.fixture
def docs_repo(tmp_path):
    root = make_repo(tmp_path / "proj")
    put(root, "config/protected-paths.txt", "docs/requirements.md\nscripts/agk/\n")
    put(root, "docs/requirements.md", "### REQ-001 — A\n\n- Status: planned\n- Acceptance: AC1\n")
    put(root, "docs/build-state.md", "# State\n")
    put(root, "scripts/agk/x.py", "x = 1\n")
    commit(root, "base")
    return root


def other_pull_request_merged(root: Path) -> None:
    put(
        root,
        "docs/requirements.md",
        (root / "docs/requirements.md").read_text()
        + "\n### REQ-002 — B\n\n- Status: planned\n- Acceptance: AC1\n",
    )
    put(root, "docs/build-state.md", "# State\n\n| 2026-10-25 | REQ-002 | proposed |\n")


def this_pull_request(root: Path) -> None:
    put(root, "scripts/agk/x.py", "x = 2\n")
    put(
        root,
        "docs/adr/0002-x.md",
        "# ADR-0002: x\n\n- Status: Accepted\n\nCovers scripts/agk/ only.\n",
    )


def test_ac2_protected_changes_counts_the_other_pull_request_with_a_stale_base(docs_repo):
    """Brief #180 answer 2: the incident of #175 and #178 (requirements.md merged meanwhile)."""
    stale, first = merge_ref(docs_repo, this_pull_request, other_pull_request_merged)
    against_both(docs_repo, "check_protected_changes.py", stale, first, "docs/requirements.md")


def test_ac2_build_state_counts_the_other_pull_request_with_a_stale_base(docs_repo):
    """Brief #180 answer 2: a docs-only change merged meanwhile read as this build's own."""
    stale, first = merge_ref(docs_repo, this_pull_request, other_pull_request_merged)
    against_both(docs_repo, "check_build_state.py", stale, first, "docs/build-state.md")


def test_ac2_the_fragment_count_includes_the_other_pull_requests_fragment_with_a_stale_base(
    tmp_path,
):
    """Brief #180 answer 2: `kit_hashes` wants exactly one fragment (SPEC-0031 rule 2)."""
    root = flow_kit(tmp_path)

    def this(root: Path) -> None:
        (root / "a.txt").write_text("a changed by this build\n", encoding="utf-8")
        (root / "changelog.d").mkdir(exist_ok=True)
        (root / "changelog.d" / "this-build.md").write_text("- this build\n", encoding="utf-8")

    def other(root: Path) -> None:
        (root / "changelog.d").mkdir(exist_ok=True)
        (root / "changelog.d" / "other-build.md").write_text(
            "- the other build\n", encoding="utf-8"
        )

    stale, first = merge_ref(root, this, other)
    assert kit_hashes.problems(root, first) == []
    found = kit_hashes.problems(root, stale)
    assert any("exactly one fragment" in f for f in found), found


def test_ac2_a_release_merged_meanwhile_is_not_this_pull_requests_release(tmp_path):
    """Brief #180 answer 2: with a stale base the release check treats a build as a release."""
    root = make_repo(tmp_path / "kit")
    versions(root, "1.0.0", "1.0.0", "1.0.0")
    put(root, "CHANGELOG.md", OLD)
    put(root, "kit/hashes.json", "{}\n")
    put(root, "scripts/agk/check_release.py", "# this check exists on the base\n")
    commit(root, "base")

    def released(root: Path) -> None:
        versions(root, "1.1.0", "1.1.0", "1.1.0")
        put(root, "CHANGELOG.md", NEW)
        put(root, "kit/hashes.json", '{"new": 1}\n')

    stale, first = merge_ref(root, lambda r: put(r, "README.md", "a build\n"), released)
    good = run_check(root, "check_release.py", first)
    assert good.returncode == 0 and good.stdout == "ok release\n", good.stdout
    bad = run_check(root, "check_release.py", stale)
    assert bad.returncode == 1 and "rule 5" in bad.stdout, bad.stdout


# --- the step of the workflows -------------------------------------------------------------------


def step_text(workflow: str) -> str:
    text = (WORKFLOWS / workflow).read_text(encoding="utf-8")
    block = text.split(f"      - name: {STEP}\n", 1)[1]
    return re.split(r"\n      - (?:name|uses):", block, maxsplit=1)[0]


def run_step(workflow: str, root: Path, tmp_path: Path, event_base: str = "") -> str:
    """Run the `run:` of the step in ROOT, with GITHUB_ENV a file, and return what it wrote."""
    block = step_text(workflow)
    script = block.split("run: |\n", 1)[1]
    script = "\n".join(line[10:] for line in script.splitlines())
    env_file = tmp_path / f"github-env-{workflow}"
    env_file.write_text("", encoding="utf-8")
    subprocess.run(
        ["bash", "-ec", script],
        cwd=root,
        env={**clean_env(), "GITHUB_ENV": str(env_file), "EVENT_BASE": event_base},
        check=True,
        capture_output=True,
    )
    return env_file.read_text(encoding="utf-8")


@pytest.mark.parametrize("workflow", ["governance.yml", "proof.yml"])
def test_ac1_the_step_sets_agk_base_to_the_first_parent_of_a_merge_commit(
    workflow, docs_repo, tmp_path
):
    """Brief #180 answer 1: the first parent wins over the event's older base sha."""
    stale, first = merge_ref(docs_repo, this_pull_request, other_pull_request_merged)
    assert run_step(workflow, docs_repo, tmp_path, event_base=stale) == f"AGK_BASE={first}\n"


@pytest.mark.parametrize("workflow", ["governance.yml", "proof.yml"])
def test_ac1_a_checkout_that_is_not_a_merge_commit_gets_the_events_base(
    workflow, docs_repo, tmp_path
):
    """Brief #180 answer 1: one parent, so the event's base sha is what the step sets."""
    base = rev(docs_repo, "main")
    git(docs_repo, "switch", "-q", "-c", "head-only")
    put(docs_repo, "README.md", "one parent\n")
    commit(docs_repo, "a head")
    assert run_step(workflow, docs_repo, tmp_path, event_base=base) == f"AGK_BASE={base}\n"


@pytest.mark.parametrize("workflow", ["governance.yml", "proof.yml"])
def test_ac1_with_no_merge_commit_and_no_event_base_nothing_is_set(workflow, docs_repo, tmp_path):
    """Brief #180 answer 1: nothing at all, so the checks fall back to the default branch."""
    git(docs_repo, "switch", "-q", "-c", "head-only")
    put(docs_repo, "README.md", "one parent\n")
    commit(docs_repo, "a head")
    assert run_step(workflow, docs_repo, tmp_path) == ""


@pytest.mark.parametrize("workflow", ["governance.yml", "proof.yml"])
def test_ac1_the_step_is_the_only_place_that_sets_agk_base_and_comes_before_the_first_check(
    workflow,
):
    """Brief #180 answer 1: no job-level `AGK_BASE` (the precedence question is removed)."""
    text = (WORKFLOWS / workflow).read_text(encoding="utf-8")
    assert not re.search(r"(?m)^\s*AGK_BASE:", text), "no env: entry sets AGK_BASE"
    assert text.count("AGK_BASE=") == 1 and text.count('>> "$GITHUB_ENV"') == 1
    block = step_text(workflow)
    assert "if: ${{ github.event_name == 'pull_request' }}" in block
    assert "EVENT_BASE: ${{ github.event.pull_request.base.sha }}" in block
    assert "git rev-parse HEAD^1" in block
    assert text.index("actions/checkout@") < text.index(f"- name: {STEP}")
    steps = re.findall(r"(?m)^      - (?:name|uses): (.+)$", text)
    first_use = next(i for i, s in enumerate(steps) if s.startswith(("check_", "Red-then-green")))
    assert steps.index(STEP) < first_use


def test_ac3_the_guide_names_the_symptom_and_the_fix():
    """Brief #180 answer 3: troubleshooting (a check fails on files the pull request left alone)."""
    guide = (KIT_ROOT / "docs" / "guides" / "getting-started.md").read_text(encoding="utf-8")
    assert "did not change" in guide and "first parent" in guide and "AGK_BASE" in guide
    assert "git rev-parse HEAD^1" in guide
