"""The product's own dependencies: its bill from the lock, the licence list and the findings
(brief #1596, ADR-0676, amendment 206 to SPEC-0054 rules 2, 4 and 6; REQ-061, REQ-079).
Git fixtures in tmp_path, invented package names and licence ids, saved invented scan results;
no network, no scanner.
"""

from __future__ import annotations

import json
import shutil
import socket
import sys
from pathlib import Path

import pytest

KIT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KIT_ROOT / "scripts" / "agk"))

import engines  # noqa: E402
import run_gates  # noqa: E402
import sbom  # noqa: E402
from gates import licences  # noqa: E402

RECORD = (
    "# ADR-0003: Stack options\n\n- Status: Accepted\n\n"
    "1. **Options**:\n   - Option A — web. Parts: node 22.11.0 MIT, tiny-util 2.1.0 ISC (verify)."
    " Why: invented.\n3. **Chosen**: Option A\n"
)
PY_RECORD = RECORD.replace("node 22.11.0 MIT", "python 3.12.7 PSF-2.0")
OLD_SIX = ("MIT", "Apache-2.0", "BSD-2-Clause", "BSD-3-Clause", "ISC", "PSF-2.0")
ADDED = ("blessing", "0BSD", "Unlicense", "Zlib", "BSL-1.0")  # brief #1811, ADR-0754
OLD_TEMPLATE = "allowed = [" + ", ".join(f'"{i}"' for i in OLD_SIX) + "]\n"


def lock(**extra: dict) -> str:
    packages = {
        "": {"name": "shop", "version": "0.1.0"},
        "node_modules/left-pad-x": {"version": "1.0.0", "license": "MIT"},
        "node_modules/tiny-util": {"version": "2.1.0"},  # its licence is the record's
        **{f"node_modules/{k}": v for k, v in extra.items()},
    }
    return json.dumps({"name": "shop", "lockfileVersion": 3, "packages": packages})


FILES = {
    "agk.toml": 'version = "0.1.0"\nmode = "init"\n\n[delivery]\nwork_type = "web-app"\n',
    "pyproject.toml": '[project]\nname = "shop"\nversion = "0.1.0"\ndependencies = []\n',
    "config/ci-tools.txt": "# none\n",
    ".gitignore": "out/\n",
    "package.json": json.dumps({"name": "shop", "private": True}),
    "package-lock.json": lock(),
    "docs/adr/0003-stack-options.md": RECORD,
}


@pytest.fixture
def product(repo, monkeypatch):
    # brief #1764: the Node pack has its own tests (test_node_pack.py); these hold the bill
    from gates import node_pack

    monkeypatch.setattr(node_pack, "on", lambda _root: False)
    shutil.copytree(KIT_ROOT / "config" / "playbooks", repo.root / "config" / "playbooks")
    repo.commit(dict(FILES))
    return repo


def bill(root: Path) -> dict:
    out = root / "out" / "bill.json"
    out.parent.mkdir(exist_ok=True)
    assert sbom.main(["make", "--out", str(out)]) == 0
    return json.loads(out.read_text(encoding="utf-8"))


def gates(root: Path, capsys) -> tuple[int, str]:
    capsys.readouterr()
    code = run_gates.main(["--root", str(root)])
    return code, capsys.readouterr().out


def test_the_lock_gives_a_bill_that_sbom_check_accepts(product, monkeypatch, capsys) -> None:
    """REQ-061, REQ-079.

    Answer 1: each package of the committed lock, class `node`, with its version and licence.
    """
    monkeypatch.chdir(product.root)
    doc = bill(product.root)
    node = {c["bom-ref"]: c for c in doc["components"] if c["bom-ref"].startswith("node:")}
    assert set(node) == {"node:left-pad-x@1.0.0", "node:tiny-util@2.1.0"}
    assert node["node:left-pad-x@1.0.0"]["purl"] == "pkg:npm/left-pad-x@1.0.0"
    assert node["node:left-pad-x@1.0.0"]["licenses"] == [{"expression": "MIT"}]
    assert node["node:tiny-util@2.1.0"]["licenses"] == [{"expression": "ISC"}]
    capsys.readouterr()
    assert sbom.main(["check", str(product.root / "out" / "bill.json")]) == 0
    assert capsys.readouterr().out == "ok bom\n"
    code, out = gates(product.root, capsys)
    assert code == 0 and "ok bom\n" in out and "ok licences\n" in out


def test_a_changed_licence_in_the_bill_is_refused(product, monkeypatch, capsys) -> None:
    """REQ-061, REQ-079."""
    monkeypatch.chdir(product.root)
    doc = bill(product.root)
    for item in doc["components"]:
        if item["bom-ref"] == "node:left-pad-x@1.0.0":
            item["licenses"] = [{"expression": "ISC"}]
    path = product.root / "out" / "bill.json"
    path.write_text(json.dumps(doc), encoding="utf-8")
    capsys.readouterr()
    assert sbom.main(["check", str(path)]) == 1
    out = capsys.readouterr().out
    assert out.startswith("FAIL bom: node ") and "left-pad-x" not in out and "ISC" not in out


def test_without_a_work_type_the_lock_is_not_read(repo, monkeypatch) -> None:
    """REQ-061, REQ-079: Answer 1: the kit's own repository keeps rule 2's reading unchanged."""
    files = dict(FILES, **{"agk.toml": 'version = "0.1.0"\n'})
    repo.commit(files)
    monkeypatch.chdir(repo.root)
    assert not [c for c in bill(repo.root)["components"] if c["bom-ref"].startswith("node:")]


def test_an_invented_licence_off_the_list_is_red(product, capsys) -> None:
    """REQ-061, REQ-079.

    Measured: red naming the licences rule and the component class, never a name or an id.
    """
    odd = {"odd-pkg": {"version": "0.0.1", "license": "LicenseRef-Invented-1"}}
    product.commit({"package-lock.json": lock(**odd)})
    assert licences.main(["--root", str(product.root)]) == 1
    out = capsys.readouterr().out
    assert out == f"FAIL licences: {licences.RULE} (component class: node)\n"
    code, out = gates(product.root, capsys)
    assert code == 1 and "FAIL gates: licences: SPEC-0054 rule 4" in out
    assert "odd-pkg" not in out and "Invented" not in out


def test_a_component_with_no_readable_licence_is_red_as_unknown(product, capsys) -> None:
    """REQ-061, REQ-079."""
    product.commit({"package-lock.json": lock(**{"bare-pkg": {"version": "3.0.0"}})})
    assert licences.main(["--root", str(product.root)]) == 1
    assert capsys.readouterr().out == f"FAIL licences: {licences.UNKNOWN} (component class: node)\n"


def test_an_or_expression_passes_when_one_side_is_allowed(product, capsys) -> None:
    """REQ-061, REQ-079."""
    either = {"either": {"version": "1.0.0", "license": "(LicenseRef-Invented-2 OR MIT)"}}
    both = {"both": {"version": "1.0.0", "license": "MIT AND LicenseRef-Invented-2"}}
    product.commit({"package-lock.json": lock(**either)})
    assert licences.main(["--root", str(product.root)]) == 0
    product.commit({"package-lock.json": lock(**either, **both)})
    assert licences.main(["--root", str(product.root)]) == 1


def test_the_project_list_widens_and_an_unknown_form_is_refused(product, capsys) -> None:
    """REQ-061, REQ-079: Answer 4: `config/licences.toml`; absent means the template's list."""
    odd = {"odd-pkg": {"version": "0.0.1", "license": "LicenseRef-Invented-1"}}
    product.commit({"package-lock.json": lock(**odd)})
    allowed = '"MIT", "ISC", "LicenseRef-Invented-1"'
    product.commit({"config/licences.toml": f"allowed = [{allowed}]\n"})
    assert licences.main(["--root", str(product.root)]) == 0
    for bad in ('allowed = "MIT"\n', "allowed = []\nextra = 1\n", "allowed = [1]\n", "x = [\n"):
        product.commit({"config/licences.toml": bad})
        capsys.readouterr()
        assert licences.main(["--root", str(product.root)]) == 1
        out = capsys.readouterr().out
        assert out == f"FAIL licences: {licences.FORM} (setting: config/licences.toml)\n"


def test_the_template_is_the_built_in_list() -> None:
    """REQ-061, REQ-079.

    Brief #1811 answer 1 (ADR-0754): the six of Q-1596-1 and five permissive ids, eleven;
    `CC0-1.0` stays off (Q-1811-1, the conservative reading).
    """
    text = (KIT_ROOT / "kit" / "templates" / "licences.toml").read_text(encoding="utf-8")
    assert licences.allowed_from(text) == licences.DEFAULT
    want = (*OLD_SIX, *ADDED)
    assert licences.DEFAULT == frozenset(want) and len(licences.DEFAULT) == 11
    assert "CC0-1.0" not in licences.DEFAULT


def test_a_python_lock_takes_its_licences_from_the_record(product, monkeypatch, capsys) -> None:
    """REQ-061, REQ-079."""
    files = {
        "package.json": None,
        "package-lock.json": None,
        "docs/adr/0003-stack-options.md": PY_RECORD,
        "requirements.lock": "tiny-util==2.1.0 \\\n    --hash=sha256:" + "ab" * 32 + "\n",
    }
    product.commit(files)
    assert licences.main(["--root", str(product.root)]) == 0
    monkeypatch.chdir(product.root)
    refs = {c["bom-ref"]: c for c in bill(product.root)["components"]}
    assert refs["python:tiny-util@2.1.0"]["licenses"] == [{"expression": "ISC"}]
    product.commit({"requirements.lock": "other-lib==1.0.0\n"})
    capsys.readouterr()
    assert licences.main(["--root", str(product.root)]) == 1
    assert "(component class: python)" in capsys.readouterr().out


def test_no_stack_or_no_lock_is_not_run_never_ok(product, capsys) -> None:
    """REQ-061, REQ-079."""
    product.commit({"package-lock.json": None})
    assert licences.main(["--root", str(product.root)]) == 0
    assert capsys.readouterr().out == "licences: not run: no lock\n"
    code, out = gates(product.root, capsys)
    assert "ok licences" not in out and "ok bom" not in out
    product.commit({"agk.toml": 'version = "0.1.0"\n'})
    assert licences.main(["--root", str(product.root)]) == 0
    assert capsys.readouterr().out == "licences: not run: no lock\n"


def test_adopt_holds_the_findings_in_the_baseline(product, capsys) -> None:
    """REQ-061, REQ-079.

    Brief #1777 answers 1 and 2: an adopted project's findings are held in the baseline and
    counted, never `ok licences`, and a new one fails as rule 7.
    """
    toml = FILES["agk.toml"].replace('mode = "init"', 'mode = "adopt"')
    odd = {"odd-pkg": {"version": "0.0.1", "license": "LicenseRef-Invented-1"}}
    product.commit({"agk.toml": toml, "package-lock.json": lock(**odd)})
    assert licences.check(product.root, {}) != []
    code, out = gates(product.root, capsys)
    held = "licences (baseline): 1 held (path class: package-lock.json)"
    assert held + "\n" in out and "ok licences" not in out, out
    assert "odd-pkg" not in out and "LicenseRef-Invented-1" not in out
    base = product.root / "config" / "agk-baseline" / "licences.txt"
    assert base.read_text(encoding="utf-8") == "package-lock.json 1\n"
    more = {"odd-two": {"version": "0.0.2", "license": "LicenseRef-Invented-2"}, **odd}
    product.commit({"package-lock.json": lock(**more)})
    code, out = gates(product.root, capsys)
    assert code == 1 and "FAIL gates: licences: SPEC-0072 rule 7" in out, out


def test_a_saved_scan_result_gives_the_issue_body(product, monkeypatch, capsys) -> None:
    """REQ-061, REQ-079.

    Answer 3: `sbom.py findings` reads the bill's `node` components (rule 7).
    """
    monkeypatch.chdir(product.root)
    bill(product.root)
    vuln = {"id": "GHSA-aaaa-bbbb-cccc", "database_specific": {"severity": "HIGH"}}
    vuln["summary"] = "MARKER-SUMMARY"
    found = {"package": {"name": "left-pad-x", "version": "1.0.0"}, "vulnerabilities": [vuln]}
    saved = product.root / "out" / "result.json"
    saved.write_text(json.dumps({"results": [{"packages": [found]}]}), encoding="utf-8")
    capsys.readouterr()
    sbom.main(["findings", str(saved), "--bom", str(product.root / "out" / "bill.json")])
    out = capsys.readouterr().out
    assert out.splitlines()[0] == "critical 0, high 1, medium 0, low 0, unknown 0"
    assert "- node left-pad-x 1.0.0 high: GHSA-aaaa-bbbb-cccc" in out
    assert "MARKER" not in out


def test_no_check_opens_a_socket(product, monkeypatch, capsys) -> None:
    """REQ-061, REQ-079."""

    def refuse(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("a socket was opened")

    monkeypatch.setattr(socket, "socket", refuse)
    monkeypatch.chdir(product.root)
    bill(product.root)
    assert licences.main(["--root", str(product.root)]) == 0
    assert gates(product.root, capsys)[0] == 0


def test_the_foundation_writes_the_list_once(product, capsys) -> None:
    """REQ-061, REQ-079.

    Answer 2: `stack-files` writes `config/licences.toml` from the template, never over one.
    """
    engines.cmd_stack_files(product.root)
    path = product.root / "config" / "licences.toml"
    template = KIT_ROOT / "kit" / "templates" / "licences.toml"
    assert path.read_text(encoding="utf-8") == template.read_text(encoding="utf-8")
    path.write_text('allowed = ["MIT"]\n', encoding="utf-8")
    engines.cmd_stack_files(product.root)
    assert path.read_text(encoding="utf-8") == 'allowed = ["MIT"]\n'
    old = "# the template a foundation wrote before brief #1811\n" + OLD_TEMPLATE
    path.write_text(old, encoding="utf-8")
    engines.cmd_stack_files(product.root)  # brief #1811 answer 2: an old copy is kept
    assert path.read_text(encoding="utf-8") == old
    assert licences.allowed_list(product.root) == frozenset(OLD_SIX)


def test_ids_are_compared_case_folded_by_one_reader() -> None:
    """REQ-061: brief #1785 answers 1 and 6 (one reader of an SPDX expression)."""
    assert licences.passes("mit", frozenset({"MIT"}))
    assert licences.passes("(LicenseRef-x OR mit)", frozenset({"MIT"}))
    assert not licences.passes("MIT+", frozenset({"MIT"}))
    assert not licences.passes("MIT AND blessing", frozenset({"MIT"}))
    assert not licences.passes("see LICENSE", frozenset({"see", "LICENSE"}))
    assert licences.ids("(MIT OR Apache-2.0) AND blessing") == ["mit", "apache-2.0", "blessing"]
    for good in ("blessing", "curl", "MIT+", "DocumentRef-a:LicenseRef-b", "(MIT OR Apache-2.0)"):
        assert licences.expression(good), good
    for bad in ("", "see LICENSE", "(MIT", "MIT OR", "AND", "MIT ()"):
        assert not licences.expression(bad), bad


def test_a_list_holding_blessing_passes_a_record_part_blessing(product, capsys) -> None:
    """REQ-061: brief #1785 answer 7 (the gate reads the record's real lower-case id)."""
    record = RECORD.replace("tiny-util 2.1.0 ISC", "tiny-util 2.1.0 blessing")
    product.commit({"docs/adr/0003-stack-options.md": record})
    product.commit({"config/licences.toml": OLD_TEMPLATE})  # brief #1811: the six-id list
    assert licences.main(["--root", str(product.root)]) == 1
    product.commit({"config/licences.toml": 'allowed = ["MIT", "blessing"]\n'})
    assert licences.main(["--root", str(product.root)]) == 0


@pytest.mark.parametrize("licence", [*ADDED, *(i.casefold() for i in ADDED), "ZLIB", "Blessing"])
def test_an_added_permissive_id_passes_with_no_project_list(product, capsys, licence) -> None:
    """REQ-061, REQ-079: brief #1811 answers 1 and 4 (each added id, SPDX case and folded)."""
    part = {"permissive": {"version": "1.0.0", "license": licence}}
    product.commit({"package-lock.json": lock(**part)})
    assert not (product.root / "config" / "licences.toml").exists()
    assert licences.main(["--root", str(product.root)]) == 0
    code, out = gates(product.root, capsys)
    assert code == 0 and "ok licences\n" in out, out


@pytest.mark.parametrize(
    "licence",
    [
        "BUSL-1.1",
        "zlib-acknowledgement",
        "CC-BY-4.0",
        "CC0-1.0",
        "MPL-2.0",
        "LGPL-2.1-only",
        "BlueOak-1.0.0",
        "Zlib+",
        "BSL-1.0 WITH x",
        "MIT AND CC0-1.0",
        "LicenseRef-Invented-3",
    ],
)
def test_ids_off_the_wider_default_still_fail(product, capsys, licence) -> None:
    """REQ-061, REQ-079: brief #1811 answer 6 (no source-available, copyleft or patent-silent)."""
    other = {"other": {"version": "1.0.0", "license": licence}}
    product.commit({"package-lock.json": lock(**other)})
    assert licences.main(["--root", str(product.root)]) == 1
    assert capsys.readouterr().out == f"FAIL licences: {licences.RULE} (component class: node)\n"


def test_expressions_over_the_wider_default() -> None:
    """REQ-061: brief #1811 answer 6 (`AND` and `OR` over the eleven ids)."""
    assert licences.passes("MIT AND blessing", licences.DEFAULT)
    assert licences.passes("(MIT OR CC0-1.0)", licences.DEFAULT)
    assert not licences.passes("MIT AND CC0-1.0", licences.DEFAULT)
    assert not licences.passes("BUSL-1.1", licences.DEFAULT)


def test_a_project_list_of_the_old_six_still_fails_blessing(product, capsys) -> None:
    """REQ-061, REQ-079: brief #1811 answer 2 (a project's own list decides; red stays red)."""
    db = {"db": {"version": "3.47.1", "license": "blessing"}}
    product.commit({"package-lock.json": lock(**db)})
    product.commit({"config/licences.toml": OLD_TEMPLATE})
    assert licences.main(["--root", str(product.root)]) == 1
    assert capsys.readouterr().out == f"FAIL licences: {licences.RULE} (component class: node)\n"


# Brief #1838 answer 3 (ADR-0768): the person names each failing licence; the gate's lines keep
# the class only.


def names(root: Path, capsys, *extra: str) -> tuple[int, str]:
    capsys.readouterr()
    code = licences.main(["--root", str(root), "--names", *extra])
    return code, capsys.readouterr().out


def tree(root: Path) -> set[str]:
    return {p.relative_to(root).as_posix() for p in root.rglob("*") if ".git" not in p.parts}


def test_names_lists_each_failing_package_for_the_person(product, capsys) -> None:
    """REQ-061, REQ-079: brief #1838 answer 3; it writes nothing and exits 1 as the check does."""
    odd = {
        "odd-pkg": {"version": "0.0.1", "license": "LicenseRef-Invented-1"},
        "no-licence": {"version": "0.0.2"},
    }
    product.commit({"package-lock.json": lock(**odd)})
    before = tree(product.root)
    code, out = names(product.root, capsys)
    assert code == 1
    assert out.splitlines() == [
        "licence off the list: node no-licence unknown (path class: package-lock.json)",
        "licence off the list: node odd-pkg LicenseRef-Invented-1 (path class: package-lock.json)",
        "licences: 2 to name; the baseline holds 0 (path class: config/agk-baseline/)",
    ]
    assert tree(product.root) == before
    capsys.readouterr()
    assert licences.main(["--root", str(product.root)]) == 1
    plain = capsys.readouterr().out
    assert "odd-pkg" not in plain and "LicenseRef-Invented-1" not in plain


def test_names_with_none_to_name_and_in_any_order(product, capsys) -> None:
    """REQ-061, REQ-079: brief #1838 answer 3."""
    code, out = names(product.root, capsys)
    assert (code, out) == (0, "ok licences (none to name)\n")
    capsys.readouterr()
    assert licences.main(["--names", "--root", str(product.root)]) == 0
    assert capsys.readouterr().out == "ok licences (none to name)\n"


def test_names_counts_what_the_baseline_holds(product, capsys) -> None:
    """REQ-061, REQ-079: brief #1838 answers 3 and 6; the gate's held row is unchanged."""
    toml = FILES["agk.toml"].replace('mode = "init"', 'mode = "adopt"')
    odd = {"odd-pkg": {"version": "0.0.1", "license": "LicenseRef-Invented-1"}}
    product.commit({"agk.toml": toml, "package-lock.json": lock(**odd)})
    code, out = gates(product.root, capsys)
    assert "licences (baseline): 1 held (path class: package-lock.json)\n" in out
    assert "odd-pkg" not in out
    swapped = {"odd-new": {"version": "0.0.3", "license": "LicenseRef-Invented-4"}}
    product.commit({"package-lock.json": lock(**swapped)})
    code, out = names(product.root, capsys)
    assert code == 1 and "node odd-new LicenseRef-Invented-4" in out and "odd-pkg" not in out
    assert out.endswith(
        "licences: 1 to name; the baseline holds 1 (path class: config/agk-baseline/)\n"
    )


def test_names_takes_a_python_licence_from_the_record(product, capsys) -> None:
    """REQ-061, REQ-079: brief #1838 answer 6."""
    record = PY_RECORD.replace("tiny-util 2.1.0 ISC", "example-qt 5.15.10 GPL-3.0")
    lock_text = "example-qt==5.15.10 \\\n    --hash=sha256:" + "ab" * 32 + "\n"
    files = {
        "package.json": None,
        "package-lock.json": None,
        "docs/adr/0003-stack-options.md": record,
        "requirements.lock": lock_text,
    }
    product.commit(files)
    code, out = names(product.root, capsys)
    assert code == 1
    assert out.splitlines()[0] == (
        "licence off the list: python example-qt GPL-3.0 (path class: requirements.lock)"
    )


def test_names_refuses_a_list_not_of_its_form_and_names_no_package(product, capsys) -> None:
    """REQ-061, REQ-079: brief #1838 answer 5."""
    odd = {"odd-pkg": {"version": "0.0.1", "license": "LicenseRef-Invented-1"}}
    product.commit({"package-lock.json": lock(**odd), "config/licences.toml": "x = [\n"})
    code, out = names(product.root, capsys)
    assert code == 1
    assert out == f"FAIL licences: {licences.FORM} (setting: config/licences.toml)\n"


def test_names_with_no_lock_or_no_work_type_is_not_run(product, capsys) -> None:
    """REQ-061, REQ-079: brief #1838 answer 5."""
    product.commit({"package-lock.json": None})
    assert names(product.root, capsys) == (0, "licences: not run: no lock\n")
    product.commit({"agk.toml": 'version = "0.1.0"\n'})
    assert names(product.root, capsys) == (0, "licences: not run: no lock\n")


@pytest.mark.parametrize("args", [["--names", "--names"], ["--names", "x"], ["--root"]])
def test_names_a_malformed_command_line_prints_usage(args: list[str], capsys) -> None:
    """REQ-061, REQ-079."""
    assert licences.main(args) == 2
    assert capsys.readouterr().err.startswith("usage: python3 scripts/agk/gates/licences.py")


def test_no_workflow_or_prepush_step_calls_names() -> None:
    """REQ-061, REQ-079: brief #1838 answer 3: the names never reach a CI log."""
    paths = [
        *(KIT_ROOT / ".github" / "workflows").glob("*.y*ml"),
        KIT_ROOT / "scripts" / "agk" / "prepush.py",
    ]
    paths += [
        KIT_ROOT / "scripts" / "agk" / "run_gates.py",
        KIT_ROOT / "scripts" / "agk" / "governance_map.py",
    ]
    for path in paths:
        if path.is_file():
            assert "--names" not in path.read_text(encoding="utf-8"), path


# Brief #1907 (ADR-0789, amendment 232 to SPEC-0054 rules 2 and 3): a Node product with no
# `pyproject.toml` names its bill from `package.json`; every other repository reads as today.

PACKAGE_FAIL = "FAIL bom: package.json {what} at the commit (rule 2)\n"
CLASS = "bom: SPEC-0054 rule 4 (amendment 206): the product's bill cannot be made or is refused"


def no_pyproject(repo, **extra: str | None) -> None:
    repo.commit({"pyproject.toml": None, **extra})


def node_refs(doc: dict) -> set[str]:
    return {c["bom-ref"] for c in doc["components"] if c["bom-ref"].startswith("node:")}


@pytest.mark.parametrize(
    "toml",
    [
        FILES["agk.toml"],
        FILES["agk.toml"].replace('mode = "init"', 'mode = "adopt"'),
        FILES["agk.toml"].replace('mode = "init"', 'mode = "init"\nexecution = "local"'),
        FILES["agk.toml"] + '\n[kit]\nlayout = "plugin"\nplugin_version = "0.1.0"\n',
        FILES["agk.toml"].replace('"web-app"', '"mobile"'),
    ],
    ids=["init", "adopt", "local", "plugin", "mobile"],
)
def test_a_node_product_without_pyproject_makes_its_bill(product, monkeypatch, capsys, toml):
    """REQ-061, REQ-078: brief #1907 answers 1, 2 and 5 (named from `package.json`)."""
    no_pyproject(product, **{"agk.toml": toml})
    monkeypatch.chdir(product.root)
    doc = bill(product.root)
    assert doc["metadata"]["component"] == {
        "type": "application",
        "name": "shop",
        "version": "0.1.0",
    }
    assert node_refs(doc) == {"node:left-pad-x@1.0.0", "node:tiny-util@2.1.0"}
    assert not [c for c in doc["components"] if c["bom-ref"].startswith("python:")]
    capsys.readouterr()
    assert sbom.main(["check", str(product.root / "out" / "bill.json")]) == 0
    assert capsys.readouterr().out == "ok bom\n"
    code, out = gates(product.root, capsys)
    assert "ok bom\n" in out, out


def test_a_scoped_name_is_kept_as_written(product, monkeypatch) -> None:
    """REQ-061: brief #1907 answer 2 (`@scope/name` too)."""
    no_pyproject(product, **{"package.json": json.dumps({"name": "@example/shop"})})
    monkeypatch.chdir(product.root)
    assert bill(product.root)["metadata"]["component"]["name"] == "@example/shop"


@pytest.mark.parametrize(
    "text,what",
    [
        (None, "cannot be read"),
        ("{not json", "cannot be parsed"),
        ("[1]", "cannot be parsed"),
        (json.dumps({"private": True}), "cannot be parsed"),
        (json.dumps({"name": 1}), "cannot be parsed"),
        (json.dumps({"name": ""}), "cannot be parsed"),
        (json.dumps({"name": "   "}), "cannot be parsed"),
        ("﻿" + json.dumps({"name": "shop"}), "cannot be parsed"),
    ],
    ids=["absent", "not-json", "not-object", "no-name", "number", "empty", "blank", "bom"],
)
def test_a_package_json_that_names_nothing_is_refused(product, monkeypatch, capsys, text, what):
    """REQ-061: brief #1907 answers 2 and 6; the line names the path, never a value."""
    no_pyproject(product, **{"package.json": text})
    monkeypatch.chdir(product.root)
    out = product.root / "out" / "bill.json"
    out.parent.mkdir(exist_ok=True)
    capsys.readouterr()
    assert sbom.main(["make", "--out", str(out)]) == 1 and not out.exists()
    assert capsys.readouterr().out == PACKAGE_FAIL.format(what=what)
    code, printed = gates(product.root, capsys)
    if text is not None:  # `bom` applies only with a chosen stack and its lock in the tree
        assert code == 1 and f"FAIL gates: {CLASS} (path class: bill of materials)" in printed


def test_a_crlf_package_json_parses(product, monkeypatch) -> None:
    """REQ-061: brief #1907 answer 6."""
    no_pyproject(product, **{"package.json": '{\r\n  "name": "shop"\r\n}\r\n'})
    monkeypatch.chdir(product.root)
    assert bill(product.root)["metadata"]["component"]["name"] == "shop"


def test_a_kept_pyproject_still_names_and_lists_python(product, monkeypatch, capsys) -> None:
    """REQ-061: brief #1907 answer 1 (present, it is read as today)."""
    py = '[project]\nname = "shop-tools"\ndependencies = ["example-req==2.0.0"]\n'
    product.commit({"pyproject.toml": py})
    monkeypatch.chdir(product.root)
    doc = bill(product.root)
    assert doc["metadata"]["component"]["name"] == "shop-tools"
    refs = {c["bom-ref"] for c in doc["components"]}
    assert "python:example-req@2.0.0" in refs and "node:left-pad-x@1.0.0" in refs
    for bad in ("[tool.example]\nx = 1\n", "x = [\n"):  # Q-SB-3: refused as today
        product.commit({"pyproject.toml": bad})
        out = product.root / "out" / "bill.json"
        capsys.readouterr()
        assert sbom.main(["make", "--out", str(out)]) == 1
        assert capsys.readouterr().out == (
            "FAIL bom: pyproject.toml cannot be parsed at the commit (rule 2)\n"
        )


@pytest.mark.parametrize(
    "files",
    [
        {"docs/adr/0003-stack-options.md": PY_RECORD},
        {"agk.toml": 'version = "0.1.0"\nmode = "init"\n'},
        {"docs/adr/0003-stack-options.md": RECORD.replace("Accepted", "Proposed")},
        {"docs/adr/0003-stack-options.md": None},
        {"docs/adr/0004-stack-options.md": RECORD},
    ],
    ids=["python-stack", "no-work-type", "proposed", "no-record", "two-records"],
)
def test_elsewhere_a_missing_pyproject_is_refused_as_today(product, monkeypatch, capsys, files):
    """REQ-061: brief #1907 answers 1 and 5 (no `node` stack chosen: today's line)."""
    no_pyproject(product, **files)
    monkeypatch.chdir(product.root)
    out = product.root / "out" / "bill.json"
    out.parent.mkdir(exist_ok=True)
    capsys.readouterr()
    assert sbom.main(["make", "--out", str(out)]) == 1
    assert capsys.readouterr().out == (
        "FAIL bom: pyproject.toml cannot be read at the commit (rule 2)\n"
    )


def test_with_both_parts_and_no_pyproject_bom_runs(product, capsys) -> None:
    """REQ-061: brief #1907 answer 5 as brief #1932 changes it (ADR-0800): two runtimes are a
    chosen stack, so `bom` runs, named by the root's `package.json`, and pins fails the Python
    runtime's missing build file."""
    both = RECORD.replace("MIT,", "MIT, python 3.12.7 PSF-2.0,")
    no_pyproject(product, **{"docs/adr/0003-stack-options.md": both})
    code, out = gates(product.root, capsys)
    assert "ok bom\n" in out and "ok licences\n" in out, out
    assert "the build file is missing or unreadable" in out and code == 1


def test_package_json_is_read_at_the_ref(product, monkeypatch, capsys) -> None:
    """REQ-061: brief #1907 answer 5 (`--ref`: the build file, `package.json` and the lock)."""
    no_pyproject(product, **{"package.json": None})
    product.commit({"package.json": json.dumps({"name": "shop"})})
    monkeypatch.chdir(product.root)
    out = product.root / "out" / "bill.json"
    out.parent.mkdir(exist_ok=True)
    capsys.readouterr()
    assert sbom.main(["make", "--ref", "HEAD~1", "--out", str(out)]) == 1
    assert capsys.readouterr().out == PACKAGE_FAIL.format(what="cannot be read")
    assert sbom.main(["make", "--out", str(out)]) == 0


def test_each_stack_has_a_name_reader() -> None:
    """REQ-061: brief #1907 answer 8 (a later `STACKS` row cannot fall back unseen)."""
    from gates import pins

    assert {row[1] for row in pins.STACKS.values()} == set(sbom.NAMERS)


# REQ-079 AC5, brief #1932 (ADR-0800): two runtimes, each lock in its own folder, one list.

TWO_RECORD = RECORD.replace(
    "tiny-util 2.1.0 ISC", "tiny-util 2.1.0 ISC, python 3.12.7 PSF-2.0, examplelib 1.2.3 MIT"
)
TWO_FILES = {
    "docs/adr/0003-stack-options.md": TWO_RECORD,
    "pyproject.toml": None,
    "service/requirements.txt": "examplelib==1.2.3\n",
    "service/requirements.lock": "examplelib==1.2.3\n",
}


def test_req079_ac5_both_locks_are_checked_against_one_list(product, capsys) -> None:
    product.commit(dict(TWO_FILES))
    assert licences.main(["--root", str(product.root)]) == 0
    assert capsys.readouterr().out == "ok licences\n"
    product.commit({"service/requirements.lock": "examplelib==1.2.3\nodd-py==0.1.0\n"})
    assert licences.main(["--root", str(product.root)]) == 1
    out = capsys.readouterr().out
    assert out == f"FAIL licences: {licences.UNKNOWN} (component class: python)\n", out
    assert licences.counts(product.root, {}) == {"service/requirements.lock": 1}
    odd = {"odd-pkg": {"version": "0.0.1", "license": "LicenseRef-Invented-1"}}
    product.commit({"package-lock.json": lock(**odd)})
    assert licences.counts(product.root, {}) == {
        "package-lock.json": 1,
        "service/requirements.lock": 1,
    }


def test_req079_ac5_a_missing_lock_of_one_runtime_skips_that_lock(product, capsys) -> None:
    product.commit({k: v for k, v in TWO_FILES.items() if k != "service/requirements.lock"})
    assert licences.main(["--root", str(product.root)]) == 0
    assert capsys.readouterr().out == "ok licences\n"
    product.commit({"package-lock.json": None})
    assert licences.main(["--root", str(product.root)]) == 0
    assert capsys.readouterr().out == f"licences: {licences.NOT_RUN}\n"


def test_req079_ac5_a_malformed_list_is_refused_for_two_runtimes(product, capsys) -> None:
    """Answer 6: one `config/licences.toml` for every runtime; another form names the setting."""
    product.commit(dict(TWO_FILES, **{"config/licences.toml": 'allowed = "MIT"\n'}))
    assert licences.main(["--root", str(product.root)]) == 1
    out = capsys.readouterr().out
    assert out == f"FAIL licences: {licences.FORM} (setting: config/licences.toml)\n"
