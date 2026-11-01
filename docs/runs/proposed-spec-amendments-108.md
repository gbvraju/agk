# Proposed spec amendments 108 (SPEC-0028, SPEC-0031; REQ-035, REQ-038, REQ-039)

Date: 2026-11-01 (from `date -u`). Approved specs change only through a proposal like this one (principle 6). Written for
ADR-0245 (brief #386), which stays `Proposed` for the maintainers' decision. The paths:
`docs/specs/0028-in-flow-mode-a-kit-build-pull-request-does-not-bump-the-vers.md` and
`docs/specs/0031-in-flow-mode-a-build-pull-request-adds-its-changelog-line-as.md`. The number 108 is the next free one on the
default branch when this was written; the conductor reserved ADR-0245 for the brief and named no amendment number (Q-386-1).
It needs a person's `Approve: SPEC-0028`; no session posts it, and the pull request does not change a status line. It is the
decision of row 10 of the split of plan #278 (SPEC-0031 into SPEC-0028), accepted by the person on 2026-11-01. Nothing about
the release or the fragments changes: `changelog_fragments.py`, `check_release.py` and `kit_hashes.py` are not touched.

1. **SPEC-0028 rules 2, 4, 5 and 6, the amended text.** SPEC-0031 rule 7 amended these rules, and amendment 54 (ADR-0108)
   gave the amendment; the spec file still held the text from before it. The four rules now say it in place: rule 2, a build
   adds exactly one fragment in place of the Unreleased line and edits neither `CHANGELOG.md` nor `kit/hashes.json`, and the
   check of the bump rule fails one that does, or that changes an installed file without exactly one fragment; rule 4, the
   release also deletes the fragments, writes their lines `- #<n> <one-line change>` in pull request order after the moved
   Unreleased lines, and regenerates `kit/hashes.json` with `python3 scripts/agk/kit_hashes.py --write`; rule 5, the release
   check also accepts the deletion of a fragment and fails a fragment left, added or edited, a line not under the new heading
   with its `#<n>` and in order, or a fragment whose pull request number cannot be read; rule 6, builds do not collide on the
   two files, and the regeneration belongs to the release. Rules 1, 3 and 7 to 10 are unchanged.
2. **SPEC-0028, a new section of its rules.** `### The changelog fragments (from SPEC-0031)` follows rule 10 inside
   `## Rules`, so that `core_audit.py` counts its rules: SPEC-0031 rules 1 to 8, text unchanged, as rules 11 to 18. One line
   before them says that a bare "rule N" inside them names rule N + 10 and "SPEC-0028 rule N" names rule N above.
3. **SPEC-0028, the Requirements line and the tests.** `- Requirements:` becomes `REQ-035, REQ-038`. `## Tests` gains one line:
   the tests of rules 11 to 18 are those of SPEC-0031 `## Tests` (REQ-038 AC1 to AC7), its rule N read as rule N + 10, and the
   first two lines are read with the fragment of the amended rule 2. The status line is not changed (Approved).
4. **SPEC-0031, pointer lines.** The spec keeps its number, title, status, Requirements line, its history (the intake
   paragraphs), `## Tests`, `## Proof`, `## Residual` and `## Open questions`; one sentence after the history says where its
   rules went. Its eight rules become one line each, `N. Now SPEC-0028 rule M.`, with M = N + 10. Never renumbered: the
   references to "SPEC-0031 rule N" elsewhere (the scripts' docstrings, `CHANGELOG.md`, other specs) still resolve.
5. **Tests.** `tests/kit/test_core_release_specs.py` (marker `REQ-039`): each SPEC-0031 rule is in SPEC-0028 with the digest
   of its old text; SPEC-0028's other rules keep theirs; the four amended rules name the fragments; the section is inside
   `## Rules`; each pointer line names a rule that exists; `check_specs.py` passes the change with this file and fails it
   without.
