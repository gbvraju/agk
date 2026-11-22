# ADR-0703: The steward asks about one pinned head and writes the line on one yes

- Status: Proposed
- Date: 2026-11-22
- Deciders: maintainers
- Related: brief #1690, ADR-0661, ADR-0681, ADR-0179, SPEC-0062, amendment 194, Q-1690-1, Q-1690-2, Q-1690-3, plan #661
- Requirements: REQ-069

## Context

ADR-0661 decides the natural confirm and names build (a): a pending ask pinned to one head and the command that writes
the exact line on the person's yes. Its decision 4 names that command `steward_owner.py confirm`, but `confirm` is now
the standard's confirm of SPEC-0072 rule 8 (brief #1601, ADR-0681). Amendment 194 items 1 to 4, 7 and 8 are unapplied.

## Decision

1. `steward_owner.py ask --target pr:<n> --qid <Q> --file <question> --line <file>` reads the pull request with one
   GET, refuses a closed one and any line outside the forms below, records the `Owner question:` with the full head and
   the link, keeps the ask in the session's own state beside the steward cache (never a tracked file) as its one open
   ask (a newer ask closes every older one) and posts today's `Question:` line and nothing else.
2. The yes command is `steward_owner.py approve --ask <Q> --said <file> --at <time> [--by <login>]` (Q-1690-1). It
   takes the person's reply only to the latest open ask and refuses, naming the rule or setting, a moved head, a closed
   target, an unreadable ask state, a reply older than the ask, an ask older than four times `[flow]
   owner_wait_minutes` (24 hours when the key is unset or 0; Q-1690-2), `AGK_STEWARD_START=conductor`, a data-guard
   match, and a question mark or a condition word (rule 14's backstop). `Not yet` records a `Decision:` and posts
   nothing; any other reply that is not a yes by `steward_voice.is_yes` posts nothing.
3. On a yes the `Maintainer answer:` forms (an owner question's answer, `accept <head>`, `amendment <n> approved`) are
   posted with `-F body=@<file>`, UTF-8 with LF, with `Owner said`, `Asked` and `Who: ProductOwner`, and one `Decision:`
   is recorded; an `Approve: <head> SPEC-nnnn`, a sign-off `Approve:` and the `Confirmed:` text are printed ready to
   paste and never posted (ADR-0661 decision 8). `Merge:`, `Verdict:`, `Final:` and `Correction:` are never written.
4. Team mode counts only a `--by` login of `spec_approvers` and never writes `Confirmed:`; personal mode reads and posts
   nothing, prints `python3 scripts/agk/personal.py confirm <target>` and records the `Decision:` in the sidecar.
5. Amendment 194 items 1 to 4, 7 and 8 are applied to SPEC-0062 word for word, with `confirm` read as `approve`.
6. Path classes changed: `scripts/agk/`, `tests/kit/`, `agk.toml`.

## Consequences

An owner's yes in the chat becomes the pinned `Maintainer answer:` line without hand relaying, and an approval form is
printed for the person to post. Build (b) changes the guard and the readers; build (c) the words.

## Residual

- (due 2026-12-20) The `spec:<id>` and `q:<id>` targets of amendment 194 item 1 are refused by this build (Q-1690-3);
  a later build adds them or the item is narrowed.
