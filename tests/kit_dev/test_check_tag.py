"""The check of a pushed tag (brief #212 build (b); ADR-0133).

`check_tag.py --tag vN.N.N [--issue-json FILE]` runs on the tagged commit: `CHANGELOG.md` has the
section of the tag, no fragment is left in `changelog.d/`, every file that states the version
states the tag's, and `kit/hashes.json` matches the kit files. On a failure it exits 1 naming the
check and, with `--issue-json`, writes the one issue `The tag <tag> is not a release` (label
`agk-brief`, `Priority: 0`, a `Measured:` line). It reads git and files only: no network, no tag,
no release, no commit. A small kit repository in `tmp_path`; no network, no model.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import kit_hashes
import pytest
import session
from conftest import KIT_ROOT, clean_env, git
from test_kit_hashes import fake_kit, write_kit

SCRIPT = KIT_ROOT / "scripts" / "agk" / "check_tag.py"
WORKFLOW = KIT_ROOT / ".github" / "workflows" / "agk-tag.yml"
CHANGELOG = "# Changelog\n\n## Unreleased\n\n## 1.1.0 (2026-10-25)\n\n- #5 a change\n"


def put(root: Path, rel: str, text: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def release(tmp_path: Path, *, toml="1.1.0", plugin="1.1.0", changelog=CHANGELOG, fragment=False,
            stale_table=False) -> Path:  # fmt: skip
    """1.0.0 released, then one commit that releases 1.1.0 (its table written before the edit when
    `stale_table`)."""
    root = fake_kit(tmp_path)
    write_kit(root, "1.1.0", "a one-one\n")
    put(root, "agk.toml", f'version = "{toml}"\npr_mode = "flow"\n')
    put(root, ".claude-plugin/plugin.json", json.dumps({"name": "agk", "version": plugin}))
    put(root, "CHANGELOG.md", changelog)
    if fragment:
        put(root, "changelog.d/left.md", "- a fragment that was not gathered\n")
    (root / "kit" / "hashes.json").write_text(
        kit_hashes.dump(kit_hashes.build_table(root, "HEAD")), encoding="utf-8"
    )
    if stale_table:
        put(root, "a.txt", "a changed after the table\n")
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "release 1.1.0")
    return root


def check(root: Path, tag="v1.1.0", out: Path | None = None):
    args = [sys.executable, str(SCRIPT), "--tag", tag]
    if out is not None:
        args += ["--issue-json", str(out)]
    return subprocess.run(args, cwd=root, capture_output=True, text=True, env=clean_env())


def test_ac1_a_release_commit_passes(tmp_path):
    """Brief #212 (b) 5: the tagged commit is a release."""
    proc = check(release(tmp_path))
    assert (proc.returncode, proc.stdout) == (0, "ok tag\n"), proc.stdout


@pytest.mark.parametrize(
    ("kwargs", "tag", "needle"),
    [
        ({"fragment": True}, "v1.1.0", "a fragment is left under changelog.d/"),
        ({"toml": "1.0.9"}, "v1.1.0", "agk.toml states a version other than the tag"),
        ({"plugin": "1.0.9"}, "v1.1.0", ".claude-plugin/plugin.json states a version"),
        ({"changelog": "# Changelog\n\n## Unreleased\n\n- #5 a change\n"}, "v1.1.0", "no section"),
        ({"stale_table": True}, "v1.1.0", "kit/hashes.json does not match the kit files"),
        ({}, "v1.2.0", "states a version other than the tag"),
        ({}, "1.1.0", "the tag is not of the form vN.N.N"),
    ],
)
def test_ac1_each_failure_names_the_check_that_failed(tmp_path, kwargs, tag, needle):
    """Brief #212 (b) 5: unreleased fragments, a version mismatch and a hash mismatch fail."""
    proc = check(release(tmp_path, **kwargs), tag)
    assert proc.returncode == 1 and proc.stdout.startswith("FAIL tag: "), proc.stdout
    assert needle in proc.stdout, proc.stdout


def test_ac2_the_issue_is_one_brief_that_names_the_commit_the_check_and_the_fix(tmp_path):
    """Brief #212 (b) 2: title, label, Priority: 0, a Measured: line, no deletion by the check."""
    root = release(tmp_path, fragment=True)
    out = tmp_path / "issue.json"
    assert check(root, out=out).returncode == 1
    issue = json.loads(out.read_text(encoding="utf-8"))
    assert issue["title"] == "The tag v1.1.0 is not a release"
    assert issue["labels"] == ["agk-brief"]
    body = issue["body"]
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=root, capture_output=True, text=True, check=True
    ).stdout.strip()
    assert commit in body and "Priority: 0" in body and "Advances: none" in body
    assert "Measured: " in body and "a fragment is left under changelog.d/" in body
    assert "delete the tag and its release" in body and "merge commit of the release" in body
    assert session.brief_problems(body) == [], session.brief_problems(body)


def test_ac2_a_passing_tag_writes_no_issue_file(tmp_path):
    """Brief #212 (b) 2: nothing is written when the tag is a release."""
    out = tmp_path / "issue.json"
    assert check(release(tmp_path), out=out).returncode == 0 and not out.exists()


def test_ac3_the_check_reads_only_and_makes_no_network_call():
    """Brief #212 (b) 3: no tag, no release, no commit, no network."""
    text = SCRIPT.read_text(encoding="utf-8")
    for word in ("urllib", '"gh"', "git tag", "tag -d", '"push"', '"commit"', "release create"):
        assert word not in text, word


def test_ac1_the_workflow_runs_on_a_pushed_tag_and_writes_only_the_one_issue():
    """Brief #212 (b) 1 and 3: the trigger, the permissions and what it never does."""
    text = WORKFLOW.read_text(encoding="utf-8")
    assert "tags:" in text and "'v*'" in text.replace('"', "'")
    assert "issues: write" in text and "contents: write" not in text
    assert "scripts/agk/check_tag.py" in text and "fetch-depth: 0" in text
    for word in ("git tag", "git push", "gh release", "git commit", "--method DELETE", "-X DELETE"):
        assert word not in text, word
    assert "The tag" in text and "agk-brief" in text
