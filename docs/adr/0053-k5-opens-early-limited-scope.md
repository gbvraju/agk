# ADR-0053: K5 opens early with a limited scope: three items before the friends launch

- Status: Accepted
- Date: 2026-10-20
- Deciders: maintainers
- Amends: ADR-0025
- Related: ADR-0021, ADR-0025, ADR-0051
- Requirements: REQ-020

## Context

K4's build is complete and kit 0.28.0 is released. ADR-0025 decision 4 says "nothing else before launch": only its dated
rows and the "before launch" residuals are built before the friends launch (2026-11-27), and every other candidate in
the residual register waits for the K5-opening ADR. The first outside developer starts on 2026-10-21 and the pilot's
scored weeks are 2026-10-26 and 2026-11-02 (criterion a). The work that depends on those weeks (the portal, the standards
pack, model choice by work size, debt) keeps waiting for them.

Three items do not depend on them, and gain from starting now:

- **K5 candidate 16, estimate against actual,** needs weeks of data before it says anything. Started after the launch, it
  would have no data until well into K5.
- **The At risk finding** of `docs/runs/short-report-live-1.md`: on the live report 88, 33 of 37 At risk lines share one
  kind ("merged with no verdict").
- **The Delivered finding** of the same record: Delivered lists every requirement that was ever done, so REQ-021 and
  REQ-022 appear in the report of week W42 although the week is not the one they became done in.

The two findings were seen on a real report, which is the evidence the register asked for.

## Decision

1. **ADR-0025 decision 4 is amended** to allow exactly three items before the friends launch, and no others:
   1. K5 candidate 16, estimate against actual (`Size:` and `Expected:` in the brief template, two metrics columns, the
      within-range count in the report's Cost totals);
   2. the At risk finding of `docs/runs/short-report-live-1.md` (one line per kind of risk, with the numbers of the pull
      requests it applies to);
   3. the Delivered finding of the same record (only the requirements that became done in the week of the report).
2. **Everything else in the register still waits** for the K5-opening ADR proper, written after criterion a (2026-11-02)
   and the first outside developer's run. Nothing in this ADR opens K5 for any other candidate.
3. **Each item goes through the full cycle,** like any requirement: an intake sentence, a requirement `planned`, a Draft
   spec and an ADR; the maintainers' rulings; Approved specs; a build per requirement from its Approved spec, tests first;
   a kit bump and a release tag. The order is At risk, Delivered, then estimate against actual.
4. **The register moves.** The register line of candidate 16 and the residuals of the two findings change their status from
   `open` to `in progress, ADR-0053` (their due dates do not change). They close when the requirement of each is `done`.
5. **The dates of ADR-0025 do not move** because of this: no row of its table is dropped, shortened or delayed by this
   work, and no check, fix list or clearance is skipped for speed.

## Consequences

- Three small requirements are built before the launch, each proven by its own tests; the report that the product owner
  reads in the first outside weeks already shows At risk by kind and Delivered by week.
- Candidate 16 begins collecting its data from the first brief that carries the two lines; a brief without them reads
  `unknown`, so no past pull request is rewritten.
- Planning cost: the work is done in the weeks the pilot is scored. The pilot repository is not touched and is held until
  its week W44 is scored on 2026-11-02; it gets these changes on its next `agk upgrade` after that.

## Residual

- 2026-10-20: the K5-opening ADR proper (every other candidate) is written after criterion a and the first outside
  developer's run (due 2026-11-30).
- 2026-10-20: the `pr-body` check should accept `Advances: none` when the pull request changes only `docs/`; the form
  requirement `REQ-020` was used twice (Q-K4-206, Q-K4-212) for planning changes that advance nothing; not built under this
  ADR (due 2026-12-31).
