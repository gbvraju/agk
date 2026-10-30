# ADR-0186: a builder runs the fast checks before every push (REQ-016, brief 326)

- Status: Proposed
- Date: 2026-10-30
- Deciders: maintainers
- Related: ADR-0185, ADR-0182, ADR-0158
- Requirements: REQ-016

Protected classes: `scripts/agk/`, `tests/kit/`, `kit/`, `config/`

## Context

Brief #326 (priority 1), part of #288 (tier T0: the checks that run in the builder's own environment before every push). In a
pilot, builders pushed often and waited for CI; many rounds failed on a pull request body, a lint error or a missing changelog
fragment, and each round cost minutes on a Free plan (#287). The kit already has every check; nothing ran them together before a
push. The brief names no `Measured:` line. The tests were written first (`tests/kit/test_prepush.py`: 20 of 20 failed at the first
checkpoint of the pull request).

## Decision

1. **`scripts/agk/prepush.py [--body FILE] [--base REF] [--quick]` (answer 1).** Standard library only; run from anywhere inside
   the work tree. The base is `--base`, else `AGK_BASE`, else the default branch (`origin/<default_branch>`, then
   `<default_branch>`), as the other checks resolve it, and the branch is its merge base to `HEAD`. The steps run in this order
   and the first failure stops the run with that step's own output:
   - `pr-body`: `check_pr_body.py --draft false FILE` on the body file, when `--body` is given; skipped otherwise.
   - `lint`: `make lint`, when the project's Makefile has a `lint` target (`make -n lint` succeeds); skipped otherwise.
   - `governance`: `make -f agk.mk agk-governance` with `AGK_BASE` set to the base: the governance checks that need no network,
     the same list as `make governance` and the governance workflow without its API inputs. A missing `agk.mk` fails the step,
     naming the path class.
   - `secret-scan`: `gitleaks git --no-banner --redact --exit-code 1 --log-opts=<merge base>..HEAD .`, the scan of the
     governance workflow over the branch's commits, when `gitleaks` is on `PATH`; otherwise the step says `gitleaks is not
     installed; secret scan: not run`, as the local-mode guide words it; it does not fail the run, and no tool is downloaded (Q-326-3).
   - `tests`: each run of `test_plan.py --json --base <merge base>` (the plan proof runs, brief #325), its command in its folder
     through proof's own `execute` (no shell of the kit's; the project's command runs under `sh -c` as in proof), ended at
     `proof_timeout`; `tests: nothing to run` when the plan has none; skipped with `--quick`.
   It prints `prepush: <step> ok|FAIL|skipped (<seconds>s)` per step, and at the end `prepush: all steps passed`, or
   `prepush: passed; not run: <steps>` when a step that should have run could not (the scanner missing). Exit 0 when no step
   failed, 1 when one did, 2 usage, a body file that cannot be read or a base that does not resolve (naming the setting, never the
   value).
2. **The hook template (answer 2).** `kit/templates/pre-push` is a POSIX shell hook that runs `prepush.py` from the top of the work
   tree. The kit never installs it: it is not in `kit/manifest.json`, and no script writes `.git/hooks` or `core.hooksPath`. The
   getting-started guide says how a person copies it, and that doing so is their choice.
3. **The session rule (answer 3, Q-326-2, Q-326-4).** `config/session-rules.md` gains rule 31: a builder runs `prepush.py` before
   each push. Rule 7 is unchanged: SPEC-0033 rule 1, an Approved spec, says a builder commits and pushes at every step, so the
   brief's "pushes at milestones" is not taken here. The verdict on f9ba218 withdrew the answer to Q-326-2 for that reason; the
   change is proposed for the maintainers in `docs/runs/proposed-spec-amendments-101.md` (SPEC-0033 rule 1 and session rule 7)
   and waits for their decision.
4. **Installed (Q-326-1).** `kit/manifest.json` lists `scripts/agk/prepush.py` with the verbatim scripts, so a project has it.
   The brief's `Touches:` does not name `kit/manifest.json`; it is the one file outside it.
5. **Tests (answer 4).** `tests/kit/test_prepush.py`: all steps in order; each step's failure stops the run with its message; no
   body file; a body file that cannot be read; a project without `make lint` and without a Makefile; a missing `agk.mk`; the base
   given to governance; the scan's range; no scanner; the plan's tests and an empty plan; `--quick`; a base that does not resolve;
   usage; the hook template; session rule 31 and rule 7 unchanged; a test run ended at `proof_timeout`.
6. **Flow mode.** Fragment `changelog.d/prepush.md`; no version bump; `kit/hashes.json` not edited (session rule 14).

## Consequences

- A builder learns in seconds, before it pushes, of the failures that cost a CI round most often: the body, lint, governance and a
  secret in the branch.
- CI stays the trust anchor (#288 tier T1): `prepush.py` adds no evidence and replaces no required check.

## Residual

- 2026-10-30: Q-326-1 answered in the verdict on 2512153: yes, `kit/manifest.json` lists `scripts/agk/prepush.py`, named in the
  body as a change outside `Touches:` (decision 4).
- 2026-10-30: Q-326-2 answered in the verdict on 2512153 (amend rule 7), and that answer withdrawn in the verdict on f9ba218
  (Q-326-4): the approved spec wins; rule 7 is as on main (decision 3).
- 2026-10-30: Q-326-3 answered in the verdict on 2512153: the reading is accepted; a missing gitleaks prints `secret scan: not
  run`, does not fail, and the run ends `prepush: passed; not run: secret-scan` (decision 1).
- 2026-10-30: Q-326-4 answered in the verdict on f9ba218: rule 7 stays; pushing at milestones is proposed in
  `docs/runs/proposed-spec-amendments-101.md` for SPEC-0033 rule 1 and session rule 7, and waits for the maintainers.
