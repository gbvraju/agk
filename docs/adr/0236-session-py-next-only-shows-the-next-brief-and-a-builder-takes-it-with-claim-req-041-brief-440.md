# ADR-0236: session.py next only shows the next brief, and a builder takes it with claim (REQ-041, brief 440)

- Status: Accepted
- Date: 2026-10-31
- Deciders: maintainers
- Related: ADR-0195, ADR-0229
- Requirements: REQ-041

Protected classes: `scripts/agk/`, `config/`, `tests/kit/`

## Context

Brief #440, from the #286 field note of 2026-10-29, item 1: `session.py next` took the brief it printed as a side effect
(session rule 5). A builder that only meant to look took a brief, and two lanes collided. `claim` (#345, merged in #361)
already takes a named brief by the plan's rules. `session.py` (`scripts/agk/`), the session rules (`config/`) and their
tests (`tests/kit/`) are protected path classes, so this ADR names them. The guides (`docs/guides/`) are not protected.
The tests were written first (`tests/kit/test_session_next_plan.py`, the `test_440_` tests: 5 failed, 8 passed at the
first checkpoint; the 8 passing were the reasons, `full`, `after` and five of the usage refusals, which hold before the
change too).

## Decision

1. **`next` only shows (answer 1).** `session.py next --session ID` makes the same choice and prints the same reasons as
   before (a stalled pull request first, then `full`, the skips and the order of the plan), then the brief and one line
   `take it with: session.py claim --session ID --brief N`. It posts nothing. A stalled pull request is shown with
   `take it over with: session.py next --session ID --take` and no `taken over:` comment (Q-440-1).
2. **`next --take` (answer 2).** `--take`, a flag without a value, of `next` only and at most once, keeps the behaviour
   before this ADR: choose and take in one step, with the reservation in the one `taken:` comment, and the takeover of a
   stalled pull request. Any other use of `--take` prints the usage and exits 2.
3. **`after` takes (answer 3).** `session.py after` with `assign = "next"` takes as before, since a finished builder is
   meant to start its next brief.
4. **The texts (answer 4).** Session rule 5 says a builder takes a brief only with `claim` or `next --take`, rule 9
   says `next --take` takes over a stalled pull request, and rule 18 says `after` with `assign = "next"` is `next --take`.
   The getting-started guide (also its step 7 on `after`), the security guide, the remote-builders guide (step 2, approved
   by the conductor's verdict on c26b62e although outside the brief's `Touches`) and the module text of `session.py` say the
   same; the launcher examples of the guide, which start sessions that build what they are handed, run `next --take`.
5. **`claim` reserves (the conductor's ruling on Q-440-2).** Since `claim` is now the default way to take a brief, a `claim`
   without `--build` writes the numbers the brief needs into its one take, as `next --take` does (`reservation`, from a
   survey that sees the open builder pull requests and every live take's reservation; SPEC-0034 rule 4). A `claim` of a
   build reserves nothing, as before. A read that fails reserves nothing and says so in one note, and the take still posts.
6. **Tests (answer 5).** `next` posts no comment and prints the claim line; it keeps its reasons and `full`; `next --take`
   posts the one `taken:`; `after` still takes; the printed claim command takes the same brief and reserves its ADR; `claim` of a whole brief reserves past the numbers in
   use; a stalled pull request is
   shown without a takeover; the usage refusals of `--take`. The earlier tests of the take run `next --take`.

## Consequences

- Asking which brief comes next never starts work on another lane's brief.
- A script or launcher that relied on `next` taking adds `--take`; `after` needs nothing.
- `claim`, `next --take` and `after` all write the reservation into the take of a whole brief, so two builders that take
  two briefs never get the same next number.

## Residual

- Q-440-1 (2026-10-31): the brief names only briefs; `claim` takes a brief and cannot take over a pull request, so the
  conservative reading shows a stalled pull request without the takeover and names `next --take` as the command that
  takes it over.
- Q-440-2 (2026-10-31): the printed `claim` wrote no `reserves` list into its take. Answered by the conductor's verdict on
  c26b62e: in scope, `claim` of a whole brief reserves (decision 5).
- Q-440-3 (2026-10-31): REQ-037 AC3, REQ-040 AC5 and REQ-041 AC1, AC3 and AC5 in `docs/requirements.md` and the specs
  they come from describe `next` as taking; requirements and specs are the reviewers', so they are not edited here.
  `scripts/agk/stalls.py` ("`next` offers it first") stays true and is outside the brief's `Touches`.
