# ADR-0048: launch docs L2: the product-owner guide, the existing-codebase guide and the security page

- Status: Proposed
- Date: 2026-10-19
- Deciders: maintainers
- Related: ADR-0047, ADR-0025, ADR-0043
- Requirements: REQ-020

Protected classes: `tests/kit_dev/`

## Context

L2 is the second of the two launch-docs pull requests (the maintainers' brief of 2026-10-19; L1 is ADR-0047). It adds the three guides ADR-0025 names for the launch minimum (the
product-owner guide, the existing-codebase path and the one-page security posture) and the second live walk. The L2 target is 2026-10-28.

ADR-0047 Decision item 3 says the label `agk-stuck` "does not exist yet". That is superseded: the label exists since 2026-10-19 (ADR-0047 itself records it as done under Q-K4-192). ADR-0047
is Accepted and is not edited.

## Decision

1. **`docs/guides/product-owner.md`**: when the report arrives (the slot, and the delay seen on 2026-10-19), the five sections with one real line each taken from the first scheduled report
   (issue 88 of this repository) and linked, the five questions of ADR-0021 in order, what to do for each of the six kinds of "Needs you", and what `unknown`, `skipped` and `proven` mean.
2. **`docs/guides/existing-codebase.md`** (ruled on Q-K4-185): `/agk:adopt` (which touches no product file), then today's behaviour recorded as baseline requirements and tests before any
   change (`Behaviour: unchanged`, the proof reads `skipped`), then `project_tests`, then the first real change with the test first (the proof reads `proven`). The differences from a
   new repository that the walk found are in it (no `make governance`, the `origin/HEAD` refusal, an ADR for `agk.toml`).
3. **`docs/guides/security.md`**, one page: what AGK stores, where code and prompts go, credentials, what each workflow may write (a table of the permissions in the workflow files), the
   architect guard and what it cannot prevent. Each statement names the file that makes it true; what rests on a tool outside AGK, or on an unproven fact, says so.
4. **`tests/kit_dev/test_docs.py`** covers the three files through the same check as L1 (it reads every file of `docs/guides/`) and gains two tests of their shape: the product-owner and
   existing-codebase guides, and the security page, whose table of workflows is compared with the workflow files (every workflow listed; `write` in the row exactly when the file grants a write).
5. **Live walk**: `docs/runs/docs-walk-2.md` records the walk of the existing-codebase guide on a throwaway copy of a small repository, what was walked and what was not, and six findings,
   all fixed in the guide.
6. **No kit bump**: no installed file changes.

## Consequences

- A product owner can read the Monday issue with a page that says what each line means and what to do about it, and an owner of an existing codebase has an order of work that starts by
  recording what the product does.
- The security page makes claims that a later change to a workflow's permissions can break; the test compares the table with the files, so it fails until the page is updated.

## Questions

| Q | Question | Reading taken (conservative) |
| --- | --- | --- |
| Q-K4-197 | The brief asks to link "the pilot's two proven examples by their records in this repository". No record in this repository names two proven examples of the pilot | none is linked and none is invented; the guide links the records that exist (the adoption of a real repository, the proof check's first readings, and the `Proven` lines of the first scheduled report) and says the pilot's are not yet recorded here |
| Q-K4-198 | The brief says the report usually arrives "Monday afternoon IST"; the ruling on #89 says "usually Monday evening" and the first scheduled report arrived about 7.5 hours after its 07:13 UTC slot (about 20:10 IST) | the guide gives the slot, the observed delay and says "Monday afternoon or evening in India, and sometimes later" |
| Q-K4-199 | `python3 -m pytest -q` in an adopted copy took 118.23 seconds once and 11.33 seconds on later runs, for three tests of the project's own | not investigated and not fixed (a script or configuration finding); the guide states only the timeout of the proof check |
| Q-K4-200 | How far may the security page say that AGK sends nothing anywhere? | only as far as a test or a file shows: no network library is imported by the architect guard, the drift audit or the report renderer (tested), the scripts that read GitHub do it by `gh api --method GET`, and no script writes to GitHub; the rest (the deployment of Claude Code, the licence of the secret-scan action) is marked `(verify)` or left out |

## Residual

- 2026-10-19: no one outside the project has followed the three guides; the first outside developer's "I got stuck" issues and the first product owner's answers to the five questions are the findings. (due 2026-11-20)
- 2026-10-19: the no-network-import tests cover three scripts; the other scripts that run `gh` are covered by reading, not by a test. A test over `scripts/agk/` would make the sentence of the security page stronger. (due 2026-12-15)
