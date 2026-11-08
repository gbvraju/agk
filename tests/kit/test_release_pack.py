"""The evidence pack's form, its release test and its offline check (SPEC-0052 build (b),
brief #769, rules 2, 4 and 10, ADR-0343).

REQ-059 AC2 and AC8. `release_pack.py check <out>/<tag>` reads the folder and the repository's
git only and prints `ok pack`, one `FAIL pack:` line per problem or one `refused:` line. Fixtures
in `tmp_path` (a small kit repository and a pack folder), invented data, no network. The tests
were written first.
"""

from __future__ import annotations

import hashlib
import json
import os
import socket
import subprocess
import sys
import tomllib
from pathlib import Path

import kit_hashes
import pytest

KIT = Path(__file__).resolve().parents[2]
SCRIPT = KIT / "scripts" / "agk" / "release_pack.py"
TAG = "v1.1.0"
CHANGELOG = "# Changelog\n\n## 1.1.0 (2026-10-25)\n\n- #5 a change\n"
PARTS = ("tests.json", "scans.json", "coverage.json", "bom.json", "decisions.json")
NO_KIT = "refused: this repository has no release test (path class kit/)\n"
DIGEST = hashlib.sha256(b"an invented installed file\n").hexdigest()
ACTION_SHA = hashlib.sha1(b"an invented action", usedforsecurity=False).hexdigest()


def git(root: Path, *args: str) -> str:
    done = subprocess.run(["git", *args], cwd=root, capture_output=True, text=True, check=True)
    return done.stdout.strip()


def env() -> dict[str, str]:
    drop = ("GITHUB_BASE_REF", "AGK_BASE", "CI", "AGK_KIT_TESTS")
    return {k: v for k, v in os.environ.items() if k not in drop}


def put(root: Path, rel: str, text: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def write_manifest(root: Path, version: str, text: str) -> None:
    manifest = {
        "kit_version": version,
        "verbatim": ["a.txt"],
        "templates": {},
        "rendered": [],
        "adopt": {"skip": [], "blocks": {}, "templates": {}},
    }
    put(root, "kit/manifest.json", json.dumps(manifest))
    put(root, "a.txt", text)


def table(root: Path) -> None:
    put(root, "kit/hashes.json", kit_hashes.dump(kit_hashes.build_table(root, "HEAD")))


def commit(root: Path, message: str) -> None:
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", message)


def kit_repo(tmp_path: Path, *, toml="1.1.0", fragment=False, tag=TAG, annotated=False) -> Path:
    """A kit released at 1.0.0, then one commit that releases 1.1.0, tagged."""
    root = tmp_path / "repo"
    root.mkdir()
    git(root, "init", "-q", "-b", "main")
    git(root, "config", "user.email", "t@example.com")
    git(root, "config", "user.name", "t")
    git(root, "config", "commit.gpgsign", "false")
    git(root, "config", "tag.gpgsign", "false")
    write_manifest(root, "1.0.0", "a one\n")
    commit(root, "kit 1.0.0")
    table(root)
    commit(root, "table")
    write_manifest(root, "1.1.0", "a one-one\n")
    put(root, "agk.toml", f'version = "{toml}"\npr_mode = "flow"\n')
    put(root, ".claude-plugin/plugin.json", json.dumps({"name": "agk", "version": "1.1.0"}))
    put(root, "CHANGELOG.md", CHANGELOG)
    put(root, "scripts/agk/check_tag.py", "# the release test is read where this file is\n")
    if fragment:
        put(root, "changelog.d/left.md", "- a fragment that was not gathered\n")
    table(root)
    commit(root, "release 1.1.0")
    git(root, "tag", *(["-a", "-m", "a release"] if annotated else []), tag)
    return root


def project_repo(tmp_path: Path) -> Path:
    """A repository without the kit's release files: `version` names the installed kit."""
    root = tmp_path / "repo"
    root.mkdir()
    git(root, "init", "-q", "-b", "main")
    git(root, "config", "user.email", "t@example.com")
    git(root, "config", "user.name", "t")
    git(root, "config", "commit.gpgsign", "false")
    put(root, "agk.toml", 'version = "1.1.0"\n')
    commit(root, "a project")
    git(root, "tag", TAG)
    return root


def bodies() -> dict[str, dict]:
    """The five parts, of the form rules 5 to 9 name."""
    return {
        "tests.json": {
            "schema": 1,
            "checks": [
                {
                    "name": "governance",
                    "conclusion": "success",
                    "passed": 12,
                    "failed": 0,
                    "skipped": "unknown",
                }
            ],
        },
        "scans.json": {
            "schema": 1,
            "scans": [
                {"kind": "secret", "scanner": "gitleaks", "version": "8.0.0", "outcome": "passed"},
                {"kind": "dependency", "scanner": "none", "version": "none", "outcome": "not run"},
            ],
        },
        "coverage.json": {"schema": 1, "covered": 81.5, "date": "2026-10-24"},
        "bom.json": {
            "schema": 1,
            "kit_version": "1.1.0",
            "files": [{"path": "a.txt", "sha256": DIGEST}],
            "tools": [{"name": "pytest", "pin": "9.0.0"}],
            "actions": [{"name": "actions/checkout", "tag": "v9", "sha": ACTION_SHA}],
        },
        "decisions.json": {
            "schema": 1,
            "adrs": [343],
            "requirements": [{"id": "REQ-059", "from": "planned", "to": "done"}],
            "failure_issues": [{"number": 12, "state": "closed"}],
            "scorecard_week": [{"metric": "red_hours", "value": "1"}],
            "skipped_tags": ["v1.0.5"],
        },
    }


def dump(data) -> str:
    return json.dumps(data, indent=1, sort_keys=True) + "\n"


def seal(pack: Path, *, tag=TAG, commit_id: str | None = None) -> None:
    """Write `pack.json` over the parts that are in the folder."""
    digests = {
        name: hashlib.sha256((pack / name).read_bytes()).hexdigest()
        for name in PARTS
        if (pack / name).is_file()
    }
    index = {"schema": 1, "tag": tag, "commit": commit_id, "date": "2026-10-25", "parts": digests}
    (pack / "pack.json").write_text(dump(index), encoding="utf-8")


def make_pack(tmp_path: Path, root: Path, tag=TAG) -> Path:
    pack = tmp_path / "out" / tag
    pack.mkdir(parents=True)
    for name, data in bodies().items():
        (pack / name).write_text(dump(data), encoding="utf-8")
    seal(pack, tag=tag, commit_id=git(root, "rev-parse", f"refs/tags/{tag}^{{commit}}"))
    return pack


def check(root: Path, pack: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT), "check", str(pack)],
        cwd=root,
        capture_output=True,
        text=True,
        env=env(),
    )


def edit(pack: Path, name: str, change) -> None:
    data = json.loads((pack / name).read_text(encoding="utf-8"))
    change(data)
    (pack / name).write_text(dump(data), encoding="utf-8")


def resealed(pack: Path, root: Path) -> None:
    seal(pack, commit_id=git(root, "rev-parse", f"refs/tags/{TAG}^{{commit}}"))


@pytest.fixture
def repo_pack(tmp_path):
    root = kit_repo(tmp_path)
    return root, make_pack(tmp_path, root)


def test_ac8_a_complete_pack_prints_ok_pack(repo_pack):
    """REQ-059 AC8: rule 10 (a complete pack; digests and commit ids are no data-guard finding)."""
    root, pack = repo_pack
    done = check(root, pack)
    assert (done.returncode, done.stdout) == (0, "ok pack\n"), done.stdout


def test_ac8_an_annotated_tag_names_its_commit(tmp_path):
    """REQ-059 AC8: rule 10 (the tag's commit, not the tag object)."""
    root = kit_repo(tmp_path, annotated=True)
    done = check(root, make_pack(tmp_path, root))
    assert (done.returncode, done.stdout) == (0, "ok pack\n"), done.stdout


def remove(pack, root):
    (pack / "scans.json").unlink()


def seventh(pack, root):
    (pack / "notes-odd-value.txt").write_text("x\n", encoding="utf-8")


def no_field(pack, root):
    edit(pack, "coverage.json", lambda d: d.pop("date"))


def extra_field(pack, root):
    edit(pack, "bom.json", lambda d: d.update({"odd_field_value": 1}))


def schema_two(pack, root):
    edit(pack, "decisions.json", lambda d: d.update({"schema": 2}))


def byte(pack, root):
    path = pack / "coverage.json"
    path.write_text(path.read_text(encoding="utf-8").replace("81.5", "81.6"), encoding="utf-8")


def not_json(pack, root):
    (pack / "tests.json").write_text("not json odd-value\n", encoding="utf-8")


def not_an_object(pack, root):
    (pack / "tests.json").write_text("[1]\n", encoding="utf-8")


def entry_no_field(pack, root):
    edit(pack, "scans.json", lambda d: d["scans"][0].pop("outcome"))


def entry_extra_field(pack, root):
    edit(pack, "tests.json", lambda d: d["checks"][0].update({"log": "odd-value"}))


def field_not_a_list(pack, root):
    edit(pack, "bom.json", lambda d: d.update({"files": "odd-value"}))


def other_commit(pack, root):
    other = git(root, "rev-parse", f"{TAG}~1")
    edit(pack, "pack.json", lambda d: d.update({"commit": other}))


def other_tag(pack, root):
    edit(pack, "pack.json", lambda d: d.update({"tag": "v1.0.0"}))


def index_digest(pack, root):
    edit(pack, "pack.json", lambda d: d["parts"].update({"bom.json": "0" * 64}))


def index_no_part(pack, root):
    edit(pack, "pack.json", lambda d: d["parts"].pop("bom.json"))


def index_extra_part(pack, root):
    edit(pack, "pack.json", lambda d: d["parts"].update({"odd-value.json": "0" * 64}))


def index_no_field(pack, root):
    edit(pack, "pack.json", lambda d: d.pop("date"))


def index_schema(pack, root):
    edit(pack, "pack.json", lambda d: d.update({"schema": 2}))


@pytest.mark.parametrize(
    ("damage", "part"),
    [
        (remove, "scans.json"),
        (seventh, "folder"),
        (no_field, "coverage.json"),
        (extra_field, "bom.json"),
        (schema_two, "decisions.json"),
        (byte, "coverage.json"),
        (not_json, "tests.json"),
        (not_an_object, "tests.json"),
        (entry_no_field, "scans.json"),
        (entry_extra_field, "tests.json"),
        (field_not_a_list, "bom.json"),
        (other_commit, "pack.json"),
        (other_tag, "pack.json"),
        (index_digest, "bom.json"),
        (index_no_part, "pack.json"),
        (index_extra_part, "pack.json"),
        (index_no_field, "pack.json"),
        (index_schema, "pack.json"),
    ],
)
def test_ac8_one_problem_is_one_fail_line_naming_the_part_and_no_value(repo_pack, damage, part):
    """REQ-059 AC8: rule 10 (each damage gives one line, and never the value)."""
    root, pack = repo_pack
    damage(pack, root)
    done = check(root, pack)
    lines = done.stdout.splitlines()
    assert done.returncode == 1 and len(lines) == 1, done.stdout
    assert lines[0].startswith(f"FAIL pack: {part} "), done.stdout
    assert "odd" not in done.stdout and "81." not in done.stdout and "v1.0.0" not in done.stdout


def test_ac8_two_problems_are_two_lines(repo_pack):
    """REQ-059 AC8: rule 10 (one line per problem, and the check does not stop at the first)."""
    root, pack = repo_pack
    remove(pack, root)
    no_field(pack, root)
    done = check(root, pack)
    assert done.returncode == 1 and len(done.stdout.splitlines()) == 2, done.stdout


def test_ac8_a_part_that_is_a_link_is_refused(repo_pack, tmp_path):
    """REQ-059 AC8: rule 10 (a part that is not a file of the folder is not read)."""
    root, pack = repo_pack
    target = tmp_path / "elsewhere.json"
    target.write_text((pack / "bom.json").read_text(encoding="utf-8"), encoding="utf-8")
    (pack / "bom.json").unlink()
    (pack / "bom.json").symlink_to(target)
    done = check(root, pack)
    assert done.returncode == 1 and done.stdout.startswith("FAIL pack: bom.json "), done.stdout
    assert len(done.stdout.splitlines()) == 1 and str(target) not in done.stdout


def test_ac8_a_secret_like_string_in_a_part_is_refused_and_not_printed(repo_pack):
    """REQ-059 AC8: rules 10 and 11 (the data guard finds it; the line never holds the value)."""
    root, pack = repo_pack
    planted = "ghp_" + "a1B2c3D4" * 5  # built at run time, invented
    edit(pack, "tests.json", lambda d: d["checks"][0].update({"name": planted}))
    resealed(pack, root)
    done = check(root, pack)
    lines = done.stdout.splitlines()
    assert done.returncode == 1 and len(lines) == 1, done.stdout
    assert lines[0].startswith("FAIL pack: tests.json ") and planted not in done.stdout


@pytest.mark.parametrize(
    ("part", "field", "index", "outcome", "line"),
    [
        ("tests.json", "checks", 0, "failure", "warn pack: tests.json governance failure"),
        ("tests.json", "checks", 0, "unknown", "warn pack: tests.json governance unknown"),
        ("scans.json", "scans", 0, "failed", "warn pack: scans.json secret failed"),
        ("scans.json", "scans", 0, "unknown", "warn pack: scans.json secret unknown"),
    ],
)
def test_ac8_a_failed_or_unknown_result_warns_and_passes(
    repo_pack, part, field, index, outcome, line
):
    """REQ-059 AC8: rule 10 (the pack records the release, it does not judge it)."""
    root, pack = repo_pack
    key = "conclusion" if part == "tests.json" else "outcome"
    edit(pack, part, lambda d: d[field][index].update({key: outcome}))
    resealed(pack, root)
    done = check(root, pack)
    assert (done.returncode, done.stdout) == (0, f"{line}\nok pack\n"), done.stdout


def test_ac8_a_scan_not_run_is_no_warning(repo_pack):
    """REQ-059 AC8: rule 10 names `failed` and `unknown`; `not run` is recorded, not warned."""
    root, pack = repo_pack
    assert "warn" not in check(root, pack).stdout


@pytest.mark.parametrize(
    ("kwargs", "tag", "needle"),
    [
        ({"toml": "1.0.9"}, TAG, "agk.toml states a version other than the tag"),
        ({}, "release-one", "the tag is not of the form vN.N.N"),
        ({"fragment": True}, TAG, "a fragment is left under changelog.d/"),
    ],
)
def test_ac2_a_tag_that_is_not_a_release_is_refused_with_the_rule_line(
    tmp_path, kwargs, tag, needle
):
    """REQ-059 AC2: rule 4 (the #433 and #476 class; the line names the check, never a version)."""
    root = kit_repo(tmp_path, tag=tag, **kwargs)
    done = check(root, make_pack(tmp_path, root, tag=tag))
    assert done.returncode == 1, done.stdout
    assert done.stdout == f"refused: the tag is not a release ({needle})\n"
    assert "1.0.9" not in done.stdout and "1.1.0" not in done.stdout


def test_ac2_a_tag_missing_from_the_repository_is_refused(repo_pack):
    """REQ-059 AC2: rule 4 (a folder named by no tag of this repository)."""
    root, pack = repo_pack
    other = pack.parent / "v9.9.9"
    pack.rename(other)
    done = check(root, other)
    assert done.returncode == 1 and done.stdout.startswith("refused: the tag is not a release (")
    assert "9.9.9" not in done.stdout


def test_ac2_a_repository_without_the_release_files_is_refused(tmp_path):
    """REQ-059 AC2: rule 4 (a project has no release test yet; the path class is named)."""
    root = project_repo(tmp_path)
    done = check(root, make_pack(tmp_path, root))
    assert (done.returncode, done.stdout) == (1, NO_KIT), done.stdout


def test_ac2_a_manifest_without_the_tag_check_at_the_tag_is_refused(tmp_path):
    """REQ-059 AC2: rule 4 (both files are read at the tagged commit)."""
    root = project_repo(tmp_path)
    git(root, "tag", "-d", TAG)
    write_manifest(root, "1.1.0", "a\n")
    commit(root, "a manifest and no tag check")
    git(root, "tag", TAG)
    done = check(root, make_pack(tmp_path, root))
    assert (done.returncode, done.stdout) == (1, NO_KIT), done.stdout


def test_ac2_the_release_test_reads_the_tag_and_not_the_work_tree(repo_pack):
    """REQ-059 AC2: rule 4 (files changed after the tag, committed or not, change nothing)."""
    root, pack = repo_pack
    put(root, "agk.toml", 'version = "1.1.1"\npr_mode = "flow"\n')
    commit(root, "the next version")
    put(root, "changelog.d/next.md", "- not committed\n")
    done = check(root, pack)
    assert (done.returncode, done.stdout) == (0, "ok pack\n"), done.stdout


def test_ac2_a_bad_commit_after_the_tag_does_not_excuse_a_bad_tag(tmp_path):
    """REQ-059 AC2: rule 4 (a good work tree does not make a bad tag a release)."""
    root = kit_repo(tmp_path, toml="1.0.9")
    pack = make_pack(tmp_path, root)
    put(root, "agk.toml", 'version = "1.1.0"\npr_mode = "flow"\n')
    commit(root, "the version corrected after the tag")
    assert check(root, pack).stdout.startswith("refused: the tag is not a release (agk.toml")


def test_ac8_the_check_leaves_the_repository_unchanged(repo_pack):
    """REQ-059 AC8: rule 10 (it reads; no file, ref or worktree record of the repository moves)."""
    root, pack = repo_pack
    put(root, "untracked.txt", "x\n")
    before = (
        git(root, "status", "--porcelain"),
        git(root, "for-each-ref"),
        git(root, "worktree", "list"),
        git(root, "rev-parse", "HEAD"),
    )
    check(root, pack)
    after = (
        git(root, "status", "--porcelain"),
        git(root, "for-each-ref"),
        git(root, "worktree", "list"),
        git(root, "rev-parse", "HEAD"),
    )
    assert before == after


def test_ac8_a_missing_folder_is_one_line(tmp_path):
    """REQ-059 AC8: rule 10 (the path is not printed)."""
    root = kit_repo(tmp_path)
    done = check(root, tmp_path / "out-odd" / TAG)
    assert done.returncode == 1 and done.stdout.startswith("FAIL pack: folder "), done.stdout
    assert "out-odd" not in done.stdout


@pytest.mark.parametrize("args", [[], ["check"], ["make"], ["check", "a", "b"], ["odd"]])
def test_ac8_a_bad_command_prints_the_usage_and_exits_2(tmp_path, args):
    """REQ-059 AC8: rule 10 (this build has `check` only; `make` is build (c))."""
    root = kit_repo(tmp_path)
    done = subprocess.run(
        [sys.executable, str(SCRIPT), *args], cwd=root, capture_output=True, text=True, env=env()
    )
    assert done.returncode == 2 and done.stdout.startswith("usage:"), done.stdout


def test_ac8_the_check_opens_no_socket(repo_pack, monkeypatch, capsys):
    """REQ-059 AC8: rule 10 (no network: a socket raises, and the check still passes)."""
    import release_pack  # noqa: PLC0415 - the tests were written before the script

    def refuse(*args, **kwargs):
        raise AssertionError("a socket was opened")

    root, pack = repo_pack
    monkeypatch.setattr(socket, "socket", refuse)
    monkeypatch.chdir(root)
    for name in ("GITHUB_BASE_REF", "AGK_BASE", "CI"):
        monkeypatch.delenv(name, raising=False)
    assert release_pack.main(["check", str(pack)]) == 0
    assert capsys.readouterr().out == "ok pack\n"


def test_ac8_no_governance_step_runs_the_check():
    """REQ-059 AC8: rule 10 (no governance step, `make governance` or prepush calls it)."""
    for rel in ("Makefile", "agk.mk", "scripts/agk/prepush.py", ".github/workflows/governance.yml"):
        assert "release_pack" not in (KIT / rel).read_text(encoding="utf-8"), rel


def test_ac8_the_script_starts_only_git_and_reads_no_network():
    """REQ-059 AC8: rules 3 and 10 (this build starts git alone, by the common reader)."""
    text = SCRIPT.read_text(encoding="utf-8")
    for word in ("urllib", "http.client", "requests", '"gh"', "subprocess.run", "os.system"):
        assert word not in text, word


def test_ac8_the_script_is_installed_and_mapped_to_its_tests():
    """REQ-059 AC8: rule 12 build (b) (the kit manifest and the one test map entry)."""
    manifest = json.loads((KIT / "kit" / "manifest.json").read_text(encoding="utf-8"))
    assert "scripts/agk/release_pack.py" in manifest["verbatim"]
    data = tomllib.loads((KIT / "agk.toml").read_text(encoding="utf-8"))
    entries = [e for e in data["testing"]["map"] if e["code"] == "scripts/agk/release_pack.py"]
    assert len(entries) == 1 and "tests/kit/test_release_pack.py" in entries[0]["tests"]
