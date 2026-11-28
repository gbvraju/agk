"""Tests of the kit's shipped parts catalogues (SPEC-0076 rules 4, 5 and 11; REQ-083 AC1; brief
#2069, ADR-0859).

The kit ships one stack catalogue per stack that has a reader, `config/parts/<stack>.toml`, each
row with a dated public source, a licence on the kit's allowed list and the maintainers' `reviewed`
date. `check_parts_catalogue.SHIPPED` names them; the manifest installs exactly those. The rows for
`lint`, `format` and `unit-tests` name the tool the standards step and the stack's template run,
so the catalogue never offers a tool the kit does not run. Reads the shipped files only: no network.
"""

from __future__ import annotations

import json
import socket
import sys
import tomllib
from pathlib import Path

import pytest

KIT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KIT_ROOT / "scripts" / "agk"))

import check_parts_catalogue as cpc  # noqa: E402
import playbook_format  # noqa: E402
from gates import licences, node_pack  # noqa: E402

FOLDER = KIT_ROOT / "config" / "parts"
# Answer 1: the needs a stack's product has; a Python service has no browser front end.
FRONT_END = {"ui-components", "routing", "state", "forms", "e2e-tests", "accessibility"}


def load(path: Path) -> dict:
    return tomllib.loads(path.read_text(encoding="utf-8"))


def need_ids() -> list[str]:
    return [n["id"] for n in load(FOLDER / cpc.NEEDS)["needs"]]


def rows(stack: str) -> list[dict]:
    return load(FOLDER / f"{stack}.toml")["parts"]


def standard(stack: str) -> dict:
    entries = load(KIT_ROOT / "config" / "standards.toml")["standards"]
    return next(e for e in entries if e["stack"] == stack)


def expected(stack: str) -> dict[str, str]:
    """Answer 2: the recommended name for each need the kit already fixes."""
    if stack == "node":
        tools = dict(node_pack.TOOLS)
        fmt = next(t for t, key in tools.items() if key == "standards.format")
        return {"lint": standard("node")["rules"]["tool"], "format": fmt}
    tool = standard(stack)["rules"]["tool"]
    template = load(KIT_ROOT / "kit/templates/stacks" / stack / "pyproject.toml")
    runner = next(iter(template["tool"].keys() - {"setuptools"}))
    return {"lint": tool, "format": tool, "unit-tests": runner}


def test_ac1_the_shipped_catalogues_pass_the_check():
    """REQ-083 AC1: SPEC-0076 rule 5 (the shipped catalogues pass, read as the step reads them)."""
    files = [("agk-core", FOLDER / cpc.NEEDS)] + [
        ("agk-core", FOLDER / f"{s}.toml") for s in cpc.SHIPPED
    ]
    assert cpc.SHIPPED
    assert cpc.findings(KIT_ROOT, files, list(cpc.SHIPPED)) == []


def test_ac1_the_check_run_alone_prints_ok(capsys):
    """REQ-083 AC1: brief #2069 measured line (`ok` with the shipped catalogues counted)."""
    assert cpc.main(["--root", str(KIT_ROOT)]) == 0
    out = capsys.readouterr().out
    assert f"{len(cpc.SHIPPED)} stack catalogues)" in out and out.startswith("ok parts-catalogue")


@pytest.mark.parametrize("stack", cpc.SHIPPED)
def test_ac1_each_licence_is_on_the_kit_list(stack):
    """REQ-083 AC1: SPEC-0076 rule 6 (no shipped row could never be proposed)."""
    allowed = frozenset(load(KIT_ROOT / "kit/templates/licences.toml")["allowed"])
    assert allowed == licences.DEFAULT
    off = [r["name"] for r in rows(stack) if not licences.passes(r["licence"], allowed)]
    assert off == []


@pytest.mark.parametrize("stack", cpc.SHIPPED)
def test_ac1_each_source_is_dated_and_each_row_reviewed(stack):
    """REQ-083 AC1: SPEC-0076 rule 5 (a public source with its access date, the review date)."""
    for row in rows(stack):
        when = playbook_format.source_date(row["source"])
        assert when is not None, row["name"]
        assert row["reviewed"] >= when.isoformat(), row["name"]
        assert "version" not in row, row["name"]


@pytest.mark.parametrize("stack", cpc.SHIPPED)
def test_ac1_each_need_has_one_recommended_row(stack):
    """REQ-083 AC1: SPEC-0076 rules 4 and 5 (answer 1: every need the stack's product has)."""
    ids = need_ids()
    wanted = set(ids) if stack == "node" else set(ids) - FRONT_END
    picks = [r["need"] for r in rows(stack) if r["pick"] == "recommended"]
    assert sorted(picks) == sorted(wanted)
    assert {r["need"] for r in rows(stack)} <= set(ids)


@pytest.mark.parametrize("stack", cpc.SHIPPED)
def test_ac1_the_catalogue_agrees_with_the_tools_the_kit_runs(stack):
    """REQ-083 AC1: SPEC-0072 rule 6 (answer 2: lint, format and unit tests name the kit's tools)."""
    found = {r["need"]: r["name"] for r in rows(stack) if r["pick"] == "recommended"}
    for need, name in expected(stack).items():
        assert found[need] == name, need


@pytest.mark.parametrize("stack", cpc.SHIPPED)
def test_ac1_a_stdlib_row_adds_no_dependency(stack):
    """REQ-083 AC1: SPEC-0076 rule 4 (answer 3: the runtime's own part is recommended only)."""
    stdlib = [r for r in rows(stack) if r["name"] == "stdlib"]
    assert stdlib and all(r["pick"] == "recommended" for r in stdlib)


def test_ac1_the_shipped_catalogues_are_the_manifests():
    """REQ-083 AC1: SPEC-0076 rule 11 (answer 8: a stack gets a catalogue only with its reader)."""
    manifest = json.loads((KIT_ROOT / "kit/manifest.json").read_text(encoding="utf-8"))
    listed = {
        Path(p).stem
        for p in manifest["verbatim"]
        if p.startswith("config/parts/") and Path(p).name != cpc.NEEDS
    }
    present = {p.stem for p in FOLDER.glob("*.toml") if p.name != cpc.NEEDS}
    assert set(cpc.SHIPPED) == listed == present


def test_ac1_the_check_opens_no_socket(monkeypatch):
    """REQ-083 AC1: CLAUDE.md item 5 (no network in checks)."""

    def refuse(*args, **kwargs):
        raise AssertionError("a socket was opened")

    monkeypatch.setattr(socket, "socket", refuse)
    files = [("agk-core", FOLDER / cpc.NEEDS)] + [
        ("agk-core", FOLDER / f"{s}.toml") for s in cpc.SHIPPED
    ]
    assert cpc.findings(KIT_ROOT, files, list(cpc.SHIPPED)) == []
