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
def product(repo):
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

    Q-1596-1: permissive licences only, until the maintainers accept the list.
    """
    text = (KIT_ROOT / "kit" / "templates" / "licences.toml").read_text(encoding="utf-8")
    assert licences.allowed_from(text) == licences.DEFAULT
    want = ("MIT", "Apache-2.0", "BSD-2-Clause", "BSD-3-Clause", "ISC", "PSF-2.0")
    assert licences.DEFAULT == frozenset(want)


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


def test_adopt_holds_the_findings_until_the_baseline(product, capsys) -> None:
    """REQ-061, REQ-079.

    Answer 4: brief #1600's baseline is not built, so an adopted project's findings are held.
    """
    toml = FILES["agk.toml"].replace('mode = "init"', 'mode = "adopt"')
    odd = {"odd-pkg": {"version": "0.0.1", "license": "LicenseRef-Invented-1"}}
    product.commit({"agk.toml": toml, "package-lock.json": lock(**odd)})
    assert licences.check(product.root, {}) == []


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
