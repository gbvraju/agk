# ADR-0305: The kit's full suite runs in parallel workers where xdist is importable (REQ-051, brief 631)

- Status: Accepted
- Date: 2026-11-06
- Deciders: maintainers
- Related: ADR-0270, ADR-0302
- Requirements: REQ-051

Protected classes: `agk.toml`, `kit/`, `tests/kit/`

## Context

Tracker #630 item 5 (owner yes, 2026-11-06): the full suite on the default branch and in a release runs in parallel
workers with the same result, so that the main check takes under 10 minutes instead of about 16. Workers exist since
#585 (SPEC-0044 rules 4 to 7) and are off: `[testing] workers` is absent, so it is 1.

In this repository the full suite of a push to the default branch and of a release pull request is the governance step
`Tests of the checks`, which runs `make -f agk.mk agk-test`, the target of `kit/agk-kit.mk`. That target ran pytest
directly and never read `[testing] workers`; only `prepush.full_command` (prepush's tests step and
`project_tests.py`) did. The step `Project tests` is skipped here (`hashFiles('kit/agk-kit.mk')`), and proof's
red-then-green runs stay single (SPEC-0044 rule 4, `Q-S0044-8`).

## Decision

1. `agk.toml` sets `[testing] workers = "auto"` (the machine's CPU count, at least 1). No other setting changes.
2. `agk-test` of `kit/agk-kit.mk` takes its command from `prepush.full_command` with that setting, as prepush and
   `project_tests.py` do: `-n <workers>` at the end when the suite's interpreter imports xdist in the repository's
   folder, otherwise the command of today after the one line `tests: pytest-xdist is not importable, running in one
   process (setting: testing.workers)`. The kit installs no plugin (`Q-S0044-2`). It prints the command it runs, and a
   malformed setting fails the target with one line naming the setting. The suite and its folders are unchanged.
3. The setting has no event of its own: every run of `agk-test` reads it, on a pull request as on a push, and so does
   prepush's full run, whose `project_tests` is a compound command and therefore stays single with its one line
   (SPEC-0044 rule 5). A test that fails only under workers is a finding for the flake ledger, never a reason to lower
   the setting (SPEC-0044 rule 1).
4. The fake `xdist` of the workers fixture also answers as `xdist.plugin`, the module of the real plugin's entry point,
   so that its same-result test (SPEC-0044 rule 6) passes where pytest-xdist is installed.

## Consequences

Where pytest-xdist is importable the kit's suite runs in as many workers as the machine has CPUs, with the same counts.
Where it is not, nothing changes but one line. The CI tooling step of `governance.yml` installs pytest, ruff and bandit
only, so CI keeps running single until a workflow change installs pytest-xdist; that change needs the owner and is not
made here (brief #631 answer 4, `Q-631-1`).

## Residual

- CI reaches workers only after the tooling step installs pytest-xdist, a workflow change for the owner (`Q-631-1`,
  2026-11-06).
- `"auto"` takes the runner's CPU count; a GitHub-hosted runner of a private repository has 2 `(verify)`, so the
  speedup there is at most about two times (2026-11-06).
