"""The bill of materials and its check (SPEC-0054 build (b), brief #787, REQ-061).

Git fixtures in tmp_path and invented data only; no network, no scanner.
"""

from __future__ import annotations

import json
import os
import socket
from pathlib import Path

import pytest
import sbom

SHA = "a1" * 20
OTHER_SHA = "b2" * 20
DIGEST = "c3" * 32
SCANNER_DIGEST = "d4" * 32
WORKFLOW = f"""name: ci
jobs:
  a:
    steps:
      - uses: actions/checkout@{SHA}   # v4.4.0
      - uses: example/tool@v2
      - env:
          SCANTOOL_VERSION: 8.30.1
          SCANTOOL_SHA256: {SCANNER_DIGEST}
"""
PYPROJECT = """[project]
name = "demo"
version = "0.0.0"
dependencies = ["Alpha_Lib==1.2.3", "beta>=2", "wild==1.*"]
[project.optional-dependencies]
docs = ["gamma == 0.1 ; python_version > '3.11'"]
[dependency-groups]
dev = ["delta==4.0", {include-group = "more"}]
more = ["epsilon"]
[build-system]
requires = ["setuptools>=61"]
"""
FILES: dict[str, str | None] = {
    "agk.toml": 'version = "1.2.0"\n',
    "pyproject.toml": PYPROJECT,
    "config/ci-tools.txt": "# pins\nbandit==1.9.4\nruff==0.17.4\n",
    ".github/workflows/ci.yml": WORKFLOW,
    ".gitignore": "out/\n",
    "kit/manifest.json": json.dumps(
        {
            "verbatim": ["scripts/agk/one.py"],
            "experimental": ["scripts/agk/two.py"],
            "templates": {"agk.toml": "kit/templates/agk.toml"},
        }
    ),
    "scripts/agk/one.py": "one\n",
    "scripts/agk/two.py": "two\n",
    "kit/templates/agk.toml": "template\n",
}
REFS = {
    "action:actions/checkout@" + SHA + ":v4.4.0",
    "action:example/tool",
    "ci-tool:bandit@1.9.4",
    "ci-tool:ruff@0.17.4",
    "kit-file:kit/templates/agk.toml",
    "kit-file:scripts/agk/one.py",
    "kit-file:scripts/agk/two.py",
    "python:alpha-lib@1.2.3",
    "python:beta",
    "python:delta@4.0",
    "python:epsilon",
    "python:gamma@0.1",
    "python:setuptools",
    "python:wild",
    "scanner:scantool@8.30.1",
}


@pytest.fixture
def repo(repo, monkeypatch: pytest.MonkeyPatch):
    """The kit's fixture repository with the bill's files committed, as the working directory."""
    repo.commit(dict(FILES))
    monkeypatch.chdir(repo.root)
    return repo


def make(tmp_path: Path, *extra: str) -> tuple[int, Path]:
    out = tmp_path / "out" / "bill.json"  # the fixture's root; `out/` is ignored there
    out.parent.mkdir(exist_ok=True)
    return sbom.main(["make", *extra, "--out", str(out)]), out


def bill(tmp_path: Path) -> tuple[dict, Path]:
    code, out = make(tmp_path)
    assert code == 0
    return json.loads(out.read_text(encoding="utf-8")), out


def by_ref(doc: dict, ref: str) -> dict:
    return next(c for c in doc["components"] if c["bom-ref"] == ref)


def props(component: dict) -> dict:
    return {p["name"]: p["value"] for p in component["properties"]}


def test_bill_lists_exactly_the_declared_components(repo, tmp_path: Path) -> None:
    """REQ-061 AC1: one CycloneDX document, every class, its pins, digests and package URLs."""
    doc, _ = bill(tmp_path)
    assert {c["bom-ref"] for c in doc["components"]} == REFS
    assert (doc["bomFormat"], doc["specVersion"], doc["version"]) == ("CycloneDX", "1.6", 1)
    assert doc["metadata"]["component"]["name"] == "demo"
    assert doc["metadata"]["component"]["version"] == "1.2.0"
    assert [c["bom-ref"] for c in doc["components"]] == sorted(REFS)
    pinned = by_ref(doc, "python:alpha-lib@1.2.3")
    assert (pinned["type"], pinned["version"]) == ("library", "1.2.3")
    assert pinned["purl"] == "pkg:pypi/alpha-lib@1.2.3"
    assert props(pinned) == {"agk:class": "python"}
    assert by_ref(doc, "ci-tool:ruff@0.17.4")["purl"] == "pkg:pypi/ruff@0.17.4"
    action = by_ref(doc, f"action:actions/checkout@{SHA}:v4.4.0")
    assert (action["type"], action["version"]) == ("application", "v4.4.0")
    assert action["purl"] == f"pkg:github/actions/checkout@{SHA}"
    scanner = by_ref(doc, "scanner:scantool@8.30.1")
    assert scanner["hashes"] == [{"alg": "SHA-256", "content": SCANNER_DIGEST}]
    kit_file = by_ref(doc, "kit-file:scripts/agk/one.py")
    assert kit_file["type"] == "file"
    assert len(kit_file["hashes"][0]["content"]) == 64


V = "SCANTOOL_VERSION: 8.30.1"
D = f"SCANTOOL_SHA256: {SCANNER_DIGEST}"
W = "SCANTOOL_VERSION: 9.0.0"
E = "SCANTOOL_SHA256: " + "e5" * 32


def scanner_refs(repo, tmp_path: Path, lines: list[str]) -> list[tuple[str, str]]:
    """The scanner components, as (version, digest), of a workflow stating these lines."""
    body = "".join(f"      - env:\n          {line}\n" for line in lines)
    repo.commit({".github/workflows/ci.yml": f"name: ci\njobs:\n  a:\n    steps:\n{body}"})
    doc, _ = bill(tmp_path)
    found = [c for c in doc["components"] if props(c)["agk:class"] == "scanner"]
    return [(c["version"], c["hashes"][0]["content"]) for c in found]


@pytest.mark.parametrize(
    ("lines", "expected"),
    [
        ([V, D], [("8.30.1", SCANNER_DIGEST)]),
        ([D, V], [("8.30.1", SCANNER_DIGEST)]),
        ([D, V, D, V], [("8.30.1", SCANNER_DIGEST)]),
        ([V, D, D, V], [("8.30.1", SCANNER_DIGEST)]),
        ([E, W, D, V], [("8.30.1", SCANNER_DIGEST), ("9.0.0", "e5" * 32)]),
        ([V, D, E, W], [("8.30.1", SCANNER_DIGEST), ("9.0.0", "e5" * 32)]),
    ],
)
def test_a_scanner_is_listed_in_either_order(
    repo, tmp_path: Path, capsys, lines: list[str], expected: list[tuple[str, str]]
) -> None:
    """REQ-061 AC1: the order of a scanner's two lines does not decide whether it is listed."""
    assert scanner_refs(repo, tmp_path, lines) == expected
    capsys.readouterr()
    assert sbom.main(["check", str(tmp_path / "out" / "bill.json")]) == 0
    assert capsys.readouterr().out.strip() == "ok bom"


@pytest.mark.parametrize("lines", [[V], [D], [D, D]])
def test_a_scanner_missing_a_line_is_not_a_pinned_scanner(
    repo, tmp_path: Path, lines: list[str]
) -> None:
    """REQ-061 AC1: no pair, no component; a version or digest is never borrowed or invented."""
    assert scanner_refs(repo, tmp_path, lines) == []


@pytest.mark.parametrize("lines", [[V, D, E], [D, V, E], [E, D, V], [V, E, D]])
def test_one_version_with_two_digests_is_refused_in_any_order(
    repo, tmp_path: Path, capsys, lines: list[str]
) -> None:
    """REQ-061 AC1: the second digest of one version is never dropped silently."""
    body = "".join(f"      - env:\n          {line}\n" for line in lines)
    repo.commit({".github/workflows/ci.yml": f"name: ci\njobs:\n  a:\n    steps:\n{body}"})
    code, out = make(tmp_path)
    assert code == 1 and not out.exists()
    assert ".github/workflows/" in capsys.readouterr().out


@pytest.mark.parametrize("ref", ["python:beta", "python:setuptools", "action:example/tool"])
def test_a_pin_that_is_not_exact_is_unpinned(repo, tmp_path: Path, ref: str) -> None:
    """REQ-061 AC1: a range or an unpinned `uses:` has `agk:pin` and never a version."""
    doc, _ = bill(tmp_path)
    component = by_ref(doc, ref)
    assert props(component)["agk:pin"] == "unpinned"
    assert "version" not in component and "purl" not in component


def test_same_commit_same_bytes_and_read_at_the_commit(repo, tmp_path: Path) -> None:
    """REQ-061 AC1: the document depends only on the commit, not on the working tree."""
    _, out = bill(tmp_path)
    first = out.read_bytes()
    repo.write("config/ci-tools.txt", "ruff==9.9.9\n")
    _, out = bill(tmp_path)
    assert out.read_bytes() == first
    repo.commit({"config/ci-tools.txt": "ruff==9.9.9\n"})
    code, older = make(tmp_path, "--ref", "HEAD~1")
    assert code == 0 and older.read_bytes() == first


def test_make_and_check_open_no_socket(
    repo, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """REQ-061 AC1: `make` and `check` run with sockets made to raise."""

    def refuse(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("socket opened")

    monkeypatch.setattr(socket, "socket", refuse)
    code, out = make(tmp_path)
    assert code == 0 and sbom.main(["check", str(out)]) == 0


def test_check_passes_a_true_bill(repo, tmp_path: Path, capsys) -> None:
    """REQ-061 AC2: the bill of the commit prints `ok bom`."""
    _, out = bill(tmp_path)
    capsys.readouterr()
    assert sbom.main(["check", str(out)]) == 0
    assert capsys.readouterr().out.strip() == "ok bom"


def _remove(doc: dict) -> None:
    doc["components"] = [c for c in doc["components"] if c["bom-ref"] != "python:delta@4.0"]


def _add(doc: dict) -> None:
    extra = dict(by_ref(doc, "python:delta@4.0"), name="zeta", version="1.0")
    extra.update({"bom-ref": "python:zeta@1.0", "purl": "pkg:pypi/zeta@1.0"})
    doc["components"].append(extra)
    doc["components"].sort(key=lambda c: c["bom-ref"])


def _pin(doc: dict) -> None:
    by_ref(doc, "python:delta@4.0")["version"] = "4.1"


def _sha(doc: dict) -> None:
    component = by_ref(doc, f"action:actions/checkout@{SHA}:v4.4.0")
    component["purl"] = f"pkg:github/actions/checkout@{OTHER_SHA}"


def _digest(doc: dict) -> None:
    by_ref(doc, "kit-file:scripts/agk/one.py")["hashes"][0]["content"] = DIGEST


def _field(doc: dict) -> None:
    by_ref(doc, "python:delta@4.0")["author"] = "someone"


def _unpinned_version(doc: dict) -> None:
    by_ref(doc, "python:beta")["version"] = "2.0"


def _odd_property(doc: dict) -> None:
    by_ref(doc, "python:delta@4.0")["properties"].append({"name": ["odd"], "value": "1"})


@pytest.mark.parametrize(
    ("change", "kind"),
    [
        (_remove, "python"),
        (_add, "python"),
        (_pin, "python"),
        (_sha, "action"),
        (_digest, "kit-file"),
        (_field, "python"),
        (_unpinned_version, "python"),
        (_odd_property, "python"),
    ],
)
def test_check_gives_one_line_per_problem(repo, tmp_path: Path, capsys, change, kind: str) -> None:
    """REQ-061 AC2: one `FAIL bom:` line naming the class, holding no name or version."""
    doc, out = bill(tmp_path)
    change(doc)
    out.write_text(json.dumps(doc), encoding="utf-8")
    capsys.readouterr()
    assert sbom.main(["check", str(out)]) == 1
    lines = capsys.readouterr().out.strip().splitlines()
    assert len(lines) == 1 and lines[0].startswith(f"FAIL bom: {kind} ")
    for value in ("delta", "zeta", "beta", "checkout", "one.py", "4.0", "4.1", "someone", "2.0"):
        assert value not in lines[0]


@pytest.mark.parametrize(
    ("key", "value"),
    [("specVersion", "9.9"), ("bomFormat", "Other"), ("extra", "zz9"), ("serialNumber", "urn:x")],
)
def test_check_refuses_another_form(repo, tmp_path: Path, capsys, key: str, value: str) -> None:
    """REQ-061 AC2: another format or version, an extra field or another commit's identity."""
    doc, out = bill(tmp_path)
    doc[key] = value
    out.write_text(json.dumps(doc), encoding="utf-8")
    capsys.readouterr()
    assert sbom.main(["check", str(out)]) == 1
    lines = capsys.readouterr().out.strip().splitlines()
    assert len(lines) == 1 and lines[0].startswith("FAIL bom: document ")
    assert value not in lines[0]


def test_check_refuses_what_is_not_json(repo, tmp_path: Path, capsys) -> None:
    """REQ-061 AC2: a file that is not JSON is one line, never a traceback."""
    bad = tmp_path / "bad.json"
    bad.write_text("not json", encoding="utf-8")
    assert sbom.main(["check", str(bad)]) == 1
    assert capsys.readouterr().out.startswith("FAIL bom: document ")


def test_an_out_inside_the_repository_is_refused(repo, capsys) -> None:
    """REQ-061 AC2: a tracked or unignored `--out` is refused; an ignored one is written."""
    assert sbom.main(["make", "--out", "bill.json"]) == 1
    assert "repository" in capsys.readouterr().out
    assert not (repo.root / "bill.json").exists()
    (repo.root / "out").mkdir(exist_ok=True)
    assert sbom.main(["make", "--out", "out/bill.json"]) == 0
    assert (repo.root / "out/bill.json").is_file()


@pytest.mark.parametrize(
    ("path", "text", "named"),
    [
        ("pyproject.toml", "not toml [", "pyproject.toml"),
        ("pyproject.toml", None, "pyproject.toml"),
        ("pyproject.toml", '[project]\ndependencies = ["=bad"]\nname = "x"\n', "pyproject.toml"),
        ("pyproject.toml", '[project]\nname = "x"\ndependencies = "abc"\n', "pyproject.toml"),
        ("pyproject.toml", "project = 1\n", "pyproject.toml"),
        ("config/ci-tools.txt", "ruff>=1\n", "config/ci-tools.txt"),
        ("agk.toml", "nothing = 1\n", "agk.toml"),
        ("kit/manifest.json", "{", "kit/manifest.json"),
        ("scripts/agk/one.py", None, "kit-file"),
    ],
)
def test_an_unreadable_file_is_refused(
    repo, tmp_path: Path, capsys, path: str, text: str | None, named: str
) -> None:
    """REQ-061 AC2: named by its path class, and no bill is written."""
    repo.commit({path: text})
    code, out = make(tmp_path)
    assert code == 1 and not out.exists()
    assert named in capsys.readouterr().out


def test_a_project_has_no_kit_files(repo, tmp_path: Path, capsys) -> None:
    """REQ-061 AC2: without `kit/manifest.json` the bill has no `kit-file` and passes."""
    repo.commit({"kit/manifest.json": None})
    doc, out = bill(tmp_path)
    assert not [c for c in doc["components"] if c["bom-ref"].startswith("kit-file:")]
    capsys.readouterr()
    assert sbom.main(["check", str(out)]) == 0


def test_a_ref_that_does_not_resolve_names_the_option(repo, tmp_path: Path, capsys) -> None:
    """REQ-061 AC2: refused naming the setting, never its value."""
    code, _ = make(tmp_path, "--ref", "no-such-ref")
    text = capsys.readouterr().out
    assert code == 1 and "--ref" in text and "no-such-ref" not in text


# SPEC-0054 build (c), rule 7: the findings from a saved scan result (brief #811).
UNREADABLE = "unknown: the scan result cannot be read"
MARKERS = ("zz-summary-marker", "zz-details-marker", "zz-reference-marker", "zz-path-marker")
GHSA_A, CVE_A = "GHSA-aaaa-bbbb-cccc", "CVE-2026-0001"
GHSA_B, GHSA_C, GHSA_D = "GHSA-dddd-eeee-ffff", "GHSA-gggg-hhhh-jjjj", "GHSA-kkkk-mmmm-nnnn"


def advisory(ident: str, aliases: tuple[str, ...] = (), severity: str | None = None) -> dict:
    """One invented advisory, with text in every field that must never be kept."""
    item: dict = {
        "id": ident,
        "aliases": list(aliases),
        "summary": "zz-summary-marker",
        "details": "zz-details-marker",
        "references": [{"type": "WEB", "url": "https://example.com/zz-reference-marker"}],
    }
    if severity is not None:
        item["database_specific"] = {"severity": severity}
    return item


def package(name: str, version: str, vulns: list, groups: list | None = None) -> dict:
    found = {"package": {"name": name, "version": version, "ecosystem": "PyPI"}}
    return {**found, "vulnerabilities": vulns, "groups": groups}


def result(*packages: dict) -> dict:
    source = {"path": "/example.com/zz-path-marker", "type": "sbom"}
    return {"results": [{"source": source, "packages": list(packages)}]}


def run_findings(tmp_path: Path, capsys, doc: object, *extra: str) -> tuple[int, str]:
    """`findings` on the saved result DOC (bytes as they are), against the fixture's bill."""
    _, bom = bill(tmp_path)
    saved = tmp_path / "out" / "result.json"
    saved.write_bytes(doc if isinstance(doc, bytes) else json.dumps(doc).encode("utf-8"))
    capsys.readouterr()
    code = sbom.main(["findings", str(saved), "--bom", str(bom), *extra])
    return code, capsys.readouterr().out


def named_all_but(*skipped: str) -> list[dict]:
    """A package with no finding for every pinned component except those named SKIPPED."""
    pins = {
        "alpha-lib": "1.2.3",
        "bandit": "1.9.4",
        "delta": "4.0",
        "gamma": "0.1",
        "ruff": "0.17.4",
        "scantool": "8.30.1",
        "actions/checkout": "v4.4.0",
    }
    return [package(n, v, []) for n, v in pins.items() if n not in skipped]


def test_findings_gives_the_counts_and_the_ids(repo, tmp_path: Path, capsys) -> None:
    """REQ-061 AC4: two advisories on one component, one on another; counts, ids, class, pin."""
    doc = result(
        package(
            "Alpha_Lib",
            "1.2.3",
            [advisory(GHSA_A, (CVE_A,)), advisory(GHSA_B, severity="MODERATE")],
            [{"ids": [GHSA_A], "max_severity": "9.8"}],
        ),
        package("ruff", "0.17.4", [advisory(GHSA_C)]),
        package("actions/checkout", SHA, [advisory(GHSA_D, severity="LOW")]),
    )
    code, out = run_findings(tmp_path, capsys, doc)
    assert code == 0
    lines = out.splitlines()
    assert lines[0] == "critical 1, high 0, medium 1, low 1, unknown 1"
    assert f"- python alpha-lib 1.2.3 critical: {CVE_A}, {GHSA_A}" in lines
    assert f"- python alpha-lib 1.2.3 medium: {GHSA_B}" in lines
    assert f"- ci-tool ruff 0.17.4 unknown: {GHSA_C}" in lines
    assert f"- action actions/checkout v4.4.0 low: {GHSA_D}" in lines
    assert lines.index(f"- python alpha-lib 1.2.3 critical: {CVE_A}, {GHSA_A}") == 2


def test_findings_keep_nothing_else_of_the_result(repo, tmp_path: Path, capsys) -> None:
    """REQ-061 AC4: no description, summary, reference, log, path or text of the result."""
    doc = result(package("delta", "4.0", [advisory(GHSA_A, severity="HIGH")]))
    code, out = run_findings(tmp_path, capsys, doc)
    assert code == 0 and GHSA_A in out
    for marker in MARKERS:
        assert marker not in out
    assert "example.com" not in out


def test_a_finding_of_a_group_is_one_finding(repo, tmp_path: Path, capsys) -> None:
    """REQ-061 AC4: the scanner's group of aliases counts once, with the ids it states."""
    vulns = [advisory(GHSA_A), advisory(GHSA_B)]
    doc = result(package("delta", "4.0", vulns, [{"ids": [GHSA_B, GHSA_A], "max_severity": "7.5"}]))
    _, out = run_findings(tmp_path, capsys, doc)
    assert out.splitlines()[0] == "critical 0, high 1, medium 0, low 0, unknown 0"
    assert f"- python delta 4.0 high: {GHSA_A}, {GHSA_B}" in out.splitlines()


def test_the_same_finding_in_two_sources_counts_once(repo, tmp_path: Path, capsys) -> None:
    """REQ-061 AC4: one line, at the worse severity the result states."""
    one = result(package("delta", "4.0", [advisory(GHSA_A, severity="LOW")]))
    two = result(package("delta", "4.0", [advisory(GHSA_A, severity="HIGH")]))
    doc = {"results": one["results"] + two["results"]}
    _, out = run_findings(tmp_path, capsys, doc)
    assert out.splitlines()[0] == "critical 0, high 1, medium 0, low 0, unknown 0"
    assert out.count(GHSA_A) == 1


def test_one_package_in_two_classes_is_a_finding_of_each(repo, tmp_path: Path, capsys) -> None:
    """REQ-061 AC4: each component of the bill with that pin is listed and counted."""
    text = PYPROJECT.replace('"beta>=2"', '"ruff==0.17.4"')
    repo.commit({"pyproject.toml": text})
    doc = result(package("ruff", "0.17.4", [advisory(GHSA_A, severity="HIGH")]))
    _, out = run_findings(tmp_path, capsys, doc)
    assert out.splitlines()[0] == "critical 0, high 2, medium 0, low 0, unknown 0"
    assert f"- ci-tool ruff 0.17.4 high: {GHSA_A}" in out.splitlines()
    assert f"- python ruff 0.17.4 high: {GHSA_A}" in out.splitlines()


@pytest.mark.parametrize(
    ("score", "label", "bucket"),
    [
        ("9.0", None, "critical 1, high 0, medium 0, low 0, unknown 0"),
        ("10", None, "critical 1, high 0, medium 0, low 0, unknown 0"),
        ("8.9", None, "critical 0, high 1, medium 0, low 0, unknown 0"),
        ("7", "LOW", "critical 0, high 1, medium 0, low 0, unknown 0"),
        ("6.9", None, "critical 0, high 0, medium 1, low 0, unknown 0"),
        ("4.0", None, "critical 0, high 0, medium 1, low 0, unknown 0"),
        ("3.9", None, "critical 0, high 0, medium 0, low 1, unknown 0"),
        ("0.1", None, "critical 0, high 0, medium 0, low 1, unknown 0"),
        ("", "CRITICAL", "critical 1, high 0, medium 0, low 0, unknown 0"),
        ("", "moderate", "critical 0, high 0, medium 1, low 0, unknown 0"),
        ("", "MEDIUM", "critical 0, high 0, medium 1, low 0, unknown 0"),
        ("", None, "critical 0, high 0, medium 0, low 0, unknown 1"),
        ("0", None, "critical 0, high 0, medium 0, low 0, unknown 1"),
        ("11", None, "critical 0, high 0, medium 0, low 0, unknown 1"),
        ("nan", None, "critical 0, high 0, medium 0, low 0, unknown 1"),
        ("", "SEVERE", "critical 0, high 0, medium 0, low 0, unknown 1"),
    ],
)
def test_a_severity_is_read_or_unknown(
    repo, tmp_path: Path, capsys, score: str, label: str | None, bucket: str
) -> None:
    """REQ-061 AC4, AC7: a severity the result does not state is `unknown`, never a lower one."""
    group = [{"ids": [GHSA_A], "max_severity": score}]
    doc = result(package("delta", "4.0", [advisory(GHSA_A, severity=label)], group))
    code, out = run_findings(tmp_path, capsys, doc)
    assert code == 0 and out.splitlines()[0] == bucket


@pytest.mark.parametrize(
    "doc",
    [
        b"not json",
        b"\xff\xfe",
        [],
        {},
        {"results": None},
        {"results": ["x"]},
        {"results": [{"source": {}}]},
        {"results": [{"packages": [{"vulnerabilities": []}]}]},
        {"results": [{"packages": [{"package": {"name": "delta"}, "vulnerabilities": []}]}]},
        {"results": [{"packages": [{"package": {"name": "delta", "version": "4.0"}}]}]},
        result(package("delta", "4.0", [{"summary": "no id"}])),
        result(package("delta", "4.0", [{"id": 7}])),
        result(package("delta", "4.0", [{"id": "two words"}])),
        result(package("delta", "4.0", [{"id": "@someone"}])),
        result(package("delta", "4.0", [advisory(GHSA_A, ("not an id!",))])),
        result(package("delta", "4.0", [{"id": GHSA_A, "aliases": "x"}])),
        result(package("delta", "4.0", [advisory(GHSA_A)], [{"ids": []}])),
        result(package("delta", "4.0", [advisory(GHSA_A)], [{"ids": [GHSA_A, 1]}])),
        result(package("delta", "4.0", [advisory(GHSA_A)], [{"ids": [GHSA_A], "max_severity": 9}])),
        result(package("delta", "4.0", [advisory(GHSA_A)], "x")),
        result(package("delta", "4.0", [{"id": GHSA_A, "database_specific": "x"}])),
    ],
)
def test_a_result_of_another_form_is_never_clean(repo, tmp_path: Path, capsys, doc) -> None:
    """REQ-061 AC7: the one line and exit 1, for a result not JSON or not the scanner's form."""
    assert run_findings(tmp_path, capsys, doc) == (1, UNREADABLE + "\n")


def test_a_missing_result_is_never_clean(repo, tmp_path: Path, capsys) -> None:
    """REQ-061 AC7: a path that cannot be read gives the same line."""
    _, bom = bill(tmp_path)
    capsys.readouterr()
    assert sbom.main(["findings", str(tmp_path / "absent"), "--bom", str(bom)]) == 1
    assert capsys.readouterr().out == UNREADABLE + "\n"


@pytest.mark.parametrize(
    "doc",
    [
        result(package("zeta", "1.0", [advisory(GHSA_A)])),
        result(package("delta", "9.9", [advisory(GHSA_A)])),
        result(package("beta", "2.0", [advisory(GHSA_A)])),
    ],
)
def test_a_finding_on_nothing_the_bill_pins_is_never_dropped(
    repo, tmp_path: Path, capsys, doc: dict
) -> None:
    """REQ-061 AC7: the result is of another bill; its name and version are not kept."""
    code, out = run_findings(tmp_path, capsys, doc)
    assert (code, out) == (1, UNREADABLE + "\n")


def test_a_component_the_result_does_not_name_is_unknown(repo, tmp_path: Path, capsys) -> None:
    """REQ-061 AC7: an empty result lists every component as `unknown`, and no clean report."""
    code, out = run_findings(tmp_path, capsys, {"results": []})
    assert code == 0
    lines = out.splitlines()
    assert lines[0] == "critical 0, high 0, medium 0, low 0, unknown 0"
    listed = [line for line in lines if line.endswith(": unknown")]
    assert len(listed) == len(REFS)
    assert "- python delta 4.0: unknown" in lines
    assert "- python beta: unknown" in lines
    assert "- action example/tool: unknown" in lines
    assert "- kit-file scripts/agk/one.py: unknown" in lines
    assert "- scanner scantool 8.30.1: unknown" in lines
    assert "clean" not in out and "no known" not in out


def test_only_what_the_result_names_leaves_unknown(repo, tmp_path: Path, capsys) -> None:
    """REQ-061 AC7: a named pin with no finding is not listed; a pin it does not name is."""
    code, out = run_findings(tmp_path, capsys, result(*named_all_but("delta")))
    assert code == 0
    listed = {line for line in out.splitlines() if line.endswith(": unknown")}
    assert "- python delta 4.0: unknown" in listed
    assert "- python alpha-lib 1.2.3: unknown" not in listed
    assert "- action actions/checkout v4.4.0: unknown" not in listed
    assert "- python beta: unknown" in listed


def test_a_package_outside_the_bill_with_no_finding_changes_nothing(
    repo, tmp_path: Path, capsys
) -> None:
    """REQ-061 AC7: it is not kept, and it names no component of the bill."""
    code, out = run_findings(tmp_path, capsys, result(package("zeta", "1.0", [])))
    assert code == 0 and "zeta" not in out and "- python delta 4.0: unknown" in out


@pytest.mark.parametrize(
    "text",
    ["not json", "[]", '{"bomFormat": "Other"}', '{"bomFormat": "CycloneDX", "components": []}'],
)
def test_a_bill_that_cannot_be_read_is_never_clean(repo, tmp_path: Path, capsys, text: str) -> None:
    """REQ-061 AC7: without the bill nothing can be matched, so one line and exit 1."""
    saved = tmp_path / "out" / "result.json"
    saved.parent.mkdir(exist_ok=True)
    saved.write_text('{"results": []}', encoding="utf-8")
    bad = tmp_path / "out" / "bill.json"
    bad.write_text(text, encoding="utf-8")
    assert sbom.main(["findings", str(saved), "--bom", str(bad)]) == 1
    assert capsys.readouterr().out == "unknown: the bill cannot be read\n"


def test_findings_needs_no_repository(
    repo, tmp_path: Path, tmp_path_factory, capsys, monkeypatch: pytest.MonkeyPatch
) -> None:
    """REQ-061 AC6: it reads the two saved files and nothing of git."""
    _, bom = bill(tmp_path)
    saved = tmp_path / "out" / "result.json"
    saved.write_text('{"results": []}', encoding="utf-8")
    monkeypatch.chdir(tmp_path_factory.mktemp("elsewhere"))
    capsys.readouterr()
    assert sbom.main(["findings", str(saved), "--bom", str(bom)]) == 0


@pytest.mark.parametrize(
    "argv",
    [
        ["findings", "r.json"],
        ["findings", "--bom", "b.json"],
        ["findings", "r.json", "--bom", "b.json", "--ref", "HEAD"],
        ["findings", "r.json", "--bom", "b.json", "--out", "x"],
        ["make", "--out", "x", "--bom", "b.json"],
        ["check", "b.json", "--bom", "b.json"],
    ],
)
def test_findings_takes_only_its_options(argv: list[str], capsys) -> None:
    """REQ-061 AC4: no threshold or other setting is read (rule 8)."""
    assert sbom.main(argv) == 2
    assert capsys.readouterr().out.startswith("usage:")


def test_no_command_opens_a_socket_or_starts_the_scanner(
    repo, tmp_path: Path, capsys, monkeypatch: pytest.MonkeyPatch
) -> None:
    """REQ-061 AC6: `make`, `check` and `findings` with sockets raising and a scanner stub."""
    marker = tmp_path / "out" / "scanner-started"
    (tmp_path / "out").mkdir(exist_ok=True)
    stub_dir = tmp_path / "out" / "bin"
    stub_dir.mkdir()
    stub = stub_dir / "osv-scanner"
    stub.write_text(f"#!/bin/sh\ntouch {marker}\n", encoding="utf-8")
    stub.chmod(0o755)
    monkeypatch.setenv("PATH", f"{stub_dir}:{os.environ['PATH']}")

    def refuse(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("socket opened")

    monkeypatch.setattr(socket, "socket", refuse)
    code, out = run_findings(tmp_path, capsys, {"results": []})
    assert code == 0 and out
    assert sbom.main(["check", str(tmp_path / "out" / "bill.json")]) == 0
    assert not marker.exists()


def test_no_governance_step_names_the_scanner() -> None:
    """REQ-061 AC6: no governance step, Makefile target or `prepush.py` step names it."""
    root = Path(__file__).resolve().parents[2]
    paths = [".github/workflows/governance.yml", "Makefile", "agk.mk", "scripts/agk/prepush.py"]
    for path in paths:
        assert "osv-scanner" not in (root / path).read_text(encoding="utf-8").lower(), path
