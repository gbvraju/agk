# ADR-0419: The real token figure from the session's transcript, and the cost per kind

- Status: Proposed
- Date: 2026-11-10
- Deciders: maintainers
- Related: SPEC-0045 rules 2, 8 and 9, amendment 145 items 7 to 10 and 13, ADR-0289, brief #798 build (a), pull request #977
- Requirements: REQ-052

Protected classes: `config/`, `scripts/agk/`, `tests/kit/`, `kit/`, `agk.toml`

## Context

Every builder `Report:` since SPEC-0045 build (d) ends `Usage: not shown`, because a session could not
see its own figure, so `metrics.py --usage-by-kind` and the caps of SPEC-0049 read nothing (brief #798,
`Measured:`). A session's own transcript holds a usage record per message. Amendment 145, approved by
the owner on #939 and applied by #954, changes SPEC-0045 rule 8 from "when the runtime shows the
figure" to "as `usage.py` prints it", adds an optional `[models.prices]` table, and asks rule 9's sums
for one line per merged pull request and one cost line per kind. Build (a) changes those decisions of
SPEC-0045 and ADR-0289, so it writes its own ADR (Q-798-1); ADR-0375 of the take was already used, and
this number was reserved on the brief by the answer to Q-798-12.

## Decision

- `scripts/agk/usage.py` (new, installed, read-only) finds the running session's transcript by the
  runtime's session id variable under the runtime's home folder, or takes `--transcript FILE`, and sums
  the four token counts of each distinct message id once, at its first entry. `--since <UTC time>`
  keeps only messages first written at or after that time, so a message counted in one `Report:` is
  never counted again. It prints `Usage: <n> tokens` or `Usage: not shown`, never 0 for a missing
  figure, and prints no text of the transcript. The lookup is marked `(verify)` (Q-798-5).
- `config.model_prices` reads `[models.prices]`: a tier to a finite number of 0 or more; anything else
  is refused naming `setting: models.prices` or `setting: models.prices.<tier>`, never the value, and
  `model_settings` accepts `prices` as a key of `[models]`. The kit ships no such table.
- `metrics.py --usage-by-kind` prints `  #<n> <tokens or not reported>` under each kind's line and, with
  a prices table, one `  cost <x> at the prices table (<k> not reported)` line. A pull request is priced
  at its kind's tier, or at `strongest` when one of its `Report:` comments is an `escalate`, carries a
  `Route:` line, or its comments cannot be read (Q-798-9); a tier with no price makes the kind's cost
  `unknown`. The amount is rounded half up to two decimals.
- Session rules 8 and 17 name `usage.py` as the source of the `Usage:` figure, within the rule budget.

## Consequences

- A builder's `Report:` and `Progress:` lines can carry a real figure, so `metrics.usage_of`, the caps
  and the weekly sums read numbers instead of `not reported`.
- The cost line reads each priced pull request's comments with one GET, only when a prices table exists;
  without the table the command reads what it read before.
- No check refuses a `Report:` line, no field is added to `report.json`, and no network call is made by
  `usage.py`.

## Residual

- 2026-11-10: the transcript lookup is read from this cloud runtime, not from its documentation; a
  runtime that writes elsewhere prints `Usage: not shown` until `--transcript` is passed (due 2027-01-31).
- 2026-11-10: a helper agent's tokens are counted only where the runtime writes them into the session's
  own file, so the figure may under-count (due 2027-01-31).
- 2026-11-10: one price for every token, cached or not, so the cost line is an upper bound (due
  2027-01-31).
