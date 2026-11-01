"""SPEC-0031 (changelog fragments) folded into SPEC-0028 (the flow-mode release) (brief #386, REQ-039).

The flow-mode release rules live in one spec. SPEC-0028 holds its own rules, with rules 2, 4, 5 and 6
in the text that SPEC-0031 rule 7 (amendment 54) gave them, and SPEC-0031's eight rules, text
unchanged, as rules 11 to 18 of a new section of its `## Rules`. SPEC-0031 keeps its number and its
history and holds one pointer line per old rule. The digests below are those of the rule texts on
the default branch before the change (ebc556f), so "text unchanged" is checked, not read. Spec
amendment 108 names both paths, so `check_specs.py` passes; ADR-0245 applies it. Files and git in
`tmp_path` only: no network, no model.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

import core_audit

ROOT = Path(__file__).resolve().parents[2]
S28 = "docs/specs/0028-in-flow-mode-a-kit-build-pull-request-does-not-bump-the-vers.md"
S31 = "docs/specs/0031-in-flow-mode-a-build-pull-request-adds-its-changelog-line-as.md"
AMENDMENT = "docs/runs/proposed-spec-amendments-108.md"
ADR = "docs/adr/0245-spec-0031-changelog-fragments-folded-into-spec-0028-req-039-brief-386.md"
NUMBERED = re.compile(r"^(\d+)\. (.*)$")
POINTER = re.compile(r"^(\d+)\. Now SPEC-0028 rule (\d+)\.$")
OFFSET = 10  # SPEC-0031 rule N is SPEC-0028 rule N + 10

# SPEC-0031 rules 1 to 8 as they stood before the change (sha256 of the text after "N. ").
OLD_31 = {
    1: "91b4ec5ea4b3d39bda40952e4bbbe60584e806bd3b2a81d04d70156924e1a962",
    2: "92f4370e3ce0ee3d445d60e9ad4615e41807642d30032049115260078412ee90",
    3: "10028207e127657e38c254e39e623f49710a2756941e401e39ebe4efdd30bf83",
    4: "857b0321f2d053527237ed6d3f8ebabd59ec09aeb6146078c67689fa21501b8b",
    5: "f52b055c10e26db5ca989284a0f52cfccc5efe8912cd4ec8f0cfe59f64abe42a",
    6: "ca902b4136db0850225037eb09c9f2c2919a8630528f18a340f87277f5c948b9",
    7: "7f467639788e57ffe4799e53a0699e76afa2138ca1a7745a43c90a8cef7ca736",
    8: "7827f40d352b33c74cac1306045c1e43010e196aea2c533085e79727e7127586",
}
# SPEC-0028's own rules before the change; 2, 4, 5 and 6 are the ones SPEC-0031 rule 7 amends.
OLD_28 = {
    1: "50c1e515ca574a1308d0afae0454d6bba9e569b9f30a129ec64fc9dd9a715eaf",
    2: "229e02c6fbcc72a11923802249fc1e876d78ea1dbccac31d696aef2d696b0e1e",
    3: "44a2720e708eed63506858ddc4d4d79d572956acb3ef50401879f5ded9c15172",
    4: "b3255a3ba3a0d590ee46edf39d30cabc0526cdcf1d41e5c7ec98dd4f54736a03",
    5: "d600081c54a2984445920da536d5db9e7a2fdda2ccfc8ed3015ca9f841eba43c",
    6: "945216f9c29d1558ab61e925d8a041c7ce1eedb28997e9390e38797b20eb7ae5",
    7: "1e0a532165327880206e6d11cbc490d339c4e8c329a8f240be9f16e30604ad1c",
    8: "35af14ddf9aa0b41d0251c5ccbade5e9eebe0028554aab0b888cc528e6f9ca3f",
    9: "68d1153540d6bb316d317e6f51ac8d5743f2dddc5c62c94fff81bfccebb1b404",
    10: "d3a24201cb4bb59c2b55797749cde9207a3ad5a95d276321738e566cd530b03d",
}
AMENDED = (2, 4, 5, 6)


def text(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def rules_section(body: str) -> list[str]:
    """The lines of the `## Rules` section (a `### ` subsection stays inside it)."""
    found: list[str] = []
    inside = False
    for line in body.splitlines():
        if line.startswith("## "):
            inside = line.strip() == "## Rules"
            continue
        if inside:
            found.append(line)
    return found


def rules(rel: str) -> dict[int, str]:
    found: dict[int, str] = {}
    for line in rules_section(text(rel)):
        match = NUMBERED.match(line)
        if match:
            found[int(match.group(1))] = match.group(2)
    return found


def digest(rule: str) -> str:
    return hashlib.sha256(rule.encode()).hexdigest()


def test_each_rule_of_spec_0031_is_in_spec_0028_text_unchanged():
    """REQ-039: brief #386 answers 1 and 5 (every SPEC-0031 rule is in SPEC-0028, text unchanged)."""
    now = rules(S28)
    for number, old in OLD_31.items():
        assert number + OFFSET in now, f"SPEC-0031 rule {number} is missing from SPEC-0028"
        assert digest(now[number + OFFSET]) == old, f"SPEC-0031 rule {number} changed its text"


def test_spec_0028_rules_that_spec_0031_does_not_amend_are_unchanged():
    """REQ-039: brief #386 answers 1 and 3 (nothing about the release changes)."""
    now = rules(S28)
    assert sorted(now) == list(range(1, 19))
    for number, old in OLD_28.items():
        if number not in AMENDED:
            assert digest(now[number]) == old, f"SPEC-0028 rule {number} changed"


def test_the_amended_rules_carry_the_fragments_in_their_amended_text():
    """REQ-039: brief #386 answer 1 (rules 2, 4, 5 and 6 as SPEC-0031 rule 7 amends them)."""
    now = rules(S28)
    for number in AMENDED:
        assert digest(now[number]) != OLD_28[number], f"SPEC-0028 rule {number} is not amended"
    two, four, five, six = (now[n] for n in AMENDED)
    assert "adds at least one line under `## Unreleased`" not in two
    assert "exactly one" in two and "`changelog.d/" in two and "rule 11" in two
    assert "does not edit `CHANGELOG.md`" in two and "`kit/hashes.json`" in two
    assert "deletes the fragments" in four and "rule 13" in four
    assert "kit_hashes.py --write" in four and "`changelog.d/`" in four
    assert "`changelog.d/`" in five and "rule 14" in five
    assert "release" in six and "kit_hashes.py --write" in six
    assert "refreshes `kit/hashes.json`" not in two


def test_the_fragment_rules_are_a_section_of_the_rules_that_the_core_audit_counts():
    """REQ-039: brief #386 answer 1 (a new section, read as rules by `core_audit.py`)."""
    lines = rules_section(text(S28))
    headings = [i for i, line in enumerate(lines) if line.startswith("### ")]
    assert len(headings) == 1 and "SPEC-0031" in lines[headings[0]]
    first = next(i for i, line in enumerate(lines) if line.startswith(f"{1 + OFFSET}. "))
    last_own = next(i for i, line in enumerate(lines) if line.startswith("10. "))
    assert last_own < headings[0] < first
    counted = core_audit.spec_rules(ROOT)
    assert counted["SPEC-0028"] == [str(n) for n in range(1, 19)]


def test_spec_0031_holds_one_pointer_line_per_old_rule_and_each_names_a_rule_that_exists():
    """REQ-039: brief #386 answers 2 and 5 (`N. Now SPEC-0028 rule M.`, M exists)."""
    lines = [line for line in rules_section(text(S31)) if line.strip()]
    assert len(lines) == len(OLD_31)
    targets = rules(S28)
    for number, line in enumerate(lines, 1):
        match = POINTER.match(line)
        assert match, f"SPEC-0031 rule {number} is not a pointer line"
        assert int(match.group(1)) == number
        assert int(match.group(2)) == number + OFFSET
        assert int(match.group(2)) in targets
    assert core_audit.spec_rules(ROOT)["SPEC-0031"] == [str(n) for n in OLD_31]


def test_spec_0031_keeps_its_number_and_its_history():
    """REQ-039: brief #386 answer 2 (never renumber; the history stays)."""
    body = text(S31)
    assert body.startswith("# SPEC-0031: In flow mode a build pull request adds its changelog line")
    assert "- Status: Approved" in body and "- Requirements: REQ-038" in body
    assert "Written by the intake of one sentence (SPEC-0012)" in body
    assert "The maintainers gave 5 answers before it was written" in body
    assert "SPEC-0028" in body.split("## Rules")[0]


def test_the_pull_request_does_not_approve_spec_0028():
    """REQ-039: brief #386 answer 4 (the status line is not changed; a person approves after)."""
    body = text(S28)
    assert body.count("- Status: ") == 1 and "- Status: Approved" in body
    assert "- Requirements: REQ-035, REQ-038" in body
    assert "Approve: SPEC-0028" in text(AMENDMENT)


def test_the_amendment_names_both_paths_and_the_adr():
    """REQ-039: brief #386 answer 1 (one amendment file, applied by ADR-0245)."""
    body = text(AMENDMENT)
    assert f"`{S28}`" in body and f"`{S31}`" in body
    assert "ADR-0245" in body
    assert "- Status: Proposed" in text(ADR)


def spec_repo(repo, amendment: bool):
    """A base with both specs before the fold and a head with them after it."""
    before_28 = text(S28).replace("\n### ", "\n### before ", 1)
    before_31 = text(S31).replace("1. Now SPEC-0028 rule 11.", "1. The fragment.", 1)
    log = "# Decisions log\n\n| Date | Decision |\n| --- | --- |\n"
    repo.commit({S28: before_28, S31: before_31, "docs/runs/decisions-log.md": log}, "base")
    repo.branch()
    files: dict[str, str | None] = {S28: text(S28), S31: text(S31)}
    if amendment:
        files[AMENDMENT] = text(AMENDMENT)
    repo.commit(files, "fold")
    return repo.run("check_specs.py", "--base", "main")


def test_check_specs_passes_the_fold_with_the_amendment(repo):
    """REQ-039: brief #386 answer 5 (`check_specs` passes)."""
    result = spec_repo(repo, amendment=True)
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.endswith("ok specs\n")


def test_check_specs_fails_the_fold_without_the_amendment(repo):
    """REQ-039: brief #386 answer 5 (the Approved specs change only by amendment)."""
    result = spec_repo(repo, amendment=False)
    assert result.returncode == 1
    assert "0028" in result.stdout + result.stderr and "0031" in result.stdout + result.stderr
