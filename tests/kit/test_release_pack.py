"""The evidence pack's form, its release test and its offline check (SPEC-0052 build (b),
brief #769, rules 2, 4 and 10, ADR-0343), and `make` from git (build (c), brief #820, rules 3, 8
and 9), and the required checks and scans read from GitHub (build (d), brief #829, rules 5 and 6).

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
import subprocess  # nosec B404 - fixed argument lists only, no shell
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
WORKFLOW = (
    "jobs:\n  g:\n    steps:\n"
    f"      - uses: acme/build@{ACTION_SHA} # v4.1.0\n"
    "      - uses: acme/loose@v1\n"
    "        env:\n          GITLEAKS_VERSION: 8.30.1\n"
)
PYPROJECT = (
    '[project]\nname = "x"\ndependencies = ["rich==13.0.0", "loose>=1"]\n'
    "[dependency-groups]\ndev = [\"pytest[cov]==9.0.0 ; python_version > '3'\"]\n"
)


def git(root: Path, *args: str) -> str:
    done = subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
        ["git", *args], cwd=root, capture_output=True, text=True, check=True
    )
    return done.stdout.strip()


def env() -> dict[str, str]:
    drop = ("GITHUB_BASE_REF", "AGK_BASE", "CI", "AGK_KIT_TESTS")
    return {k: v for k, v in os.environ.items() if k not in drop}


def put(root: Path, rel: str, text: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def write_manifest(root: Path, version: str, text: str, listed=()) -> None:
    manifest = {
        "kit_version": version,
        "verbatim": ["a.txt", *listed],
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


def put_bill(root: Path) -> None:
    """The files the bill of materials and the decisions part read."""
    put(root, "config/ci-tools.txt", "# the pins\nbandit==1.2.3\n")
    put(root, "pyproject.toml", PYPROJECT)
    put(root, ".github/workflows/governance.yml", WORKFLOW)
    put(root, "docs/adr/0001-one.md", "# ADR-0001\n\n- Status: Proposed\n")
    put(root, "docs/adr/0002-two.md", "# ADR-0002\n\n- Status: Accepted\n")
    put(root, "docs/requirements.md", requirements("planned", "done"))


def requirements(first: str, second: str) -> str:
    return f"### REQ-001 — one\n\n- Status: {first}\n\n### REQ-002 — two\n\n- Status: {second}\n"


def kit_repo(
    tmp_path: Path, *, toml="1.1.0", fragment=False, tag=TAG, annotated=False, bill=False, listed=()
) -> Path:
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
    write_manifest(root, "1.1.0", "a one-one\n", listed)
    if bill:
        put_bill(root)
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
    return subprocess.run(  # nosec B603 - fixed argument list, no shell
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


def planted_key() -> str:
    return "ghp_" + "a1B2c3D4" * 5  # built at run time, invented


def fails(done: subprocess.CompletedProcess, part: str, count: int) -> list[str]:
    """The reasons of the `FAIL pack:` lines, each naming `part`, and that there are `count`."""
    lines = done.stdout.splitlines()
    assert done.returncode == 1 and len(lines) == count, done.stdout
    assert all(line.startswith(f"FAIL pack: {part} ") for line in lines), done.stdout
    return [line.removeprefix(f"FAIL pack: {part} ") for line in lines]


def test_ac8_a_form_problem_does_not_hide_a_guard_finding_in_the_same_part(repo_pack):
    """REQ-059 AC8: rule 10 (one line each; the form line explains the digest, not the guard's)."""
    root, pack = repo_pack
    planted = planted_key()

    def change(data):
        data["schema"] = 2
        data["checks"][0]["name"] = planted

    edit(pack, "tests.json", change)
    done = check(root, pack)
    assert fails(done, "tests.json", 2) == [
        "has a schema other than 1",
        "holds data the guard refuses",
    ]
    assert planted not in done.stdout


def test_ac8_a_digest_and_a_guard_finding_are_two_lines(repo_pack):
    """REQ-059 AC8: rule 10 (a part of its form still has its digest line and the guard's)."""
    root, pack = repo_pack
    edit(pack, "tests.json", lambda d: d["checks"][0].update({"name": planted_key()}))
    assert fails(check(root, pack), "tests.json", 2) == [
        "does not match its digest in the index",
        "holds data the guard refuses",
    ]


def test_ac8_two_form_problems_in_one_part_are_two_lines(repo_pack):
    """REQ-059 AC8: rule 10 (per problem, not per part)."""
    root, pack = repo_pack

    def change(data):
        data["schema"] = 2
        data.pop("date")

    edit(pack, "coverage.json", change)
    assert sorted(fails(check(root, pack), "coverage.json", 2)) == [
        "has a missing or extra field",
        "has a schema other than 1",
    ]


def test_ac8_a_part_that_is_not_json_is_still_read_by_the_guard(repo_pack):
    """REQ-059 AC8: rule 10 (the guard reads the bytes, whatever their form)."""
    root, pack = repo_pack
    planted = planted_key()
    (pack / "tests.json").write_bytes(b"\xff not json " + planted.encode("ascii") + b"\n")
    done = check(root, pack)
    assert fails(done, "tests.json", 2) == ["is not JSON", "holds data the guard refuses"]
    assert planted not in done.stdout


def test_ac8_two_problems_of_the_index_are_two_lines(repo_pack):
    """REQ-059 AC8: rule 10 (the index is collected as a part is)."""
    root, pack = repo_pack
    edit(pack, "pack.json", lambda d: d.update({"tag": "v1.0.0", "commit": "0" * 40}))
    assert fails(check(root, pack), "pack.json", 2) == [
        "names another tag",
        "names another commit",
    ]


def test_ac8_a_guard_finding_in_the_index_beside_a_form_problem_is_its_own_line(repo_pack):
    """REQ-059 AC8: rule 10 (the guard's line of the index is always printed)."""
    root, pack = repo_pack
    planted = planted_key()
    edit(pack, "pack.json", lambda d: d.update({"schema": 2, "date": planted}))
    done = check(root, pack)
    assert fails(done, "pack.json", 2) == [
        "has a schema other than 1",
        "holds data the guard refuses",
    ]
    assert planted not in done.stdout


def test_ac8_two_stray_files_are_two_lines(repo_pack):
    """REQ-059 AC8: rule 10 (each file that is not one of the six is a problem)."""
    root, pack = repo_pack
    (pack / "odd-one.json").write_text("{}\n", encoding="utf-8")
    (pack / "odd-two.json").write_text("{}\n", encoding="utf-8")
    done = check(root, pack)
    fails(done, "folder", 2)
    assert "odd" not in done.stdout


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


@pytest.mark.parametrize(
    "args",
    [[], ["check"], ["make"], ["check", "a", "b"], ["odd"], ["make", "--tag", TAG, "--out"]],
)
def test_ac8_a_bad_command_prints_the_usage_and_exits_2(tmp_path, args):
    """REQ-059 AC8: rule 10 (a command that is neither `check` nor a whole `make`)."""
    root = kit_repo(tmp_path)
    done = subprocess.run(  # nosec B603 - fixed argument list, no shell
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
    """REQ-059 AC8: rules 3 and 10 (git and `gh api --method GET`, by the shared readers)."""
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


# Build (c): `make` from git (rules 3, 8 and 9). Nothing here reads GitHub: --api-dir names no file.


def make(root: Path, out, tag=TAG, api=None) -> subprocess.CompletedProcess:
    place = str(api or Path(out).parent / "no-api")
    return subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, str(SCRIPT), "make", "--tag", tag, "--out", str(out), "--api-dir", place],
        cwd=root,
        capture_output=True,
        text=True,
        env=env(),
    )


def part(out: Path, name: str, tag=TAG) -> dict:
    return json.loads((out / tag / name).read_text(encoding="utf-8"))


def release(root: Path, version: str, *, tag: str | None = None) -> None:
    """One more release commit, tagged; a tag other than its version is not a release."""
    write_manifest(root, version, f"a {version}\n")
    put(root, "agk.toml", f'version = "{version}"\npr_mode = "flow"\n')
    plugin = {"name": "agk", "version": version}
    put(root, ".claude-plugin/plugin.json", json.dumps(plugin))
    log = (root / "CHANGELOG.md").read_text(encoding="utf-8")
    put(root, "CHANGELOG.md", f"{log}\n## {version} (2026-10-26)\n\n- #6 a change\n")
    table(root)
    commit(root, f"release {version}")
    git(root, "tag", tag or f"v{version}")


def state(root: Path) -> tuple[str, str, str, str]:
    return (
        git(root, "status", "--porcelain", "--ignored"),
        git(root, "show-ref"),
        git(root, "worktree", "list"),
        git(root, "rev-parse", "HEAD"),
    )


@pytest.fixture
def billed(tmp_path):
    return kit_repo(tmp_path, bill=True), tmp_path / "out"


def test_ac6_the_bill_names_files_pins_and_actions_at_the_tag(billed):
    """REQ-059 AC6: rule 8 (the installed files, the pinned tools and the SHA-pinned actions)."""
    root, out = billed
    make(root, out)
    assert part(out, "bom.json") == {
        "schema": 1,
        "kit_version": "1.1.0",
        "files": [{"path": "a.txt", "sha256": hashlib.sha256(b"a one-one\n").hexdigest()}],
        "tools": [
            {"name": "bandit", "pin": "1.2.3"},
            {"name": "gitleaks", "pin": "8.30.1"},
            {"name": "pytest", "pin": "9.0.0"},
            {"name": "rich", "pin": "13.0.0"},
        ],
        "actions": [{"name": "acme/build", "tag": "v4.1.0", "sha": ACTION_SHA}],
    }


def test_ac6_the_pins_are_the_ones_the_scorecard_reads(billed):
    """REQ-059 AC6: rule 8 (`as scorecard.action_pins and python_pins read them`)."""
    import scorecard  # noqa: PLC0415 - imported here as the other tests import the script

    root, out = billed
    make(root, out)
    bill = part(out, "bom.json")
    assert [(a["name"], a["tag"]) for a in bill["actions"]] == scorecard.action_pins(root)
    names = {t["name"] for t in bill["tools"]}
    assert set(scorecard.python_pins(root)) == names - {"bandit", "gitleaks"}


def test_ac6_a_file_changed_after_the_tag_gives_its_content_at_the_tag(billed):
    """REQ-059 AC6: rule 8 (read with `git show`, whatever the work tree holds)."""
    root, out = billed
    put(root, "a.txt", "changed and committed\n")
    commit(root, "after the tag")
    put(root, "a.txt", "changed and left in the work tree\n")
    make(root, out)
    digest = hashlib.sha256(b"a one-one\n").hexdigest()
    assert part(out, "bom.json")["files"][0]["sha256"] == digest


def test_ac6_a_file_the_manifest_names_that_is_missing_at_the_tag_is_refused(tmp_path):
    """REQ-059 AC6: rule 8 (naming the path class, with no pack written)."""
    root = kit_repo(tmp_path, bill=True, listed=("gone-away.txt",))
    done = make(root, tmp_path / "out")
    assert done.returncode == 1
    assert done.stdout == "refused: a file the bill names cannot be read (path class kit/)\n"
    assert not (tmp_path / "out").exists()


@pytest.mark.parametrize(
    ("rel", "name"), [("config/ci-tools.txt", "config/"), ("pyproject.toml", "pyproject.toml")]
)
def test_ac6_a_pin_file_missing_at_the_tag_is_refused(tmp_path, rel, name):
    """REQ-059 AC6: rule 8 (Q-820-2: a file the bill names includes the pin files)."""
    root = kit_repo(tmp_path, bill=True, tag="v9.9.9")
    (root / rel).unlink()
    commit(root, "no pin file")
    git(root, "tag", TAG)
    done = make(root, tmp_path / "out")
    assert done.stdout == f"refused: a file the bill names cannot be read (path class {name})\n"
    assert not (tmp_path / "out").exists()


def test_ac6_no_scanner_pin_is_no_tool_and_no_refusal(tmp_path):
    """REQ-059 AC6: rules 6 and 8 (a scan nothing configures is build (d)'s `not run`)."""
    root = kit_repo(tmp_path, bill=True, tag="v9.9.9")
    (root / ".github/workflows/governance.yml").unlink()
    commit(root, "no workflow")
    git(root, "tag", TAG)
    out = tmp_path / "out"
    assert make(root, out).returncode == 0
    assert "gitleaks" not in {t["name"] for t in part(out, "bom.json")["tools"]}


def test_ac1_an_out_inside_the_repository_that_git_does_not_ignore_is_refused(billed):
    """REQ-059 AC1: rule 2 (principle 5: naming the path class, and nothing written)."""
    root, _ = billed
    before = state(root)
    done = make(root, root / "packs")
    assert done.returncode == 1
    assert done.stdout == "refused: the folder is inside the repository (path class <out>)\n"
    assert not (root / "packs").exists() and state(root) == before


def test_ac1_an_out_inside_the_git_folder_is_refused(billed):
    """REQ-059 AC1: rules 2 and 3 (the command changes no file of the repository)."""
    root, _ = billed
    assert make(root, root / ".git" / "packs").returncode == 1
    assert not (root / ".git" / "packs").exists()


def test_ac1_an_ignored_out_inside_the_repository_is_written(billed):
    """REQ-059 AC1: rule 2 (`or git-ignored`, Q-S0052-2), for a folder that does not exist yet."""
    root, _ = billed
    put(root, ".gitignore", "packs/\n")
    commit(root, "ignore")
    assert make(root, root / "packs").returncode == 0
    assert (root / "packs" / TAG / "bom.json").is_file()


@pytest.mark.parametrize("kind", ["folder", "link"])
def test_ac1_an_existing_tag_folder_is_refused_and_left_as_it_is(billed, tmp_path, kind):
    """REQ-059 AC1: rule 3 (Q-S0052-4: never replaced)."""
    root, out = billed
    out.mkdir()
    if kind == "folder":
        (out / TAG).mkdir()
        (out / TAG / "old.txt").write_text("old\n", encoding="utf-8")
    else:
        (out / TAG).symlink_to(tmp_path / "elsewhere")
    done = make(root, out)
    assert done.returncode == 1
    assert done.stdout == "refused: the folder exists already (path class <out>/<tag>)\n"
    assert not (tmp_path / "elsewhere").exists()
    if kind == "folder":
        assert [p.name for p in (out / TAG).iterdir()] == ["old.txt"]


def test_ac1_an_out_that_cannot_be_made_is_one_line(billed, tmp_path):
    """REQ-059 AC1: rule 3 (a file where the folder would go; names the path class)."""
    root, _ = billed
    (tmp_path / "a-file").write_text("x\n", encoding="utf-8")
    done = make(root, tmp_path / "a-file")
    assert done.returncode == 1
    assert done.stdout == "refused: the folder cannot be written (path class <out>)\n"


@pytest.mark.parametrize(
    ("kwargs", "line"),
    [
        ({"toml": "1.0.9"}, "refused: the tag is not a release (agk.toml states a version other"),
        ({"fragment": True}, "refused: the tag is not a release (a fragment is left under"),
    ],
)
def test_ac2_make_refuses_a_tag_that_is_not_a_release_and_writes_nothing(tmp_path, kwargs, line):
    """REQ-059 AC2: rule 4 (the release test comes first; the line holds no version)."""
    root = kit_repo(tmp_path, bill=True, **kwargs)
    done = make(root, tmp_path / "out")
    assert done.returncode == 1 and done.stdout.startswith(line), done.stdout
    assert "1.0.9" not in done.stdout and not (tmp_path / "out").exists()


def test_ac2_make_refuses_a_repository_without_the_release_files(tmp_path):
    """REQ-059 AC2: rule 4 (`refused:` naming the path class; nothing written)."""
    root = project_repo(tmp_path)
    done = make(root, tmp_path / "out")
    assert done.returncode == 1 and done.stdout == NO_KIT
    assert not (tmp_path / "out").exists()


def test_ac6_make_opens_no_socket(billed, monkeypatch, capsys):
    """REQ-059 AC6: rule 8 (no network: a socket raises, and `make` still passes)."""
    import release_pack  # noqa: PLC0415 - the tests were written before the script

    def refuse(*args, **kwargs):
        raise AssertionError("a socket was opened")

    root, out = billed
    monkeypatch.setattr(socket, "socket", refuse)
    monkeypatch.chdir(root)
    for name in ("GITHUB_BASE_REF", "AGK_BASE", "CI"):
        monkeypatch.delenv(name, raising=False)
    argv = ["make", "--tag", TAG, "--out", str(out), "--api-dir", str(out.parent / "no-api")]
    assert release_pack.main(argv) == 0
    assert (out / TAG / "bom.json").is_file()
    capsys.readouterr()


# Build (d): the required checks and the scans (rules 5 and 6), from saved responses.

NO_SCANNER = {"kind": "dependency", "scanner": "none", "version": "none", "outcome": "not run"}


def responses(root: Path, **over) -> dict:
    url = "https://example.com/o/r/actions/runs/{}/job/1"
    data = {
        "rules-branch": [
            {"type": "pull_request", "parameters": {}},
            {
                "type": "required_status_checks",
                "parameters": {
                    "required_status_checks": [{"context": "governance"}, {"context": "proof"}]
                },
            },
        ],
        "check-runs": {
            "check_runs": [
                {
                    "id": 1,
                    "name": "governance",
                    "conclusion": "failure",
                    "details_url": url.format(76),
                },
                {
                    "id": 2,
                    "name": "governance",
                    "conclusion": "success",
                    "details_url": url.format(77),
                    "output": {"title": "12 passed", "summary": "12 passed, 0 failed in 3s"},
                },
            ]
        },
        "run-jobs-77": {"jobs": [{"steps": [{"name": "Secret scan", "conclusion": "success"}]}]},
    }
    data.update(over)
    return data


def saved(root: Path, place: Path, **over) -> Path:
    """The saved responses; a name given as None is one GitHub would not answer."""
    api = place / "api"
    api.mkdir()
    for name, value in responses(root, **over).items():
        if value is not None:
            (api / f"{name}.json").write_text(json.dumps(value), encoding="utf-8")
    return api


def made(billed_repo, tmp_path, name: str, **over) -> dict:
    root, out = billed_repo
    done = make(root, out, api=saved(root, tmp_path, **over))
    assert done.returncode == 0, done.stdout
    return part(out, name)


def test_ac1_a_pack_is_not_written_for_a_tag_that_is_not_a_release_with_api_dir(tmp_path):
    """REQ-059 AC2: rule 4 (the release test comes before any read of GitHub)."""
    root = kit_repo(tmp_path, toml="9.9.9", bill=True)
    out = tmp_path / "out"
    done = make(root, out, api=tmp_path / "none")
    assert done.returncode == 1 and done.stdout.startswith("refused: the tag is not a release")
    assert not out.exists()


def test_ac3_the_required_checks_with_their_latest_run_and_stated_counts(billed, tmp_path):
    """REQ-059 AC3: rule 5 (the latest run; a count only where stated; a missing run unknown)."""
    assert made(billed, tmp_path, "tests.json") == {
        "schema": 1,
        "checks": [
            {
                "name": "governance",
                "conclusion": "success",
                "passed": 12,
                "failed": 0,
                "skipped": "unknown",
            },
            {
                "name": "proof",
                "conclusion": "unknown",
                "passed": "unknown",
                "failed": "unknown",
                "skipped": "unknown",
            },
        ],
    }


UNKNOWN_CHECK = {
    "conclusion": "unknown",
    "passed": "unknown",
    "failed": "unknown",
    "skipped": "unknown",
}


@pytest.mark.parametrize(
    "rules", [None, {"message": "Not Found"}, [{"type": "required_status_checks"}]]
)
def test_ac3_rules_that_cannot_be_read_are_unknown_never_success(billed, tmp_path, rules):
    """REQ-059 AC3: rule 5 (an empty list would say that nothing is required)."""
    data = made(billed, tmp_path, "tests.json", **{"rules-branch": rules})
    assert data["checks"] == [{"name": "unknown", **UNKNOWN_CHECK}]


@pytest.mark.parametrize(
    "run",
    [
        {"status": "in_progress", "conclusion": None},
        {"conclusion": "success", "output": {"summary": "a run with no count"}},
    ],
)
def test_ac3_no_conclusion_is_unknown_and_no_count_is_never_zero(billed, tmp_path, run):
    """REQ-059 AC3: rule 5 (no conclusion is `unknown`; no count is `unknown`, never 0)."""
    runs = {"check_runs": [{"id": 9, "name": "governance", **run}]}
    entry = made(billed, tmp_path, "tests.json", **{"check-runs": runs})["checks"][0]
    assert entry["conclusion"] == (run["conclusion"] or "unknown")
    assert (entry["passed"], entry["failed"], entry["skipped"]) == ("unknown",) * 3


def test_ac3_a_check_run_output_is_never_copied(billed, tmp_path):
    """REQ-059 AC3: rule 11 (counts only, never the run's text)."""
    runs = {
        "check_runs": [
            {
                "id": 9,
                "name": "governance",
                "conclusion": "success",
                "output": {"text": "line-of-a-log 3 passed"},
            }
        ]
    }
    root, out = billed
    made(billed, tmp_path, "tests.json", **{"check-runs": runs})
    assert "line-of-a-log" not in (out / TAG / "tests.json").read_text()
    assert part(out, "tests.json")["checks"][0]["passed"] == 3
    assert root.is_dir()


@pytest.mark.parametrize(
    ("step", "outcome"),
    [
        ("success", "passed"),
        ("failure", "failed"),
        ("skipped", "not run"),
        ("cancelled", "unknown"),
        (None, "unknown"),
    ],
)
def test_ac4_the_secret_scan_is_the_pinned_scanner_and_its_step(billed, tmp_path, step, outcome):
    """REQ-059 AC4: rule 6 (the version at the tag, the outcome from the run's jobs)."""
    jobs = {"jobs": [{"steps": [{"name": "Secret scan", "conclusion": step}]}]}
    assert made(billed, tmp_path, "scans.json", **{"run-jobs-77": jobs}) == {
        "schema": 1,
        "scans": [
            {"kind": "secret", "scanner": "gitleaks", "version": "8.30.1", "outcome": outcome},
            NO_SCANNER,
        ],
    }


def test_ac4_the_latest_attempt_of_the_run_decides(billed, tmp_path):
    """REQ-059 AC4: rule 6 (a re-run's step replaces the earlier attempt's)."""
    step = {"name": "Secret scan", "conclusion": "{}"}
    first = {"run_attempt": 1, "steps": [{**step, "conclusion": "failure"}]}
    second = {"run_attempt": 2, "steps": [{**step, "conclusion": "success"}]}
    data = made(billed, tmp_path, "scans.json", **{"run-jobs-77": {"jobs": [second, first]}})
    assert data["scans"][0]["outcome"] == "passed"


@pytest.mark.parametrize("jobs", [None, {"jobs": [{"steps": []}]}, {"jobs": "x"}])
def test_ac4_a_job_that_cannot_be_read_is_unknown(billed, tmp_path, jobs):
    """REQ-059 AC4: rule 6 (no job or no step is `unknown`, never passed)."""
    data = made(billed, tmp_path, "scans.json", **{"run-jobs-77": jobs})
    assert data["scans"][0]["outcome"] == "unknown"


def test_ac4_no_scanner_configured_is_not_run_and_is_no_refusal(tmp_path):
    """REQ-059 AC4: rule 6 (nothing configures it: `not run`, scanner `none`, never passed)."""
    root = kit_repo(tmp_path, bill=True)
    put(root, ".github/workflows/governance.yml", "jobs: {}\n")
    commit(root, "no scanner")
    git(root, "tag", "-f", TAG)
    out = tmp_path / "out"
    assert make(root, out, api=saved(root, tmp_path)).returncode == 0
    assert part(out, "scans.json")["scans"] == [{**NO_SCANNER, "kind": "secret"}, NO_SCANNER]


def test_ac4_a_dependency_scanner_in_a_workflow_is_not_recorded_as_not_run(tmp_path):
    """REQ-059 AC4: rule 6 (`not run` is for a scan nothing configures; its outcome is unread)."""
    root = kit_repo(tmp_path, bill=True)
    put(root, ".github/workflows/deps.yml", "jobs:\n  d:\n    steps:\n      - run: pip-audit\n")
    commit(root, "a scanner")
    git(root, "tag", "-f", TAG)
    out = tmp_path / "out"
    assert make(root, out, api=saved(root, tmp_path)).returncode == 0
    assert part(out, "scans.json")["scans"][1] == {
        "kind": "dependency",
        "scanner": "pip-audit",
        "version": "unknown",
        "outcome": "unknown",
    }


@pytest.mark.parametrize("extra", [["--api-dir"], ["--bad", "x"], ["--tag", "v2"]])
def test_ac1_make_with_a_bad_option_prints_the_usage(billed, extra):
    """REQ-059 AC1: rule 3 (only the flags the rule lists, each once)."""
    root, out = billed
    argv = [sys.executable, str(SCRIPT), "make", "--tag", TAG, "--out", str(out), *extra]
    done = subprocess.run(  # nosec B603 - fixed argument list, no shell
        argv, cwd=root, capture_output=True, text=True, env=env()
    )
    assert done.returncode == 2 and done.stdout.startswith("usage:"), done.stdout
    assert not out.exists()
