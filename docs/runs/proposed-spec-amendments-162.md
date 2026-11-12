# Proposed spec amendments 162 (SPEC-0032; REQ-039)

Date: 2026-11-12 (from `date -u`). Approved specs change only through a proposal like this one (principle 6). Written for
ADR-0453 (brief #1071), which stays `Proposed` for the maintainers' decision. The path:
`docs/specs/0032-github-events-label-each-pr-people-approve-specs-a-red-branch-stops-work.md` (rules 2 and 3). The number
162 is the one brief #1071 reserved. The brief asks for the amendment and its build in one pull request, so this
amendment is applied to the spec text in the same pull request: one sentence at the end of rule 2 and one at the end of
rule 3. Amendment 150 (the eleven states) is not written into rule 2's text yet either; this amendment reads with it and
adds a twelfth state. The owner decides it with `Approve: <head> SPEC-0032` on this pull request; no session posts it.

The sentence (brief #1071): "A builder that stops posts one standard `Report: <head> handing over: <reason>` line, and
`route.py` labels its pull request `agk:handover`, so the launcher restarts a builder for exactly those pull requests
without a schedule or a person."

The owner's word, quoted as data (brief #1071, 2026-11-12 09:29 to 09:31 IST): "If you observe some comments in stalled
PRs, it is commented Builders is stopping, we need to standardized that and trigger the lable"; no 15-minute schedule
(Actions cost); "File it".

## What is on the default branch today

Read in the code by this session (main 7bc1a17):

- `scripts/agk/route.py` `STATES` holds eleven labels (amendment 150 item 1); `BUILT` reads only
  `Report: <sha> ready for review|fix list applied|merge of main`, so a `handing over` report changes no label.
- On #1045 `Report: a990f50124d6 handing over` (2026-11-11 13:53Z) left the pull request in `agk:fix`; on #1041
  `Report: 645bfc0 handing over` (17:17Z) and `Report: 7ee353e5 handing over` (2026-11-12 02:21Z) did the same. #1041
  also carries the older successor form `Report: 3c94853 handing over to cb1030r (...)`, with no colon.
- `session.py queue --role builder` lists `agk:build`, `agk:fix`, `agk:conflict` and `agk:ci-red` by number;
  `conductor.py sweep` prints no line for a stopped builder; only the launcher's `STALL`/`SILENT` rules of 45 minutes
  catch one.

## Items

1. **SPEC-0032 rule 2, a twelfth state.** `agk:handover` (actor `launcher`, description
   `AGK: launcher acts next: a new builder for a pull request whose builder stopped`). It is not a place in the order of
   amendment 150 item 1: it replaces the state the order gives when that state is the builder's (`agk:build`,
   `agk:ci-red`, `agk:conflict`, `agk:fix`) and the pull request's builder has handed over (item 3). A state of the
   owner (`agk:parked`, `agk:question`, `agk:approve`, `agk:owner-merge`), the checks, the conductor or the merger is
   never replaced.
2. **The standard line.** A builder that stops posts, as its last comment, one `Report:` whose first line is
   `Report: <head> handing over: <reason>`, the reason one of `six hours`, `to <session>`, `blocked: <what>` or `done`.
   `route.py` reads it with one pattern, `Report: <sha> handing over`, an optional colon, then the reason; the older form
   with no reason reads as `six hours`, and the older form with a successor and no colon (`handing over to cb1030r`)
   reads as `to <session>`.
3. **When it holds.** `route.py` gives `agk:handover` when the newest `Report:` by the pull request's author or a listed
   verdict author is a handing-over line whose reason does not start `to ` or `done`, no comment by those authors other
   than a `Verdict:`, `Answer:` or `Correction:` came after it, and no push came after it (the head commit's committer
   date, as for `agk:question`). The next comment of a builder (`Progress:`, `Report:`, `Question:`, `taken over:`) or a
   push clears it, and the router sets the state the order gives. The router creates the label with its own colour
   (`f9d0c4`) the first time it sets it, as for every state.
4. **SPEC-0032 rule 3, the queue and the sweep.** `session.py queue --role builder` lists the `agk:handover` pull
   requests first, then the others by number. `conductor.py sweep` prints `HANDOVER #<pr> <minutes>m` for each open pull
   request labelled `agk:handover`, counted from its newest handing-over `Report:` by the pull request's author, or
   `unknown` without one.
5. **What stays outside the repository.** The builder and launcher prompts are scheduled tasks, not files of this
   repository, and are the co-owner's to change: builders end with the standard line; the launcher restarts a builder
   for each `agk:handover` pull request. No workflow changes: `agk-route` already runs on every comment and push.

## Text applied to SPEC-0032

At the end of rule 2: "Amendment 162 adds a twelfth state, `agk:handover` (actor `launcher`: a new builder for a pull
request whose builder stopped). It is not a place in the order: it replaces a builder's state (`agk:build`,
`agk:ci-red`, `agk:conflict`, `agk:fix`) while the newest `Report:` by the pull request's author or a listed verdict
author is `Report: <head> handing over: <reason>` with a reason other than `to <session>` or `done` (no reason reads as
`six hours`) and neither a comment by those authors other than a `Verdict:`, `Answer:` or `Correction:` nor a push came
after it; an owner's state is never replaced."

At the end of rule 3: "`queue --role builder` also lists `agk:handover` pull requests, first, so the launcher starts a
builder for exactly those (amendment 162), and `conductor.py sweep` prints `HANDOVER #<pr> <minutes>m` for each."

## Tests

`tests/kit/test_route.py` (brief #1071 tests (a) to (f)), `tests/kit/test_session.py` and
`tests/kit/test_conductor_commands.py` (test (g)), `tests/kit/test_pr_state_lifecycle.py` (the twelve states, the
builder's queue, the doctor fixture); saved responses and invented data only, no network.
