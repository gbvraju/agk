"""The evidence check sees the same bytes as the conductor's governance run (brief #1291, ADR-0550).

`evidence.py check` makes its worktree of the head and runs governance there. On a Windows cloud PC
with `core.autocrlf=true` in the person's git configuration, that worktree checked the text files
out with CRLF line ends, while the conductor's own run (`git worktree add`, then `env -i PATH HOME=
<scratch> make ... agk-governance`) saw the committed LF bytes: `check_design.py` then failed rule 5
(the runtime's hash), rule 9 (a signed-off version's digest) and rule 15 (imported files against
`manifest.json`) in the evidence run only, and the check reported `differs` on a correct record.
Measured on Linux in this file's fixture before the change: `core.autocrlf=true` reproduces all
three rules; `core.autocrlf=false`, `core.eol=crlf` alone and a 150-character temporary path do
not.

After the change the evidence check adds its worktree with `-c core.autocrlf=false -c
core.eol=lf`, and runs governance with the conductor's environment (`PATH`, a scratch `HOME`,
`AGK_BASE`); and the digests of rules 9 and 15 (`design_signoff.digest`, `design_import`'s file
reading) use a file's committed bytes when the checkout changed only its line ends, so a person's
own CRLF checkout agrees with CI. Invented data only (example.com); no network.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
from pathlib import Path

import pytest
from test_prepush import TOML, path_with, scanner

KIT = Path(__file__).resolve().parents[2]
SCRIPTS = KIT / "scripts" / "agk"
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import design_import  # noqa: E402
import design_signoff  # noqa: E402
import test_check_design_prototype as proto  # noqa: E402
import test_design_import as imp  # noqa: E402

CHECK = SCRIPTS / "check_design.py"
DESIGN = SCRIPTS / "design.py"
V1 = "docs/design/prototype/v1"
I1 = "docs/design/imported/i1"
PAGE = f"{V1}/book-list--default.html"
LINE = re.compile(r"^Evidence check: (agrees|differs), head ([0-9a-f]{12})", re.M)
MAP = (
    "# Screen map of i1\n\n"
    "- index.html -> out: an early page the customer replaced\n"
    "- empty.html -> out: an early page the customer replaced\n"
    "- img/sketch.png -> out: an early sketch\n"
    "- flows.pdf#page=1 -> out: the flow overview\n"
    "- flows.pdf#page=2 -> out: the release notes\n"
)
LINK = "https://example.com/acme/books/pull/12#issuecomment-345"
GOVERNANCE = f'agk-governance:\n\t@"{sys.executable}" "{CHECK}"\n'


# --- the fixture ---------------------------------------------------------------------------------


@pytest.fixture
def outside(tmp_path_factory) -> Path:
    """A folder outside the fixture repository: configs, records, locks, worktrees."""
    return tmp_path_factory.mktemp("outside")


def person_config(outside: Path, autocrlf: str) -> Path:
    """The person's own git configuration (`~/.gitconfig`), with `core.autocrlf` as given."""
    path = outside / f"gitconfig-{autocrlf}"
    path.write_text(f"[core]\n\tautocrlf = {autocrlf}\n", encoding="utf-8")
    return path


def person_env(outside: Path, autocrlf: str) -> dict[str, str]:
    config = person_config(outside, autocrlf)
    temp = outside / "tmp"
    temp.mkdir(exist_ok=True)
    return {"GIT_CONFIG_GLOBAL": str(config), "TMPDIR": str(temp), "TMP": str(temp)}


def signoffs(digest: str) -> str:
    return (
        "# Design sign-offs\n\n"
        "| kind | version | digest | head | date | comment |\n|---|---|---|---|---|---|\n"
        f"| design | v1 | {digest} | {'0' * 40} | 2026-11-03 | {LINK} |\n"
    )


def design_files(root: Path, outside: Path) -> None:
    """A kit prototype v1 signed off by its digest, and an imported i1 with its manifest."""
    proto.version(root)
    source = imp.prototype(outside / "customer")
    made = subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, str(DESIGN), "import", str(source), "--root", str(root)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert made.returncode == 0, made.stdout + made.stderr
    (root / I1 / "map.md").write_text(MAP, encoding="utf-8")
    digest = design_signoff.version_digest(root, "v1")
    (root / "docs" / "design" / "signoffs.md").write_text(signoffs(digest), encoding="utf-8")


def project(repo, outside: Path) -> None:
    """A project whose governance is the kit's `check_design.py`, on a branch off main."""
    design_files(repo.root, outside)
    toml = TOML + f"lock_dir = '{outside / 'locks'}'\n"
    repo.commit({"agk.toml": toml, "agk.mk": GOVERNANCE, "Makefile": "lint:\n\t@true\n"}, "base")
    repo.branch("feature")
    repo.commit({"src/a.txt": "b\n"}, "change")


def change_signed_off_page(repo) -> None:
    """A real change to a file of the signed-off version, committed."""
    text = (repo.root / PAGE).read_text(encoding="utf-8")
    repo.commit({PAGE: text.replace("</h1>", " today</h1>", 1)}, "edit a signed-off page")


def conductor_run(repo, outside: Path, name: str) -> tuple[int, list[str]]:
    """The conductor's run of the local-mode guide: `git worktree add <scratch> <sha>`, then
    `env -i PATH="$PATH" HOME=<scratch> AGK_BASE=<base> make -C <scratch> -f agk.mk
    agk-governance`."""
    scratch = outside / f"conductor-{name}"
    home = outside / f"conductor-home-{name}"
    home.mkdir()
    clean = {"PATH": os.environ["PATH"], "HOME": str(home)}
    head = repo.git("rev-parse", "HEAD").strip()
    subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
        ["git", "worktree", "add", "--detach", "-q", str(scratch), head],
        cwd=repo.root,
        env=clean,
        check=True,
    )
    try:
        proc = subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
            ["make", "-C", str(scratch), "-f", "agk.mk", "agk-governance"],
            env={**clean, "AGK_BASE": repo.git("rev-parse", "main").strip()},
            capture_output=True,
            text=True,
            check=False,
        )
    finally:
        repo.git("worktree", "remove", "--force", str(scratch))
    return proc.returncode, design_lines(proc.stdout)


def design_lines(out: str) -> list[str]:
    return sorted(line for line in out.splitlines() if "FAIL design" in line or line == "ok design")


def record(repo, outside: Path, env: dict[str, str]) -> Path:
    """A record that prepush writes for the head, in the person's own checkout."""
    path = outside / "record.json"
    scan = scanner(outside / "bin", 0)
    made = repo.run("prepush.py", "--record", str(path), PATH=path_with(scan), **env)
    assert made.returncode == 0, made.stdout + made.stderr
    return path


def hand_record(repo, outside: Path) -> Path:
    """A record of a passing run, written by hand, for a head whose governance fails."""
    head = repo.git("rev-parse", "HEAD").strip()
    data = {
        "schema": 1,
        "head": head,
        "base": repo.git("rev-parse", "main").strip(),
        "started": "2026-11-14T00:00:00Z",
        "tree_clean": True,
        "versions": {"python3": "3.12.0"},
        "steps": [
            {
                "name": "lint",
                "outcome": "ok",
                "not_run": False,
                "argv": ["make", "lint"],
                "cwd": ".",
                "exit": 0,
                "seconds": 0.1,
                "output_sha256": hashlib.sha256(b"").hexdigest(),
                "output_bytes": 0,
            }
        ],
        "not_run": [],
        "result": "passed",
    }
    path = outside / "hand-record.json"
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def evidence(repo, outside: Path, path: Path, env: dict[str, str]):
    scan = scanner(outside / "bin", 0)
    return repo.run("evidence.py", "check", str(path), PATH=path_with(scan), **env)


def crlf_checkout(repo, outside: Path, name: str) -> Path:
    """A worktree of HEAD checked out with `core.autocrlf=true`, as a Windows person's would be."""
    tree = outside / f"crlf-{name}"
    repo.git("-c", "core.autocrlf=true", "worktree", "add", "--detach", "-q", str(tree), "HEAD")
    assert b"\r\n" in (tree / PAGE).read_bytes()  # the checkout converted the line ends
    return tree


# --- (a) a correct record agrees with autocrlf=true ----------------------------------------------


def test_a_correct_record_agrees_with_autocrlf_true(repo, outside):
    """REQ-039: brief #1291 answer 3 (a): `core.autocrlf=true` in the person's configuration."""
    project(repo, outside)
    env = person_env(outside, "true")
    proc = evidence(repo, outside, record(repo, outside, env), env)
    found = LINE.search(proc.stdout)
    assert found and found.group(1) == "agrees", proc.stdout + proc.stderr
    assert proc.returncode == 0
    assert "governance ok" in proc.stdout
    assert "rule 9" not in proc.stdout and "rule 15" not in proc.stdout


def test_a_correct_record_agrees_with_autocrlf_false(repo, outside):
    """REQ-039: brief #1291 answer 3 (a): and with `core.autocrlf=false`, as before."""
    project(repo, outside)
    env = person_env(outside, "false")
    proc = evidence(repo, outside, record(repo, outside, env), env)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert LINE.search(proc.stdout).group(1) == "agrees"


def test_the_worktree_is_added_with_the_committed_line_ends():
    """REQ-039: brief #1291 answer 2: the `git worktree add` of the evidence check overrides the
    person's line-ending settings."""
    import evidence

    assert evidence.CHECKOUT == ("-c", "core.autocrlf=false", "-c", "core.eol=lf")
    text = (SCRIPTS / "evidence.py").read_text(encoding="utf-8")
    body = text.split("\ndef in_worktree(", 1)[1].split("\ndef ", 1)[0]
    assert 'git(root, *CHECKOUT, "worktree", "add"' in body


def test_governance_runs_with_the_conductors_environment(repo, outside, monkeypatch):
    """REQ-039: brief #1291 answer 2: governance gets PATH, a scratch HOME and AGK_BASE, not the
    person's whole environment (their HOME, their git configuration, their tokens)."""
    seen = outside / "env.txt"
    project(repo, outside)
    repo.commit({"agk.mk": f"agk-governance:\n\t@env > '{seen}'\n"}, "governance prints its env")
    env = person_env(outside, "true")
    env["AGK_EXAMPLE_TOKEN"] = "invented-value"  # nosec B105 - an invented name and value
    path = hand_record(repo, outside)
    proc = evidence(repo, outside, path, env)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    names = dict(
        line.split("=", 1) for line in seen.read_text(encoding="utf-8").splitlines() if "=" in line
    )
    assert "AGK_EXAMPLE_TOKEN" not in names
    assert "GIT_CONFIG_GLOBAL" not in names
    assert names["AGK_BASE"] == repo.git("rev-parse", "main").strip()
    assert names["HOME"] != os.environ.get("HOME")
    assert not Path(names["HOME"]).exists()  # the scratch home goes with the worktree


# --- (b) a really changed signed-off file still fails rule 9 in both runs ------------------------


@pytest.mark.parametrize("autocrlf", ["true", "false"])
def test_a_really_changed_signed_off_file_fails_rule_9_in_both_runs(repo, outside, autocrlf):
    """REQ-039: brief #1291 answer 3 (b)."""
    project(repo, outside)
    change_signed_off_page(repo)
    code, lines = conductor_run(repo, outside, autocrlf)
    assert code != 0
    assert any("rule 9: docs/design/prototype/v1" in line for line in lines), lines
    env = person_env(outside, autocrlf)
    proc = evidence(repo, outside, hand_record(repo, outside), env)
    assert proc.returncode == 1, proc.stdout + proc.stderr
    assert LINE.search(proc.stdout).group(1) == "differs"
    assert "rule 9: docs/design/prototype/v1: a signed-off version changed" in proc.stdout


# --- (c) the same check_design result in both runs -----------------------------------------------


@pytest.mark.parametrize("autocrlf", ["true", "false"])
@pytest.mark.parametrize("changed", [False, True])
def test_the_conductors_run_and_the_evidence_run_give_the_same_result(
    repo, outside, autocrlf, changed
):
    """REQ-039: brief #1291 answer 3 (c): the same `check_design.py` lines on the same head."""
    project(repo, outside)
    if changed:
        change_signed_off_page(repo)
    code, lines = conductor_run(repo, outside, f"{autocrlf}-{changed}")
    env = person_env(outside, autocrlf)
    proc = evidence(repo, outside, hand_record(repo, outside), env)
    assert (code == 0) == (proc.returncode == 0), proc.stdout + proc.stderr
    if code == 0:
        assert lines == ["ok design"]
        assert "governance ok" in proc.stdout
    else:
        assert design_lines(proc.stdout) == lines


# --- the digests of rules 9 and 15 read committed bytes ------------------------------------------


def test_a_crlf_checkout_gives_the_committed_digest(repo, outside):
    """REQ-039: brief #1291 answer 2: rule 9's digest of a version is the same in a CRLF checkout
    as in the LF one, so a sign-off taken on either agrees with CI."""
    project(repo, outside)
    tree = crlf_checkout(repo, outside, "digest")
    assert design_signoff.version_digest(tree, "v1") == design_signoff.version_digest(
        repo.root, "v1"
    )
    assert design_signoff.frozen_problems(tree) == []


def test_a_crlf_checkout_of_an_imported_version_matches_its_manifest(repo, outside):
    """REQ-039: brief #1291 answer 2: rule 15's size and SHA-256 are of the committed bytes."""
    project(repo, outside)
    tree = crlf_checkout(repo, outside, "import")
    assert b"\r\n" in (tree / I1 / "files" / "index.html").read_bytes()
    assert design_import.imported_problems(tree) == []


def test_a_crlf_checkout_still_sees_a_real_change(repo, outside):
    """REQ-039: brief #1291 answer 3 (b): a change beyond the line ends, made in the CRLF checkout
    and not committed, still fails rules 9 and 15."""
    project(repo, outside)
    tree = crlf_checkout(repo, outside, "edit")
    page = tree / PAGE
    page.write_bytes(page.read_bytes().replace(b"</h1>", b" today</h1>", 1))
    found = tree / I1 / "files" / "index.html"
    found.write_bytes(found.read_bytes() + b"<p>more</p>\r\n")
    assert any(
        p.startswith("rule 9: docs/design/prototype/v1")
        for p in design_signoff.frozen_problems(tree)
    )
    assert any("files/index.html" in p for p in design_import.imported_problems(tree))


def test_a_file_committed_with_crlf_keeps_its_own_bytes(repo, outside):
    """REQ-039: brief #1291 answer 2: committed CRLF bytes are the committed bytes; the digest is
    of them, as before."""
    project(repo, outside)
    page = repo.root / PAGE
    page.write_bytes(page.read_bytes().replace(b"\n", b"\r\n"))
    repo.git("-c", "core.autocrlf=false", "add", PAGE)
    repo.git("-c", "core.autocrlf=false", "commit", "-q", "-m", "a page with CRLF")
    raw = hashlib.sha256(page.read_bytes()).hexdigest()
    assert design_signoff._file_hash(page) == raw
    assert any(p.startswith("rule 9:") for p in design_signoff.frozen_problems(repo.root))


def test_an_lf_folder_outside_git_is_read_as_before(tmp_path):
    """REQ-039: brief #1291 contexts (github, personal): outside a repository, and in an LF
    checkout, the digest is that of the bytes on disk, unchanged."""
    proto.version(tmp_path)
    page = tmp_path / PAGE
    page.write_bytes(page.read_bytes().replace(b"\n", b"\r\n"))
    files = [p for p in (tmp_path / V1).rglob("*") if p.is_file()]
    lines = sorted(
        f"{p.relative_to(tmp_path).as_posix()} {hashlib.sha256(p.read_bytes()).hexdigest()}"
        for p in files
    )
    expected = hashlib.sha256("".join(f"{line}\n" for line in lines).encode("utf-8")).hexdigest()
    assert design_signoff.version_digest(tmp_path, "v1") == expected
