"""SPEC-0041 build (b): principle 10's test map, session rule 37, its core-rules line (brief #562).

Amendment 113 items 1, 2 and 9, and amendment 119 (owner ruling D2 on plan #542) applied to
SPEC-0041. The new session rule is 37, not the 36 that amendment 113 named: rule 36 is the
`Covered-by:` rule of ADR-0271, merged first, and a moved rule number is a mechanical change
(session rule 15).
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PRINCIPLES = ROOT / "constitution" / "principles.md"
RULES = ROOT / "config" / "session-rules.md"
PAGE = ROOT / "config" / "core-rules.md"
SPEC = next((ROOT / "docs" / "specs").glob("0041-*.md"))
AMENDMENT = ROOT / "docs" / "runs" / "proposed-spec-amendments-119.md"

OLD_10 = (
    "10. Dates come from `date -u`; PR bodies state what they advance; tests carry REQ markers."
)
NEW_10 = (
    "10. Dates come from `date -u`; PR bodies state what they advance; tests carry REQ "
    "markers or, in personal mode, the state's test map."
)

# The other eleven principles as they read on the default branch at 617351b.
OTHERS = {
    1: (
        "A protected change requires an ADR in the same PR, or, for a build of an Approved "
        "spec, a `Covered-by:` line naming that spec's Accepted ADR, which names the class."
    ),
    2: (
        "Agents never merge, and never bypass checks. The one exception: with "
        "`auto_merge = true` on the default branch, the conductor alone may merge a pull "
        "request it cleared, and only through `scripts/agk/merge_cleared.py`."
    ),
    3: (
        "One PR per item, branched from the default branch; never stacked on another's "
        "unmerged change (a dependence is declared with `Depends-on`)."
    ),
    4: "Build-state is only appended, and only by docs commits.",
    5: "Generated files are never committed.",
    6: "Approved specs are owned by a reviewer group; agents propose patches.",
    7: "Questions are recorded, never guessed; unconfirmed facts are marked (verify).",
    8: "Refusals name the setting or path class, never the value.",
    9: ("No secrets in the repository or in an agent session; scanners' ignore lists never grow."),
    11: "A check is never weakened to go green; it is changed by ADR.",
    12: "Unattended work stops on ambiguity and reports per PR.",
}

RULE_37 = (
    'In personal mode (a sidecar with `forge = "files"`, SPEC-0041) a session never pushes '
    "to a remote of the product, never runs `personal.py confirm` or `sync`, and never "
    "strips, rewrites or amends an attribution trailer; the developer pushes, confirms and "
    "syncs."
)
CORE_LINE = (
    "- `session rule 37`: in personal mode a session never pushes to the customer, never "
    "confirms and never strips attribution."
)


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def flat(text: str) -> str:
    return " ".join(text.split())


def numbered(text: str) -> dict[int, str]:
    items: dict[int, str] = {}
    current = None
    for line in text.splitlines():
        m = re.match(r"^(\d+)\. (.*)$", line)
        if m:
            current = int(m.group(1))
            items[current] = m.group(2)
        elif current is not None and line.startswith("   ") and line.strip():
            items[current] += " " + line.strip()
        else:
            current = None
    return {n: flat(t) for n, t in items.items()}


def test_req048_principle_10_gains_exactly_the_test_map_clause():
    """REQ-048 AC4: amendment 113 item 1 (principle 10 reads the state's test map)."""
    lines = read(PRINCIPLES).splitlines()
    assert NEW_10 in lines
    assert OLD_10 not in lines


def test_req048_no_other_principle_changes():
    """REQ-048 AC4: amendment 113 item 1 (nothing else of the constitution changes)."""
    text = read(PRINCIPLES)
    items = numbered(text)
    assert sorted(items) == list(range(1, 13))
    for n, sentence in OTHERS.items():
        assert items[n] == flat(sentence), f"principle {n}"
    assert text.startswith("# Principles\n\nThe twelve rules. Briefs cite them by number.\n\n1. ")


def test_req048_session_rule_37_names_the_three_prohibitions():
    """REQ-048 AC6: amendment 113 item 2 (push, confirm or sync, strip attribution)."""
    rules = numbered(read(RULES))
    assert max(rules) == 37
    assert rules[37] == flat(RULE_37)
    assert rules[36].startswith("A build of an Approved spec whose protected change")


def test_req048_the_core_rules_page_lists_session_rule_37_under_safety():
    """REQ-048 AC6: amendment 113 item 2 (one line under the safety rules)."""
    page = read(PAGE)
    safety = re.search(r"(?ms)^## Safety rules\n(.*?)(?=^## )", page)
    assert safety
    assert CORE_LINE in safety.group(1).splitlines()
    assert page.count("`session rule 37`") == 1


def test_req048_check_requirements_in_team_mode_counts_only_markers_in_tests(repo):
    """REQ-048 AC4: amendment 113 item 9 (a test map is no marker in a team-mode repository)."""
    reqs = "# Requirements\n\n### REQ-001 — t\n\n- Acceptance: AC1\n- Status: done\n\n"
    repo.commit(
        {
            "docs/requirements.md": reqs,
            "test-map.toml": '"REQ-001 AC1" = ["tests/test_t.py::test_t"]\n',
            "tests/test_t.py": "def test_t():\n    pass\n",
        }
    )
    proc = repo.run("check_requirements.py")
    assert proc.returncode == 1
    assert "REQ-001" in proc.stdout
    repo.commit({"tests/test_t.py": "def test_t():\n    '''REQ-001 AC1'''\n"})
    assert repo.run("check_requirements.py").returncode == 0


def test_req048_amendment_119_is_applied_to_spec_0041():
    """REQ-048 AC5: amendment 119 (ruling D2: the levels in team mode, `light` by default)."""
    assert SPEC.relative_to(ROOT).as_posix() in read(AMENDMENT)
    text = read(SPEC)
    rule = numbered(text)[31]
    for phrase in (
        "`[governance] level`",
        "`light` for a project that `init.py` or `adopt.py` sets up",
        "no `level` key reads as today",
        "refused naming the setting",
        "build (o)",
    ):
        assert phrase in rule, phrase
    assert "    - (o) " in text
    assert re.search(r"(?m)^- Rule 31: ", text)


def test_req048_spec_0041_names_the_new_session_rule_by_its_number():
    """REQ-048 AC6: amendment 119 (the rule amendment 113 called 36 is session rule 37)."""
    spec = read(SPEC)
    assert "session rule 36" not in spec
    assert spec.count("session rule 37") == 3
