# ADR-0589: Every mode runs the same autopilot jobs: the launcher is the supervisor in CI mode, and agk next runs one

- Status: Proposed
- Date: 2026-11-16
- Deciders: maintainers
- Related: brief #1391, SPEC-0064 rules 4, 13, 14 and 16 (f), brief #1389 (ADR-0586), brief #1390 (ADR-0587), brief #1387 (ADR-0585), SPEC-0041, plan #661
- Requirements: REQ-071

## Context

SPEC-0064 (Approved) runs every AI session as a short job that one supervisor per machine starts. Builds (a) to (e)
gave the job record, the local supervisor pass, builders as short jobs, the `[autopilot]` setting and the background
adapters. Build (f) is rule 13: in CI mode the cloud launcher task is the supervisor and jobs are cloud sessions, in
personal mode `agk next` runs one job in the foreground and posts nothing, several machines never run one job, and
solo and team start the same jobs. Today the cloud texts still run a 12-hour conductor that waits with
`conductor.py watch` and starts builders itself, and a builder that waits in the foreground for 6 hours
(`builder.txt` LIFETIME); a cloud session has no local job record, so build (c)'s `watch_builders` cannot see it, and a
personal-mode sidecar has no GitHub, so the plan and the review queue cannot be read there.

## Decision

1. **One choice of jobs over any forge.** `autopilot.pick(pulls, issues, comments, now, ready)` chooses a pass's jobs
   from GitHub-shaped records, read from GitHub (`session.pages`) or from a sidecar's files forge
   (`forge.FilesForge`): one `review` job while a non-draft pull request's newest `Report:` is newer than its newest
   `Verdict:`, `Correction:`, `Answer:` or `Maintainer answer:`; a `fix` job (session `cb<brief>`) wherever build
   (c)'s `conductor.job_gate` sees its event (an owed comment newer than the builder's last move, or `agk:conflict` /
   `agk:ci-red`), the same function the local pass uses, so CI and local start the same fix jobs, except that a newest
   `Verdict: cleared` is no event (the pull request waits for its merge; Q-1391-1); a `build` job per
   open `agk-brief` issue that no open pull request names, among the plan's `start` and `assign` rows where GitHub
   has a plan (with their build letter), else whose `Depends-on` issues are closed. The review mode is not read: solo
   and team start the same jobs.
2. **Several machines (Q-S0064-4).** An item whose newest `Started:` or `taken:` comment is newer than its event and
   than `conductor.START_HOURS` (2 hours, the launcher's existing hold) is `held` by that comment's session and never
   started again until the take lapses; a newer event (a new verdict) is a new job. `autopilot.py jobs --claim`
   posts one `Started: <session> <UTC> by the supervisor (<kind>)` on the item of each build and fix job before it
   prints its `job:` line, and a review job is held while a conductor holds the plan issue's lease.
3. **The setting.** Each job passes `job_allowed` (ADR-0587) before it is named: `mode = "off"` and a reached budget
   print `not started: <kind> #<item> <session> (<why naming the setting>)` and claim nothing, as ADR-0587 said build
   (f) would read it.
4. **CI mode.** `kit/templates/runtime/launcher.txt` runs `autopilot.py jobs --claim` as its pass and fires one cloud
   session per `job:` line: the conductor task for a review job, the builder task by kind for a build or a fix job
   (a fix job's message says `one short job`), within the plan's capacity; it keeps its 45-minute safety net for a
   builder that ended without a line. `conductor.txt` is one review job (one pass, the lease released, no `watch`, no
   builder start, no scheduled task fired). `builder.txt` drops the foreground watch form: in a cloud task or under
   any supervisor a builder is a short job that ends at its `Report:`, and only an interactive session a person
   started waits, in the background. No workflow, ruleset or required check changes.
5. **Personal mode (SPEC-0041).** `autopilot.py next [--brief N]` (`agk next`) picks the first allowed job by
   decision 1, from the files forge in a sidecar and from GitHub elsewhere, starts it through `[flow] launch_adapter`
   (`launch.start_with` with the build or fix prompt, `launch.role_main` for a review), waits in the foreground for
   the job's exit file (at most six hours) and ends with its exit code. It posts nothing and runs no `gh` in a
   sidecar; the job's prompt says to post and push nothing there (session rule 37). `--brief N` is the owner's own
   yes to that build (Q-S0064-8). Nothing due starts nothing.
6. **The guide.** `docs/guides/getting-started.md` opens "Running the loop" with a block of at most ten lines:
   `agk autopilot on` per machine, `agk status`, `agk next`, and the launcher as CI mode's supervisor; the hand-started
   conductor and builder items stay as the manual way.

Protected path classes changed: `scripts/agk/` (`autopilot.py`; `conductor.py` for `claim_job`, the supervisor's one
write, so `autopilot.py` keeps holding none, ADR-0584), `kit/` (`templates/runtime/launcher.txt`,
`conductor.txt`, `builder.txt`, `README.md`), `tests/kit/` (`test_autopilot_modes.py`, `test_runtime_templates.py`,
whose brief #1202 assertions on the long-run conductor move to the launcher), `agk.toml` (the `[[testing.map]]`
entry), `docs/adr/` (this file) and `changelog.d/` (one fragment).

## Consequences

The cloud runs no session that waits: the launcher's pass picks and claims each job, and every job ends. A local
machine keeps build (b) and (c)'s pass, whose fix rule `pick` reuses; a personal-mode developer runs `agk next` for
each step. Two supervisors that read before either claim can still both post a claim in the same minute; the later
one sees the earlier claim on its next pass.

## Residual

- 2026-11-16: a held verdict that waits on the owner's `Answer:` restarts the builder's fix job, not a review job,
  as build (c)'s `job_gate` reads an answer; the conductor reviews it again on the builder's next `Report:` (due
  2027-03-31).
- 2026-11-16: two machines that read in the same minute may both claim one job; the claim is a comment, not a lock
  (due 2027-03-31).
- 2026-11-16: the local pass (`conductor.py watchdog --pass`) does not yet call `pick` for its build starts, which the
  conductor job makes from the plan as before; both read the plan's starts (due 2027-03-31).
