# ADR-0714: The steward fixes a brief's mechanical lines and files an approved draft as a brief

- Status: Proposed
- Date: 2026-11-22
- Deciders: maintainers
- Related: brief #1715, ADR-0557, ADR-0594, ADR-0704, SPEC-0059, Q-1715-1, Q-1715-2, Q-1715-3, plan #661
- Requirements: REQ-066

Protected classes this decision changes: `.claude/`, `scripts/agk/`, `config/`, `agk.toml` (one `[[testing.map]]`
line: `scripts/agk/steward_owner.py` names `tests/kit/test_steward_fix_brief.py`) and `tests/kit/`.

## Context

A steward's corrected brief body waited about four hours for a person to paste it (#1583), and a brief the steward
files is labelled `agk-steward`, which the plan never offers, so every steward draft needs a person to add `agk-brief`.
SPEC-0059 rule 6 lets the steward file a project brief once `check_brief.py` passes, while rule 11 and ADR-0594
decision 4 deny the `agk-brief` label (Q-1715-3).

## Decision

1. **The fix.** `steward_owner.py fix-brief --brief N --file FILE --seen UPDATED_AT` replaces an open brief's body
   only with `[steward] fix_briefs = true`, in solo mode with one person listed, never in a steward the supervisor
   started (`AGK_STEWARD_START=conductor`), and only when the issue is labelled `agk-brief`, has no `agk:taken` label
   and no unreleased `taken:` or `Started:` comment, its title does not start `Intake:`, its `updated_at` equals
   `--seen`, every changed line starts `Adds:`, `Touches:`, `Reserved:`, `Depends-on:` or `Evidence`, and the new
   body passes `check_brief.body_problems` with the root and the neutrality lists. It posts the old body first as one
   `Body fixed:` comment (a failed post writes no body), then the body, records one `Decision` note and prints the
   new `seen:`. Any other change, `fix_briefs` false, team mode and solo mode with none or two people listed print
   `Proposed body:` and write nothing (exit 1).
2. **The filing.** `steward_owner.py file-brief --file FILE --title TEXT [--said FILE --at TIME [--by LOGIN]]` opens
   one issue labelled `agk-brief` when the draft passes the same checks and either its `Priority:` is at or below
   `[steward] auto_file` (never with `false`) or the person's explicit yes is given: one line, a yes by
   `steward_voice.is_yes` with no condition, in team mode (or solo mode without one person) by a listed
   `spec_approvers` login, no older than four times `[flow] owner_wait_minutes` (24 hours unset or 0). The body then
   gains `Owner said (<UTC time>): "<words>"` before `Who: AGK steward`.
3. **The guard.** `steward_guard.py` keeps denying `agk-brief` on a direct `gh` call, so the command is the one route,
   and denies a direct issue body edit (`gh issue edit --body`/`--body-file`, a `PATCH` of `issues/N` with a body)
   unless `fix_briefs = true`, naming `setting: steward.fix_briefs`. This changes ADR-0594 decision 4 and SPEC-0059
   rule 11 for `agk-brief` through the command only; the patch of rules 11 and 12 waits for the spec approvers.
4. **The setting.** `[steward] fix_briefs`, `true` or `false`, default `false` (Q-1715-1); another value is refused
   naming `setting: steward.fix_briefs`, never the value.
5. **By mode.** In personal mode both commands print and write nothing. `pr_mode`, `[flow] assign`, `builder_start`
   and `execution` are not read; where no GitHub job runs, the in-command brief check is the check. A malformed
   `[kit] layout` is refused by `kit_root.layout`. The conductor files and fixes nothing.

## Consequences

- With `fix_briefs = true` a mechanical fix and an approved filing land in the steward's pass; the plan offers them.
- Every fix leaves the old body in one comment, so one copy restores it.

## Residual

- (due 2026-12-20) Count the fixes, the `Proposed body:` lines and the filings by route, and propose a change only
  from that count.
- Q-1715-2: a conductor `tell` asking for a fix is checked the same way; no tell route is built here.
