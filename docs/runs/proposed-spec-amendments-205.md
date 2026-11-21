# Proposed spec amendments 205 (SPEC-0048; REQ-055)

Date: 2026-11-21 (from `date -u`). Approved specs change only through a proposal like this one (principle 6). Written for
ADR-0675 (brief #1595), which stays `Proposed` for the maintainers' decision. The path:
`docs/specs/0048-a-problem-in-a-person-s-words-takes-one-guided-path-to-the-builds.md` (rule 7 and the `## Tests`
section). Brief #1595 reserved amendment 205. This file proposes the lines and does not edit the spec. They are applied
word for word, on a person's `Approve: SPEC-0048`; no session posts it.

## Why

On the default branch at 11fa8bc8 (2026-11-21) a front-door design `docs/design/architecture/<slug>.md` and the record
`docs/architecture.md` of SPEC-0072 rule 5 are two architecture records that nothing links (gap G23, brief #1595).

## Items

1. **Rule 7, two sentences added at its end.** "`docs/architecture.md` (SPEC-0072 rule 5) is the product's one
   architecture record; a front-door design is a slice document that carries one line
   `Architecture: docs/architecture.md` and adds only what its problem changes, and a change to a layer, a store or a
   service goes through the record's ADR. `check-design` refuses a design it is given by name without that line, holds
   one read with the whole folder as a warning until its next edit, and checks the record when it exists." (answer 3)
2. **The `## Tests` section, one line added after the "Rules 7 to 9" line.** "- Rule 7, one record: a named design without the
   `Architecture:` line, or with a wrong or repeated one, is refused, and an existing design read with the folder is a
   warning; REQ-055."
3. **Unchanged:** rules 1 to 6 and 8 to the last, the Proof, the Residual and the Open questions.
