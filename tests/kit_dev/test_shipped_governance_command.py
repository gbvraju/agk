"""Every shipped skill, role file, guide and template names a governance command that works in
both layouts (brief #1759, ADR-0737; REQ-078).

A clean project (`[kit] layout = "plugin"`) has no `Makefile` and no `agk.mk`, so a shipped text
that tells a session to run `make governance` or `make -f agk.mk agk-governance` names a step that
fails there. Each such mention carries the installed-project clause (the words `installed project`
close to it), or the whole text says that it describes an installed project (`INSTALLED_ONLY`). A
shipped skill cites only guides the plugin ships. Each failure names the path class and the file,
never the line.
"""

from __future__ import annotations

import re
import subprocess

from conftest import KIT_ROOT, manifest

# The shipped texts of the brief: skills, role files, guides and the templates of products.
CLASSES = ("skills/", ".claude/agents/", "docs/guides/", "kit/templates/")
# Brief #1841: also `make -C <scratch>` with a separate `-f agk.mk` span later in the sentence.
MAKE_FORM = re.compile(
    r"make governance|make -f agk\.mk agk-governance|make -C <[^>]*>[^.`]*`[^.]*?`-f agk\.mk"
)
CLAUSE = "installed project"
INSTALLED_ONLY = "This guide describes an installed project"
WINDOW = 300  # characters on each side of a mention in which the clause must stand
GUIDE_CITE = re.compile(r"docs/guides/[A-Za-z0-9_.-]+\.md")


def shipped(rel: str, listed: list[str]) -> bool:
    return any(rel.startswith(a) if a.endswith("/") else rel == a for a in listed)


def tracked() -> list[str]:
    out = subprocess.run(  # nosec B603 B607 - fixed argv, read-only
        ["git", "ls-files", *CLASSES], cwd=KIT_ROOT, capture_output=True, text=True, check=True
    ).stdout
    return sorted(line for line in out.splitlines() if line)


def shipped_texts() -> dict[str, str]:
    listed = manifest()["snapshot"]
    texts = {}
    for rel in tracked():
        if not shipped(rel, listed):
            continue
        try:
            texts[rel] = (KIT_ROOT / rel).read_text(encoding="utf-8")
        except (UnicodeDecodeError, FileNotFoundError):
            continue
    return texts


def path_class(rel: str) -> str:
    return next(c for c in CLASSES if rel.startswith(c))


def bare_mentions(text: str) -> int:
    """How many mentions of the make form stand without the installed-project clause."""
    if INSTALLED_ONLY in text:
        return 0
    count = 0
    for found in MAKE_FORM.finditer(text):
        near = text[max(0, found.start() - WINDOW) : found.end() + WINDOW]
        if CLAUSE not in near:
            count += 1
    return count


def failures_of(texts: dict[str, str]) -> list[str]:
    return [
        f"{path_class(rel)}: {rel} names the make form of the governance gate without the "
        "installed-project clause (setting: [kit] layout)"
        for rel, text in sorted(texts.items())
        if bare_mentions(text)
    ]


def uncovered_guides(texts: dict[str, str], listed: list[str]) -> list[str]:
    missing = set()
    for rel, text in texts.items():
        if rel.startswith("skills/"):
            missing |= {g for g in GUIDE_CITE.findall(text) if not shipped(g, listed)}
    return sorted(missing)


def test_req078_a_bare_make_form_is_caught_and_the_clause_clears_it():
    """REQ-078: the check of the check; a mention far from the clause still counts."""
    assert bare_mentions("then run `make governance`.") == 1
    assert bare_mentions("then run `make -f agk.mk agk-governance`.") == 1
    assert (
        bare_mentions("`kit_root.py governance` (in an installed project, `make governance`)") == 0
    )
    far = "in an installed project." + " x" * WINDOW + " then run `make governance`."
    assert bare_mentions(far) == 1
    assert bare_mentions(f"{INSTALLED_ONLY}.\n\n" + far) == 0
    old = (  # conductor.md before brief #1841: the make forms in separate code spans
        "- Run only `make -C <scratch> test`, `governance`, `-f agk.mk agk-governance` or "
        "`-f agk.mk agk-project-test` (prefer `agk.mk`, the kit's own file in every project)."
    )
    assert bare_mentions(old) == 1
    assert bare_mentions(old.replace("Run only", "In an installed project run only")) == 0
    assert bare_mentions("`make -C <scratch> test`. Then `-f agk.mk` elsewhere.") == 0
    found = failures_of({"skills/x/SKILL.md": "run `make governance`"})
    assert found and found[0].startswith("skills/: skills/x/SKILL.md ") and "`make" not in found[0]


def test_req078_an_unshipped_guide_cited_by_a_skill_is_caught():
    """REQ-078: the check of the check for the guides a skill cites."""
    texts = {
        "skills/x/SKILL.md": "see `docs/guides/a.md` and docs/guides/b.md",
        "kit/t.md": "docs/guides/c.md",
    }
    assert uncovered_guides(texts, ["docs/guides/a.md"]) == ["docs/guides/b.md"]
    assert uncovered_guides(texts, ["docs/guides/"]) == []


def test_req078_every_shipped_text_names_a_command_that_works_in_both_layouts():
    """REQ-078 (brief #1759 answer 1): no shipped text sends a clean project to a make target."""
    texts = shipped_texts()
    assert texts, "no shipped text found (setting: snapshot)"
    assert failures_of(texts) == []


def test_req078_every_guide_a_shipped_skill_cites_ships_with_the_plugin():
    """REQ-078 (brief #1759 answer 2): the next-step pointer names a file the session can read."""
    listed = manifest()["snapshot"]
    missing = uncovered_guides(shipped_texts(), listed)
    assert missing == [], (
        "docs/guides/: a cited guide is outside the plugin's list (setting: snapshot)"
    )
    for guide in (
        "docs/guides/planning.md",
        "docs/guides/testing.md",
        "docs/guides/getting-started.md",
    ):
        assert guide in listed and (KIT_ROOT / guide).is_file(), guide


def test_req078_the_skills_name_the_resolvers_gate():
    """REQ-078 (brief #1759 answer 1): the skills that ran the make form now name the resolver."""
    gate = 'python3 "${CLAUDE_PLUGIN_ROOT}/scripts/agk/kit_root.py" governance'
    for skill in ("design", "spec", "stack", "start", "upgrade", "vision"):
        text = (KIT_ROOT / "skills" / skill / "SKILL.md").read_text(encoding="utf-8")
        assert gate in text, f"skills/: skills/{skill}/SKILL.md"
