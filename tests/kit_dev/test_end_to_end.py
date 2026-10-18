"""One flow through the stages: init, requirement and tests, governance, proof, facts, report.

This is the test that fails if any stage breaks another. Each stage is the installed script run as
a user runs it; the only stand-ins are the project's test command (a command that fails without the
feature) and the pull request record that GitHub would supply to the facts (written into the facts
document, as the recorded API files are in the facts fixtures). A marker is written as `@nnn ACn`
and the `@` replaced, so that this file carries no marker of its own.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from conftest import KIT_ROOT, clean_env, git

TODAY = "2026-10-14"  # a Wednesday; the report covers 2026-10-05 to 2026-10-11 (ISO week 2026-W41)
MERGED = "2026-10-08T10:00:00Z"
OPENED = "2026-10-06T10:00:00Z"
REQUIREMENTS = """# Requirements

### REQ-101 — The feature works

- Acceptance: AC1 the feature returns one; AC2 the feature returns two
- Status: done

### REQ-102 — The next thing

- Acceptance: AC1 it is built
- Status: planned
"""


def make(root: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["make", *args], cwd=root, capture_output=True, text=True, env=clean_env()
    )


def marker(req: str, ac: str) -> str:
    return f"@-{req} {ac}".replace("@-", "REQ-")


def script(root: Path, name: str, *args: str, **env: str) -> subprocess.CompletedProcess:
    full = {**clean_env(), **env}
    return subprocess.run(
        [sys.executable, f"scripts/agk/{name}", *args],
        cwd=root,
        capture_output=True,
        text=True,
        env=full,
    )


def no_gh_path(root: Path) -> str:
    """A PATH with `git`, `make` and the interpreters, and no `gh` (the facts then say unknown)."""
    bin_dir = root.parent / "bin"
    bin_dir.mkdir(exist_ok=True)
    for tool in ("git", "make", "sh", "go"):
        found = shutil.which(tool)
        if found and not (bin_dir / tool).exists():
            (bin_dir / tool).symlink_to(found)
    return str(bin_dir)


def configure(root: Path, **settings: str) -> None:
    text = (root / "agk.toml").read_text(encoding="utf-8")
    for key, value in settings.items():
        line = f"{key} = {value}"
        pattern = rf"(?m)^{key}\s*=.*$"
        text = (
            re.sub(pattern, lambda _m, line=line: line, text)
            if re.search(pattern, text)
            else (text.rstrip("\n") + "\n" + line + "\n")
        )
    (root / "agk.toml").write_text(text, encoding="utf-8")


def commit(root: Path, message: str) -> str:
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", message)
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=root, capture_output=True, text=True, check=True
    ).stdout.strip()


def run_stages(root: Path, base: str, head: str, files: list[str]) -> dict:
    """governance, proof, facts, then the report from facts that carry the merged change."""
    gov = make(root, "governance")
    assert gov.returncode == 0, gov.stdout + gov.stderr
    proof = script(root, "proof.py", "--base", base, "--head", head, "--json")
    outcome = json.loads(proof.stdout)
    facts = script(
        root,
        "facts.py",
        "--today",
        TODAY,
        "--repo",
        "demo-org/demo-repo",
        PATH=no_gh_path(root),
    )
    assert facts.returncode == 0, facts.stdout + facts.stderr
    doc = json.loads(facts.stdout)
    doc["pull_requests"] = [
        {
            "number": 1,
            "title": "Add the feature",
            "state": "merged",
            "base": "main",
            "head": head,
            "created_at": OPENED,
            "merged_at": MERGED,
            "closed_at": MERGED,
            "files": files,
            "behaviour": None,
            "verdicts": [{"at": MERGED, "kind": "cleared", "sha": head[:7]}],
            "proof": outcome["outcome"],
        }
    ]
    path = root / "facts-input.json"
    path.write_text(json.dumps(doc), encoding="utf-8")
    report = script(root, "product_report.py", "--facts", str(path), "--today", TODAY)
    assert report.returncode == 0, report.stdout + report.stderr
    return {"proof": outcome, "facts": doc, "report": report.stdout}


def section(report: str, heading: str) -> list[str]:
    lines = report.splitlines()
    start = lines.index(f"## {heading}") + 1
    end = next((i for i in range(start, len(lines)) if lines[i].startswith("## ")), len(lines))
    return [ln for ln in lines[start:end] if ln]


def python_repo(installed: Path, passes_on_base: bool) -> tuple[str, str, list[str]]:
    """A Python project: a base commit, then a change that adds the feature and its tests."""
    (installed / "docs" / "requirements.md").write_text(REQUIREMENTS, encoding="utf-8")
    configure(installed, project_tests='"PYTHONPATH=. python3 tests/test_feature.py"')
    base = commit(installed, "base")
    (installed / "feature.py").write_text("ONE = 1\nTWO = 2\n", encoding="utf-8")
    body = "import feature\n\nassert feature.ONE == 1\nassert feature.TWO == 2\n"
    if passes_on_base:
        body = "assert 1 + 1 == 2\n"
    (installed / "tests" / "test_feature.py").write_text(
        f"# {marker('REQ-101', 'AC1')}\n# {marker('REQ-101', 'AC2')}\n{body}", encoding="utf-8"
    )
    return base, commit(installed, "feature"), ["feature.py", "tests/test_feature.py"]


@pytest.fixture
def stage(installed: Path) -> Path:
    git(installed, "add", "-A")
    git(installed, "commit", "-q", "-m", "install the kit")
    (installed / "tests").mkdir(exist_ok=True)
    return installed


def test_ac1_a_change_with_a_test_that_fails_without_it_is_proven_and_reported(stage):
    """REQ-016 AC1: init, tests, governance, proof, facts and the report agree on one change."""
    base, head, files = python_repo(stage, passes_on_base=False)
    out = run_stages(stage, base, head, files)
    assert out["proof"]["outcome"] == "proven", out["proof"]
    ours = {(m["file"], m["ac"]) for m in out["facts"]["markers"] if m["req"] == "REQ-101"}
    assert ours == {("tests/test_feature.py", "AC1"), ("tests/test_feature.py", "AC2")}
    proven = section(out["report"], "Proven")
    assert any(ln.startswith("- REQ-101 is proven (last change PR #1: proven)") for ln in proven)
    needs = "\n".join(section(out["report"], "Needs you"))
    assert 'REQ-102 "The next thing" is planned and no spec names it' in needs
    assert "### Planned requirements with no spec (" in needs
    assert out["report"].rstrip().endswith("drift audit: unknown")


def test_ac1_a_test_that_passes_without_the_change_is_not_proven_in_the_report(stage):
    """REQ-016 AC1: the proof outcome travels through the facts into the Proven line."""
    base, head, files = python_repo(stage, passes_on_base=True)
    out = run_stages(stage, base, head, files)
    assert out["proof"]["outcome"] == "not-proven", out["proof"]
    proven = "\n".join(section(out["report"], "Proven"))
    assert "REQ-101 is not proven: the last change (PR #1) was not shown to need its test" in proven


@pytest.mark.skipif(shutil.which("go") is None, reason="go is not installed")
def test_ac1_the_same_flow_in_a_go_layout_with_the_fixtures_under_testdata(stage):
    """REQ-016 AC1: a Go project; `go test ./...` ignores the kit fixtures under testdata."""
    (stage / "docs" / "requirements.md").write_text(REQUIREMENTS, encoding="utf-8")
    (stage / "go.mod").write_text("module demo\n\ngo 1.21\n", encoding="utf-8")
    (stage / "pkg").mkdir()
    configure(
        stage,
        project_tests='"go test ./..."',
        test_dirs='["pkg"]',
        test_patterns='["*_test.go"]',
    )
    base = commit(stage, "base")
    (stage / "pkg" / "feature.go").write_text(
        "package pkg\n\nfunc One() int { return 1 }\n\nfunc Two() int { return 2 }\n",
        encoding="utf-8",
    )
    (stage / "pkg" / "feature_test.go").write_text(
        'package pkg\n\nimport "testing"\n\n'
        f"// {marker('REQ-101', 'AC1')}\nfunc TestOne(t *testing.T) {{\n"
        "\tif One() != 1 {\n\t\tt.Fatal(One())\n\t}\n}\n\n"
        f"// {marker('REQ-101', 'AC2')}\nfunc TestTwo(t *testing.T) {{\n"
        "\tif Two() != 2 {\n\t\tt.Fatal(Two())\n\t}\n}\n",
        encoding="utf-8",
    )
    head = commit(stage, "feature")
    os.environ.setdefault("GOFLAGS", "-mod=mod")
    out = run_stages(stage, base, head, ["pkg/feature.go", "pkg/feature_test.go"])
    assert out["proof"]["outcome"] == "proven", out["proof"]
    assert {(m["file"], m["ac"]) for m in out["facts"]["markers"] if m["req"] == "REQ-101"} == {
        ("pkg/feature_test.go", "AC1"),
        ("pkg/feature_test.go", "AC2"),
    }
    assert any(
        ln.startswith("- REQ-101 is proven (last change PR #1: proven)")
        for ln in section(out["report"], "Proven")
    )


def intake(root: Path, *args: str) -> subprocess.CompletedProcess:
    """The kit-only script, run from the kit against the installed target."""
    return subprocess.run(
        [
            sys.executable,
            str(KIT_ROOT / "scripts" / "agk" / "intake.py"),
            *args,
            "--root",
            str(root),
        ],
        capture_output=True,
        text=True,
        env=clean_env(),
    )


def test_ac1_an_intake_passes_its_checks_and_governance_and_waits_in_the_report(stage):
    """REQ-019 AC1: a sentence becomes three files that every check accepts.

    REQ-019 AC2: after the merge the report lists the Draft spec and the Proposed ADR as waiting
    and delivers nothing.
    """
    existing = (
        "# Requirements\n\n### REQ-101 — Existing\n\n- Acceptance: AC1 x\n- Status: planned\n"
    )
    (stage / "docs" / "requirements.md").write_text(existing, encoding="utf-8")
    commit(stage, "base")
    git(stage, "switch", "-q", "-c", "intake/work")
    num = "102"
    sentence = "Let a visitor export a saved list as a file."
    out = intake(stage, "ids", "--sentence", sentence, "--ref", "main")
    ids = json.loads(out.stdout)
    assert (ids["req"], ids["spec"]) == ("REQ-102", "0001")
    title = "Export a saved list"
    stub = intake(
        stage,
        "stub",
        "--req",
        ids["req"],
        "--title",
        title,
        "--sentence",
        sentence,
        "--ref",
        "main",
    )
    assert stub.returncode == 0, stub.stdout
    ac = (
        "AC1 Given a saved list, when the visitor exports it, then a file with every item is "
        "downloaded; AC2 Given an empty list, when the visitor exports it, then no file is made"
    )
    with (stage / "docs" / "requirements.md").open("a", encoding="utf-8") as fh:
        fh.write(f"\n### {ids['req']} — {title}\n\n- Acceptance: {ac}\n- Status: planned\n")
    spec = (
        f"# SPEC-{ids['spec']}: {title}\n\n- Status: Draft\n- Owner: reviewer group\n"
        f"- Requirements: {ids['req']}\n\n## Rules\n\n1. The export lists every item.\n\n"
        "## Tests\n\n"
        f"- Rule 1: {marker(num, 'AC1')}\n- Rule 1: {marker(num, 'AC2')}\n\n"
        "## Proof\n\nRule 1.\n\n## Residual\n\nnone\n\n"
        f"## Open questions\n\n- Q-S{ids['spec']}-1 which file format?\n"
    )
    (stage / "docs" / "specs" / f"{ids['spec']}-{ids['slug']}.md").write_text(
        spec, encoding="utf-8"
    )
    check = intake(stage, "check", "--base", "main")
    assert check.stdout == "ok intake\n", check.stdout
    gov = make(stage, "governance")
    assert gov.returncode == 0, gov.stdout + gov.stderr
    commit(stage, "intake")
    git(stage, "switch", "-q", "main")
    git(stage, "merge", "-q", "--ff-only", "intake/work")
    facts = script(
        stage, "facts.py", "--today", TODAY, "--repo", "demo-org/demo-repo", PATH=no_gh_path(stage)
    )
    assert facts.returncode == 0, facts.stdout + facts.stderr
    (stage / "facts-input.json").write_text(facts.stdout, encoding="utf-8")
    report = script(stage, "product_report.py", "--facts", "facts-input.json", "--today", TODAY)
    assert report.returncode == 0, report.stdout
    assert ids["req"] not in "\n".join(section(report.stdout, "Delivered"))
    needs = "\n".join(section(report.stdout, "Needs you"))
    assert f"SPEC-{ids['spec']}" in needs and "ADR-" in needs and f"Q-S{ids['spec']}-1" in needs
