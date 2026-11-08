"""The bill of materials and its check (SPEC-0054 build (b), brief #787, REQ-061).

Git fixtures in tmp_path and invented data only; no network, no scanner.
"""

from __future__ import annotations

import json
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
