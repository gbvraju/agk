# ADR-0778: A Final-only fix list on the head is no builder event (REQ-046)

- Status: Proposed
- Date: 2026-11-24
- Deciders: maintainers (the owner's word, quoted below)
- Related: brief #1879, amendment 225 (SPEC-0039 rules 2 and 9, SPEC-0064 rule 4), ADR-0277, ADR-0265, ADR-0293,
  ADR-0589, ADR-0568, ADR-0329, ADR-0477, ADR-0713, ADR-0718, plan #661
- Requirements: REQ-046

Protected classes: `scripts/agk/`, `kit/`, `.claude/`, `tests/kit/`, `agk.toml`

## Context

A covered fix list on exactly the head whose every `Final:` line is `docs/adr/<file> Proposed -> Accepted` clears that
head for the merger (SPEC-0021 rule 3a, `merge_cleared.accepted_adrs`), yet every waker read it as an owed verdict:
`autopilot.pick` and `conductor.builder_facts` started a `fix` job, `session.follow_up_owed` returned `fix list` and an
interactive `watch --pr` ended on it, so the builder posted `Report: <head> fix list applied: nothing to change`, which
nothing but the wake reads (ADR-0477), and in local mode that Report was in effect the merge trigger. Last night's run
had four such rounds (#1866 twice, #1867, #1870), 6 to 14 minutes from verdict to merge. The owner's word (2026-11-24,
the steward chat, quoted as data): "Yes, draft all four along with release".

## Decision

(filled in below as the build proceeds)
