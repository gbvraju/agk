# ADR-0038: intake, part 2 of 3: `intake.py check` C1 to C9 and the draft-is-not-a-fact test (SPEC-0012 rules 11 and 14)

- Status: Proposed
- Date: 2026-10-18
- Deciders: maintainers
- Related: ADR-0021, ADR-0037
- Requirements: REQ-019

Protected classes: `scripts/agk/`, `tests/kit_dev/`

## Context

Part 2 of the three-part build of SPEC-0012 announced in ADR-0037. Part 1 (#76) added `intake.py ids` and `stub`. This part adds the
deterministic checks of rule 11 and the test of rule 14. Nothing here is installed in a target (`intake.py` is kit-only), so the kit version is
unchanged. Part 3 adds `next-steps`, the skill form, the template and form edits, the two spec amendments and the end-to-end test.

## Decision

1. **`python3 scripts/agk/intake.py check [--base REF] [--root DIR]`** reads the work tree and the merge base with the base ref
   (`--base`, else `AGK_BASE`, `GITHUB_BASE_REF` or `origin/<default branch>`, by `common.resolve_base`) and prints `ok intake` or one
   `FAIL intake: Cn <rule text>` line per failed check; exit 1 on any failure. Messages name the check and the rule, never the sentence or any
   text of the files. A base that does not resolve is a failure (the check never passes for lack of a base).
2. **The nine checks** are those of SPEC-0012 rule 11: C1 ids are the next free ones of the base; C2 the difference is the requirements file
   (modified), one new spec `docs/specs/<spec>-<slug>.md` and one new ADR `docs/adr/<adr>-add-<req id lower case>-<slug>.md`, both directly in
   their folder with a slug of lowercase letters, digits and hyphens (a wrong name fails C2 with a message that names the rule and no part of the
   name), and the requirements file only gains one section at its end (the old text is a prefix of the new);
   C3 the acceptance line parses into 1 to 8 criteria from `AC1` in order with no repeat and no `; ` inside a criterion, and the title is at
   most 80 characters with no semicolon; C4 each criterion has given, when, then in order (case-insensitive, text after each); C5 a negative
   case in a `then` part (the word list of rule 6) or the spec line `Negative cases: none, because <20 characters or more>`; C6 requirement
   `planned` (exactly one status line), spec `Draft`, ADR `Proposed`; C7 the spec's `Requirements:` line is exactly the new requirement and the
   `## Tests` section has a `REQ-nnn ACn` marker for every criterion and none for another number or another requirement; C8 the spec has
   `## Proof` (not empty), `## Residual` (every bullet dated `(due YYYY-MM-DD)`, or `none`) and `## Open questions`, and every `Q-` id in the
   spec is `Q-S<spec>-<n>`; C9 the ADR's `Protected classes:` line names `docs/requirements.md`.
3. **Tests** (`tests/kit_dev/test_intake.py`, no model): a good draft passes; the script-rendered stub passes in its place; each of C1 to C9
   has a failing case (a skipped number, a fourth file, a changed existing line, a missing ADR, a repeated or skipped `ACn`, a semicolon inside a
   criterion, nine criteria and eight, free text, a criterion without `then`, out of order, a bare `when`; no negative case with no reason, a
   short reason and a long one; `done` and `in-progress`; a spec `Approved`; an ADR `Accepted`; a foreign requirement in the `Requirements:`
   line, a missing, a stray and a foreign marker; a missing or empty section, an undated bullet, `none`, `- none`, `- none.` (pass) and `- none` beside a dated bullet (fails), a spec in a subfolder, an ADR without `add-req-nnn-` or with a wrong id or slug (fail) and the stub's own name (passes), a foreign `Q-` id, a `Q-K4-` id; an ADR
   that does not name the file); a failure never prints a word of the sentence; no base fails. **A draft is not a fact (rule 14):** a repository
   with a default branch and an intake branch, `facts.py` run on the default branch: the draft requirement, spec and ADR are absent from
   `requirements`, `specs` and `adrs` and from the report and the inbox; run on the branch itself, the requirement is present.
4. **Not in this part:** the pull-request-open case of rule 14 (SPEC-0009 rule 14 lists changed file names only; it is covered by SPEC-0009's own
   fixtures) and the assertion that, after the merge, the spec and ADR wait in the inbox (part 3, with the `open_in` change).

## Consequences

- A draft that breaks a rule of form is refused with the rule named, before any reviewer reads it. The checks cannot tell that the criteria are the
  right ones (rule 12); that is the review.
- Until part 3 merges nothing calls `check`.

## Questions

| Q | Question | Ruling (maintainers, 2026-10-18: all three ruled as read) |
| --- | --- | --- |
| Q-K4-174 ruled | C1 compares to "the ids rule 2 prints for the base". Which base: the default branch tip, or the merge base? | The merge base of the branch (`common.merge_base`): a branch cut from the default branch passes when it was fresh; if the default branch has moved on and allocated the same numbers, the conflict at merge is the residual of SPEC-0012, not a failure of the branch. Conservative: no false failure from a stale ref. |
| Q-K4-175 ruled | Does a bare `none` count for an empty `## Residual`? Rule 7 says "may be empty with the text `none`". | Yes: a line that is `none` or `- none`, optionally with a final dot, is an empty Residual; it passes only when it is the only bullet (mixed with dated bullets it is undated and fails C8). An empty section is a failure. |
| Q-K4-176 ruled | Does a marker of another requirement in `## Tests` fail C7? Rule 11 names markers "for a criterion that does not exist". | Yes. The spec's `Requirements:` line names only the new requirement, so another requirement's marker is stray. |

## Residual

- 2026-10-18: C1 reads the merge base, so two intake branches cut from the same default branch tip pass individually; the second to merge is
  renumbered by hand (SPEC-0012 residual, due 2026-12-31).
