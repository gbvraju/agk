"""SPEC-0025 (parallel pull requests) folded into SPEC-0034 (parallel builders) (brief #387, ADR-0246).

The rules of SPEC-0025 move into a new section of SPEC-0034's `## Rules`, rule n of SPEC-0025
becoming rule n + 16 there (15 and 16 are left to the new rules that amendments 88 and 89 propose),
their text unchanged, and rule 8 in the text SPEC-0028 amended it to (amendment 50, item 2).
SPEC-0025 keeps its number and history and holds one line per old rule, `N. Now SPEC-0034 rule M.`.
The text each old rule had is pinned below by its SHA-256, read from the commit where SPEC-0025
last changed before the fold; where that commit is in the history, the pins are checked against it.
Files and git only: no network, no model.
"""

from __future__ import annotations

import hashlib
import re
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SPEC_0025 = "docs/specs/0025-a-team-can-run-independent-pull-requests-in-parallel-without.md"
SPEC_0034 = "docs/specs/0034-a-team-sets-how-many-builder-sessions-run-at-once-and-agk-ha.md"
AMENDMENT = "docs/runs/proposed-spec-amendments-108.md"
AMENDMENT_50 = "docs/runs/proposed-spec-amendments-50.md"
BEFORE = "ab1d6aeb3d9d0332054caef625d1ea7dea9e3d21"  # SPEC-0025's last change before the fold
OFFSET = 16
RULE = re.compile(r"^(\d+[a-z]?)\. (.*)$")
POINTER = re.compile(r"^(\d+)\. Now SPEC-0034 rule (\d+)\.$")

# rule of SPEC-0025 -> (its bold title, the first 16 hex digits of the SHA-256 of its text after "N. ")
OLD = {
    1: ("Duplicate numbers fail.", "730cf2034738dc30"),
    2: ("Renumbering is a command, never a hand edit.", "42f0623bc47e2b5b"),
    3: ("The append-only logs merge as a union.", "d9a2da854e235da3"),
    4: ("No self-clearance.", "b9f06490a66b1c1c"),
    5: ("Declared dependence.", "9711ae49ab756e66"),
    6: ("The mode.", "50757082ad9d2aa7"),
    7: ("The workflow reads and writes files only.", "8d13b3bbfcf9902c"),
    8: ("This repository.", "fec9d801c92a84d9"),
    9: ("Not built.", "49dd7f699593fe4f"),
    10: ("How it is built.", "c9f18d66964cdffd"),
    11: ("The tests.", "b39f4cf6a236421a"),
}
# Rule 8 keeps its first two sentences; its last one (the release model, left to a later intake)
# becomes the text of amendment 50 item 2, the release model SPEC-0028 gave it.
RULE_8_KEPT = (
    "**This repository.** Parts 1 to 5 are built for every project. After they are released a "
    "separate pull request switches this repository to `flow` by an ADR; until then this repository "
    "stays strict, with the maintainers' docs-only exception of 2026-10-24."
)
RULE_8_OLD_TAIL = (
    "The release model in answer 7 (kit build pull requests do not bump the version in flow mode; one "
    "release pull request bumps `agk.toml`, `kit/manifest.json` and the plugin together and moves an "
    "Unreleased changelog section) is a later intake of this repository only and is not built here."
)
RULE_8_NEW_LEAD = "The release model, as SPEC-0028 amended it (amendment 50, item 2): "


def digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def rules(text: str) -> dict[str, str]:
    """Rule number -> its text after `N. `, for every numbered line of the `## Rules` section."""
    found: dict[str, str] = {}
    inside = False
    for line in text.splitlines():
        if line.startswith("## "):
            inside = line.strip() == "## Rules"
            continue
        match = RULE.match(line) if inside else None
        if match:
            found.setdefault(match.group(1), match.group(2))
    return found


def amendment_50_release_model() -> str:
    """The text of amendment 50 item 2 after its bold title, its wrapped lines joined."""
    lines = read(AMENDMENT_50).splitlines()
    start = next(i for i, ln in enumerate(lines) if ln.startswith("2. **SPEC-0025 rule 8"))
    item = [lines[start]]
    for ln in lines[start + 1 :]:
        if not ln.startswith("   "):
            break
        item.append(ln.strip())
    return re.sub(r"^2\. \*\*[^*]+\*\* ", "", " ".join(item))


def expected_rule_8() -> str:
    return f"{RULE_8_KEPT} {RULE_8_NEW_LEAD}{amendment_50_release_model()}"


def old_text_at(commit: str) -> str | None:
    proc = subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
        ["git", "show", f"{commit}:{SPEC_0025}"], cwd=ROOT, capture_output=True, text=True
    )
    return proc.stdout if proc.returncode == 0 else None


def test_the_pins_are_the_text_spec_0025_had_before_the_fold():
    """Brief #387 answer 5 (REQ-041): the pinned digests are those of SPEC-0025's rules before it."""
    old = old_text_at(BEFORE)
    if old is None:
        pytest.skip("the commit before the fold is not in this clone's history")
    found = rules(old)
    assert sorted(found, key=int) == [str(n) for n in OLD]
    for n, (title, pin) in OLD.items():
        assert found[str(n)].startswith(f"**{title}**")
        assert digest(found[str(n)]) == pin, f"SPEC-0025 rule {n}"
    assert found["8"] == f"{RULE_8_KEPT} {RULE_8_OLD_TAIL}"


@pytest.mark.parametrize("n", [n for n in OLD if n != 8])
def test_each_rule_of_spec_0025_is_in_spec_0034_unchanged(n):
    """Brief #387 answers 1 and 5 (REQ-041): SPEC-0025 rule n is SPEC-0034 rule n + 16, word for word."""
    moved = rules(read(SPEC_0034)).get(str(n + OFFSET))
    title, pin = OLD[n]
    assert moved is not None, f"SPEC-0034 rule {n + OFFSET}"
    assert moved.startswith(f"**{title}**")
    assert digest(moved) == pin


def test_rule_8_moves_in_the_text_spec_0028_amended_it_to():
    """Brief #387 answer 1 (REQ-041): the release model of rule 8 is amendment 50 item 2's text."""
    moved = rules(read(SPEC_0034)).get(str(8 + OFFSET))
    assert moved == expected_rule_8()
    assert "is a later intake of this repository only" not in moved
    assert "`scripts/agk/check_release.py` checks it (SPEC-0028 rules 4 and 5)." in moved


def test_spec_0034_keeps_its_own_rules_and_leaves_15_and_16_free():
    """Brief #387 answer 3 (REQ-041): rules 1 to 14 stay; 15 and 16 stay for amendments 88 and 89."""
    numbers = list(rules(read(SPEC_0034)))
    own = [str(n) for n in range(1, 15)]
    moved = [str(n + OFFSET) for n in OLD]
    assert numbers == own + moved
    assert "### Independent pull requests (from SPEC-0025)" in read(SPEC_0034)


def test_spec_0025_says_where_each_rule_went():
    """Brief #387 answers 2 and 5 (REQ-041): one pointer line per old rule, each naming a rule that exists."""
    text = read(SPEC_0025)
    assert text.startswith("# SPEC-0025: ")
    inside = False
    pointers: dict[int, int] = {}
    numbered = 0
    for line in text.splitlines():
        if line.startswith("## "):
            inside = line.strip() == "## Rules"
            continue
        if inside and RULE.match(line):
            numbered += 1
            match = POINTER.match(line)
            assert match, line
            pointers[int(match.group(1))] = int(match.group(2))
    assert numbered == len(OLD)
    assert pointers == {n: n + OFFSET for n in OLD}
    exists = rules(read(SPEC_0034))
    assert all(str(m) in exists for m in pointers.values())


def test_both_specs_stay_approved_and_their_other_sections_stay():
    """Brief #387 answer 4 (REQ-041): the pull request approves nothing; history is kept."""
    for rel in (SPEC_0025, SPEC_0034):
        text = read(rel)
        assert "- Status: Approved" in text.splitlines()
        for heading in ("## Rules", "## Tests", "## Proof", "## Residual", "## Open questions"):
            assert heading in text.splitlines(), (rel, heading)
    old = old_text_at(BEFORE)
    if old is not None:  # SPEC-0025 changes only inside `## Rules`
        def outside(text: str) -> list[str]:
            kept, inside = [], False
            for line in text.splitlines():
                if line.startswith("## "):
                    inside = line.strip() == "## Rules"
                if not inside or line.startswith("## "):
                    kept.append(line)
            return kept

        assert outside(read(SPEC_0025)) == outside(old)


def test_the_amendment_names_both_specs_and_check_specs_passes(repo):
    """Brief #387 answer 5 (REQ-041): `check_specs` passes the change with the amendment, fails without."""
    placeholder = "# SPEC-{n}: x\n\n- Status: Approved\n- Owner: maintainers\n\n## Rules\n\n1. old\n"
    repo.commit(
        {
            SPEC_0025: placeholder.format(n="0025"),
            SPEC_0034: placeholder.format(n="0034"),
            "docs/specs/TEMPLATE.md": "# SPEC-NNNN: t\n\n- Status: Draft\n",
        },
        "base",
    )
    repo.branch()
    repo.commit({SPEC_0025: read(SPEC_0025), SPEC_0034: read(SPEC_0034)})
    assert repo.run("check_specs.py", "--base", "main").returncode == 1
    amendment = read(AMENDMENT)
    assert SPEC_0025 in amendment and SPEC_0034 in amendment
    assert "ADR-0246" in amendment
    repo.commit({AMENDMENT: amendment})
    proc = repo.run("check_specs.py", "--base", "main")
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_no_script_is_touched_and_citations_still_resolve():
    """Brief #387 answer 3 (REQ-041): every `SPEC-0025 rule n` cited in scripts names a pointer line."""
    pointers = rules(read(SPEC_0025))
    cited = set()
    for path in sorted((ROOT / "scripts" / "agk").glob("*.py")):
        cited |= set(re.findall(r"SPEC-0025 rules? (\d+)", path.read_text(encoding="utf-8")))
    assert cited, "scripts cite SPEC-0025 rules"
    assert all(n in pointers for n in cited)
    sys.path.insert(0, str(ROOT / "scripts" / "agk"))
    import core_audit

    found = core_audit.spec_rules(ROOT)
    assert found["SPEC-0025"] == [str(n) for n in OLD]
    assert [str(n + OFFSET) for n in OLD] == found["SPEC-0034"][-len(OLD) :]
