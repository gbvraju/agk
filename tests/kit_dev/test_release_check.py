"""Kit-only tests of `check_release.py`, the release pull request check (SPEC-0028 rules 4 and 5).

A release pull request raises `version` in `agk.toml` in flow mode, changes only five files, moves
the Unreleased lines under the new version and raises the three versions together. No network, no
model.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
from conftest import KIT_ROOT, clean_env, git

SCRIPT = KIT_ROOT / "scripts" / "agk" / "check_release.py"
LINES = "- #5 the first change\n- #6 the second change\n"
OLD = f"# Changelog\n\n## Unreleased\n\n{LINES}\n## 1.0.0 (2026-01-01)\n\n- #1 the start\n"
NEW = (
    f"# Changelog\n\n## Unreleased\n\n## 1.1.0 (2026-10-24)\n\n{LINES}\n"
    "## 1.0.0 (2026-01-01)\n\n- #1 the start\n"
)


def put(root: Path, rel: str, text: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def versions(root: Path, agk: str, manifest: str, plugin: str, mode: str = "flow") -> None:
    put(root, "agk.toml", f'version = "{agk}"\npr_mode = "{mode}"\n')
    put(root, "kit/manifest.json", json.dumps({"kit_version": manifest}))
    put(root, ".claude-plugin/plugin.json", json.dumps({"name": "agk", "version": plugin}))


@pytest.fixture
def repo(tmp_path):
    root = tmp_path / "kit"
    root.mkdir()
    git(root, "init", "-q", "-b", "main")
    git(root, "config", "user.email", "t@example.invalid")
    git(root, "config", "user.name", "t")
    git(root, "config", "commit.gpgsign", "false")
    versions(root, "1.0.0", "1.0.0", "1.0.0")
    put(root, "CHANGELOG.md", OLD)
    put(root, "kit/hashes.json", "{}\n")
    put(root, "README.md", "readme\n")
    put(root, "scripts/agk/check_release.py", "# this check exists on the base\n")
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "base")
    return root


def release(root: Path, agk="1.1.0", manifest="1.1.0", plugin="1.1.0", changelog=NEW) -> None:
    git(root, "switch", "-q", "-c", "release")
    versions(root, agk, manifest, plugin)
    put(root, "CHANGELOG.md", changelog)
    put(root, "kit/hashes.json", '{"new": 1}\n')


def check(root: Path, *args: str):
    base = subprocess.run(
        ["git", "rev-parse", "main"], cwd=root, capture_output=True, text=True, check=True
    ).stdout.strip()
    env = {**clean_env(), "AGK_BASE": base}
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args], cwd=root, capture_output=True, text=True, env=env
    )


def failed(proc, needle: str) -> None:
    assert proc.returncode == 1, proc.stdout
    assert proc.stdout.startswith("FAIL release: rule 5"), proc.stdout
    assert needle in proc.stdout, proc.stdout


def test_ac4_a_release_that_moves_the_lines_and_raises_the_three_versions_passes(repo):
    """REQ-035 AC4: rules 4 and 5."""
    release(repo)
    proc = check(repo)
    assert (proc.returncode, proc.stdout) == (0, "ok release\n"), proc.stdout


def test_ac4_a_pull_request_that_raises_no_version_is_not_a_release(repo):
    """REQ-035 AC4: rule 5 (a build pull request is left alone)."""
    git(repo, "switch", "-q", "-c", "build")
    put(repo, "README.md", "a build changes other files\n")
    proc = check(repo)
    assert (proc.returncode, proc.stdout) == (0, "ok release\n")


def test_ac3_in_strict_mode_nothing_is_checked(repo):
    """REQ-035 AC3: rule 5 (a bump with any other file passes as before)."""
    release(repo)
    versions(repo, "1.1.0", "1.1.0", "1.1.0", mode="strict")
    put(repo, "README.md", "strict allows this\n")
    proc = check(repo)
    assert (proc.returncode, proc.stdout) == (0, "ok release\n")


def test_ac5_a_sixth_changed_file_fails_naming_the_path(repo):
    """REQ-035 AC5: rule 5 (exactly the five files)."""
    release(repo)
    put(repo, "README.md", "a sixth file\n")
    failed(check(repo), "README.md")


def test_ac5_a_new_file_outside_the_five_fails(repo):
    """REQ-035 AC5: rule 5 (an untracked file counts as changed)."""
    release(repo)
    put(repo, "scripts/agk/new.py", "x = 1\n")
    failed(check(repo), "scripts/agk/new.py")


@pytest.mark.parametrize(
    ("agk", "manifest", "plugin"),
    [("1.1.0", "1.1.0", "1.0.0"), ("1.1.0", "1.0.0", "1.1.0"), ("1.1.0", "1.2.0", "1.1.0")],
)
def test_ac5_versions_that_differ_fail(repo, agk, manifest, plugin):
    """REQ-035 AC5: rule 5 (the three are raised together)."""
    release(repo, agk, manifest, plugin)
    failed(check(repo), "three versions differ")


@pytest.mark.parametrize("version", ["0.9.0", "0.10.0"])
def test_ac5_versions_that_do_not_rise_fail(repo, version):
    """REQ-035 AC5: rule 5 (greater than the old one, compared as numbers)."""
    release(repo, version, version, version)
    failed(check(repo), "do not rise")


def test_ac5_a_numeric_comparison_accepts_ten_after_nine(repo):
    """REQ-035 AC5: rule 5 (1.10.0 is greater than 1.9.0)."""
    versions(repo, "1.9.0", "1.9.0", "1.9.0")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "base at 1.9.0")
    release(repo, "1.10.0", "1.10.0", "1.10.0", NEW.replace("1.1.0", "1.10.0"))
    assert check(repo).stdout == "ok release\n"


def test_ac5_a_line_changed_while_it_is_moved_fails(repo):
    """REQ-035 AC5: rule 5 (moved unchanged and in order)."""
    release(repo, changelog=NEW.replace("the first change", "the first change, reworded"))
    failed(check(repo), "moved unchanged")


def test_ac5_lines_in_another_order_or_dropped_fail(repo):
    """REQ-035 AC5: rule 5."""
    swapped = NEW.replace(LINES, "- #6 the second change\n- #5 the first change\n")
    release(repo, changelog=swapped)
    failed(check(repo), "moved unchanged")
    put(repo, "CHANGELOG.md", NEW.replace(LINES, "- #5 the first change\n"))
    failed(check(repo), "moved unchanged")


def test_ac5_an_unreleased_section_that_is_not_empty_fails(repo):
    """REQ-035 AC5: rule 5 (nothing is left under Unreleased)."""
    release(
        repo, changelog=NEW.replace("## Unreleased\n", "## Unreleased\n\n- #9 left behind\n", 1)
    )
    failed(check(repo), "Unreleased is not empty")


def test_ac5_an_older_release_section_that_changed_fails(repo):
    """REQ-035 AC5: rule 5 (the rest of the changelog is as it was)."""
    release(repo, changelog=NEW.replace("- #1 the start", "- #1 the start, rewritten"))
    failed(check(repo), "moved unchanged")


def test_ac5_a_new_heading_without_the_new_version_fails(repo):
    """REQ-035 AC5: rule 5 (the heading names the new version and a date)."""
    release(repo, changelog=NEW.replace("## 1.1.0 (2026-10-24)", "## 1.2.0 (2026-10-24)"))
    failed(check(repo), "moved unchanged")


def test_ac5_the_messages_name_the_rule_and_never_a_version_value(repo):
    """REQ-035 AC5: rule 5 and CLAUDE.md rule 6 (refusals name the setting or path class)."""
    release(repo, "1.1.0", "1.4.7", "1.1.0")
    proc = check(repo)
    assert "1.4.7" not in proc.stdout and "1.1.0" not in proc.stdout


def test_ac5_the_check_reads_git_and_files_only_and_is_not_installed():
    """REQ-035 AC5: rule 5 (no network; kit-only)."""
    import ast

    tree = ast.parse(SCRIPT.read_text(encoding="utf-8"))
    names = {
        a.name.split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names
    }
    names |= {
        n.module.split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and n.module
    }
    assert not names & {"socket", "urllib", "http", "requests", "ssl"}
    manifest = json.loads((KIT_ROOT / "kit" / "manifest.json").read_text(encoding="utf-8"))
    assert "scripts/agk/check_release.py" not in manifest["verbatim"]


def test_ac5_the_pull_request_that_adds_the_check_is_not_checked_by_it(repo):
    """REQ-035 AC5: rule 9 (the last build that bumps itself; the base has no check yet)."""
    git(repo, "rm", "-q", "scripts/agk/check_release.py")
    git(repo, "commit", "-q", "-m", "a base without the check")
    release(repo)
    put(repo, "README.md", "the adding pull request changes other files and bumps\n")
    put(repo, "scripts/agk/check_release.py", "# added by this pull request\n")
    proc = check(repo)
    assert (proc.returncode, proc.stdout) == (0, "ok release\n"), proc.stdout


# --- brief #557 fix list item 2: the release flips each ADR accepted by a Final line -----------

ADR = "docs/adr/0001-x.md"
RECORD = "Example (#7)\n\nADR-0001 Accepted (Final 42)\nMerged-by: merge_cleared.py\n"


def adr(status: str) -> str:
    return f"# ADR-0001: x\n\n- Status: {status}\n- Date: 2026-11-05\n\n## Decision\n\nd\n"


def recorded(root: Path, message: str = RECORD) -> None:
    put(root, "config/reviewers.yaml", "version: 1\nverdict_authors: [reviewer]\n")
    put(root, ADR, adr("Proposed"))
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", message)


def test_a_release_fails_while_an_adr_accepted_by_a_final_still_says_proposed(repo):
    """REQ-028: SPEC-0021 rule 3a and SPEC-0028 rule 5 as amended (the flip is a release step)."""
    recorded(repo)
    release(repo)
    proc = check(repo, "--comments", final_comments(repo))
    failed(proc, "docs/adr/")
    assert "Proposed" in proc.stdout


def test_a_release_that_flips_the_status_line_of_each_recorded_adr_passes(repo):
    """REQ-028: SPEC-0028 rules 4 and 5 as amended (the Status line only, Proposed to Accepted)."""
    recorded(repo)
    release(repo)
    put(repo, ADR, adr("Accepted"))
    proc = check(repo, "--comments", final_comments(repo))
    assert (proc.returncode, proc.stdout) == (0, "ok release\n"), proc.stdout


def test_a_release_may_not_change_an_adr_beyond_its_status_line_or_an_unrecorded_one(repo):
    """REQ-028: SPEC-0028 rule 5 as amended (no other ADR change rides on a release)."""
    recorded(repo)
    release(repo)
    saved = final_comments(repo)
    put(repo, ADR, adr("Accepted").replace("\nd\n", "\nchanged\n"))
    failed(check(repo, "--comments", saved), ADR)
    put(repo, ADR, adr("Accepted"))
    put(repo, "docs/adr/0002-y.md", adr("Accepted").replace("0001", "0002"))
    failed(check(repo, "--comments", saved), "docs/adr/0002-y.md")


def test_an_unread_record_asks_no_flip(repo):
    """REQ-028: rule 3a (a record line outside a merge_cleared.py squash commit is not read)."""
    recorded(repo, "Example\n\nADR-0001 Accepted (Final 42)\n")
    release(repo)
    proc = check(repo)
    assert (proc.returncode, proc.stdout) == (0, "ok release\n"), proc.stdout


# --- fix list of 2026-11-05 on e5e45d5: a record counts only once its comment verifies it -------

FORGED = (  # GitHub's default squash message copies the commit bodies of the pull request
    "Example (#7)\n\n* an ordinary change\n\nADR-0001 Accepted (Final 42)\n"
    "Merged-by: merge_cleared.py\n"
)


def final_comments(root: Path, pr: int = 7, cid: int = 42) -> str:
    """The Final comments of the base's records, as `gh api repos/{repo}/issues/comments/<id>`."""
    item = {
        "id": cid,
        "issue_url": f"https://api.example.com/repos/example-owner/example-repo/issues/{pr}",
        "user": {"login": "reviewer"},
        "body": f"Verdict: fix list a1b2c3d\n\nreviewed.\n\nFinal: {ADR} Proposed -> Accepted\n",
    }
    path = root.parent / "final-comments.json"
    path.write_text(json.dumps([item]), encoding="utf-8")
    return str(path)


def test_a_release_fails_closed_without_the_final_comments_when_the_base_holds_a_record(repo):
    """REQ-028: SPEC-0028 rule 5 as amended (an unverified record accepts nothing)."""
    recorded(repo)
    release(repo)
    put(repo, ADR, adr("Accepted"))
    proc = check(repo)
    failed(proc, "--comments")


@pytest.mark.parametrize(("pr", "cid"), [(8, 42), (7, 43)])
def test_a_release_that_flips_an_adr_of_a_forged_default_message_record_fails(repo, pr, cid):
    """REQ-028: SPEC-0021 rule 3a and SPEC-0028 rule 5 (a copied record line asks no flip)."""
    recorded(repo, FORGED)
    release(repo)
    put(repo, ADR, adr("Accepted"))
    failed(check(repo, "--comments", final_comments(repo, pr, cid)), ADR)
    put(repo, ADR, adr("Proposed"))
    proc = check(repo, "--comments", final_comments(repo, pr, cid))
    assert (proc.returncode, proc.stdout) == (0, "ok release\n"), proc.stdout


# --- fix list of 2026-11-05 on 94c0d39: a valid release with its Final comments is a release ----

PROTECTED = KIT_ROOT / "scripts" / "agk" / "check_protected_changes.py"
WORKFLOW = KIT_ROOT / ".github" / "workflows" / "governance.yml"
ADRS = KIT_ROOT / "scripts" / "agk" / "check_adrs.py"


def protected(root: Path, *args: str):
    base = subprocess.run(
        ["git", "rev-parse", "main"], cwd=root, capture_output=True, text=True, check=True
    ).stdout.strip()
    env = {**clean_env(), "AGK_BASE": base}
    return subprocess.run(
        [sys.executable, str(PROTECTED), *args], cwd=root, capture_output=True, text=True, env=env
    )


def flipped_release(root: Path) -> None:
    put(root, "config/protected-paths.txt", "agk.toml\nkit/\n.claude-plugin/\n")
    recorded(root)
    release(root)
    put(root, ADR, adr("Accepted"))


def test_a_valid_release_with_its_final_comment_is_a_release_for_both_checks(repo):
    """REQ-028: SPEC-0028 rule 5 and SPEC-0021 rule 3a (the comments reach `valid_release`)."""
    flipped_release(repo)
    saved = final_comments(repo)
    proc = check(repo, "--comments", saved)
    assert (proc.returncode, proc.stdout) == (0, "ok release\n"), proc.stdout
    proc = protected(repo, "--comments", saved)
    assert proc.returncode == 0, proc.stdout
    assert "(a release pull request)" in proc.stdout


def test_a_release_without_the_final_comments_is_not_a_release_for_the_protected_check(repo):
    """REQ-028: SPEC-0021 rule 3a (fail closed: no comments, no release exemption)."""
    flipped_release(repo)
    proc = protected(repo)
    assert proc.returncode != 0, proc.stdout
    assert "a release pull request" not in proc.stdout
    proc = protected(repo, "--comments", str(repo.parent / "missing.json"))
    assert proc.returncode != 0, proc.stdout


def test_valid_release_passes_the_comments_to_check(repo):
    """REQ-028: `valid_release` takes the comments `check` needs once the base holds a record."""
    flipped_release(repo)
    code = (
        "import json, sys; sys.path.insert(0, sys.argv[1]); import check_release, check_adrs;"
        "from pathlib import Path;"
        "c = check_adrs.read_comments(sys.argv[2]);"
        "print(check_release.valid_release(Path('.'), 'main', c),"
        " check_release.valid_release(Path('.'), 'main'))"
    )
    proc = subprocess.run(
        [sys.executable, "-c", code, str(SCRIPT.parent), final_comments(repo)],
        cwd=repo,
        capture_output=True,
        text=True,
        env={**clean_env(), "AGK_BASE": "main"},
    )
    assert proc.stdout.strip() == "True False", proc.stdout + proc.stderr


def test_record_ids_lists_the_final_comment_id_of_each_read_record(repo):
    """REQ-028: the workflow fetches the Final comment of each record `final_records` reads."""
    recorded(repo)
    for message in (
        "Other (#9)\n\nADR-0002 Accepted (Final 77)\nMerged-by: merge_cleared.py\n",
        "Unread\n\nADR-0003 Accepted (Final 99)\n",
    ):
        git(repo, "commit", "-q", "--allow-empty", "-m", message)
    proc = subprocess.run(
        [sys.executable, str(ADRS), "--record-ids"],
        cwd=repo,
        capture_output=True,
        text=True,
        env=clean_env(),
    )
    assert (proc.returncode, proc.stdout) == (0, "42\n77\n"), proc.stdout + proc.stderr


def test_the_governance_workflow_saves_the_record_comments_and_passes_them():
    """REQ-028: Q-557-5 (the Release check and check_protected_changes read the Final comments)."""
    text = WORKFLOW.read_text(encoding="utf-8")
    assert "check_adrs.py --record-ids" in text
    assert "issues/comments/$id" in text
    assert 'check_release.py --comments "$RUNNER_TEMP/record-comments.json"' in text
    assert '--comments "$RUNNER_TEMP/record-comments.json"' in text.split(
        "check_protected_changes.py", 1
    )[1].splitlines()[0]
    assert text.index("name: Record comments") < text.index("name: check_protected_changes")
