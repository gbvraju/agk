"""Tests of kit/manifest.json and kit/templates/ (SPEC-0001 rules 6-9, 19-21)."""

from __future__ import annotations

import re
import subprocess
import tomllib

from conftest import KIT_ROOT, manifest

ROOTS = (".claude/", ".github/", "scripts/agk/", "tests/kit/")
KIT_ONLY = {"scripts/agk/init.py"}
RENDERED = {".github/CODEOWNERS"}
SINGLES = {
    "CLAUDE.md",
    "Makefile",
    ".gitignore",
    "constitution/principles.md",
    "docs/adr/TEMPLATE.md",
    "docs/specs/TEMPLATE.md",
    "docs/briefs/TEMPLATE.md",
}
FORBIDDEN = [r"gbvraju", r"day-\d", r"\bK[0-4]\b", r"PR #\d+", r"Q-K\d"]
ALLOWED_VARS = {"project", "date", "kit_version"}


def tracked() -> list[str]:
    out = subprocess.run(
        ["git", "ls-files", "-z"], cwd=KIT_ROOT, capture_output=True, text=True, check=True
    ).stdout
    return [p for p in out.split("\0") if p]


def lines(rel: str) -> list[str]:
    text = (KIT_ROOT / rel).read_text(encoding="utf-8")
    return [ln.strip() for ln in text.splitlines() if ln.strip() and not ln.startswith("#")]


def test_ac2_manifest_shape_and_version():
    """REQ-009 AC2: rule 6."""
    m = manifest()
    assert set(m) == {"kit_version", "verbatim", "templates", "rendered"}
    assert re.fullmatch(r"\d+\.\d+\.\d+", m["kit_version"])
    assert sorted(m["verbatim"]) == m["verbatim"]
    assert not set(m["verbatim"]) & set(m["templates"])


def test_ac2_every_manifest_path_exists():
    """REQ-009 AC2: rule 9."""
    m = manifest()
    for rel in m["verbatim"]:
        assert (KIT_ROOT / rel).is_file(), rel
    for src in m["templates"].values():
        assert (KIT_ROOT / src).is_file(), src


def test_ac2_law_files_are_all_in_the_manifest_and_kit_only_are_not():
    """REQ-009 AC2: rules 7 and 9."""
    m = manifest()
    verbatim = set(m["verbatim"])
    law = {p for p in tracked() if p.startswith(ROOTS) and p not in KIT_ONLY and p not in RENDERED}
    assert law | SINGLES == verbatim
    for rel in verbatim:
        assert not rel.startswith(("kit/", "tests/kit_dev/")) and rel not in KIT_ONLY


def test_ac2_rendered_files_are_codeowners_only():
    """REQ-009 AC2: rule 10."""
    assert set(manifest()["rendered"]) == RENDERED


def test_ac2_templates_use_only_allowed_variables_and_are_neutral():
    """REQ-009 AC2: rules 8 and 20."""
    for dest, src in manifest()["templates"].items():
        text = (KIT_ROOT / src).read_text(encoding="utf-8")
        assert set(re.findall(r"\{\{(\w+)\}\}", text)) <= ALLOWED_VARS, src
        for pat in FORBIDDEN:
            assert not re.search(pat, text), (src, pat)
        assert not re.findall(r"ADR-(?!0001)\d{4}", text), src
        assert dest


def test_ac2_verbatim_files_are_neutral():
    """REQ-009 AC2: rule 20."""
    for rel in manifest()["verbatim"]:
        text = (KIT_ROOT / rel).read_text(encoding="utf-8")
        for pat in FORBIDDEN:
            assert not re.search(pat, text), (rel, pat)


def test_ac2_kit_protected_list_is_template_plus_kit_only_entries():
    """REQ-009 AC2: rule 21."""
    template = lines(manifest()["templates"]["config/protected-paths.txt"])
    assert template == [
        "constitution/",
        "config/",
        ".claude/",
        ".github/",
        "docs/requirements.md",
        "CLAUDE.md",
        "scripts/agk/",
        "tests/kit/",
        "Makefile",
        "pyproject.toml",
    ]
    assert lines("config/protected-paths.txt") == template + ["kit/", "tests/kit_dev/"]


def test_ac2_templates_reviewers_protected_class_equals_template_list():
    """REQ-009 AC2: rule 21."""
    src = manifest()["templates"]["config/reviewers.yaml"]
    text = (KIT_ROOT / src).read_text(encoding="utf-8")
    match = re.search(r"protected:\s*\{paths: \[([^\]]*)\]", text)
    assert match
    paths = [p.strip() for p in match.group(1).split(",")]
    assert paths == lines(manifest()["templates"]["config/protected-paths.txt"])


def test_ac2_branch_rules_text_equals_kit_adr_decision_3():
    """REQ-009 AC2: rule 19."""
    rules = (KIT_ROOT / "kit" / "templates" / "branch-rules.txt").read_text(encoding="utf-8")
    adr = (KIT_ROOT / "docs" / "adr" / "0001-the-kit-governs-itself.md").read_text(encoding="utf-8")
    norm_adr = " ".join(adr.split())
    sentences = [" ".join(s.split()) for s in rules.strip().split("\n") if s.strip()]
    assert len(sentences) >= 2
    for sentence in sentences:
        assert sentence in norm_adr, sentence


def test_ac2_make_test_and_testpaths_cover_all_of_tests():
    """REQ-009 AC2: rule 18 (amended). The kit and an installed repository run `pytest tests`."""
    makefile = (KIT_ROOT / "Makefile").read_text(encoding="utf-8")
    assert "$(PY) -m pytest tests -q" in makefile
    template = manifest()["templates"]["pyproject.toml"]
    for rel in ("pyproject.toml", template):
        text = (KIT_ROOT / rel).read_text(encoding="utf-8").replace("{{", "").replace("}}", "")
        data = tomllib.loads(text)
        assert data["tool"]["pytest"]["ini_options"]["testpaths"] == ["tests"], rel


def test_ac2_kit_version_is_at_least_0_2_0_and_check_specs_is_wired():
    """REQ-009 AC2: installed content changed (pins, renderer, new check)."""
    m = manifest()
    assert tuple(int(x) for x in m["kit_version"].split(".")) >= (0, 2, 0)
    assert "scripts/agk/check_specs.py" in m["verbatim"]
    assert "tests/kit/test_check_specs.py" in m["verbatim"]
    makefile = (KIT_ROOT / "Makefile").read_text(encoding="utf-8")
    assert "scripts/agk/check_specs.py" in makefile


def test_ac2_adr_template_names_the_creation_commit_as_the_one_direct_commit():
    """REQ-009 AC2: decision 3 of the installed ADR-0001 records the one direct commit."""
    text = (KIT_ROOT / manifest()["templates"]["docs/adr/0001-adopt-agk.md"]).read_text(
        encoding="utf-8"
    )
    flat = " ".join(text.split())
    assert "one direct commit to the default branch is the repository's creation commit" in flat
    assert "everything else goes through a pull request" in flat.lower()


def test_ac2_readme_has_an_installing_section():
    """REQ-009 AC2"""
    text = (KIT_ROOT / "README.md").read_text(encoding="utf-8")
    assert "## Installing" in text
    flat = " ".join(text.split())
    assert "one first commit" in flat and "maintainer-approved" in flat
