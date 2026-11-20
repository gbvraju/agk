# ADR-0687: A measured solo trial from AGK's own records (REQ-012)

- Status: Proposed
- Date: 2026-11-20
- Deciders: maintainers
- Related: brief #1618, SPEC-0007 rules 25 to 28, amendment 213, ADR-0659, SPEC-0045 rule 2, brief #1282, brief #1534
- Requirements: REQ-012

Protected classes: `scripts/agk/`, `tests/kit/`

## Context

The owner runs AGK solo and asks to measure speed, quality and cost from AGK's records only (brief #1618). `measures.py`
(ADR-0659) gives per feature `lead_hours`, `fix_rounds`, `tokens` and `owner_wait_minutes`, but its owner wait counts
only a `Question:` for the maintainers, while the conductor's `Owner needed:` is the most common ask; nothing reads park
time, the `The default branch is red` issues or reverts; and no record names the tier a session ran on (Q-1557-4).
Options weighed: (A) new columns on every feature row; (B) one `--trial` option that adds one range row and leaves the
default output byte-identical.

## Decision

(B) is chosen.

1. `measures.py --trial` adds one `trial` row, text and `--json`; without the option the output does not change.
   `--trial` takes no value and is given once, else it is refused naming the option (exit 2).
2. The owner's wait is read as `session.open_owner_items` reads it (with no label item, a label being today's state),
   walked over each feature's brief and pull request threads: an item opens on a `Question:` for the maintainers or an
   `Owner needed:` by a listed verdict author and closes on the answer that rule names, else at the finishing merge.
3. Park time runs from each `Parked-by: wait` to the next `Unparked-by:`; an open one runs to the end of `--to` and is
   counted as `(<n> open)`.
4. Red spells are the issues titled `The default branch is red` that overlap the range (one GET of the issues updated
   since `--from`), opened to closed, cut to the range. Reverts are merged pull requests in the range whose merge commit,
   read by local git, starts `Revert "`.
5. The tier is the configured tier of the brief's kind (`session.kind_of` on the brief body with `config.model_settings`),
   labelled `(configured)`; a pull request tied to no brief is `unknown`. No cost is estimated (rule 27, Q-1618-1).
6. In solo mode `confirmations` counts the one person's `Confirmed:` lines; team mode prints `none (team mode)`.
   Personal mode prints `none (personal mode)` for the owner, park, red and confirmation figures; local mode still reads
   red spells and reverts.
7. `metrics.py` and the weekly report do not change (ADR-0659 decision 7, Q-1618-2).

## Consequences

One command shows how a solo run performs. The trial is a reading of today's records and settings: the tier is the
configured one, not the one a session actually used. SPEC-0007 gains rule 29 only by amendment 213, on the owner's
`Approve: SPEC-0007`.

## Residual

- The actual tier of a `Report:` is not recorded; recording `AGK_TIER` there is a separate brief (due 2026-12-20).
