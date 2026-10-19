"""Kit-only tests of the docs check: the README and the guides name only what exists (L1).

`problems(root, files)` reads every fenced code block, indented code block and inline code span of
the given Markdown files and reports a script under `scripts/agk/`, a skill `/agk:<name>`, a make
target or a workflow file that does not exist under `root`, and every relative link to a file that
does not exist. The real documents are checked against this repository; the check itself is tested
on small trees in `tmp_path`. No model, no network.
"""

from __future__ import annotations

import re
from pathlib import Path

from conftest import KIT_ROOT

FENCE = re.compile(r"(?ms)^(?P<mark>`{3,}|~{3,})[^\n]*\n(?P<body>.*?)^(?P=mark)[ \t]*$")
INLINE = re.compile(r"`([^`\n]+)`")
INDENTED = re.compile(r"(?m)^(?: {4}|\t)(\S.*)$")
LINK = re.compile(r"\]\(([^)\s]+)\)")
SCRIPT = re.compile(r"scripts/agk/[A-Za-z0-9_]+\.py")
SKILL = re.compile(r"(?<![\w/])/agk:([a-z][a-z-]*)")
MAKE = re.compile(r"\bmake(?: -f (\S+))? ([A-Za-z][\w-]*)")
WORKFLOW = re.compile(r"(?:\.github/workflows/)?([A-Za-z0-9_-]+\.yml)\b")
TARGET = re.compile(r"(?m)^([A-Za-z][\w-]*):")


def doc_files(root: Path) -> list[Path]:
    found = [root / "README.md", *sorted((root / "docs" / "guides").glob("*.md"))]
    return [p for p in found if p.is_file()]


def code_text(text: str) -> list[str]:
    """Every fenced block, indented code line and inline span of a Markdown text."""
    out = [m.group("body") for m in FENCE.finditer(text)]
    rest = FENCE.sub("", text)
    out += INDENTED.findall(rest)
    out += INLINE.findall(rest)
    return out


def make_targets(root: Path, name: str) -> set[str]:
    try:
        return set(TARGET.findall((root / name).read_text(encoding="utf-8")))
    except OSError:
        return set()


def problems(root: Path, files: list[Path]) -> list[str]:
    out: list[str] = []
    skills = {p.parent.name for p in (root / "skills").glob("*/SKILL.md")}
    workflows = {p.name for p in (root / ".github" / "workflows").glob("*.yml")}
    for doc in files:
        rel = doc.relative_to(root).as_posix()
        text = doc.read_text(encoding="utf-8")
        for chunk in code_text(text):
            for script in SCRIPT.findall(chunk):
                if not (root / script).is_file():
                    out.append(f"{rel}: names a script that does not exist: {script}")
            for skill in SKILL.findall(chunk):
                if skill not in skills:
                    out.append(f"{rel}: names a skill that does not exist: /agk:{skill}")
            for makefile, target in MAKE.findall(chunk):
                if target not in make_targets(root, makefile or "Makefile"):
                    out.append(f"{rel}: names a make target that does not exist: {target}")
            for name in WORKFLOW.findall(chunk):
                if name not in workflows:
                    out.append(f"{rel}: names a workflow file that does not exist: {name}")
        for link in LINK.findall(FENCE.sub("", text)):
            if re.match(r"(?:[a-z][a-z0-9+.-]*:|#)", link):
                continue
            target = (doc.parent / link.split("#", 1)[0]).resolve()
            if not target.exists():
                out.append(f"{rel}: links to a file that does not exist: {link}")
    return out


def tree(tmp_path: Path) -> Path:
    """A small repository that has one script, one skill, two make targets and one workflow."""
    files = {
        "scripts/agk/tool.py": "",
        "skills/go/SKILL.md": "---\nname: go\n---\n",
        "Makefile": "governance: agk-governance\ntest: agk-test\n",
        "agk.mk": "agk-governance:\n\ttrue\n",
        ".github/workflows/w.yml": "name: w\n",
        "docs/guides/other.md": "# Other\n",
    }
    for rel, text in files.items():
        path = tmp_path / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    return tmp_path


def check(root: Path, body: str) -> list[str]:
    doc = root / "docs" / "guides" / "page.md"
    doc.write_text(body, encoding="utf-8")
    return problems(root, [doc])


def test_ac1_the_real_readme_and_guides_name_only_what_exists():
    """REQ-020 AC1: launch docs rule 4 (L1)."""
    files = doc_files(KIT_ROOT)
    names = {p.relative_to(KIT_ROOT).as_posix() for p in files}
    assert {"README.md", "docs/guides/getting-started.md", "docs/guides/reference.md"} <= names
    assert problems(KIT_ROOT, files) == []


def test_ac1_a_valid_page_passes(tmp_path):
    """REQ-020 AC1: launch docs rule 4 (L1)."""
    body = (
        "Run `python3 scripts/agk/tool.py`, then `make governance` and "
        "`make -f agk.mk agk-governance`.\n\n"
        "```\n/agk:go\nmake test\n```\n\n    make governance\n\n"
        "See `w.yml`, `.github/workflows/w.yml` and [the other page](other.md#top).\n"
    )
    assert check(tree(tmp_path), body) == []


def test_ac1_it_fails_on_a_script_that_does_not_exist(tmp_path):
    """REQ-020 AC1: launch docs rule 4 (L1)."""
    found = check(tree(tmp_path), "Run `python3 scripts/agk/missing.py`.\n")
    assert found == [
        "docs/guides/page.md: names a script that does not exist: scripts/agk/missing.py"
    ]


def test_ac1_it_fails_on_a_skill_that_does_not_exist(tmp_path):
    """REQ-020 AC1: launch docs rule 4 (L1)."""
    found = check(tree(tmp_path), "```\n/agk:nope\n```\n")
    assert found == ["docs/guides/page.md: names a skill that does not exist: /agk:nope"]


def test_ac1_it_fails_on_a_make_target_that_does_not_exist(tmp_path):
    """REQ-020 AC1: launch docs rule 4 (L1)."""
    root = tree(tmp_path)
    assert len(check(root, "Run `make deploy`.\n")) == 1
    assert len(check(root, "    make -f agk.mk agk-deploy\n")) == 1
    # a target of agk.mk is not a target of the Makefile
    assert len(check(root, "Run `make agk-governance`.\n")) == 1


def test_ac1_it_fails_on_a_workflow_file_that_does_not_exist(tmp_path):
    """REQ-020 AC1: launch docs rule 4 (L1)."""
    root = tree(tmp_path)
    assert check(root, "See `.github/workflows/gone.yml`.\n") == [
        "docs/guides/page.md: names a workflow file that does not exist: gone.yml"
    ]
    assert len(check(root, "```\nstart gone.yml\n```\n")) == 1


def test_ac1_it_fails_on_a_relative_link_to_a_missing_file(tmp_path):
    """REQ-020 AC1: launch docs rule 4 (L1)."""
    root = tree(tmp_path)
    assert check(root, "[x](missing.md) and [y](../../absent/file.md#top)\n") == [
        "docs/guides/page.md: links to a file that does not exist: missing.md",
        "docs/guides/page.md: links to a file that does not exist: ../../absent/file.md#top",
    ]
    assert check(root, "[a](https://example.org/x) [b](#here) [c](other.md)\n") == []


def test_ac1_prose_outside_code_is_not_read_as_a_command(tmp_path):
    """REQ-020 AC1: launch docs rule 4 (L1): `make sure` in a sentence is not a make target."""
    assert (
        check(tree(tmp_path), "Make sure you run /agk:nope and scripts/agk/missing.py first.\n")
        == []
    )


def test_ac1_the_guides_hold_what_the_launch_brief_asks(tmp_path):
    """REQ-020 AC1: launch docs rules 1 to 3 (L1)."""
    readme = (KIT_ROOT / "README.md").read_text(encoding="utf-8")
    assert len(readme.splitlines()) <= 150
    order = [
        readme.index(h)
        for h in (
            "# agk",
            "## Who it is for",
            "## The 10-minute path",
            "## What you get each week",
            "## Honest limits",
            "## The guides",
        )
    ]
    assert order == sorted(order)
    assert "docs/guides/getting-started.md" in readme and "docs/guides/reference.md" in readme
    guide = (KIT_ROOT / "docs" / "guides" / "getting-started.md").read_text(encoding="utf-8")
    steps = [
        "claude plugin marketplace add",
        "claude plugin install",
        "/agk:init",
        "/agk:ruleset",
        "/agk:start",
        "/agk:spec",
        "claude --agent architect",
        "Verdict: cleared",
    ]
    where = [guide.index(s) for s in steps]
    assert where == sorted(where)
    trouble = guide[guide.index("## When something goes wrong") :]
    for needle in ("4 hours 20 minutes", "fork", "Issues", "admin", "not-proven"):
        assert needle in trouble, needle


def test_ac1_the_stuck_form_asks_the_five_things_and_sets_its_label():
    """REQ-020 AC1: launch docs rule 3 (L1)."""
    text = (KIT_ROOT / ".github" / "ISSUE_TEMPLATE" / "stuck.md").read_text(encoding="utf-8")
    head = text.split("---")[1]
    assert re.search(r"(?m)^labels: agk-stuck$", head)
    assert re.findall(r"(?m)^## (.+)$", text) == [
        "Which guide",
        "Which step number",
        "What I typed",
        "What I saw",
        "What I expected",
    ]


def test_ac1_the_l2_guides_hold_what_the_launch_brief_asks():
    """REQ-020 AC1: launch docs L2 rules 1 to 4."""
    guides = KIT_ROOT / "docs" / "guides"
    owner = (guides / "product-owner.md").read_text(encoding="utf-8")
    for needle in ("Monday", "07:13 UTC", "issues/88", "unknown"):
        assert needle in owner, needle
    sections = ("Delivered", "Proven", "Needs you", "At risk", "Cost")
    where = [owner.index(f"| {s} |") for s in sections]
    assert where == sorted(where)
    for kind in (
        "Draft spec",
        "Proposed ADR",
        "Question",
        "has had no verdict",
        "Overdue",
        "is planned",
    ):
        assert kind in owner, kind
    assert len(re.findall(r"(?m)^\d\. ", owner)) == 5
    existing = (guides / "existing-codebase.md").read_text(encoding="utf-8")
    heads = re.findall(r"(?m)^## Step (\d)\. (.+)$", existing)
    assert [h[0] for h in heads] == ["1", "2", "3", "4", "5"]
    needles = {
        "1": "/agk:adopt",
        "2": "/agk:spec",
        "3": "unchanged",
        "4": "project_tests",
        "5": "tests first",
    }
    for number, needle in needles.items():
        body = existing.split(f"## Step {number}.", 1)[1].split("\n## ", 1)[0]
        assert needle in body, (number, needle)
    assert "skipped" in existing and "REQ-" in existing
    security = (guides / "security.md").read_text(encoding="utf-8")
    for needle in (
        "What AGK stores",
        "Where your code and prompts go",
        "Credentials",
        "What each workflow may write",
        "The architect guard",
        "cannot prevent",
        "secrets.GITHUB_TOKEN",
    ):
        assert needle in security, needle


def test_ac1_the_security_page_lists_every_workflow_and_its_permissions():
    """REQ-020 AC1: launch docs L2 rule 3 (each statement points to the file that makes it true)."""
    security = (KIT_ROOT / "docs" / "guides" / "security.md").read_text(encoding="utf-8")
    for workflow in sorted((KIT_ROOT / ".github" / "workflows").glob("*.yml")):
        assert f"`{workflow.name}`" in security, workflow.name
        text = workflow.read_text(encoding="utf-8")
        writes = re.search(r"(?m)^  (\w[\w-]*): write$", text)
        row = next(ln for ln in security.splitlines() if ln.startswith(f"| `{workflow.name}`"))
        assert ("write" in row) == bool(writes), workflow.name
