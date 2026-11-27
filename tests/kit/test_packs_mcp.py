"""Tests of SPEC-0077 build (f): a documentation server is used only in the steward's recorded
research (rules 6, 7 and 12; REQ-084 AC4; brief #2044, ADR-0845).

`packs.servers(root)` gives the names of `[packs] mcp` that a pack of `[packs] use` declares in
`permissions.mcp` and that passes `packs.verify` (the lock, the trust and the `kit` range);
`steward_owner.py research --server NAME` refuses a name outside it before anything is recorded,
naming `packs.mcp` and never the name, and on a yes prints `server: <name>` beside `search:`.
`doctor.py` counts the servers and warns about a listed one left out, never naming it. No check,
gate or verdict role reads a server. Fixtures in `tmp_path` only: invented data (`example.com`),
a stub search, the personal sidecar's memory (nothing posted), no network, no model.
"""

from __future__ import annotations

import hashlib
import re
import socket
import sys
from pathlib import Path

import pytest

KIT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KIT_ROOT / "scripts" / "agk"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import check_packs  # noqa: E402
import doctor  # noqa: E402
import governance_map  # noqa: E402
import packs  # noqa: E402
import steward  # noqa: E402
import steward_owner  # noqa: E402
from test_steward_memory import GitHub  # noqa: E402

import config  # noqa: E402

SERVER = "docs-example"
AT = "2026-11-27T13:30Z"
GENERIC = "a booking web app for small clinics"
SKILL = "# An invented skill\n\nDraft the shop's terms.\n"
MANIFEST = """format = 1
id = "{pid}"
version = "1.2.0"
publisher = "Example Org"
tier = "{tier}"
licence = "MIT"
source = "https://example.com/packs/{pid}.git"
kit = "{kit}"
as_of = "2026-11-20"
reviewed = "2026-11-21 by maintainers"
kinds = ["skills"]

[permissions]
mcp = {mcp}

[files]
"skills/shop/SKILL.md" = "{sha}"
"""
REFUSED = "refused: the documentation server is not allowed (setting: packs.mcp)"
LEFT_OUT = (
    "warn packs: a listed documentation server has no verified pack in use (setting: packs.mcp)"
)


def stub_pack(root: Path, pid: str, tier: str = "curated", kit: str = ">=0.60.0,<1.0.0",
              mcp: str = f'["{SERVER}"]') -> Path:  # fmt: skip
    folder = root / check_packs.FOLDER / pid
    (folder / "skills" / "shop").mkdir(parents=True, exist_ok=True)
    (folder / "skills" / "shop" / "SKILL.md").write_text(SKILL, encoding="utf-8")
    sha = hashlib.sha256(SKILL.encode()).hexdigest()
    text = MANIFEST.format(pid=pid, tier=tier, kit=kit, mcp=mcp, sha=sha)
    (folder / check_packs.MANIFEST).write_text(text, encoding="utf-8")
    return folder


def project(tmp_path: Path, pids=("zz-docs",), mcp: str = f'["{SERVER}"]', extra: str = "",
            **pack) -> Path:  # fmt: skip
    """A personal-mode project with each stub pack in `[packs] use` and in the lock."""
    root = tmp_path / "product"
    folders = [stub_pack(root, pid, **pack) for pid in pids]
    (root / packs.LOCK).write_text(packs.lock_text([packs.lock_entry(f) for f in folders]))
    use = ", ".join(
        f'{{ id = "{f.name}", version = "1.2.0", '
        f'sha256 = "{check_packs.digest(f / check_packs.MANIFEST)}" }}'
        for f in folders
    )
    table = f"[packs]\nuse = [{use}]\nmcp = {mcp}\n{extra}" if pids else ""
    text = f'review_mode = "solo"\n\n[personal]\nlevel = "light"\nforge = "files"\n\n{table}'
    (root / "agk.toml").write_text(text, encoding="utf-8")
    return root


def said(tmp_path: Path, words: str) -> Path:
    path = tmp_path / "said.txt"
    path.write_text(words, encoding="utf-8")
    return path


def memory(root: Path) -> list[str]:
    return [e["body"] for e in steward.personal_entries(root)]


def research(root: Path, tmp_path: Path, words: str, server, text: str = GENERIC):
    sent: list[str] = []
    code, lines = steward_owner.research(
        root, said(tmp_path, words), AT, text, GitHub(), sent.append, server=server
    )
    return code, lines, sent


@pytest.fixture
def no_socket(monkeypatch):
    def refuse(*args, **kwargs):
        raise AssertionError("a socket was opened")

    monkeypatch.setattr(socket, "socket", refuse)
    monkeypatch.setattr(socket, "create_connection", refuse)


def test_ac4_a_listed_server_of_a_verified_pack_is_allowed_offline(tmp_path, no_socket):
    """REQ-084 AC4: SPEC-0077 rule 7 (answer 1: listed, declared, verified; files only)."""
    root = project(tmp_path)
    assert packs.check(root) == []
    assert packs.servers(root) == [SERVER]
    assert packs.left_out(root) == []


@pytest.mark.parametrize("table", ["", "[packs]\nmcp = []\n"])
def test_ac4_no_table_or_an_empty_list_allows_no_server(tmp_path, table, no_socket):
    """REQ-084 AC4: SPEC-0077 rule 12 (absent or `mcp = []`: research as today, `--server`
    refused naming `packs.mcp`)."""
    root = tmp_path / "product"
    root.mkdir()
    (root / "agk.toml").write_text(
        f'review_mode = "solo"\n[personal]\nlevel = "light"\nforge = "files"\n{table}',
        encoding="utf-8",
    )
    assert packs.servers(root) == []
    code, lines, sent = research(root, tmp_path, "yes", None)
    assert code == 0 and sent == [GENERIC] and lines[-1] == f"search: {GENERIC}"
    assert memory(root) == [f'Setup: web-research: yes because the person said "yes" at {AT}']
    code, lines, sent = research(root, tmp_path, "yes", SERVER)
    assert (code, lines, sent) == (2, [REFUSED], [])
    assert len(memory(root)) == 1


def test_ac4_research_on_a_yes_prints_the_server_and_the_generic_words(tmp_path, no_socket):
    """REQ-084 AC4: SPEC-0077 rule 7 (answer 2: the record names the server; then `server:` and
    `search:`)."""
    root = project(tmp_path)
    code, lines, sent = research(root, tmp_path, "yes", SERVER)
    assert code == 0 and sent == [GENERIC]
    assert lines[-2:] == [f"server: {SERVER}", f"search: {GENERIC}"]
    assert memory(root) == [
        f'Setup: web-research: yes because the person said "yes" at {AT} (server: {SERVER})'
    ]


def test_ac4_research_on_a_no_records_the_no_and_searches_nothing(tmp_path):
    """REQ-084 AC4: SPEC-0077 rule 7 (answer 2: a no is recorded, no server line)."""
    root = project(tmp_path)
    code, lines, sent = research(root, tmp_path, "no", SERVER)
    assert code == 0 and sent == [] and lines[-1] == steward_owner.NO_SEARCH
    assert not any(line.startswith("server:") for line in lines)
    assert memory(root) == [
        f'Setup: web-research: no because the person said "no" at {AT} (server: {SERVER})'
    ]


def _byte(root: Path) -> None:
    skill = root / check_packs.FOLDER / "zz-docs" / "skills" / "shop" / "SKILL.md"
    skill.write_text(SKILL + "x\n", encoding="utf-8")


@pytest.mark.parametrize(
    ("pack", "change"),
    [
        ({}, _byte),  # the lock's verify fails
        ({"tier": "community"}, None),  # below `[packs] trust` (curated)
        ({"kit": ">=9.0.0,<10.0.0"}, None),  # the `kit` range misses the running kit
    ],
)
def test_ac4_a_declaring_pack_that_fails_verify_leaves_the_server_out(tmp_path, pack, change):
    """REQ-084 AC4: SPEC-0077 rules 4, 6 and 7 (answer 5: left out, refused, doctor warns)."""
    root = project(tmp_path, **pack)
    if change:
        change(root)
    assert packs.check(root) != []
    assert packs.servers(root) == []
    assert packs.left_out(root) == [SERVER]
    code, lines, sent = research(root, tmp_path, "yes", SERVER)
    assert (code, lines, sent) == (2, [REFUSED], [])
    assert memory(root) == []
    assert doctor.pack_server_lines(root) == [LEFT_OUT]
    assert SERVER not in LEFT_OUT and "(setting: packs.mcp)" in LEFT_OUT


@pytest.mark.parametrize("server", ["other-docs", "", "docs example"])
def test_ac4_an_unlisted_empty_or_odd_name_is_refused_before_any_record(tmp_path, server):
    """REQ-084 AC4: SPEC-0077 rule 7 (answer 6: never the name, nothing recorded)."""
    root = project(tmp_path)
    code, lines, sent = research(root, tmp_path, "yes", server)
    assert (code, lines, sent) == (2, [REFUSED], [])
    assert memory(root) == []


@pytest.mark.parametrize(
    ("mcp", "extra"),
    [
        ('"docs-example"', ""),  # not a list
        ("true", ""),  # a bool
        ('["-docs"]', ""),  # out of form
        ('["other-docs"]', ""),  # no pack in use declares it
        (f'["{SERVER}"]', '\n[guard]\npatterns = [{ name = "docs", regex = "docs-ex" }]\n'),
    ],
)
def test_ac4_a_refused_mcp_value_names_the_setting(tmp_path, mcp, extra):
    """REQ-084 AC4: SPEC-0077 rule 12 (build (a)'s refusals kept; a name the guard flags too)."""
    root = project(tmp_path, mcp=mcp)
    if extra:
        path = root / "agk.toml"
        path.write_text(path.read_text(encoding="utf-8") + extra, encoding="utf-8")
    with pytest.raises(config.PacksSettingError, match=r"\(setting: packs\.mcp\)"):
        config.packs_settings(root)
    with pytest.raises(packs.Refused, match=r"\(setting: packs\.mcp\)"):
        packs.servers(root)
    code, lines, _ = research(root, tmp_path, "yes", SERVER)
    assert (code, lines) == (2, [REFUSED])
    assert doctor.pack_server_lines(root) == []  # the packs-settings row names the refusal


def test_ac4_a_server_declared_by_two_packs_is_allowed_through_the_one_that_verifies(tmp_path):
    """REQ-084 AC4: SPEC-0077 rule 7 (answer 6: one declaring pack fails, the other passes)."""
    root = project(tmp_path, pids=("zz-docs", "zz-more"))
    skill = root / check_packs.FOLDER / "zz-more" / "skills" / "shop" / "SKILL.md"
    skill.write_text(SKILL + "x\n", encoding="utf-8")
    assert packs.servers(root) == [SERVER] and packs.left_out(root) == []


def test_ac4_a_pack_removed_from_use_takes_its_server_with_it(tmp_path):
    """REQ-084 AC4: SPEC-0077 rule 12 (the declaring pack out of `use`: `packs.mcp` refused)."""
    root = project(tmp_path)
    path = root / "agk.toml"
    text = re.sub(r"use = \[.*\]\n", "use = []\n", path.read_text(encoding="utf-8"))
    path.write_text(text, encoding="utf-8")
    with pytest.raises(packs.Refused, match=r"\(setting: packs\.mcp\)"):
        packs.servers(root)


def test_ac4_a_description_the_guard_refuses_names_no_server_and_records_nothing(tmp_path):
    """REQ-084 AC4: SPEC-0072 rule 8 (`generic_problem` as today with `--server`)."""
    root = project(tmp_path)
    code, lines, sent = research(root, tmp_path, "yes", SERVER, "a booking app for 3 clinics")
    assert code == 2 and sent == [] and SERVER not in lines[0]
    assert memory(root) == []


def test_ac4_a_steward_the_supervisor_started_is_refused_as_today(tmp_path, monkeypatch):
    """REQ-084 AC4: SPEC-0077 rule 7 (`AGK_STEWARD_START=conductor`: refused as today)."""
    root = project(tmp_path)
    monkeypatch.setenv("AGK_STEWARD_START", "conductor")
    code, lines, sent = research(root, tmp_path, "yes", SERVER)
    assert code == 2 and "(setting: AGK_STEWARD_START)" in lines[0] and sent == []
    assert memory(root) == []


def test_ac4_the_command_takes_server_and_refuses_without_naming_it(tmp_path, capsys, monkeypatch):
    """REQ-084 AC4: SPEC-0077 rule 7 (the CLI: `--server`, exit 2, never the name)."""
    root = project(tmp_path)
    monkeypatch.setattr(steward_owner, "repo_root", lambda: root)
    words = said(tmp_path, "yes")
    argv = ["research", "--said", str(words), "--at", AT, "--describe", GENERIC]
    code = steward_owner.main([*argv, "--server", "other-docs"])
    out = capsys.readouterr()
    assert code == 2 and REFUSED in out.out + out.err and "other-docs" not in out.out + out.err


def test_ac4_a_pack_server_name_out_of_form_fails_rule_3():
    """REQ-084 AC4: SPEC-0077 rule 6 (`permissions.mcp` names in form)."""
    data = {"permissions": {"mcp": ["docs example", ""]}}
    assert ("the key has the wrong value", "permissions.mcp") in check_packs._keys(data)
    assert ("the key has the wrong value", "permissions.mcp") not in check_packs._keys(
        {"permissions": {"mcp": [SERVER]}}
    )


def test_ac4_doctor_counts_the_servers(tmp_path):
    """REQ-084 AC4: SPEC-0077 rule 12 (answer 4: `, servers <n>`; no warning when allowed)."""
    root = project(tmp_path)
    assert doctor.packs_settings_result(root).message == "(1 packs, trust curated, servers 1)"
    assert doctor.pack_server_lines(root) == []
    empty = tmp_path / "empty"
    empty.mkdir()
    assert doctor.packs_settings_result(empty).message == "(0 packs, trust curated, servers 0)"


def test_ac4_the_class_stays_closed_no_check_gate_or_verdict_role_reads_a_server():
    """REQ-084 AC4: SPEC-0077 rule 7 (answer 8: never in a check, a gate or a verdict)."""
    scripts = {KIT_ROOT / p for _, paths in governance_map.CHECKS for p in paths}
    scripts |= set((KIT_ROOT / "scripts" / "agk" / "gates").glob("*.py"))
    for path in sorted(scripts):
        if path.suffix == ".py" and path.is_file():
            text = path.read_text(encoding="utf-8")
            assert "servers(" not in text and "packs.mcp" not in text, path.name
    for role in ("reviewer", "architect-review", "personal-reviewer", "drift-auditor", "shadow"):
        head = (KIT_ROOT / ".claude" / "agents" / f"{role}.md").read_text(encoding="utf-8")
        tools = re.search(r"^tools:(.*)$", head, re.MULTILINE)
        assert tools and "mcp__" not in tools.group(1), role
