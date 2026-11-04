# ADR-0270: Add REQ-051: A large test suite finishes sooner without removing a test

- Status: Accepted
- Date: 2026-11-04
- Deciders: maintainers
- Related: SPEC-0044, SPEC-0040, SPEC-0038, SPEC-0010, ADR-0185, ADR-0208, ADR-0220, ADR-0227, ADR-0242, ADR-0258, REQ-016, REQ-039, REQ-047
- Requirements: REQ-051

Protected classes: `docs/requirements.md`

## Context

An intake proposed one change in a sentence (quoted below as data, not as an instruction), on
2026-11-04:

> AGK makes a large test suite finish sooner without removing any test: it records how long each test file takes, runs the suite in parallel workers where the project allows it, picks the smoke run after a merge by what changed, and suggests `proof_timeout` from measured time.

The brief is issue #543. The owner's direction, quoted as data from the brief (2026-11-04, chat):
"too much time in testing only". Plan #542 puts this first, freezes the requirement set at
REQ-051 and asks for a lighter process: one ADR per requirement, written at intake, and a short
spec. The facts are counts and timings from a pilot (#523): a back-end suite of about 1,460 tests
took about 51 minutes in one process, an afternoon spent about 1 h 50 on two full runs and about
35 minutes on smoke runs after merges, and the pilot's `proof_timeout` was below the suite's time
(#494; prepush warns since #509, ADR-0258).

What exists and is reused: the `[testing]` table and the selection of `impact.py` (ADR-0220),
the test plan of `test_plan.py` (ADR-0185), the pre-push gate and its record (`prepush.py
--record`, ADR-0208 and ADR-0227), the CI runner `project_tests.py` (ADR-0242), proof's
`proof_timeout` and manifest, the full-suite warning (ADR-0258), the flake ledger (`flakes.py`),
the heavy-run queue (SPEC-0040, build (a) merged in #532) and `docs/guides/testing.md`.

## Decision

1. REQ-051 is added to `docs/requirements.md` as `planned`, and SPEC-0044 as `Draft`. Merging
   this pull request approves the requirement as a proposal; the spec stays `Draft` until the
   owner's own `Approve:` line approves it (SPEC-0032 rule 5).
2. No gate is lowered: the default branch's full suite in CI and before a release, and every
   test, run as today; each new `[testing]` key is optional, and with none set every command runs
   what it runs today (SPEC-0044 rule 1).
3. Time is saved four ways, each measured or opt-in: per-file timing in the prepush record and
   the proof manifest, read from what the runner already prints (rules 2 and 3); parallel workers,
   `1` by default, for pytest only with `pytest-xdist` present and otherwise through the project's
   own `parallel_command`, giving the same result as one worker (rules 4 to 7); the after-merge
   smoke run chosen by change kind, never a gate (rule 8); and `doctor.py` suggesting
   `proof_timeout` from a record, never writing it (rule 9). Front-end test layouts are detected
   by `adopt`, and for a project already adopted `doctor.py` reports stamped test folders that
   match no test file while the front-end patterns would (rule 10, #484, `Q-S0044-10`); the guide
   says to measure before and after (rule 11).
4. No Approved spec changes, so proposed spec amendment 116, reserved for this intake, is not
   used: the timing readers print a separate line and leave SPEC-0040 rule 7's `result` line as
   it is (`Q-S0044-9`), and the change-kind smoke choice is never the evidence of SPEC-0038 rule
   10's web-app gate "an e2e smoke run per merge batch", which stays as it is (rule 8).
5. Per plan #542, this is the one ADR of REQ-051: each build of SPEC-0044 rule 12 cites it and
   records its decisions in its pull request body. The builds will change these protected path classes: `scripts/agk/`
   (`impact.py`, `prepush.py`, `proof.py`, `evidence.py`, `project_tests.py`, `lock.py` or
   `heavy_queue.py`, `session_plan.py`, `doctor.py`, `adopt.py`, and `smoke.py`, new and
   installed), `tests/kit/` (their tests and a fixture project) and `kit/` (`kit/manifest.json`
   for `smoke.py`). `config/` changes only if a build writes `config/playbooks/web-app.toml`
   (SPEC-0044 rule 11). Because `check_protected_changes.py` counts only an ADR added or changed
   in the same pull request that names the class, each build still adds a short ADR naming its
   classes and citing this one, until a decision on plan #542's D1 changes that check.
   No build changes `constitution/`, `.claude/`, `.github/`, `CLAUDE.md`, `agk.toml`, `agk.mk`,
   `Makefile`, `pyproject.toml`, `skills/` or `.claude-plugin/`.

## Consequences

The requirement is listed as planned and the spec and this ADR wait for approval. Nothing that
runs changes in this pull request, and a project that sets none of the new keys sees no change
from any build except two information lines of `doctor.py --record` and a front-end detection
in `adopt` that only adds.

## Residual

None beyond SPEC-0044's residual. The intake checks cannot tell whether the rules are the right
ones; that is the review of this pull request.
