"""Kit tests: uv and pnpm projects are read by their own lock (SPEC-0076 rules 8, 11 and 15 build
(h1); brief #2075, ADR-0865; REQ-083 AC7).

`pins.LOCKS` lists per runtime its lock files in order with their readers; the first present in
the runtime's folder picks the row, so a `pyproject.toml` with `uv.lock` and a `package.json` with
`pnpm-lock.yaml` are checked by `pins`, `licences`, the bill and the `parts` step instead of
failing on a missing lock. Each line names the rule and the component class, never a name or a
version. Invented names under a temporary root (example.com); no network.
"""

from __future__ import annotations

import json
import socket
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
import tomllib
from pathlib import Path

import pytest
from test_parts_step import REQUIRED, row, write_record
from test_pins import (
    NODE_PARTS,
    PY_LOCK,
    SECRET_WORDS,
    TWO_PARTS,
    check,
    gate_rows,
    no_values,
    node_files,
    project,
    record,
)

KIT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KIT_ROOT / "scripts" / "agk"))

import sbom  # noqa: E402
from gates import licences, parts, pins  # noqa: E402

UNPINNED = "a direct dependency is not pinned exactly (component class: dependency)"
STALE = "a direct dependency differs from the lock (component class: dependency)"
UNREADABLE = "the lock file is unreadable (component class: lock file)"
MISSING = "the lock file is missing (component class: lock file)"
QUIET = (*SECRET_WORDS, "example-scoped", "1.0.0")


@pytest.fixture(autouse=True)
def no_network(monkeypatch: pytest.MonkeyPatch) -> None:
    def refuse(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("a reader opened a network connection")

    monkeypatch.setattr(socket, "socket", refuse)
    monkeypatch.setattr(socket, "create_connection", refuse)
    for name in ("AGK_BASE", "GITHUB_BASE_REF", "CI"):
        monkeypatch.delenv(name, raising=False)


def uv_lock(version: str = "1.2.3") -> str:
    return (
        'version = 1\nrequires-python = ">=3.12"\n\n[[package]]\nname = "examplelib"\n'
        f'version = "{version}"\nsource = {{ registry = "https://example.com/simple" }}\n\n'
        '[[package]]\nname = "sample"\nversion = "0.0.0"\nsource = { editable = "." }\n'
    )


def uv_files(
    base: Path, deps: str = '"examplelib==1.2.3"', extra: str = "", lock: str = ""
) -> None:
    base.mkdir(parents=True, exist_ok=True)
    text = f'[project]\nname = "sample"\nversion = "0.0.0"\ndependencies = [{deps}]\n{extra}'
    (base / "pyproject.toml").write_text(text, encoding="utf-8")
    (base / "uv.lock").write_text(lock or uv_lock(), encoding="utf-8")


def uv_tree(tmp: Path, toml: str | None = None, **kw: str) -> Path:
    text = record(status="Accepted", chosen="Option A")
    root = project(tmp, text) if toml is None else project(tmp, text, toml=toml)
    uv_files(root, **kw)
    return root


def pnpm_lock(version: str = "4.21.1", head: str = "lockfileVersion: '9.0'") -> str:
    return (
        f"{head}\n\nsettings:\n  autoInstallPeers: true\n\nimporters:\n\n  .:\n    dependencies:\n"
        "      example-web:\n        specifier: 4.21.1\n        version: 4.21.1\n\npackages:\n\n"
        f"  example-web@{version}:\n    resolution: {{integrity: sha512-AAAA}}\n\n"
        "  '@example/example-scoped@1.0.0(example-web@4.21.1)':\n"
        "    resolution: {integrity: sha512-BBBB}\n\n"
        "snapshots:\n\n  example-web@9.9.9: {}\n"
    )


def pnpm_files(base: Path, deps: dict | None = None, lock: str = "") -> None:
    base.mkdir(parents=True, exist_ok=True)
    pkg = {"name": "sample", "version": "0.0.0", "dependencies": deps or {"example-web": "4.21.1"}}
    (base / "package.json").write_text(json.dumps(pkg), encoding="utf-8")
    (base / "pnpm-lock.yaml").write_text(lock or pnpm_lock(), encoding="utf-8")


def pnpm_tree(tmp: Path, toml: str | None = None, deps: dict | None = None, lock: str = "") -> Path:
    text = record(a_parts=NODE_PARTS, status="Accepted", chosen="Option A")
    root = project(tmp, text) if toml is None else project(tmp, text, toml=toml)
    pnpm_files(root, deps=deps, lock=lock)
    return root


def quiet(text: str) -> None:
    no_values(text)
    for word in QUIET:
        assert word not in text, word


def red(root: Path, wanted: str) -> None:
    result = check(root)
    assert result.returncode == 1, result.stdout + result.stderr
    assert any(ln.endswith(wanted) for ln in result.stdout.splitlines()), result.stdout
    assert all(ln.startswith("FAIL pins: SPEC-0072 rule 4") for ln in result.stdout.splitlines())
    quiet(result.stdout)


# Answers 1 to 3: a tree in step passes; the lock picks the reader.


@pytest.mark.parametrize("tree", [uv_tree, pnpm_tree])
def test_req083_ac7_a_uv_or_pnpm_tree_in_step_passes(tmp_path: Path, tree) -> None:
    result = check(tree(tmp_path))
    assert (result.returncode, result.stdout) == (0, "ok pins\n"), result.stdout + result.stderr


def test_req083_ac7_the_lock_picks_the_row(tmp_path: Path) -> None:
    for tree, reader in ((uv_tree, "uv"), (pnpm_tree, "pnpm")):
        found = pins.runtimes_of(tree(tmp_path / reader))
        assert [r.row[3] for r in found or []] == [reader]
    assert pins.STACKS["python"][2:] == ("requirements.lock", "requirements")
    assert pins.STACKS["node"][2:] == ("package-lock.json", "npm")


def test_req083_ac7_a_scoped_name_with_a_peer_suffix_is_read(tmp_path: Path) -> None:
    deps = {"example-web": "4.21.1", "@example/example-scoped": "1.0.0"}
    assert check(pnpm_tree(tmp_path, deps=deps)).stdout == "ok pins\n"


@pytest.mark.parametrize(
    ("deps", "extra"),
    [
        ('"examplelib>=1.2"', ""),
        ('"examplelib==1.2.3"', '\n[project.optional-dependencies]\nweb = ["examplelib~=1.2"]\n'),
        ('"examplelib==1.2.3"', '\n[dependency-groups]\ndev = ["examplelib>=1"]\n'),
        ('"examplelib==1.2.3"', '\n[tool.uv]\ndev-dependencies = ["examplelib"]\n'),
    ],
)
def test_req083_ac7_a_uv_range_is_unpinned(tmp_path: Path, deps: str, extra: str) -> None:
    red(uv_tree(tmp_path, deps=deps, extra=extra), UNPINNED)


def test_req083_ac7_an_include_group_is_skipped(tmp_path: Path) -> None:
    extra = (
        '\n[dependency-groups]\nlint = ["examplelib==1.2.3"]\n'
        'dev = [{include-group = "lint"}, "examplelib==1.2.3"]\n'
    )
    assert check(uv_tree(tmp_path, extra=extra)).stdout == "ok pins\n"


@pytest.mark.parametrize("spec", ["^4.21.1", "workspace:*", "catalog:", "4.x"])
def test_req083_ac7_a_pnpm_range_is_unpinned(tmp_path: Path, spec: str) -> None:
    red(pnpm_tree(tmp_path, deps={"example-web": spec}), UNPINNED)


def test_req083_ac7_a_version_that_differs_from_the_lock_is_stale(tmp_path: Path) -> None:
    red(uv_tree(tmp_path / "uv", lock=uv_lock("1.2.4")), STALE)
    red(pnpm_tree(tmp_path / "pnpm", lock=pnpm_lock("4.21.2")), STALE)


@pytest.mark.parametrize(
    "lock",
    ["[[[ not toml", 'version = 1\npackage = "none"\n', "version = 1\n", "\xff\xfe"],
)
def test_req083_ac7_an_unreadable_uv_lock(tmp_path: Path, lock: str) -> None:
    root = uv_tree(tmp_path)
    (root / "uv.lock").write_bytes(lock.encode("latin-1"))
    red(root, UNREADABLE)


@pytest.mark.parametrize(
    "lock",
    [
        pnpm_lock(head="lockfileVersion: '6.0'"),
        pnpm_lock(head="lockfileVersion: 5.4"),
        "lockfileVersion: '9.0'\n\nimporters: {}\n",
        "\xff\xfe",
    ],
)
def test_req083_ac7_an_unreadable_pnpm_lock(tmp_path: Path, lock: str) -> None:
    root = pnpm_tree(tmp_path)
    (root / "pnpm-lock.yaml").write_bytes(lock.encode("latin-1"))
    red(root, UNREADABLE)


# Answer 6: two locks of one runtime read today's; none still fails naming the lock file.


def test_req083_ac7_two_locks_read_todays_lock(tmp_path: Path) -> None:
    node = pnpm_tree(tmp_path / "node", lock=pnpm_lock(head="lockfileVersion: '6.0'"))
    node_files(node)
    py = uv_tree(tmp_path / "py", lock="[[[ not toml")
    (py / "requirements.lock").write_text(PY_LOCK, encoding="utf-8")
    for root, reader in ((node, "npm"), (py, "requirements")):
        assert [r.row[3] for r in pins.runtimes_of(root) or []] == [reader]
        assert check(root).stdout == "ok pins\n"


def test_req083_ac7_no_lock_and_a_lock_in_a_subfolder_still_fail(tmp_path: Path) -> None:
    root = uv_tree(tmp_path)
    (root / "sub").mkdir()
    (root / "uv.lock").rename(root / "sub" / "uv.lock")
    red(root, MISSING)
    result = check(root)
    assert "requirements.lock" not in result.stdout


def test_req083_ac7_two_runtimes_each_read_their_own_lock(tmp_path: Path) -> None:
    root = project(tmp_path, record(a_parts=TWO_PARTS, status="Accepted", chosen="Option A"))
    pnpm_files(root)
    uv_files(root / "service")
    found = pins.runtimes_of(root) or []
    assert [(r.row[3], r.folder) for r in found] == [("pnpm", ""), ("uv", "service")]
    assert check(root).stdout == "ok pins\n"


# Answer 5: the settings beside the readers.


def test_req083_ac7_no_work_type_is_not_run(tmp_path: Path) -> None:
    root = uv_tree(tmp_path, toml="")
    assert check(root).stdout == "pins: not run: no stack chosen\n"
    assert gate_rows(root) == []


def test_req083_ac7_an_adopted_uv_project_drops_the_old_finding(tmp_path: Path) -> None:
    root = uv_tree(tmp_path)
    (root / "uv.lock").unlink()
    text = (root / "agk.toml").read_text(encoding="utf-8")
    (root / "agk.toml").write_text('mode = "adopt"\n' + text, encoding="utf-8")
    rows = gate_rows(root)
    assert (True, "pins (baseline)") in rows, rows
    held = (root / "config" / "agk-baseline" / "pins.txt").read_text(encoding="utf-8")
    assert "requirements.lock" in held, held
    (root / "uv.lock").write_text(uv_lock(), encoding="utf-8")
    assert all(passed for passed, _ in gate_rows(root)), gate_rows(root)
    (root / "uv.lock").write_text(uv_lock("1.2.4"), encoding="utf-8")
    rows = gate_rows(root)
    assert any(p is False and "SPEC-0072 rule 7" in line for p, line in rows), rows


# Answer 4: licences, the bill and the parts step read the new locks.


def test_req083_ac7_licences_read_both_locks(tmp_path: Path) -> None:
    assert licences.CLASSES["uv"] == "python" and licences.CLASSES["pnpm"] == "node"
    uv = uv_tree(tmp_path / "uv")
    (reader, text, option, held), *rest = licences.locks_of(uv) or [None]
    assert (reader, held, rest) == ("uv", "uv.lock", [])
    assert licences.components(reader, text, option) == [
        ("python", "examplelib", "1.2.3", "MIT"),
        ("python", "sample", "0.0.0", ""),
    ]
    pnpm = pnpm_tree(tmp_path / "pnpm")
    (reader, text, option, held), *rest = licences.locks_of(pnpm) or [None]
    assert (reader, held, rest) == ("pnpm", "pnpm-lock.yaml", [])
    assert licences.components(reader, text, option) == [
        ("node", "@example/example-scoped", "1.0.0", ""),
        ("node", "example-web", "4.21.1", "MIT"),
    ]
    out = subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, str(KIT_ROOT / "scripts/agk/gates/licences.py"), "--root", str(pnpm)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert "unknown" in out.stdout, out.stdout + out.stderr
    quiet(out.stdout)


def git(root: Path, *args: str) -> None:
    subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
        ["git", "-c", "user.name=t", "-c", "user.email=t@example.com", *args],
        cwd=root,
        check=True,
        capture_output=True,
    )


@pytest.mark.parametrize(
    ("tree", "purl"),
    [
        (uv_tree, "pkg:pypi/examplelib@1.2.3"),
        (pnpm_tree, "pkg:npm/%40example/example-scoped@1.0.0"),
    ],
)
def test_req083_ac7_the_bill_lists_their_components(tmp_path: Path, tree, purl: str) -> None:
    root = tree(tmp_path)
    git(root, "init", "-q")
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "tree")
    config = tomllib.loads((root / "agk.toml").read_text(encoding="utf-8"))
    commit = sbom.resolve(root, "HEAD")
    items = sbom.lock_components(root, commit, sbom.chosen_at(root, commit, config))
    assert purl in {i.get("purl") for i in items}, items


@pytest.mark.parametrize("tree", [uv_tree, pnpm_tree])
def test_req083_ac7_the_parts_step_reads_both(tmp_path: Path, tree) -> None:
    root = tree(tmp_path / "named", toml=REQUIRED)
    name, version = ("examplelib", "1.2.3") if tree is uv_tree else ("example-web", "4.21.1")
    write_record(root, {"stack": row(name, version)})
    assert parts.skipped(root) is None
    assert parts.evaluate(root)[0] == []
    other = tree(tmp_path / "unnamed", toml=REQUIRED)
    write_record(other, {"stack": row("example-clock", "2.0.0", "time")})
    fails = parts.evaluate(other)[0]
    assert fails and all(cls in ("record part", "dependency", "record row") for _, cls, _ in fails)
    quiet(repr([(w, c) for w, c, _ in fails]))


def test_req083_ac7_the_parts_step_reads_two_runtimes(tmp_path: Path) -> None:
    text = record(a_parts=TWO_PARTS, status="Accepted", chosen="Option A")
    root = project(tmp_path, text, toml=REQUIRED)
    pnpm_files(root)
    uv_files(root / "service")
    write_record(root, {"node": row("example-web", "4.21.1"), "python": row("examplelib", "1.2.3")})
    assert parts.skipped(root) is None
    assert parts.evaluate(root)[0] == []


# Answer 9: the class stays closed: every lock the signals name has a reader or is listed here.

NO_READER = {"poetry.lock", "pdm.lock", "bun.lock", "yarn.lock", "npm-shrinkwrap.json"}


def test_req083_ac7_every_signalled_lock_has_a_reader_or_is_listed() -> None:
    signals = tomllib.loads((KIT_ROOT / "config" / "stack-signals.toml").read_text("utf-8"))
    named = {
        lock
        for stack in signals["stack"]
        if stack["name"] in ("python-pyproject", "node")
        for lock in stack["locks"]
    }
    read = {lock for rows in pins.LOCKS.values() for lock, _ in rows}
    assert named <= read | NO_READER, named - read - NO_READER
    assert not read & NO_READER
    assert {k: rows[0] for k, rows in pins.LOCKS.items()} == {
        k: v[2:] for k, v in pins.STACKS.items()
    }
    assert set(licences.CLASSES) == {reader for rows in pins.LOCKS.values() for _, reader in rows}
