"""The row of a version ends where the version was released (brief #212, ADR-0108's residual).

In flow mode a build between two releases leaves the version as it is, so the commits after the
release of V still state V. The table must not put what they add in the row of V: a project that
installed V would then read a file added since as one it deleted. The row of V holds the digests at
the first commit of the first-parent history that states V, which is the release commit; the
builds after it belong to the next version's row. Strict mode, where every change bumps, is as
before. A small kit repository in `tmp_path`; no network, no model.
"""

from __future__ import annotations

import json

import kit_hashes
from conftest import git
from test_kit_hashes import fake_kit, write_kit


def flow_history(tmp_path):
    """1.0.0 released, two builds that keep 1.0.0, then the release of 1.1.0."""
    root = fake_kit(tmp_path)
    (root / "agk.toml").write_text('version = "1.0.0"\npr_mode = "flow"\n', encoding="utf-8")
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "flow mode")
    for text in ("a two\n", "a three\n"):
        write_kit(root, "1.0.0", text)
        git(root, "commit", "-qam", f"build {text.strip()}")
    write_kit(root, "1.1.0", "a three\n")
    (root / "agk.toml").write_text('version = "1.1.0"\npr_mode = "flow"\n', encoding="utf-8")
    git(root, "commit", "-qam", "release 1.1.0")
    return root


def heads(root) -> list[str]:
    import subprocess

    out = subprocess.run(
        ["git", "rev-list", "--first-parent", "--reverse", "HEAD"],
        cwd=root,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    return out.split()


def test_ac4_a_row_holds_the_digests_of_the_release_commit_only(tmp_path):
    """REQ-035 AC4: the builds after 1.0.0 do not add their digests to its row."""
    root = flow_history(tmp_path)
    rows = kit_hashes.build_table(root, "HEAD")["releases"]
    assert len(rows["1.0.0"]["verbatim"]["a.txt"]) == 1
    assert len(rows["1.1.0"]["verbatim"]["a.txt"]) == 1
    assert rows["1.0.0"]["verbatim"]["a.txt"] != rows["1.1.0"]["verbatim"]["a.txt"]
    commits = heads(root)
    assert rows["1.0.0"]["commits"] == [commits[0]]  # the first commit that states 1.0.0
    assert rows["1.1.0"]["commits"] == [commits[-1]]  # the release commit


def test_ac4_the_regenerated_table_of_that_history_has_no_problems(tmp_path):
    """REQ-035 AC4: the table written by `--write` is the one `problems` finds right."""
    root = flow_history(tmp_path)
    (root / "kit" / "hashes.json").write_text(
        kit_hashes.dump(kit_hashes.build_table(root, "HEAD")), encoding="utf-8"
    )
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "table")
    assert kit_hashes.problems(root, "HEAD") == []


def test_ac4_between_two_releases_the_current_row_is_still_the_release_commit(tmp_path):
    """REQ-035 AC4: a build in flow mode does not widen the row of the current version."""
    root = fake_kit(tmp_path)
    (root / "agk.toml").write_text('version = "1.0.0"\npr_mode = "flow"\n', encoding="utf-8")
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "flow mode")
    write_kit(root, "1.0.0", "a two\n")
    git(root, "commit", "-qam", "a build")
    row = kit_hashes.build_table(root, "HEAD")["releases"]["1.0.0"]
    assert len(row["verbatim"]["a.txt"]) == 1 and len(row["commits"]) == 1


def test_ac4_in_strict_mode_a_second_hash_at_one_version_is_still_kept(tmp_path):
    """REQ-035 AC4: the bump rule's evidence (a change without a bump) is as before."""
    root = fake_kit(tmp_path)
    write_kit(root, "1.0.0", "a changed\n")
    git(root, "commit", "-qam", "a change without a bump")
    row = kit_hashes.build_table(root, "HEAD")["releases"]["1.0.0"]
    assert len(row["verbatim"]["a.txt"]) == 2 and json.dumps(row)
