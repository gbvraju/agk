# ADR-0145: the router judges only the checks a project requires (REQ-039, brief 231, SPEC-0032 rules 2 and 7)

- Status: Proposed
- Date: 2026-10-26
- Deciders: maintainers
- Related: ADR-0123, ADR-0143
- Requirements: REQ-039

Protected classes: `agk.toml`, `kit/`, `scripts/agk/`, `tests/kit/`

## Context

Brief #231 (priority 1, measured 2026-10-26): a project that uses agk also runs checks agk does not own, such as a hosting provider's preview build. On one such project an optional preview build failed on every pull request for days while the checks its branch rules require (`proof`, `governance`) were green. The router counted every check run, so every pull request there was labelled `agk:ci-red`, a session read that as "fix CI" and a person learned to ignore the label. The tests were written first.

## Decision

1. **The setting.** `agk.toml` gains `required_checks`, a list of check names, default `["proof", "governance"]` (`common.required_checks`). A value that is not a non-empty list of non-empty strings is refused, naming the setting and never the value. The kit's two `agk.toml` templates carry the default with a comment; this repository's `agk.toml` states it.
2. **The judgement** (`route.py`, `judged`). `decide` takes the latest run (ADR-0143) of each listed name and the latest status of each listed context. A check that is not listed is ignored for the label, so a failing optional check with listed green checks leaves the pull request green. A listed check that has not reported keeps the pull request `agk:ci-running`; a listed check that is red stays red; running still comes before red in the order of SPEC-0032 rule 2. The router's own job `agk-route` is never judged, even when listed.
3. **The default branch** (`branch_state`, and `failing` for the check named in the red-branch brief) judges by the same list but waits only for the listed names that have a run or a status on the head: `proof` runs on pull requests only, so waiting for it would keep a broken main `pending` forever and rule 7 would never open or close the issue (the verdict on 51c566d). It is `pending` while a reported listed check is not completed and when none has reported; red when a reported listed check is red; green otherwise. This is the generic way the verdict names; a list of the checks that run on the default branch would need a second setting.
4. **An invalid setting** makes the router print `FAIL route: …` naming `required_checks` and exit 1 before it reads or writes anything.
5. **The pure functions** keep the earlier reading (every check counts) when called without a list; the router always passes the setting. This keeps the saved-response tests of `decide`, `branch_state` and `failing` readable.
6. **The guide** (`docs/guides/getting-started.md`, "When something goes wrong") says how to add a check a project wants to count.
7. Amendment 81 (`docs/runs/proposed-spec-amendments-81.md`) is applied to SPEC-0032 rules 2 and 7 and settles its residual of 2026-10-25. Flow mode: fragment `changelog.d/required-checks.md`; no version bump.

## Consequences

- An optional third-party check no longer paints a pull request red or opens the red-branch brief; a project that wants a check counted names it once.
- An existing project that names checks other than `proof` and `governance` in its branch rules must list them, or the router will not judge them (the guide says so).

## Residual

- 2026-10-26: a project whose required checks are not named `proof` and `governance` and that has not set `required_checks` sees its pull requests stay `agk:ci-running` until it does (due 2026-12-31).
