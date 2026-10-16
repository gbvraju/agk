# Proposed spec amendments 14 (SPEC-0005, SPEC-0009; found while drafting SPEC-0012)

Date: 2026-10-16 (from `date -u`). Approved specs change only through a proposal like this one (principle 6). Nothing here is applied on the merge of SPEC-0012: the maintainers' ruling is that both items are applied **at implementation**, by the ADR of the
implementation pull request of SPEC-0012 (as for Q-K4-52); until then SPEC-0012 (Approved) is ahead of the Approved text of the rules below. The paths: `docs/specs/0005-distribution.md`,
`docs/specs/0009-facts.md`.

## SPEC-0005 (`docs/specs/0005-distribution.md`)

1. **Rule 8, the `/agk:spec` row.** Proposed cell: "`new_spec.py spec` (a Draft spec), `new_spec.py requirement` (a requirement proposal with its
   ADR draft), or, for one plain-language sentence, `intake.py` (SPEC-0012): a requirement, a Draft spec and an ADR stub on a new branch".
   Needed by SPEC-0012 rule 1. No ruling is needed beyond the maintainers' approval of SPEC-0012.
## SPEC-0009 (`docs/specs/0009-facts.md`)

2. **Rule 13, `open_in`.** Proposed: add to the places that make a question "open": "the `## Open questions` section of a `Draft` spec file". The
   sentence now reads "a notes file of a `Draft` spec, a `Proposed` ADR, the `## Open` section of a notes file, or the `## Open questions`
   section of a `Draft` spec file". Needed so that a `Q-S<spec>-<n>` id of an intake spec (SPEC-0012 rule 10) is waiting in the inbox until a
   person rules it. The fixture `question-forms` gains a case for it.

## Withdrawn

- The item that would have let `/agk:spec` commit the three files and open the pull request (SPEC-0005 rules 8 and 10) is **withdrawn**: `Q-K4-61` was
  ruled "no" on 2026-10-16. A skill never commits, pushes or opens a pull request; the script prints the commands and the body, and the session runs
  them under its `CLAUDE.md`. The former item 3 is now item 2.
