"""Tests of kit/manifest.json and kit/templates/ (SPEC-0001 rules 6-9, 19-21)."""

from __future__ import annotations

import re
import subprocess
import tomllib

from conftest import KIT_ROOT, manifest

# tests/kit/ is not a law root: the kit's own tests are not installed in targets (ADR-0052).
ROOTS = (".claude/", ".github/", "scripts/agk/")
KIT_ONLY = {
    "scripts/agk/init.py",
    "scripts/agk/adopt.py",
    "scripts/agk/kit_hashes.py",
    "scripts/agk/check_release.py",
    "scripts/agk/check_tag.py",
    "scripts/agk/changelog_fragments.py",
    "scripts/agk/upgrade.py",
    "scripts/agk/uninstall.py",
    "scripts/agk/new_spec.py",
    "scripts/agk/intake.py",
    "scripts/agk/ruleset.py",
    "scripts/agk/playbook.py",
    "scripts/agk/engines.py",
    "scripts/agk/design.py",
    "scripts/agk/shadow_count.py",
    "scripts/agk/pr_body.py",
    "scripts/agk/core_audit.py",
}
# Files under the law roots that belong to this repository only and are not installed in targets.
REPO_ONLY = {".github/ISSUE_TEMPLATE/stuck.md", ".github/workflows/agk-tag.yml"}
RENDERED = {".github/CODEOWNERS"}
SINGLES = {
    "CLAUDE.md",
    "Makefile",
    "agk.mk",
    ".gitignore",
    "constitution/principles.md",
    "docs/adr/TEMPLATE.md",
    "docs/specs/TEMPLATE.md",
    "docs/briefs/TEMPLATE.md",
    "config/review-checklist.md",
    "config/session-rules.md",
}
FORBIDDEN = [r"gbvraju", r"day-\d", r"\bK[0-4]\b", r"PR #\d+", r"Q-K\d"]
ALLOWED_VARS = {
    "project",
    "date",
    "kit_version",
    "default_branch",
    "test_dirs",
    "test_patterns",
    "existing_protected",
}


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
    assert set(m) == {
        "kit_version",
        "kit_tests",
        "verbatim",
        "experimental",
        "templates",
        "rendered",
        "adopt",
        "extendable",
    }
    assert m["kit_tests"] == "tests/kit" and (KIT_ROOT / m["kit_tests"]).is_dir()
    assert re.fullmatch(r"\d+\.\d+\.\d+", m["kit_version"])
    assert sorted(m["verbatim"]) == m["verbatim"]
    assert not set(m["verbatim"]) & set(m["templates"])


def test_ac2_every_manifest_path_exists():
    """REQ-009 AC2: rule 9."""
    m = manifest()
    for rel in [*m["verbatim"], *m["experimental"]]:
        assert (KIT_ROOT / rel).is_file(), rel
    for src in m["templates"].values():
        assert (KIT_ROOT / src).is_file(), src


def test_ac2_law_files_are_all_in_the_manifest_and_kit_only_are_not():
    """REQ-009 AC2: rules 7 and 9."""
    m = manifest()
    verbatim = set(m["verbatim"])
    optional = set(m["experimental"])
    assert not optional & verbatim
    law = {
        p
        for p in tracked()
        if p.startswith(ROOTS) and p not in KIT_ONLY and p not in RENDERED and p not in REPO_ONLY
    }
    assert (law - optional) | SINGLES == verbatim
    assert optional <= law
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
        "Makefile",
        "pyproject.toml",
        "agk.mk",
        "agk.toml",
    ]
    assert lines("config/protected-paths.txt") == template + [
        "tests/kit/",
        "kit/",
        "tests/kit_dev/",
        ".claude-plugin/",
        "skills/",
    ]


def test_ac2_templates_reviewers_protected_class_equals_template_list():
    """REQ-009 AC2: rule 21."""
    src = manifest()["templates"]["config/reviewers.yaml"]
    text = (KIT_ROOT / src).read_text(encoding="utf-8")
    match = re.search(r"protected:\s*\{paths: \[([^\]]*)\]", text)
    assert match
    paths = [p.strip() for p in match.group(1).split(",")]
    assert paths == lines(manifest()["templates"]["config/protected-paths.txt"])


def test_ac2_branch_rules_say_default_branch_and_match_the_kit_adr_apart_from_the_name():
    """REQ-009 AC2: rule 19 (amended). The ruleset named `main` in this repository's immutable
    ADR-0001 reads "ruleset for the default branch" in the printed text; the rest is equal."""
    rules = (KIT_ROOT / "kit" / "templates" / "branch-rules.txt").read_text(encoding="utf-8")
    adr = (KIT_ROOT / "docs" / "adr" / "0001-the-kit-governs-itself.md").read_text(encoding="utf-8")
    norm_adr = " ".join(adr.split())
    assert "The ruleset `main` is exactly:" in norm_adr  # the ADR itself is untouched
    sentences = [" ".join(s.split()) for s in rules.strip().split("\n") if s.strip()]
    assert len(sentences) >= 2
    assert sentences[0].startswith("The ruleset for the default branch is exactly: ")
    assert "ruleset `main`" not in " ".join(sentences)
    tail = sentences[0].split("is exactly: ", 1)[1]
    assert tail in norm_adr
    for sentence in sentences[1:]:
        assert sentence in norm_adr, sentence


def test_ac2_make_test_and_testpaths_cover_all_of_tests():
    """REQ-009 AC2: rule 18 (amended). `make test` runs agk-test then the project tests."""
    makefile = (KIT_ROOT / "Makefile").read_text(encoding="utf-8")
    assert "test: agk-test agk-project-test" in makefile
    for rel in ("agk.toml", manifest()["templates"]["agk.toml"]):
        cfg = tomllib.loads(
            (KIT_ROOT / rel).read_text(encoding="utf-8").replace("{{", "").replace("}}", "")
        )
        if rel == "agk.toml":
            # this repository's own tests are the kit tests, collected as `agk-test` collects them
            command = cfg["project_tests"]
            assert "AGK_KIT_TESTS=1" in command and "tests/kit tests/kit_dev" in command, rel
        else:
            assert "-m pytest tests -q" in cfg["project_tests"], rel
    template = manifest()["templates"]["pyproject.toml"]
    for rel in ("pyproject.toml", template):
        text = (KIT_ROOT / rel).read_text(encoding="utf-8").replace("{{", "").replace("}}", "")
        data = tomllib.loads(text)
        assert data["tool"]["pytest"]["ini_options"]["testpaths"] == ["tests"], rel


def test_ac2_kit_version_is_at_least_0_4_1_and_check_specs_is_wired():
    """REQ-009 AC2: installed content changed (pins, renderer, new check)."""
    m = manifest()
    assert tuple(int(x) for x in m["kit_version"].split(".")) >= (0, 4, 1)
    assert "scripts/agk/check_specs.py" in m["verbatim"]
    assert (KIT_ROOT / "tests/kit/test_check_specs.py").is_file()
    agk_mk = (KIT_ROOT / "agk.mk").read_text(encoding="utf-8")
    assert "scripts/agk/check_specs.py" in agk_mk


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
    text = (KIT_ROOT / "docs" / "guides" / "reference.md").read_text(encoding="utf-8")
    assert "## Installing" in text
    flat = " ".join(text.split())
    assert "one first commit" in flat and "maintainer-approved" in flat


def test_ac1_shared_layout_files_are_in_the_manifest_and_the_repository():
    """REQ-010 AC1: SPEC-0002 rules 5 and 10."""
    m = manifest()
    for rel in ("agk.mk", "scripts/agk/config.py"):
        assert rel in m["verbatim"], rel
    for rel in ("tests/kit/pytest.ini", "tests/kit/conftest.py"):
        assert (KIT_ROOT / rel).is_file() and rel not in m["verbatim"], rel
    assert "agk.toml" in m["templates"]
    toml = tomllib.loads((KIT_ROOT / "agk.toml").read_text(encoding="utf-8"))
    assert toml["default_branch"] == "main"
    assert "tests" in toml["lint_paths"]


def test_ac1_this_repository_makefile_is_thin_aliases():
    """REQ-010 AC1: SPEC-0002 rule 5 (the repository adopts agk.mk itself)."""
    makefile = (KIT_ROOT / "Makefile").read_text(encoding="utf-8")
    assert "include agk.mk" in makefile
    for alias in (
        "governance: agk-governance",
        "lint: agk-lint",
        "test: agk-test agk-project-test",
    ):
        assert alias in makefile
    assert "scripts/agk/check_" not in makefile


def test_ac1_adr_template_uses_the_default_branch_variable():
    """REQ-010 AC1: SPEC-0002 rule 8."""
    text = (KIT_ROOT / manifest()["templates"]["docs/adr/0001-adopt-agk.md"]).read_text()
    assert "{{default_branch}}" in text
    assert "ruleset `main`" not in text


def test_ac1_templates_carry_project_tests_and_no_pyproject_stamp():
    """REQ-010 AC1: SPEC-0002 rule 5 and SPEC-0001 rule 14 (amended)."""
    templates = manifest()["templates"]
    agk = (KIT_ROOT / templates["agk.toml"]).read_text(encoding="utf-8")
    assert "project_tests" in agk and "pytest tests" in agk and "exit $rc" in agk
    pyproject = (KIT_ROOT / templates["pyproject.toml"]).read_text(encoding="utf-8")
    assert "[tool.agk]" not in pyproject
    own = tomllib.loads((KIT_ROOT / "agk.toml").read_text(encoding="utf-8"))
    assert "pytest" in own["project_tests"] and "tests/kit" in own["project_tests"]


def test_ac1_adopt_section_shape_and_paths():
    """REQ-010 AC1: SPEC-0002 rules 4 and 11."""
    a = manifest()["adopt"]
    assert set(a) == {"skip", "blocks", "block_sources", "templates"}
    assert a["skip"] == ["Makefile"]
    assert a["block_sources"] == {
        ".gitattributes": "kit/templates/gitattributes",
        ".gitignore": "kit/templates/gitignore",
    }
    assert a["blocks"] == {
        ".gitignore": "hash",
        ".gitattributes": "hash",
        "CLAUDE.md": "html",
        ".github/PULL_REQUEST_TEMPLATE.md": "html",
        ".github/CODEOWNERS": "hash",
    }
    for src in a["templates"].values():
        assert (KIT_ROOT / src).is_file(), src
    assert "Makefile" not in a["templates"] and "pyproject.toml" not in a["templates"]
    sources = {rel: a["block_sources"].get(rel, rel) for rel in a["blocks"]}
    assert {src for rel, src in sources.items() if rel != ".github/CODEOWNERS"} <= (
        set(manifest()["verbatim"]) | set(a["block_sources"].values())
    )
    assert ".gitattributes" not in manifest()["verbatim"], "this repository must not carry it"


def test_ac1_adopt_templates_are_neutral_and_use_allowed_variables():
    """REQ-010 AC1: SPEC-0002 rules 9 and 13."""
    for src in manifest()["adopt"]["templates"].values():
        text = (KIT_ROOT / src).read_text(encoding="utf-8")
        assert set(re.findall(r"\{\{(\w+)\}\}", text)) <= ALLOWED_VARS, src
        for pat in FORBIDDEN:
            assert not re.search(pat, text), (src, pat)
        assert not re.findall(r"ADR-(?!0001)\d{4}", text), src


def test_ac1_adopt_protected_template_and_reviewers_are_equal_and_exclude_project_files():
    """REQ-010 AC1: SPEC-0002 rule 12 (adopted mode)."""
    templates = manifest()["adopt"]["templates"]
    listed = lines(templates["config/protected-paths.txt"])
    assert listed == [
        "constitution/",
        "config/",
        ".claude/",
        ".github/",
        "docs/requirements.md",
        "CLAUDE.md",
        "scripts/agk/",
        "agk.mk",
        "agk.toml",
    ]
    text = (KIT_ROOT / templates["config/reviewers.yaml"]).read_text(encoding="utf-8")
    match = re.search(r"protected:\s*\{paths: \[([^\]]*)\]", text)
    assert [p.strip() for p in match.group(1).split(",")] == listed
    assert "Makefile" not in text and "pyproject.toml" not in text


def test_ac1_adopt_agk_toml_template_has_empty_project_tests_and_adopt_mode():
    """REQ-010 AC1: SPEC-0002 rules 5 and 9."""
    src = manifest()["adopt"]["templates"]["agk.toml"]
    text = (KIT_ROOT / src).read_text(encoding="utf-8")
    assert 'mode = "adopt"' in text and 'project_tests = ""' in text
    assert "{{test_dirs}}" in text and "{{test_patterns}}" in text


def test_ac1_adopt_adr_template_has_no_creation_commit_claim():
    """REQ-010 AC1: SPEC-0002 rule 13."""
    src = manifest()["adopt"]["templates"]["docs/adr/0001-adopt-agk.md"]
    flat = " ".join((KIT_ROOT / src).read_text(encoding="utf-8").split())
    assert "creation commit" not in flat
    assert "first governed change" in flat and "not governed" in flat
    assert "{{existing_protected}}" in flat


def test_scanner_excludes_template_covers_each_tool_and_each_kit_path():
    """REQ-010: ADR-0010 decision 3. One source file; kit-only (not installed)."""
    text = (KIT_ROOT / "kit" / "templates" / "scanner-excludes.txt").read_text(encoding="utf-8")
    for tool in ("bandit", "flake8", "pylint", "mypy"):
        line = next(ln for ln in text.splitlines() if ln.strip().startswith(f"{tool}:"))
        assert "scripts/agk" in line and ".claude" in line, tool
        assert "tests/kit" not in line, tool
    assert "tests/kit" not in text
    installed = set(manifest()["verbatim"]) | set(manifest()["templates"].values())
    assert "kit/templates/scanner-excludes.txt" not in installed


def test_readme_existing_scanners_section_quotes_the_template():
    """REQ-010: ADR-0010 decision 3. The README quotes the template line for line."""
    readme = (KIT_ROOT / "docs" / "guides" / "reference.md").read_text(encoding="utf-8")
    assert "## Existing scanners" in readme
    section = readme.split("## Existing scanners", 1)[1].split("\n## ", 1)[0]
    template = (KIT_ROOT / "kit" / "templates" / "scanner-excludes.txt").read_text(encoding="utf-8")
    for line in template.rstrip().splitlines():
        assert line in section, line


def test_ac1_this_repository_records_the_kit_version_it_ships():
    """REQ-021 AC1: ADR-0050 (Q-K4-201). agk.toml and kit/manifest.json name one version.

    Every kit bump updates both, so this repository's own report names its version.
    """
    toml = tomllib.loads((KIT_ROOT / "agk.toml").read_text(encoding="utf-8"))
    assert toml.get("version") == manifest()["kit_version"]


def test_ac2_the_kit_tests_are_not_installed_and_gitattributes_marks_the_scripts():
    """REQ-009 AC2: lean install (ADR-0052): nothing under tests/ is installed."""
    m = manifest()
    listed = [*m["verbatim"], *m["experimental"], *m["templates"], *m["adopt"]["templates"]]
    assert not [p for p in listed if p.startswith("tests/")]
    assert (KIT_ROOT / "tests" / "kit").is_dir() and tracked()
    text = (KIT_ROOT / m["templates"][".gitattributes"]).read_text(encoding="utf-8")
    assert "scripts/agk/** linguist-generated=true" in text.splitlines()
    # ADR-0084: this repository marks only the logs, never its own scripts as generated.
    own = (KIT_ROOT / ".gitattributes").read_text(encoding="utf-8")
    assert "linguist-generated" not in own


UNION_LOGS = (
    "docs/runs/decisions-log.md",
    "docs/runs/residuals.md",
    "docs/runs/architect-catches-*.md",
)


def _rules(text: str) -> list[str]:
    return [ln for ln in text.splitlines() if ln.strip() and not ln.startswith("#")]


def test_adr0084_the_template_and_this_repository_mark_the_append_only_logs_merge_union():
    """REQ-032 AC3: SPEC-0025 rule 3 (ADR-0084): the append-only logs merge by union."""
    m = manifest()
    template = (KIT_ROOT / m["templates"][".gitattributes"]).read_text(encoding="utf-8")
    own = (KIT_ROOT / ".gitattributes").read_text(encoding="utf-8")
    for text in (template, own):
        rules = _rules(text)
        for log in UNION_LOGS:
            assert f"{log} merge=union" in rules
        assert not [r for r in rules if "requirements.md" in r]
        assert len([r for r in rules if "merge=" in r]) == len(UNION_LOGS)
