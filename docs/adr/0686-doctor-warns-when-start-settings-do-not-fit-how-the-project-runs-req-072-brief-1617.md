# ADR-0686: Doctor warns when the start settings do not fit how the project runs (REQ-072)

- Status: Proposed
- Date: 2026-11-20
- Deciders: maintainers
- Related: brief #1617, SPEC-0006 rule 5, SPEC-0045 rules 2 and 4, SPEC-0034 rule 1, ADR-0402, ADR-0409, ADR-0525, ADR-0662
- Requirements: REQ-072

Protected classes: `scripts/agk/`, `tests/kit/`

## Context

The owner runs AGK solo and asks for settings that move fast (brief #1617). Four settings did not fit how the project
runs, and `doctor.py` said nothing: no open kit brief reaches the `mid` tier, since a brief that touches a protected path
is `build` (SPEC-0045 rule 4); `auto_start` with a Windows `.ps1` adapter while every session runs in the cloud;
`reviews_in_flight` 9 under `max_builders` 12; and builder slots whose markers are days old. Options weighed: (A) change the
routing or the settings; (B) four information rows in `doctor.py` and no change of a setting.

## Decision

(B) is chosen; each row is severity `warn`, never an error.

1. `tier-use`: the open `agk-brief` issues (the GET `brief-broad-touches` already makes), each given its kind by
   `session.kind_of` and its tier by `config.model_settings`. It prints each tier's count and warns for a tier that a
   brief kind uses and no open brief gets. No open briefs is `ok (no open briefs)`; briefs that cannot be read are
   `cannot-check`; a refused `[models]` entry names `models.<kind>`. Routing protected-path work to `mid` is a later spec
   decision (Q-1617-1).
2. `launch-adapter` gains two lines with `auto_start` on: in a cloud session (`common.REMOTE_RUNTIME`, `(verify)`; one it
   cannot detect is treated as not cloud) `auto_start starts nothing from a cloud session, not run here`, and a `.ps1`
   adapter on a machine that is not Windows. Each names `[flow] launch_adapter`, never the command (Q-1617-2).
3. `review-ceiling`: `reviews_in_flight` under `max_builders`, both through `session_plan.ceilings`, prints the
   difference as builds that may wait for a review; no value is proposed (Q-1617-3). `[capacity] profile = "fixed"` sets
   them equal, so it is quiet.
4. `slot-use`: with `builder_start = "assign"`, every comment of the assignments issue is read (a marker is edited in
   place, so `since=` would hide an old one); the slots whose newest marker is over 24 hours old are stale, and the runs of
   the last 24 hours whose `decided:` is `none` are idle. The account's scheduled tasks cannot be read, so it says
   `(verify)`. Any other `builder_start` reads nothing.
5. Personal mode prints its own doctor line and runs none of these rows. No workflow and no setting changes.

## Consequences

`doctor.py` prints 55 rows. A project whose briefs touch no protected path uses `mid`, so `tier-use` stays quiet there; in
this repository it warns until routing changes. The owner changes `agk.toml` by an ADR.

## Residual

- `slot-schedule` reads a doubled repository path in a live run (found-bug #1625); due 2026-12-20.
