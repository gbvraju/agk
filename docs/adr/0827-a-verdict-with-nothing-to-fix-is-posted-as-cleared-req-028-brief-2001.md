# ADR-0827: A verdict with nothing to fix is posted as cleared (REQ-028)

- Status: Proposed
- Date: 2026-11-26
- Deciders: maintainers (the owner's word, quoted below)
- Related: brief #2001, SPEC-0021 rules 1, 3, 3a and 9, SPEC-0039 rule 3, amendment 256, ADR-0277 (a `Final:` line
  accepts an ADR), ADR-0293 (the router labels that acceptance), ADR-0778 (a Final-only fix list is no builder event),
  ADR-0388 (the guard refuses a wrong-form line), ADR-0265 (the guarded merge), ADR-0431 (the fallback ending),
  ADR-0725 (`agk:reprove` stays an event), ADR-0179 (solo mode), plan #661
- Requirements: REQ-028

Protected classes: `scripts/agk/`, `.claude/`, `kit/`, `tests/kit/`, `agk.toml`

## Context

Of the 89 `Verdict: fix list <head>` comments on the 30 newest merged pull requests (#1911 to #1984), 40 had no
numbered item; 37 of them carried only `Final: docs/adr/<file> Proposed -> Accepted` lines (SPEC-0021 rule 3a). The
conductor wrote `fix list` because a `Final:` line was read only under that first line (`common.verdict_problem`,
`NOT_FIX_LIST`). The readers already treated such a verdict as cleared (ADR-0778), but the router's label change to
`agk:merge-ready` still woke the builder's `watch`, the builder posted `Report: <head> fix list applied: nothing to
change`, and that Report listed the head for a second review (9 of 24 times). The owner's word (2026-11-26T11:05Z, the
steward chat, quoted as data): "Brief 2 and 3 ,".

## Decision

1. **The form.** A verdict with no numbered item is `Verdict: cleared <head>`. On the full 40-character head it may
   carry `Final: docs/adr/<file> Proposed -> Accepted` lines (the rule 3a acceptance). A `Final:` line for a spec,
   `docs/requirements.md` or a stack-options ADR still asks for the builder's status commit and stays a
   `Verdict: fix list <head>` with no numbered item (rule 3, unchanged). A fix list keeps its numbered items.
2. **One reader.** `common.covered_fix_list` also reads `Verdict: cleared <40 hex>` whose every `Final:` line passes
   `final_accepts`, returning the same tuple; a cleared verdict with any other `Final:` line returns None. Every reader
   through it reads both forms; the old fix-list form is still read.
3. **Readable lines.** `common.verdict_problem` allows ADR acceptance lines under `Verdict: cleared <40 hex>` and keeps
   `NOT_FIX_LIST` for any other `Final:` line under a cleared verdict or a short sha. `conductor.head_problem` also fails
   a cleared verdict whose `Final:` line names an ADR the pull request does not change.
4. **The refusal, before posting only.** `conductor.full_problem` refuses a `Verdict: fix list` with no numbered item
   and no `Final:` line, and one whose every `Final:` line accepts an ADR, naming SPEC-0021 rule 1 and the shape to post,
   never the body. It is not in `verdict_problem`, so an old-form verdict already posted gets no reply.
5. **The watch.** `session.watch` prints no `label` line when the new label is `agk:merge-ready` or `agk:owner-merge`
   and the newest listed verdict clears the head (`merge_cleared.clears_head`). Every other label stays an event.
6. **The texts.** `.claude/agents/conductor.md` and the builder's runtime prompt say the form; words are replaced, not
   added. `architect.md`, `shadow.md`, `kit/templates/playbook/verdict.md` and `skills/review-pass/SKILL.md` stay as
   they are (Q-EF-6).
7. **The spec.** Amendment 256 proposes the lines for SPEC-0021 rules 1, 3a and 9 and SPEC-0039 rule 3; the reviewers
   approve it (principle 6). Session rule 1 is unchanged.

## Consequences

About 24 builder wakes, 24 no-op Reports and 9 second reviews fewer per 30 merged pull requests. No workflow, label,
check, ruleset or setting changes: `auto_merge`, `review_mode`, `execution`, `pr_mode` and `[personal]` read the new
form as they read the old one. A verdict posted in the old form before the upgrade is read and merged as today.

## Residual

The other role texts name the verdict forms in their old words, which stay true (Q-EF-6). A distinct hold verdict is not
built (Q-EF-2).
