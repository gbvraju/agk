# Proposed spec amendments 15 (SPEC-0005, SPEC-0006, SPEC-0009, SPEC-0011, SPEC-0001, SPEC-0002; found while drafting SPEC-0013)

Date: 2026-10-16 (from `date -u`). Approved specs change only through a proposal like this one (principle 6). Nothing here is applied; until the
maintainers apply it, SPEC-0013 (Draft) is ahead of the Approved text of the rules below. The paths: `docs/specs/0005-distribution.md`,
`docs/specs/0006-doctor.md`, `docs/specs/0009-facts.md`, `docs/specs/0011-inbox-and-report.md`, `docs/specs/0001-agk-init.md`,
`docs/specs/0002-agk-adopt.md`.

**Items 1 (the `/agk:ruleset` part), 4 and 5 applied by ADR-0041** (2026-10-18). **Item 2 applied by ADR-0040** (2026-10-18; SPEC-0009 rules 16 and 17 in `docs/specs/0009-facts.md`). The other items are applied by the later
implementation pull requests of SPEC-0013.

## SPEC-0005 (`docs/specs/0005-distribution.md`)

1. **Rules 8, 9, 10 and 19: three more commands.** Proposed: the table of rule 8 gains `/agk:start` (`playbook.py`: a vision and a project charter,
   two files on a branch; no network), `/agk:architect` (prints how to start the architect session; reads only) and `/agk:ruleset` (`ruleset.py plan`,
   then the person's `gh` applies it; writes a ruleset and two repository settings after asking); rule 9's list of user-invoked commands gains
   `start` and `ruleset` (`architect` reads and writes nothing); rule 10 becomes "`/agk:issue` and `/agk:ruleset` are the only commands that write
   outside the working tree, and each asks before it does"; the test of rule 19 expects eleven skills and allows `gh api --method POST|PUT|PATCH`
   in `skills/ruleset/SKILL.md` only (no other forbidden verb). `skills/architect/SKILL.md` and `skills/start/SKILL.md` stay under the
   forbidden verbs of rule 10.

## SPEC-0009 (`docs/specs/0009-facts.md`)

2. **Rule 16, the `questions` row.** Proposed: add a row "question ids, asked and ruled: `common.find_questions` (new, SPEC-0013 rule 25)" to the
   table, and say in rule 17 that the function is extracted from the facts' own parsing by a behaviour-preserving change. (Item 3 of
   `proposed-spec-amendments-14.md` is the other proposed change to rule 13.)

## SPEC-0011 (`docs/specs/0011-inbox-and-report.md`)

3. **Rule 10, "At risk", a fifth line.** Proposed: "(v) each pull request merged in the week whose last `Verdict: cleared` names a commit other than
   its merged `head`, or that has no verdict line: `PR #N was merged before its last commit was cleared` or `PR #N was merged with no verdict`,
   derived from `pull_requests[].head`, `merged_at` and `verdicts`". It reports after the fact and blocks nothing (SPEC-0013 rule 18).

## SPEC-0006 (`docs/specs/0006-doctor.md`)

4. **Rule 5, the printed fix of `required-check-governance`.** Proposed: "require the status check `governance`; if the ruleset was applied in phase 1
   and `governance` has not yet run on the default branch, run `/agk:ruleset` after its first run". No id is added.

## SPEC-0001 and SPEC-0002 (`docs/specs/0001-agk-init.md`, `docs/specs/0002-agk-adopt.md`)

5. **The printed block.** Proposed: `init` and `adopt` print one more line after the branch rules: "or run `/agk:ruleset` to apply them (phase 1 now,
   phase 2 after the first `governance` run)". The branch-rules text stays.
