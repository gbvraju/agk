"""Tests of scripts/agk/plugin_snapshot.py: one licensed plugin snapshot per release for a private
release repository (brief #1476, ADR-0627). REQ-014: a customer installs AGK without its history.

Every test runs on a saved git tree of an invented kit; nothing pushes, tags a remote or calls the
network, and the `gh` on PATH is a stub that records any call.
"""

from __future__ import annotations

import json
import os
import re
import stat
import tomllib
from pathlib import Path

import check_licence_notice as notice

ROOT = Path(__file__).resolve().parents[2]
HEAD = "\n".join(notice.header_lines("hash")) + "\n"
REUSE = (
    "version = 1\n\n[[annotations]]\n"
    'path = ["**/*.json"]\n'
    'precedence = "aggregate"\n'
    'SPDX-FileCopyrightText = "2026 Balavardhi Raju Gangula"\n'
    'SPDX-License-Identifier = "LicenseRef-AGK-Proprietary"\n'
)
SNAPSHOT = [".claude-plugin/", "LICENSE", "LICENSE-AGK", "REUSE.toml", "kit/", "scripts/agk/"]
# The tag's own hash check, a stub: it fails when the tag holds `kit/hashes.fail`.
HASH_STUB = HEAD + (
    "import pathlib, sys\nsys.exit(1 if pathlib.Path('kit/hashes.fail').exists() else 0)\n"
)
ROWS = {"table": 1, "releases": {v: {"verbatim": {}} for v in ("0.9.0", "0.9.1", "1.0.0")}}


def kit(repo, extra: dict[str, str] | None = None, tag: str = "v1.0.0") -> None:
    manifest = {"kit_version": "1.0.0", "verbatim": ["scripts/agk/tool.py"], "snapshot": SNAPSHOT}
    files = {
        "kit/manifest.json": json.dumps(manifest) + "\n",
        "kit/hashes.json": json.dumps(ROWS, indent=2) + "\n",
        "kit/templates/note.md": "a template\n",
        "scripts/agk/tool.py": HEAD + "print('tool')\n",
        "scripts/agk/kit_hashes.py": HASH_STUB,
        ".claude-plugin/plugin.json": '{"name": "agk", "version": "1.0.0"}\n',
        ".claude-plugin/marketplace.json": '{"plugins": [{"name": "agk", "source": "."}]}\n',
        "LICENSE": "the licence\n",
        "LICENSE-AGK": "the licence\n",
        "REUSE.toml": REUSE,
        "docs/adr/0001-a-decision.md": "a decision\n",
        "docs/briefs/0001.md": "a brief\n",
        "changelog.d/1.md": "a fragment\n",
        "tests/kit_dev/test_x.py": "x = 1\n",
        "agk.toml": '[release]\nrepository = "example-owner/agk-release"\n',
        **(extra or {}),
    }
    repo.commit(files)
    repo.git("tag", tag)


def gh_stub(tmp_path: Path) -> dict[str, str]:
    """A PATH whose `gh` records its call; `git push` and `git tag` are never stubbed out."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(exist_ok=True)
    gh = bin_dir / "gh"
    gh.write_text(f"#!/bin/sh\necho called >> {tmp_path / 'gh-called'}\n", encoding="utf-8")
    gh.chmod(gh.stat().st_mode | stat.S_IEXEC)
    return {"PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}"}


def files_of(folder: Path) -> dict[str, bytes]:
    return {
        p.relative_to(folder).as_posix(): p.read_bytes() for p in folder.rglob("*") if p.is_file()
    }


def test_req014_the_snapshot_holds_only_the_allow_list(repo, tmp_path_factory):
    """REQ-014 answers 1 and 3: only the allow list, with the release marketplace at the tag."""
    kit(repo)
    out = tmp_path_factory.mktemp("snap") / "v1.0.0"
    proc = repo.run("plugin_snapshot.py", "build", "--tag", "v1.0.0", "--out", str(out))
    assert proc.returncode == 0, proc.stdout + proc.stderr
    got = files_of(out)
    assert all(any(p.startswith(a) if a.endswith("/") else p == a for a in SNAPSHOT) for p in got)
    for left_out in ("docs/", "changelog.d/", "tests/kit_dev/", "agk.toml", ".git"):
        assert not any(p.startswith(left_out) for p in got), left_out
    market = json.loads(got[".claude-plugin/marketplace.json"])
    assert market["plugins"] == [
        {
            "name": "agk",
            "source": ".",
            "description": "Workflow commands for repositories governed by agk.",
            "version": "1.0.0",
        }
    ]
    assert re.search(r"^digest [0-9a-f]{64}$", proc.stdout, re.M)


def test_req014_every_release_row_of_the_hash_table_is_kept(repo, tmp_path_factory):
    """REQ-014: the table built from the full history is copied, every row kept (uninstall)."""
    kit(repo)
    out = tmp_path_factory.mktemp("snap") / "s"
    assert (
        repo.run("plugin_snapshot.py", "build", "--tag", "v1.0.0", "--out", str(out)).returncode
        == 0
    )
    table = json.loads((out / "kit/hashes.json").read_text(encoding="utf-8"))
    assert sorted(table["releases"]) == ["0.9.0", "0.9.1", "1.0.0"]
    assert (out / "kit/hashes.json").read_text(encoding="utf-8") == json.dumps(
        ROWS, indent=2
    ) + "\n"


def test_req014_two_builds_of_one_tag_give_one_digest(repo, tmp_path_factory):
    """REQ-014 answer 1: deterministic, the same tag gives one tree and one digest."""
    kit(repo)
    base = tmp_path_factory.mktemp("snap")
    runs = [
        repo.run("plugin_snapshot.py", "build", "--tag", "v1.0.0", "--out", str(base / n))
        for n in ("a", "b")
    ]
    assert [r.returncode for r in runs] == [0, 0]
    assert runs[0].stdout.splitlines()[-1] == runs[1].stdout.splitlines()[-1]
    assert files_of(base / "a") == files_of(base / "b")
    # a later commit on the branch does not change the tag's snapshot
    repo.commit({"scripts/agk/tool.py": HEAD + "print('later')\n"})
    again = repo.run("plugin_snapshot.py", "build", "--tag", "v1.0.0", "--out", str(base / "c"))
    assert again.stdout.splitlines()[-1] == runs[0].stdout.splitlines()[-1]


def test_req014_a_file_without_the_licence_header_fails_and_writes_nothing(repo, tmp_path_factory):
    """REQ-014 answer 2: an unlicensed kit file fails the build, naming its path class."""
    kit(repo, {"scripts/agk/bare.py": "print('no header')\n"})
    out = tmp_path_factory.mktemp("snap") / "s"
    proc = repo.run("plugin_snapshot.py", "build", "--tag", "v1.0.0", "--out", str(out))
    assert proc.returncode == 1
    assert (
        "scripts/agk/bare.py has no owner and licence header (path class scripts/)" in proc.stdout
    )
    assert "nothing written" in proc.stdout
    assert not out.exists()


def test_req014_a_secret_shape_in_a_template_fails(repo, tmp_path_factory):
    """REQ-014 answer 2: a personal-data shape anywhere in the snapshot fails it, never quoted."""
    address = "member-example-1" + "@" + "example.invalid"  # built here; example.com is exempt
    kit(repo, {"kit/templates/contact.md": f"write to {address}\n"})
    out = tmp_path_factory.mktemp("snap") / "s"
    proc = repo.run("plugin_snapshot.py", "build", "--tag", "v1.0.0", "--out", str(out))
    assert proc.returncode == 1
    assert "kit/templates/contact.md holds a EMAIL shape (path class kit/)" in proc.stdout
    assert address not in proc.stdout
    assert not out.exists()


def test_req014_a_failing_hash_check_at_the_tag_fails(repo, tmp_path_factory):
    """REQ-014 answer 2: `kit_hashes.py --check` at the tag fails the build."""
    kit(repo, {"kit/hashes.fail": "x\n"})
    out = tmp_path_factory.mktemp("snap") / "s"
    proc = repo.run("plugin_snapshot.py", "build", "--tag", "v1.0.0", "--out", str(out))
    assert proc.returncode == 1
    assert "kit/hashes.json fails its check (path class kit/)" in proc.stdout
    assert not out.exists()


def test_req014_verify_matches_a_clone_and_names_the_first_difference(repo, tmp_path_factory):
    """REQ-014 answer 6: a clone equal to the build passes; one that differs names the path."""
    kit(repo)
    clone = tmp_path_factory.mktemp("clone") / "release"
    assert (
        repo.run("plugin_snapshot.py", "build", "--tag", "v1.0.0", "--out", str(clone)).returncode
        == 0
    )
    (clone / ".git").mkdir()
    (clone / ".git" / "HEAD").write_text("ref: refs/heads/main\n", encoding="utf-8")
    ok = repo.run("plugin_snapshot.py", "verify", "--tag", "v1.0.0", "--clone", str(clone))
    assert ok.returncode == 0, ok.stdout
    (clone / "scripts/agk/tool.py").write_text(HEAD + "print('edited')\n", encoding="utf-8")
    (clone / "scripts/agk/zz.py").write_text(HEAD, encoding="utf-8")
    bad = repo.run("plugin_snapshot.py", "verify", "--tag", "v1.0.0", "--clone", str(clone))
    assert bad.returncode == 1
    assert "FAIL plugin-snapshot: scripts/agk/tool.py differs from the build" in bad.stdout


def test_req014_publish_refuses_without_the_release_repository(repo, tmp_path):
    """REQ-014 answer 3: `[release] repository` unset is refused naming the setting."""
    kit(repo, {"agk.toml": "[kit]\n"})
    proc = repo.run("plugin_snapshot.py", "publish", "--tag", "v1.0.0", "--dir", "/x/snap")
    assert proc.returncode == 1
    assert "the setting [release] repository is unset" in proc.stdout


def test_req014_publish_prints_and_never_runs(repo, tmp_path):
    """REQ-014 answer 4: the commands are printed; no gh call, no tag, no push."""
    kit(repo)
    tags = repo.git("tag")
    proc = repo.run(
        "plugin_snapshot.py", "publish", "--tag", "v1.0.0", "--dir", "/x/snap", **gh_stub(tmp_path)
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    lines = proc.stdout.splitlines()
    assert 'git -C /x/snap.release commit -m "Release v1.0.0"' in lines
    assert "git -C /x/snap.release tag v1.0.0" in lines
    assert (
        "gh api --method PUT repos/example-owner/agk-release/collaborators/<login> "
        "-f permission=pull"
    ) in lines
    assert not (tmp_path / "gh-called").exists()
    assert repo.git("tag") == tags
    assert not Path("/x/snap.release").exists()


def test_req014_the_kit_manifest_snapshot_covers_every_installed_path():
    """REQ-014: the kit's allow list holds what a machine needs and none of the history."""
    manifest = json.loads((ROOT / "kit/manifest.json").read_text(encoding="utf-8"))
    listed = manifest["snapshot"]
    assert listed == sorted(listed)
    adopt = manifest.get("adopt") or {}
    installed = {
        *manifest["verbatim"],
        *manifest["experimental"],
        *manifest["templates"].values(),
        *manifest["rendered"],
        *(adopt.get("templates") or {}).values(),
    }
    for rel in installed:
        assert any(rel.startswith(a) if a.endswith("/") else rel == a for a in listed), rel
    for folder in (".claude-plugin/", "skills/", "scripts/agk/", "kit/", "config/", "tests/kit/"):
        assert folder in listed
    for never in (
        "docs/adr/",
        "docs/specs/",
        "docs/runs/",
        "docs/briefs/",
        "changelog.d/",
        "tests/kit_dev/",
    ):
        assert not any(a.startswith(never) and not a.endswith("TEMPLATE.md") for a in listed)
    assert ".github/workflows/agk-tag.yml" not in listed  # the kit's own workflow
    cfg = tomllib.loads((ROOT / "agk.toml").read_text(encoding="utf-8"))
    entry = [e for e in cfg["testing"]["map"] if e["code"] == "scripts/agk/plugin_snapshot.py"]
    assert entry and "tests/kit/test_plugin_snapshot.py" in entry[0]["tests"]
    assert "scripts/agk/plugin_snapshot.py" not in manifest["verbatim"]  # kit-only
