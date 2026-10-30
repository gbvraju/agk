# ADR-0205: one read-only command lists every stall with its cause and fix (REQ-040, brief 367)

- Status: Proposed
- Date: 2026-10-30
- Deciders: maintainers
- Related: ADR-0184, ADR-0191, ADR-0195
- Requirements: REQ-040

Protected classes: `scripts/agk/`, `tests/kit/`, `kit/`

## Context

Brief #367 (priority 1), split from #286 parts 1 and 4. In a pilot a separate guide session spent the day spotting stalls the
kit did not report (a stale `agk:ci-running` label, a cancelled-run tie, a pull request at `agk:review` with no verdict, a
claimed brief with no pull request, an idle builder after a merge) and finding their cause in the kit's source. The kit already
reads every fact needed: `session_plan.py` the claims and the capacity, `route.py` the checks and the one label. The brief
names no `Measured:` line. The tests were written first (`tests/kit/test_stalls.py`: 34 failed with no `stalls.py`, at the
first checkpoint of the pull request).

## Decision

1. **`scripts/agk/stalls.py [--json]` (answer 1).** Standard library, `gh api` GET only; `gh` holds the credential. It prints
   one line per stall, `stall <kind> #<n>: <cause>; fix: <one plain step>`, or `no stall`; `--json` prints
   `{"stalls": [{"kind", "number", "cause", "fix"}]}`, the same stalls. It writes nothing and posts nothing. Exit 0 with no
   stall, 3 with any, 1 when a read fails (`error: rule 2 (<kinds>): <what> cannot be read`, naming the rule and the kinds,
   never a repository, a number or another value), 2 for a usage error.
2. **The kinds (answer 2)** are the rows of the table `KINDS` in the script, each with its name, its limit in minutes, how it
   is detected, its cause line and its fix line, and are printed in that order, then by number:
   - `stale-label`: the required checks of the head are green (route's `judged`: none missing, all finished, none failed or
     pending), and the time since the later of the last required check finishing and the label `agk:ci-running` last being
     set (the issue's `labeled` events) is more than 10 minutes. Fix: `route.py --pr <n>`, or re-run the router job.
   - `no-verdict`: `agk:review` on the pull request, route's own `decide` on its facts still reads `agk:review` (no verdict by
     a counted author names the head, solo mode included), and the label was set more than 30 minutes ago (with no `labeled`
     event, the time the required checks finished green).
   - `stuck-run`: on every open pull request, the latest run of a required check (route's `judged`, which drops older runs and
     the router's own job) is queued or in progress for more than 60 minutes from its `started_at`, or was cancelled; being
     the latest run means no newer run followed.
   - `red-default`: an open issue that `session.is_red` reads as the router's "The default branch is red" (title, author and
     `Priority: 0`); one written by a person is not.
   - `idle-capacity`: `session_plan.build` names sessions to start and the newest `taken:` on any open brief is more than 15
     minutes old (or there is none). One line per session to start, with the `claim` command the plan implies.
   - `claim-no-pr`: a live take (`session.live_takes`, `claim_hours`) of a session that has taken no later brief, with no pull
     request of its work (`session_plan.fits`, any state), and no `taken:` by it or `Progress:`, `Report:` or `Request:` that
     names it on the open briefs or the `agk-conductor` issue for more than 2 hours.
3. **Reuse (answer 3).** `route.py` (`read_facts`, `decide`, `judged`, `listing`), `session.py` (`pages`, `all_takes`,
   `live_takes`, `is_red`, `flow_int`) and `session_plan.py` (`build`, `fits`, `own_posts`, `conductor_comments`) are imported
   and not changed. `session_plan.build` reads the briefs and pull requests again: the cost of not changing it.
4. **Tests (answer 4).** `tests/kit/test_stalls.py` with the `gh` stub of the session tests serving saved responses: one fixture
   per kind that reports it and one just under each limit that does not (10, 30, 60, 15 and 120 minutes), and the cases that
   must not report (a red or missing required check, a verdict naming the head, a newer run after a cancelled one, a check
   that is not required, a red-titled issue by a person, a plan that starts nobody, a post by the session, a pull request
   naming the brief, a released take); `no stall`; `--json`; usage; a repository, and a pull request's facts, that cannot be
   read (exit 1, the rule named, no value); every call a GET.
5. **Installed.** `kit/manifest.json` lists `scripts/agk/stalls.py` with the verbatim scripts, so a project and its conductor
   have the command; `docs/guides/reference.md` gets a `Stalls` section, which `tests/kit_dev/test_reference_commands.py`
   requires of every installed script. Both are outside the brief's `Touches:`.
6. **Flow mode.** Fragment `changelog.d/stalls.md`; no version bump; `kit/hashes.json` not edited (session rule 14).

## Consequences

- A person, a conductor or a later steward process (#286 part 1, after its ADR) runs one command and sees why work stopped,
  without reading the kit's source.
- One run makes about two reads per open brief and up to eight per open pull request at `agk:ci-running` or `agk:review`; on a
  large queue it is slow but bounded by the rate-limit wait of `session.gh`.

## Residual

- 2026-10-30: the limits (10, 30, 60, 15, 120 minutes) are the brief's and are constants in the table, not settings.
