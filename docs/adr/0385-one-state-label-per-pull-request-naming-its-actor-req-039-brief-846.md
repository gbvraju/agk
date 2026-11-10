# ADR-0385: One state label per pull request, naming who acts next

- Status: Proposed
- Date: 2026-11-10
- Deciders: maintainers
- Related: SPEC-0032 rules 2 and 3, SPEC-0006 rule 5, amendment 150, ADR-0293, ADR-0384, brief #846
- Requirements: REQ-039

Protected classes: `scripts/agk/`, `tests/kit/`

## Context

The router set one of seven labels, all with the description "AGK: the state of a pull request". A draft still being
built got `agk:review`, so a person and the plan read it as waiting for the conductor, and `agk:ready` stood for two
next actors, the merger and the owner. Amendment 150, approved on #944, gives eleven states, each naming its actor.
This is build (a) of brief #846: its items 1 to 4 and 8.

## Decision

1. `route.py` has one table `STATES` of eleven labels, each with its actor and a description of the form
   `AGK: <actor> acts next: <what>`, and one function `pr_state(facts) -> (label, actor)`; `decide` is its label.
   The new states are `agk:build` (a draft, or a `Brief:` pull request with no ready `Report:` on its head),
   `agk:question` (an open `Owner needed:` line), `agk:owner-merge` and `agk:merge-ready` (a cleared head, split by the
   one list `merge_cleared.py` refuses to merge). `agk:parked` wins over every state and the router never sets or
   removes it.
2. The order of precedence is amendment 150's, with one exception: `agk:conflict` stays before the checks, because a
   dirty head starts no workflow and would wait at `agk:ci-running` for ever (`Q-846-8`).
3. A head that a verdict by a listed author names, or that the latest verdict covers, is past `agk:build` without a
   `Report:` (`Q-846-7`), so a status-only commit after a clearing verdict is not held.
4. `agk:ready` is no longer set. The router removes it as one of the other labels; the plan, `session.py queue` (a new
   `merger` role) and `uninstall.py` read it as `agk:merge-ready` until the release after this build.
   `merge_cleared.py` holds a pull request labelled `agk:parked` as it holds `agk:hold`, and reports a cleared head
   labelled `agk:build` as stale.
5. `doctor.py` has the warning row `state-labels`: a state label missing in the repository, or whose description does
   not name its actor, read with one GET. It reads nothing and prints `not applicable` without a router or with
   `execution = "local"`.
6. The plan's verdict wait stays as ADR-0384 decision 4 reads it, from the comments (`Q-846-9`): it counts exactly the
   pull requests that item 1 labels `agk:review`, and does not depend on a label that may lag.

## Consequences

A person sees on GitHub who acts next on each pull request. Labels created before this build keep their old description
until a person edits it; `doctor.py` lists each one. The state's age, the sweep's `STUCK` lines and the pipeline
document's schema 2 are build (b).

## Residual

- 2026-11-10: the reading of `agk:ready` is removed by the first build after the next kit release (amendment 150 item 2).
- 2026-11-10: `Q-846-7`, `Q-846-8` and `Q-846-9` wait for the conductor's ruling on the pull request.
