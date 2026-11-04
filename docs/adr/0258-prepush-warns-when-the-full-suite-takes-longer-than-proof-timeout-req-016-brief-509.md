# ADR-0258: prepush warns when the full suite takes longer than proof_timeout (REQ-016, brief 509)

- Status: Proposed
- Date: 2026-11-04
- Deciders: maintainers
- Related: ADR-0186, ADR-0208, ADR-0227, ADR-0257
- Requirements: REQ-016

Protected classes: `scripts/agk/`, `tests/kit/`

## Context

In the pilot (#494) the full suite took about 1,234 s while `proof_timeout` was 900 s. Every pull
request that selected the full suite ended "did not finish" in proof, and evidence read differs, until
a person noticed and raised the setting. Nothing told the project at once that proof could never
finish. This ADR number was reserved for brief #509 by the conductor (the field note on #509).

## Decision

1. In `scripts/agk/prepush.py`, after a regression run whose name is `full` finishes with an exit
   status, when its seconds exceed `common.proof_timeout(root)`, the tests step prints one line:
   `prepush: warning: the full suite took <n> s, more than proof_timeout (<m> s); proof will not finish
   (setting: proof_timeout); a value of about <v> s leaves headroom`, where `<n>` is the run's seconds
   rounded to a whole second and `<v>` is `ceil(n * 1.5 / 60) * 60`.
2. The outcome of prepush does not change: a run that passed still passes and a run that failed still
   fails. The line is added to `notes`, a new list of the `--record` file (empty when no warning was
   printed); the record stays schema 1, because a key is only added.
3. Only the regression run named `full` warns: a selected area run, or a proof-plan run, over the limit
   prints nothing. A run that the limit ended prints the timeout note as before and no warning
   (Q-509-1). A refused `proof_timeout` setting keeps today's refusal.
4. `docs/guides/testing.md` gains one sentence in the pre-push gate section, where `proof_timeout` is
   described: set it above the full suite's time with headroom, and prepush warns when it is not.

## Consequences

A project whose full suite outgrows `proof_timeout` sees the setting, both durations and a suggested
value in the first prepush that runs it to the end, before any proof run reads "did not finish".
Changing `proof_timeout` stays a person's change; nothing raises it automatically.

## Residual

- 2026-11-04: prepush holds each run to `proof_timeout` itself (ADR-0227), so a full suite slower than
  the limit is ended there and prints the timeout note naming the setting; the warning appears only when
  a run finishes past the limit (Q-509-1). Doctor does not warn (out of scope of the brief).
