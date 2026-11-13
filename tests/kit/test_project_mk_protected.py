"""A project's own `project.mk` stays protected (brief #1155, ADR-0491, REQ-001).

Answer 1: an init project's `config/protected-paths.txt` and `classes.protected.paths` of its
`config/reviewers.yaml` list `project.mk` right after `Makefile`, and `reviewers.py --check` still
passes; the adopt templates list neither. Answer 2: an upgrade refused over an edited `Makefile`
prints the fix line with its protection clause. Answer 3: the guide says it where it describes
`project.mk`. Fixtures in `tmp_path`, invented data, no network.
"""

from __future__ import annotations

from pathlib import Path

import reviewers
import upgrade

ROOT = Path(__file__).resolve().parents[2]
INIT = ("kit/templates/protected-paths.txt", "kit/templates/reviewers.yaml")
ADOPT = ("kit/templates/protected-paths.adopt.txt", "kit/templates/reviewers.adopt.yaml")
CLAUSE = (
    "and, where Makefile is protected, add project.mk to config/protected-paths.txt and "
    "config/reviewers.yaml in the same pull request"
)


def text(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def entries(rel: str) -> list[str]:
    return [ln.strip() for ln in text(rel).splitlines() if ln.strip() and not ln.startswith("#")]


def protected_class(rel: str) -> list[str]:
    return list(reviewers.parse(text(rel))["classes"]["protected"]["paths"])


# --- answer 1: the init templates ----------------------------------------------------------------


def test_req001_init_protected_paths_list_project_mk_right_after_makefile():
    paths = entries(INIT[0])
    assert paths.count("project.mk") == 1
    assert paths.index("project.mk") == paths.index("Makefile") + 1


def test_req001_init_reviewers_protected_class_lists_project_mk_right_after_makefile():
    paths = protected_class(INIT[1])
    assert paths.count("project.mk") == 1
    assert paths.index("project.mk") == paths.index("Makefile") + 1
    assert paths == entries(INIT[0])


def test_req001_a_fresh_init_install_still_passes_the_reviewers_check(repo):
    repo.write("config/protected-paths.txt", text(INIT[0]))
    repo.write("config/reviewers.yaml", text(INIT[1]).replace("@REPLACE-ME", "@ada"))
    proc = repo.run("reviewers.py", "--check")
    assert proc.returncode == 0, proc.stdout


# --- answer 1: the adopt templates stay as they are ----------------------------------------------


def test_req001_adopt_templates_protect_neither_makefile_nor_project_mk():
    for paths in (entries(ADOPT[0]), protected_class(ADOPT[1])):
        assert "project.mk" not in paths and "Makefile" not in paths


# --- answer 2: the upgrade's fix line ------------------------------------------------------------


def test_req001_the_refusal_over_an_edited_makefile_prints_the_protection_clause():
    plan = upgrade.Plan("1.0.0", "2.0.0", "init")
    plan.items = [upgrade.Item("Makefile", "conflict", " (differs)")]
    lines = [ln for ln in upgrade.report(plan, False) if "project.mk" in ln]
    assert len(lines) == 1
    line = lines[0]
    assert line.startswith("fix: move the project's own make targets from Makefile to project.mk")
    assert CLAUSE in line and line.endswith("then run again")


def test_req001_a_refusal_over_another_file_prints_no_protection_clause():
    plan = upgrade.Plan("1.0.0", "2.0.0", "init")
    plan.items = [upgrade.Item("CLAUDE.md", "conflict", " (differs)")]
    assert not any(CLAUSE in ln for ln in upgrade.report(plan, False))


# --- answer 3: the guide -------------------------------------------------------------------------


def test_req001_the_guide_says_project_mk_stays_protected():
    guide = text("docs/guides/getting-started.md")
    at = guide.index("**Your own make targets go in `project.mk`.**")
    bullet = guide[at : guide.index("\n- **", at + 1)]
    flat = " ".join(bullet.split())
    assert "`config/protected-paths.txt`" in flat and "`config/reviewers.yaml`" in flat
    assert "protect" in flat.split("`project.mk`.**", 1)[1]

