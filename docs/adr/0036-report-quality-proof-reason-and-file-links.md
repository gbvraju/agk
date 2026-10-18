# ADR-0036: the Proven line prints the proof reason; the facts carry a path for each spec and ADR, kit 0.18.0

- Status: Proposed
- Date: 2026-10-18
- Deciders: maintainers
- Related: ADR-0026, ADR-0028, ADR-0029
- Requirements: REQ-016, REQ-017, REQ-018

Protected classes: `.github/`, `scripts/agk/`, `tests/kit/`, `kit/`, `.claude-plugin/`

## Context

The first live product report (issue 68, `docs/runs/product-report-live-1.md`) showed REQ-001 and REQ-003 as `not proven` with no way
for a reader to tell an environment fault (the proof job of PR #60 ran without pytest: `red-on-head`) from a real gap (`green-on-base`:
the new tests already pass without the change). The maintainers' ruling of 2026-10-18 asked for the reason next to `not-proven`
(residual, due 2026-11-15). ADR-0029 left a second residual (due 2026-11-30): the facts carry no path for a spec or an ADR, so the
inbox linked the directory, not the file. Both are done here.

## Decision

1. **The proof workflow names its outcome steps with the reason.** The run step of `proof.yml` writes a second output, `reason` (the
   `reason` of `proof.py --json`; empty for `proven` and `skipped`). The steps are named `outcome: proven`,
   `outcome: not-proven (${{ steps.proof.outputs.reason }})`, `outcome: skipped` and `outcome: unknown (${{ ... }})`, so the job's steps
   carry the reason in the one place `facts.py` already reads, with no log download and no artifact.
2. **The facts gain `proof_reason`** for each pull request (a word such as `red-on-head`; `null` for `proven` and `skipped`; `"unknown"`
   when the outcome could not be read or the step name carries no reason, as in a run made before this change), and **`path`** for each
   spec and ADR. Both are optional properties of `kit/facts-schema.json`. `schema` stays `1`: no released consumer reads either field (the
   renderer of kits 0.15.0 to 0.17.1 ignores keys it does not know, and the renderer of this change treats a document without them as
   before); a change to the meaning or removal of a key would raise it.
3. **The renderer prints the reason**: `REQ-001 is not proven: the last change (PR #60) was not shown to need its test (not-proven:
   red-on-head, the tests fail on the change itself)`; the five reasons of `proof.py` have a plain-language gloss; a reason without one is
   printed as it is; a missing or unknown reason reads `(not-proven: reason unknown)`. The inbox lines for a Draft spec and a Proposed ADR
   link the file at the facts commit when the document carries a `path`, and the directory otherwise.
4. **Specs amended** (`docs/runs/proposed-spec-amendments-23.md`, applied here): SPEC-0010 rule 17, SPEC-0009 rules 10, 11 and 14,
   SPEC-0011 rules 3, 9 and 11.
5. **Fixtures**: the recorded job responses of the facts fixtures carry the new step names (`red-on-head` for PR 12 of `pr-states`,
   `timeout` for PR 15); the report fixtures carry `path` and `proof_reason`; every golden is regenerated and read. New tests: the reason
   is read from the name; an old step name reads `unknown`; a malformed reason reads `unknown`; the paths of specs and ADRs; the five
   reasons in the Proven line; a document without the new fields still renders; the file link and the directory fallback; the workflow's
   step names and its `reason` output.
6. **Kit 0.18.0**: manifest, hashes, plugin version. The register's two lines are closed (below).

## Verified in a clean environment (ADR-0028)

This change touches the `proof` job, so the exact `project_tests` command was run from the repository root in a fresh `python3 -m venv`
with nothing installed, with a `PATH` of the venv, the Go toolchain and the system `bin` directories (no `pytest` and no `ruff` on it):

```
COMMAND: (python3 -m pytest --version && ruff --version) >/dev/null 2>&1 || python3 -m pip install -q pytest ruff; AGK_KIT_TESTS=1 python3 -m pytest -c tests/kit/pytest.ini tests/kit tests/kit_dev -q
1071 passed, 4 skipped in 361.42s (0:06:01)
exit=0
pytest    9.1.1
ruff      0.17.1
```

Python 3.13.16, pip 26.2.1. (Four skipped here against three in the developer environment; the skips are tests that need a tool
that is not on this `PATH`.)

## Consequences

- A reader of the next product report can tell an environment fault from a gap; the issue-68 reading of REQ-001 and REQ-003 would have
  said `red-on-head, the tests fail on the change itself`.
- A pull request whose proof job ran before this merges reads `reason unknown`; only runs made after it carry the reason.
- The new step names are first seen on GitHub when the `proof` job of this pull request runs; they are not read here (CI is not
  polled). The live reading is a step after the merge: `facts.py` on this repository, `proof_reason` of this pull request.

## Questions

| Q | Question | Reading taken (conservative) |
| --- | --- | --- |
| Q-K4-169 | Where can the reason travel from the proof job to the facts? | in the name of the succeeded outcome step: the only place `facts.py` already reads; a log download or an artifact would add a read and a permission |
| Q-K4-170 | Schema 1 or 2 for `proof_reason` and `path`? | 1: additive optional properties, no released consumer reads either, the renderer tolerates their absence; stated in the amendments file |
| Q-K4-171 | The kit version. | 0.18.0: installed files (`proof.yml`, `facts.py`, the renderer, fixtures, tests) change and the facts document gains fields |
| Q-K4-172 | The Closed rows of the register do not silence the D4 finding for an overdue bullet of an Accepted ADR. | the two lines are closed in the register's Closed table as for the earlier ones; the ADR-0029 bullet (due 2026-11-30) stays in an Accepted ADR and `drift_audit.d4_documents` does not read the Closed table, so it will report as overdue on 2026-12-01 unless the maintainers rule how a delivered bullet is retired |

## Residual

- 2026-10-18: the Closed table of the register is informational; a delivered residual bullet in an Accepted ADR keeps reading as
  overdue after its due date (Q-K4-172) (due 2026-11-30).
