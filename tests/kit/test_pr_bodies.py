"""`Brief: none (design)` and `Brief: none (spec)` in a pull request body (brief #273, field note).

A pull request that answers no brief and changes only `docs/design/`, or only `docs/specs/` and
`docs/requirements.md`, may say so with `Brief: none (design)` or `Brief: none (spec)` where the
repository has an open brief. Any other change keeps needing `Brief: #n`. The changed files are read
from git against the base (the merge checkout of the workflow sets `AGK_BASE`); no network.
Invented repositories in `tmp_path`. REQ-020.
"""

from __future__ import annotations

import json

import pytest

BRIEFS = [{"number": 7, "labels": [{"name": "agk-brief"}]}]


def body(brief: str) -> str:
    return (
        f"Brief: {brief}\nAdvances: REQ-001\n"
        "Build-state row: 2026-10-29 REQ-001 planned (unchanged)\n"
        "Summary: Adds a page design for the owner to look at.\n"
    )


@pytest.fixture
def based(repo):
    repo.commit({"agk.toml": 'default_branch = "main"\n', "README.md": "x\n"}, "base")
    repo.branch()
    repo.write("briefs.json", json.dumps(BRIEFS))
    repo.git("add", "briefs.json")
    repo.git("commit", "-q", "-m", "the saved copy")
    repo.git("branch", "-f", "main", "HEAD")
    return repo


def check(repo, text: str, **env: str):
    env = {"AGK_BASE": "main", **env}
    return repo.run("check_pr_body.py", "--issues", "briefs.json", "-", stdin=text, **env)


@pytest.mark.parametrize(
    ("form", "files"),
    [
        (
            "none (design)",
            {"docs/design/theme.md": "t\n", "docs/design/mockups/a/index.html": "<p>\n"},
        ),
        ("none (spec)", {"docs/specs/0002-x.md": "s\n", "docs/requirements.md": "r\n"}),
        ("none (spec)", {"docs/specs/0002-x.md": "s\n"}),
    ],
)
def test_a_none_form_passes_for_a_change_of_only_its_paths(based, form, files):
    """REQ-020: the field note of brief #273 (design and spec pull requests answer no brief)."""
    based.commit(files)
    proc = check(based, body(form))
    assert proc.returncode == 0, proc.stdout
    assert proc.stdout == "ok pr-body\n"


@pytest.mark.parametrize(
    ("form", "files"),
    [
        ("none (design)", {"docs/design/theme.md": "t\n", "scripts/x.py": "x\n"}),
        ("none (design)", {"docs/specs/0002-x.md": "s\n"}),
        ("none (spec)", {"docs/specs/0002-x.md": "s\n", "docs/runs/residuals.md": "a\n"}),
        ("none (spec)", {"docs/design/theme.md": "t\n"}),
    ],
)
def test_a_none_form_fails_for_any_other_change_naming_the_rule_and_the_path_classes(
    based, form, files
):
    """REQ-020: brief #273 (the none forms are for those paths only; the message names no file)."""
    based.commit(files)
    proc = check(based, body(form))
    assert proc.returncode == 1
    assert "FAIL pr-body: rule 9: 'Brief: none" in proc.stdout
    assert "docs/design/" in proc.stdout and "docs/specs/" in proc.stdout
    for name in files:
        if name.startswith(("scripts/", "docs/runs/")):
            assert name not in proc.stdout


def test_a_none_form_with_nothing_changed_fails(based):
    """REQ-020: brief #273 (an empty change is not a design or a spec change)."""
    proc = check(based, body("none (design)"))
    assert proc.returncode == 1 and "rule 9" in proc.stdout


def test_an_uncommitted_change_counts_as_the_check_reads_the_work_tree(based):
    """REQ-020: brief #273 (the printed body is checked before the commit is made)."""
    based.write("docs/design/theme.md", "t\n")
    assert check(based, body("none (design)")).returncode == 0
    based.write("notes.txt", "n\n")
    assert check(based, body("none (design)")).returncode == 1


@pytest.mark.parametrize("brief", ["none", "none (adr)", "none(design)", "#7 none (spec)", "# 7"])
def test_other_forms_still_fail(based, brief):
    """REQ-020: SPEC-0034 rule 9 (only `#n` and the two none forms)."""
    based.commit({"docs/specs/0002-x.md": "s\n"})
    proc = check(based, body(brief))
    assert proc.returncode == 1 and "rule 9" in proc.stdout


def test_brief_n_passes_as_before_and_without_an_open_brief_no_line_is_needed(based):
    """REQ-020: SPEC-0034 rule 9 unchanged."""
    based.commit({"scripts/x.py": "x\n"})
    assert check(based, body("#7")).returncode == 0
    based.write("briefs.json", "[]")
    no_brief = body("#7").replace("Brief: #7\n", "")
    assert check(based, no_brief).returncode == 0


def test_without_a_base_a_none_form_fails_and_never_crashes(based):
    """REQ-020: brief #273 (the changed files cannot be read, so the form cannot be shown true)."""
    based.commit({"docs/design/theme.md": "t\n"})
    proc = check(based, body("none (design)"), AGK_BASE="no-such-ref")
    assert proc.returncode == 1 and "rule 9" in proc.stdout and "Traceback" not in proc.stderr


# --- the verdict on 2c9d862, Q-273-1: the documents a spec or design pull request also carries ----

AMEND = "docs/runs/proposed-spec-amendments-3.md"
LOG = "docs/runs/decisions-log.md"


@pytest.mark.parametrize(
    ("form", "files"),
    [
        (
            "none (spec)",
            {"docs/specs/0002-x.md": "s\n", "docs/adr/0003-x.md": "a\n", AMEND: "p\n", LOG: "l\n"},
        ),
        ("none (spec)", {"docs/requirements.md": "r\n", "docs/adr/0003-x.md": "a\n"}),
        ("none (design)", {"docs/design/theme.md": "t\n", "docs/adr/0003-x.md": "a\n", LOG: "l\n"}),
    ],
)
def test_a_none_form_also_takes_an_adr_the_amendments_and_the_decisions_log(based, form, files):
    """REQ-020: brief #273, Q-273-1 as answered (documents only, never code)."""
    based.commit(files)
    proc = check(based, body(form))
    assert proc.returncode == 0, proc.stdout


@pytest.mark.parametrize("form", ["none (spec)", "none (design)"])
@pytest.mark.parametrize(
    "extra",
    [
        {"scripts/x.py": "x\n"},
        {"frontend/app.js": "x\n"},
        {"docs/runs/proposed-spec-amendments-3.txt": "p\n"},
        {"docs/runs/proposed-spec-amendments/3.md": "p\n"},
        {"docs/runs/residuals.md": "r\n"},
    ],
)
def test_code_or_any_other_path_beside_them_fits_neither_form(based, form, extra):
    """REQ-020: brief #273, Q-273-1 (the amendments file by its pattern, not a prefix)."""
    own = {"docs/specs/0002-x.md": "s\n"} if form == "none (spec)" else {"docs/design/a.md": "t\n"}
    based.commit({**own, "docs/adr/0003-x.md": "a\n", **extra})
    proc = check(based, body(form))
    assert proc.returncode == 1 and "rule 9" in proc.stdout
    assert "proposed-spec-amendments-*.md" in proc.stdout


@pytest.mark.parametrize("form", ["none (spec)", "none (design)"])
def test_the_shared_documents_alone_fit_neither_form(based, form):
    """REQ-020: brief #273 (a change of only an ADR or the log is not a spec or a design change)."""
    based.commit({"docs/adr/0003-x.md": "a\n", AMEND: "p\n", LOG: "l\n"})
    assert check(based, body(form)).returncode == 1
