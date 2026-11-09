"""Tests of `front_door.py` build (k): the derived playbook and its check (SPEC-0048 22, 24, 25).

REQ-055 AC8. `derive-write` writes one engagement's skeleton from `default`, the named modules and
the research record's slug, which passes the checks and holds every `default` gate; it writes
nothing else, never under `kit/` or `agk.toml`, and the kit's manifest lists no derived playbook. A
gate of a derived playbook with neither `source` nor `basis = "expected"` fails. `check-playbook
--date` flags a gate source more than 180 days old, without failing, and fails when a design cites
that playbook; 180 days passes. Fixtures in `tmp_path` only: invented data (`example.com`), no
network (a socket stub raises).
"""

from __future__ import annotations

import json
import socket
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
import tomllib
from pathlib import Path

import pytest

KIT_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = KIT_ROOT / "scripts" / "agk"
SCRIPT = SCRIPTS / "front_door.py"
CHECK = SCRIPTS / "check_playbooks.py"
sys.path.insert(0, str(SCRIPTS))

import check_playbooks  # noqa: E402
import playbook_format  # noqa: E402

TODAY = "2026-11-08"
DAY_180 = "2026-05-12"  # 180 days before TODAY
DAY_181 = "2026-05-11"  # 181 days before TODAY
SLUG = "chat-store-plugin"
REL = f"config/playbooks/{SLUG}.toml"
URL = "https://standards.example.com/signing"
CRITERIA = (
    "capability fit",
    "cost",
    "licence",
    "data handling and residency",
    "maturity",
    "integration effort",
    "lock-in",
)


def record_text() -> str:
    lines = ["# Research: A chat store plugin", ""]
    for name, host in (("Alpha", "alpha"), ("Beta", "beta")):
        lines += [f"## Option: {name}", ""]
        lines += [f"- Source: https://{host}.example.com/docs (accessed 2026-10-01)", ""]
    lines += ["## Criteria", "", "| Criterion | Alpha | Beta |", "| --- | --- | --- |"]
    lines += [f"| {c} | invented | invented |" for c in CRITERIA]
    lines += ["", "## Recommendation", "", "Alpha, for its fit (proposal).", ""]
    return "\n".join(lines)


def write(root: Path, rel: str, text: str) -> Path:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


@pytest.fixture
def root(tmp_path: Path) -> Path:
    for name in ("default", "web-app"):
        source = KIT_ROOT / "config" / "playbooks" / f"{name}.toml"
        write(tmp_path, f"config/playbooks/{name}.toml", source.read_text(encoding="utf-8"))
    write(tmp_path, f"docs/research/{SLUG}.md", record_text())
    return tmp_path


def run(root: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, str(SCRIPT), *args, "--root", str(root)],
        capture_output=True,
        text=True,
        cwd=root,
        check=False,
    )


def governance(root: Path) -> subprocess.CompletedProcess:
    return subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, str(CHECK), "--root", str(root)],
        capture_output=True,
        text=True,
        cwd=root,
        check=False,
    )


def derive(root: Path, *extra: str) -> subprocess.CompletedProcess:
    return run(root, "derive-write", "--slug", SLUG, *extra)


def check(root: Path, date: str = TODAY) -> subprocess.CompletedProcess:
    return run(root, "check-playbook", "--date", date)


def tree(root: Path) -> dict[str, bytes]:
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob("*") if p.is_file()}


GATE = """
[[gates]]
id = "store-signing"
kind = "judgement"
text = "The plugin's store listing is reviewed."
owner_only = false
"""


def with_gate(root: Path, extra: str, gate: str = GATE) -> Path:
    """The derived skeleton with one gate of its own."""
    assert derive(root).returncode == 0
    path = root / REL
    text = path.read_text(encoding="utf-8").replace("gates = []\n", "")
    path.write_text(text + gate + extra, encoding="utf-8")
    return path


def sourced(root: Path, accessed: str) -> Path:
    return with_gate(root, f'source = "{URL} (accessed {accessed})"\n')


def default_ids() -> set[str]:
    data = tomllib.loads((KIT_ROOT / "config/playbooks/default.toml").read_text(encoding="utf-8"))
    return {gate["id"] for gate in data["gates"]}


# --- derive-write (rule 22) ---


def test_skeleton_passes_both_checks_and_holds_every_default_gate(root: Path) -> None:
    done = derive(root)
    assert done.returncode == 0, done.stdout + done.stderr
    assert REL in done.stdout
    assert governance(root).returncode == 0
    checked = check(root)
    assert checked.returncode == 0, checked.stdout
    gates, _, found = check_playbooks.composed(root / REL, root)
    assert found == []
    assert default_ids() <= {gate["id"] for gate in gates}


def test_skeleton_holds_the_discovery_ids_and_its_slug(root: Path) -> None:
    assert derive(root).returncode == 0
    data = tomllib.loads((root / REL).read_text(encoding="utf-8"))
    assert data["work_type"] == SLUG
    assert set(playbook_format.DISCOVERY_IDS) <= {row["id"] for row in data["discovery"]}


def test_a_named_module_is_taken_whole(root: Path) -> None:
    assert derive(root, "--modules", "web-app").returncode == 0
    data = tomllib.loads((root / REL).read_text(encoding="utf-8"))
    assert data["modules"] == ["web-app"]
    module = tomllib.loads((root / "config/playbooks/web-app.toml").read_text(encoding="utf-8"))
    gates, evidence, found = check_playbooks.composed(root / REL, root)
    assert found == []
    assert {gate["id"] for gate in module["gates"]} <= {gate["id"] for gate in gates}
    assert set(module["evidence"]) <= set(evidence)
    assert check(root).returncode == 0


def test_a_module_that_is_not_shipped_writes_nothing(root: Path) -> None:
    before = tree(root)
    done = derive(root, "--modules", "zz-unshipped")
    assert done.returncode == 1
    assert "rule 23" in done.stdout and "modules" in done.stdout
    assert "zz-unshipped" not in done.stdout
    assert tree(root) == before


@pytest.mark.parametrize("name", ["web-app", "default", "pilot"])
def test_a_shipped_name_is_refused(root: Path, name: str) -> None:
    write(root, f"docs/research/{name}.md", record_text())
    before = tree(root)
    done = run(root, "derive-write", "--slug", name)
    assert done.returncode == 1
    assert "rule 22" in done.stdout and "--slug" in done.stdout
    assert tree(root) == before


@pytest.mark.parametrize("name", ["../kit/x", "Upper", "a/b", "kit/manifest"])
def test_a_slug_that_is_not_a_slug_is_refused(root: Path, name: str) -> None:
    before = tree(root)
    done = run(root, "derive-write", "--slug", name)
    assert done.returncode == 1
    assert "--slug" in done.stdout and name not in done.stdout
    assert tree(root) == before


def test_no_research_record_writes_nothing(root: Path) -> None:
    (root / f"docs/research/{SLUG}.md").unlink()
    before = tree(root)
    done = derive(root)
    assert done.returncode == 1
    assert "rule 22" in done.stdout and f"docs/research/{SLUG}.md" in done.stdout
    assert tree(root) == before


def test_a_record_that_fails_rule_6_writes_nothing(root: Path) -> None:
    write(root, f"docs/research/{SLUG}.md", "# Research: Thin\n")
    before = tree(root)
    done = derive(root)
    assert done.returncode == 1
    assert "rule 6" in done.stdout
    assert tree(root) == before


def test_no_default_playbook_writes_nothing(root: Path) -> None:
    (root / "config/playbooks/default.toml").unlink()
    before = tree(root)
    done = derive(root)
    assert done.returncode == 1
    assert "rule 22" in done.stdout and "default.toml" in done.stdout
    assert tree(root) == before


def test_an_existing_playbook_is_never_overwritten(root: Path) -> None:
    write(root, REL, "held\n")
    before = tree(root)
    done = derive(root)
    assert done.returncode == 1
    assert "rule 22" in done.stdout
    assert tree(root) == before


def test_it_writes_one_file_and_never_kit_or_agk_toml(root: Path) -> None:
    write(root, "agk.toml", 'version = "0.0.1"\n')
    write(root, "kit/notes.txt", "invented\n")
    before = tree(root)
    assert derive(root).returncode == 0
    after = tree(root)
    assert set(after) - set(before) == {REL}
    assert {k: after[k] for k in before} == before


def test_the_kit_itself_holds_no_derived_playbook(root: Path) -> None:
    write(root, "kit/manifest.json", "{}\n")
    before = tree(root)
    done = derive(root)
    assert done.returncode == 1
    assert "rule 22" in done.stdout and "kit/" in done.stdout
    assert tree(root) == before


def test_the_manifest_lists_no_derived_playbook() -> None:
    manifest = json.loads((KIT_ROOT / "kit" / "manifest.json").read_text(encoding="utf-8"))
    listed = [p for p in manifest["verbatim"] if p.startswith("config/playbooks/")]
    assert listed
    allowed = {*playbook_format.WORK_TYPES, playbook_format.BASE}
    assert {Path(p).stem for p in listed} <= allowed


# --- the gates of a derived playbook (rule 22) ---


def test_a_gate_with_neither_source_nor_expected_fails_both_checks(root: Path) -> None:
    with_gate(root, "")
    for done in (governance(root), check(root)):
        assert done.returncode == 1
        assert "rule 22" in done.stdout and REL in done.stdout


def test_a_dated_source_passes(root: Path) -> None:
    sourced(root, "2026-10-01")
    assert governance(root).returncode == 0
    assert check(root).returncode == 0


def test_basis_expected_passes(root: Path) -> None:
    with_gate(root, 'basis = "expected"\n')
    assert governance(root).returncode == 0
    assert check(root).returncode == 0


@pytest.mark.parametrize(
    "extra",
    [
        f'source = "{URL}"\n',
        f'source = "{URL} (accessed 2026-13-45)"\n',
        'source = "not-a-url (accessed 2026-10-01)"\n',
        'basis = "measured"\n',
    ],
    ids=["no-date", "bad-date", "no-url", "basis-measured"],
)
def test_a_malformed_source_or_basis_fails_naming_no_value(root: Path, extra: str) -> None:
    with_gate(root, extra)
    done = governance(root)
    assert done.returncode == 1
    assert "rule 22" in done.stdout
    assert "not-a-url" not in done.stdout and "2026-13-45" not in done.stdout


def test_a_shipped_playbook_may_not_carry_a_gate_source(root: Path) -> None:
    path = root / "config/playbooks/default.toml"
    text = path.read_text(encoding="utf-8")
    old = 'id = "tests-first"\n'
    path.write_text(text.replace(old, old + f'source = "{URL} (accessed 2026-10-01)"\n'))
    done = governance(root)
    assert done.returncode == 1
    assert "outside the format" in done.stdout


def test_a_slug_with_no_research_record_is_still_an_unknown_work_type(root: Path) -> None:
    sourced(root, "2026-10-01")
    (root / f"docs/research/{SLUG}.md").unlink()
    done = governance(root)
    assert done.returncode == 1
    assert "is not one of the work types" in done.stdout


def test_a_derived_playbook_cannot_weaken_a_module_gate(root: Path) -> None:
    module = tomllib.loads((root / "config/playbooks/web-app.toml").read_text(encoding="utf-8"))
    held = next(gate for gate in module["gates"] if gate["kind"] == "check")
    assert derive(root, "--modules", "web-app").returncode == 0
    path = root / REL
    weaker = (
        f'\n[[gates]]\nid = "{held["id"]}"\nkind = "judgement"\ntext = "Weaker."\n'
        f'owner_only = false\nbasis = "expected"\n'
    )
    path.write_text(
        path.read_text(encoding="utf-8").replace("gates = []\n", "") + weaker, encoding="utf-8"
    )
    done = check(root)
    assert done.returncode == 1
    assert "rule 21" in done.stdout


# --- check-playbook and freshness (rule 25) ---


def cite(root: Path) -> None:
    write(root, f"docs/design/architecture/{SLUG}.md", f"# Architecture\n\nUses `{REL}`.\n")


def test_181_days_is_flagged_and_does_not_fail(root: Path) -> None:
    sourced(root, DAY_181)
    done = check(root)
    assert done.returncode == 0, done.stdout
    assert "flag" in done.stdout and "rule 25" in done.stdout and REL in done.stdout
    assert DAY_181 not in done.stdout and URL not in done.stdout


def test_180_days_is_not_flagged(root: Path) -> None:
    sourced(root, DAY_180)
    done = check(root)
    assert done.returncode == 0
    assert "flag" not in done.stdout


def test_181_days_fails_when_a_design_cites_the_playbook(root: Path) -> None:
    sourced(root, DAY_181)
    cite(root)
    done = check(root)
    assert done.returncode == 1
    assert "rule 25" in done.stdout and REL in done.stdout


def test_180_days_passes_when_a_design_cites_the_playbook(root: Path) -> None:
    sourced(root, DAY_180)
    cite(root)
    assert check(root).returncode == 0


def test_a_design_that_cites_another_playbook_does_not_fail_this_one(root: Path) -> None:
    sourced(root, DAY_181)
    write(root, "docs/design/architecture/other.md", "Uses `config/playbooks/web-app.toml`.\n")
    assert check(root).returncode == 0


def test_the_reviewed_key_is_refused_until_its_amendment_is_approved(root: Path) -> None:
    assert derive(root).returncode == 0
    path = root / REL
    path.write_text(f'reviewed = "{TODAY}"\n' + path.read_text(encoding="utf-8"), encoding="utf-8")
    done = check(root)
    assert done.returncode == 1
    assert "outside the format" in done.stdout


def test_the_shipped_playbooks_pass_with_nothing_to_flag() -> None:
    done = subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, str(SCRIPT), "check-playbook", "--date", TODAY, "--root", str(KIT_ROOT)],
        capture_output=True,
        text=True,
        cwd=KIT_ROOT,
        check=False,
    )
    assert done.returncode == 0, done.stdout
    assert "flag" not in done.stdout


def test_a_named_file_is_the_only_one_checked(root: Path) -> None:
    with_gate(root, "")
    good = root / "config/playbooks/default.toml"
    done = run(root, "check-playbook", "--date", TODAY, str(good))
    assert done.returncode == 0, done.stdout
    assert run(root, "check-playbook", "--date", TODAY, REL).returncode == 1


@pytest.mark.parametrize(
    "args",
    [
        ["check-playbook"],
        ["check-playbook", "--date", "soon"],
        ["derive-write"],
        ["derive-write", "--slug", SLUG, "--date", TODAY],
        ["derive-write", "--slug", SLUG, "extra"],
    ],
    ids=["no-date", "bad-date", "no-slug", "date-on-write", "stray-argument"],
)
def test_usage(root: Path, args: list[str]) -> None:
    assert run(root, *args).returncode == 2


def test_no_url_is_fetched(root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """SPEC-0048 rule 16: files only."""

    def refuse(*_args, **_kwargs):
        raise AssertionError("a check opened a socket")

    monkeypatch.setattr(socket, "socket", refuse)
    monkeypatch.setattr(socket, "create_connection", refuse)
    import front_door

    base = ["--root", str(root)]
    assert front_door.main(["derive-write", "--slug", SLUG, *base]) == 0
    assert front_door.main(["check-playbook", "--date", TODAY, *base]) == 0
