"""Kit-only tests of kit/hashes.json and kit_hashes.py (SPEC-0008 rules 1-3, 19, 22, 25)."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import pytest
from conftest import KIT_ROOT, git, manifest

sys.path.insert(0, str(KIT_ROOT / "scripts" / "agk"))
import kit_hashes  # noqa: E402

TABLE = KIT_ROOT / "kit" / "hashes.json"
VERSIONS = "0.1.0 0.2.0 0.3.0 0.4.0 0.4.1 0.4.2 0.5.0 0.6.0 0.6.1 0.6.2".split()
HEX = re.compile(r"^[0-9a-f]{64}$")
SHA = re.compile(r"^[0-9a-f]{40}$")


def table() -> dict:
    return json.loads(TABLE.read_text(encoding="utf-8"))


def test_ac1_table_has_the_shape_of_rule_2():
    """REQ-014 AC5: rule 2."""
    data = table()
    assert data["table"] == 1 and list(data) == ["table", "releases"]
    for version, row in data["releases"].items():
        assert re.fullmatch(r"\d+\.\d+\.\d+", version)
        assert list(row) == ["commits", "verbatim", "blocks", "templates"]
        assert all(SHA.match(c) for c in row["commits"])
        for name in ("verbatim", "blocks", "templates"):
            for path, digests in row[name].items():
                assert isinstance(path, str) and digests
                assert all(HEX.match(d) for d in digests), (version, path)


def test_ac1_table_is_written_in_the_canonical_form():
    """REQ-014 AC5: rule 2 (the file is exactly what `--write` prints, one line per path)."""
    assert kit_hashes.dump(table()) == TABLE.read_text(encoding="utf-8")


def test_ac1_every_released_version_of_rule_22_and_the_current_one_has_a_row():
    """REQ-014 AC5: rules 2 and 22."""
    rows = table()["releases"]
    assert set(VERSIONS) <= set(rows)
    assert manifest()["kit_version"] in rows


def test_ac1_zero_point_one_zero_has_two_commits_and_both_makefiles():
    """REQ-014 AC5: rule 22 (the second commit changed Makefile without a bump)."""
    row = table()["releases"]["0.1.0"]
    assert len(row["commits"]) == 2
    assert len(row["verbatim"]["Makefile"]) == 2
    multi = {
        (name, path)
        for name in ("verbatim", "blocks", "templates")
        for path, digests in row[name].items()
        if len(digests) > 1
    }
    assert ("verbatim", "Makefile") in multi


def test_ac1_only_zero_point_one_zero_has_more_than_one_hash_for_a_path():
    """REQ-014 AC5: rules 2 and 25 (the bump rule's one recorded exception)."""
    for version, row in table()["releases"].items():
        if version == kit_hashes.EXCEPTION:
            continue
        for name in ("verbatim", "blocks", "templates"):
            assert all(len(d) == 1 for d in row[name].values()), (version, name)


def test_ac1_every_row_is_regenerated_from_history_and_compared():
    """REQ-014 AC5: rule 2 and 25 (full history; the CI checkout has `fetch-depth: 0`)."""
    assert kit_hashes.problems(KIT_ROOT) == []


def test_ac1_the_current_row_equals_the_working_tree():
    """REQ-014 AC5: rule 2."""
    version, snap = kit_hashes.snapshot_worktree(KIT_ROOT)
    row = table()["releases"][version]
    for name in ("verbatim", "blocks", "templates"):
        assert set(row[name]) == set(snap[name])
        assert all(snap[name][p] in row[name][p] for p in snap[name])


def test_ac1_ci_checks_out_the_full_history_for_the_kit_dev_tests():
    """REQ-014 AC5: rule 2 (the workflow that runs the tests checks out with `fetch-depth: 0`)."""
    text = (KIT_ROOT / ".github" / "workflows" / "governance.yml").read_text(encoding="utf-8")
    checkout = text.split("actions/checkout@", 1)[1].split("- uses:", 1)[0]
    assert re.search(r"fetch-depth:\s*0", checkout)


def test_ac1_the_table_and_the_script_are_not_installed():
    """REQ-014 AC5: rules 2 and 24."""
    installed = set(manifest()["verbatim"]) | set(manifest()["templates"].values())
    assert "kit/hashes.json" not in installed
    assert (
        "scripts/agk/kit_hashes.py" not in installed and "scripts/agk/upgrade.py" not in installed
    )


def test_ac1_a_changed_hash_is_found(tmp_path):
    """REQ-014 AC5: rule 2 (the regeneration compares every row)."""
    root = fake_kit(tmp_path)
    data = json.loads((root / "kit" / "hashes.json").read_text(encoding="utf-8"))
    data["releases"]["1.0.0"]["verbatim"]["a.txt"] = ["0" * 64]
    (root / "kit" / "hashes.json").write_text(kit_hashes.dump(data), encoding="utf-8")
    found = kit_hashes.problems(root, "HEAD")
    assert any("row 1.0.0 differs from the history in verbatim" in f for f in found)


# --- a small kit repository: the bump rule and the commits of a row ------------------------------


def fake_kit(tmp_path: Path) -> Path:
    """A repository with a kit at 1.0.0 (one commit) and an up-to-date table."""
    root = tmp_path / "fake"
    root.mkdir()
    git(root, "init", "-q", "-b", "main")
    git(root, "config", "user.email", "t@example.invalid")
    git(root, "config", "user.name", "t")
    git(root, "config", "commit.gpgsign", "false")
    write_kit(root, "1.0.0", "a one\n")
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "kit 1.0.0")
    (root / "kit" / "hashes.json").write_text(
        kit_hashes.dump(kit_hashes.build_table(root, "HEAD")), encoding="utf-8"
    )
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "table")
    return root


def write_kit(root: Path, version: str, text: str) -> None:
    (root / "kit").mkdir(exist_ok=True)
    (root / "kit" / "manifest.json").write_text(
        json.dumps(
            {
                "kit_version": version,
                "verbatim": ["a.txt"],
                "templates": {},
                "rendered": [],
                "adopt": {"skip": [], "blocks": {}, "templates": {}},
            }
        ),
        encoding="utf-8",
    )
    (root / "a.txt").write_text(text, encoding="utf-8")


def test_ac1_a_fresh_kit_repository_has_no_problems(tmp_path):
    """REQ-014 AC5: rule 2."""
    assert kit_hashes.problems(fake_kit(tmp_path), "HEAD") == []


def test_ac1_a_change_without_a_bump_fails(tmp_path):
    """REQ-014 AC5: rule 25 (a second hash for a path at one version)."""
    root = fake_kit(tmp_path)
    (root / "a.txt").write_text("a changed\n", encoding="utf-8")
    found = kit_hashes.problems(root, "HEAD")
    assert any("a.txt has more than one version of its file" in f for f in found)
    assert any("needs a kit_version bump" in f for f in found)


def test_ac1_a_change_with_a_bump_needs_only_the_regenerated_table(tmp_path):
    """REQ-014 AC5: rules 2 and 25."""
    root = fake_kit(tmp_path)
    write_kit(root, "1.1.0", "a changed\n")
    assert any("no row for kit_version 1.1.0" in f for f in kit_hashes.problems(root, "HEAD"))
    (root / "kit" / "hashes.json").write_text(
        kit_hashes.dump(kit_hashes.build_table(root, "HEAD")), encoding="utf-8"
    )
    assert kit_hashes.problems(root, "HEAD") == []
    rows = json.loads((root / "kit" / "hashes.json").read_text(encoding="utf-8"))["releases"]
    assert len(rows["1.0.0"]["commits"]) == 1 and rows["1.1.0"]["commits"] == []
    assert len(rows["1.0.0"]["verbatim"]["a.txt"]) == 1


def test_ac1_a_released_row_must_name_its_commits(tmp_path):
    """REQ-014 AC5: rule 2 (a past version's commit list is exact; the current one may lag)."""
    root = fake_kit(tmp_path)
    data = json.loads((root / "kit" / "hashes.json").read_text(encoding="utf-8"))
    assert data["releases"]["1.0.0"]["commits"]  # the current version, already in history
    data["releases"]["1.0.0"]["commits"] = []  # allowed while 1.0.0 is the current version
    (root / "kit" / "hashes.json").write_text(kit_hashes.dump(data), encoding="utf-8")
    assert kit_hashes.problems(root, "HEAD") == []
    write_kit(root, "1.1.0", "a changed\n")
    fresh = kit_hashes.build_table(root, "HEAD")
    data["releases"]["1.1.0"] = fresh["releases"]["1.1.0"]
    (root / "kit" / "hashes.json").write_text(kit_hashes.dump(data), encoding="utf-8")
    found = kit_hashes.problems(root, "HEAD")
    assert any("row 1.0.0 names commits that differ" in f for f in found)


def test_ac1_a_shallow_clone_is_reported(tmp_path):
    """REQ-014 AC5: rule 2 (the check needs the full history)."""
    root = fake_kit(tmp_path)
    shallow = tmp_path / "shallow"
    subprocess.run(
        ["git", "clone", "-q", "--depth", "1", f"file://{root}", str(shallow)],
        check=True,
        capture_output=True,
    )
    found = kit_hashes.problems(shallow, "HEAD")
    assert found and "shallow" in found[0]


@pytest.mark.parametrize("args", [["--bogus"], ["--write", "--check"]])
def test_ac1_usage_errors_exit_2(args):
    """REQ-014 AC5: rule 2."""
    proc = subprocess.run(
        [sys.executable, str(KIT_ROOT / "scripts" / "agk" / "kit_hashes.py"), *args],
        capture_output=True,
        text=True,
        cwd=KIT_ROOT,
    )
    assert proc.returncode == 2


def test_ac1_a_block_is_hashed_from_its_block_source(tmp_path):
    """REQ-014 AC5: lean install (ADR-0052): adopt.block_sources names a block's source file."""
    import hashlib

    manifest = {
        "kit_version": "1.0.0",
        "verbatim": [],
        "templates": {},
        "adopt": {
            "skip": [],
            "blocks": {".gitattributes": "hash"},
            "block_sources": {".gitattributes": "kit/templates/gitattributes"},
            "templates": {},
        },
    }
    files = {"kit/templates/gitattributes": b"scripts/agk/** linguist-generated=true\n\n"}
    snap = kit_hashes.snapshot_of(manifest, files.get)
    want = hashlib.sha256(b"scripts/agk/** linguist-generated=true\n").hexdigest()
    assert snap["blocks"] == {".gitattributes": want}
    assert ".gitattributes" not in files  # the repository itself carries no such file
