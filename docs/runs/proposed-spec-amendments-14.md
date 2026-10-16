# Proposed spec amendments 14 (SPEC-0005, SPEC-0009; found while drafting SPEC-0012)

Date: 2026-10-16 (from `date -u`). Approved specs change only through a proposal like this one (principle 6). Nothing here is applied; until
the maintainers apply it, SPEC-0012 (Draft) is ahead of the Approved text of the rules below. The paths: `docs/specs/0005-distribution.md`,
`docs/specs/0009-facts.md`.

## SPEC-0005 (`docs/specs/0005-distribution.md`)

1. **Rule 8, the `/agk:spec` row.** Proposed cell: "`new_spec.py spec` (a Draft spec), `new_spec.py requirement` (a requirement proposal with its
   ADR draft), or, for one plain-language sentence, `intake.py` (SPEC-0012): a requirement, a Draft spec and an ADR stub on a new branch".
   Needed by SPEC-0012 rule 1. No ruling is needed beyond the maintainers' approval of SPEC-0012.
2. **Rules 8 and 10, only if `Q-K4-61` is ruled "yes".** Rule 8 says a command that writes does not commit, push or merge; rule 10 makes a test fail on
   `git push`, `git commit`, `gh pr`, `gh issue close`, `gh issue comment` and on `gh issue create` outside `issue`. To let `/agk:spec` commit the
   three files of SPEC-0012 and open the pull request, proposed text: "`/agk:spec` with a sentence may, after `intake.py check` and `make
   governance` pass, make one commit of the three files and open one pull request with the body that `intake.py next-steps` prints; it never
   pushes to the default branch, never merges, and `/agk:issue` stays the only command that writes outside the working tree and the
   repository". Rule 10's test then allows `git commit`, `git push` and `gh pr create` in `skills/spec/SKILL.md` only, and checks that the
   only push target is the branch `intake/...`. Not applied; the conservative reading of SPEC-0012 is that the skill stops before the commit.

## SPEC-0009 (`docs/specs/0009-facts.md`)

3. **Rule 13, `open_in`.** Proposed: add to the places that make a question "open": "the `## Open questions` section of a `Draft` spec file". The
   sentence now reads "a notes file of a `Draft` spec, a `Proposed` ADR, the `## Open` section of a notes file, or the `## Open questions`
   section of a `Draft` spec file". Needed so that a `Q-S<spec>-<n>` id of an intake spec (SPEC-0012 rule 10) is waiting in the inbox until a
   person rules it. The fixture `question-forms` gains a case for it.

## Question (open)

- `Q-K4-61`: item 2.
