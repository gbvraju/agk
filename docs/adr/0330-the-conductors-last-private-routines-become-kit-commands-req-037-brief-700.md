# ADR-0330: The conductor's last private routines become kit commands (REQ-037, brief 700)

- Status: Accepted
- Date: 2026-11-07
- Deciders: maintainers
- Related: ADR-0308, ADR-0329, ADR-0322, ADR-0327, ADR-0154, SPEC-0021, SPEC-0039
- Requirements: REQ-037

Protected classes: `scripts/agk/`, `tests/kit/`, `tests/kit_dev/`, `.claude/`

## Context

The owner's question of 2026-11-07 (quoted as data in brief #700) asked which private scripts the chat conductor still
ran beside the kit. The self-adoption audit of plan #661 mapped them: the watch and the merge chains are retired by
`conductor.py watch` (ADR-0308) and `merge-queue` (ADR-0329); four remained outside the kit, so a conductor in AGK or in
a project still drove part of the work from private scripts, against the sentence of the brief. Rows 18 and 19 of the
conductor catch log (a push cancelled the runs of the head before it; a push to a ready pull request left only skipped
runs) are the incidents the first command guards. The ADR number was reserved by the brief.

## Decision

1. **`conductor.py rerun --pr N [--apply]`.** It reads the pull request and the `pull_request` runs of its head (one
   GET each) and prints one line `rerun: #<n> <sha12>: run <id> (<name>) cancelled; ...` per cancelled run; only with
   `--apply` does it rerun them, each with `POST repos/{owner}/{repo}/actions/runs/<id>/rerun` (row 18). When every
   run of the head concluded `skipped` (row 19) and the pull request is not a draft, it says so and prints the one
   step that starts them, converting the pull request to a draft and back, and takes it only with `--apply`: `POST
   repos/{owner}/{repo}/pulls/<n>/ccr/convert_to_draft`, then `POST .../ccr/ready_for_review`, the routes of the
   runtime that session rule 7 names `(verify: the draft route is read as the twin of the ready route that rule 7
   documents, not from the runtime's documentation)`. A draft's runs skip by design and are left alone, said as such.
   Otherwise it prints `nothing to rerun` or `no run of the head`. A run of another event (a push) is not a run of
   the head. A read that fails, or a rerun or step that GitHub refuses, fails the command (exit 1) naming what.
2. **`conductor.py check-verdict FILE`.** It prints `ok`, or the problem of the verdict's `Final:` lines by
   `common.verdict_problem`, the reading `route.py` imports and applies when the router reads a verdict (the brief's
   `route.verdict_problem`; the function lives in `common.py`), or `the first line is not `Verdict: cleared|fix
   list|rejected <sha>` (session rule 1)` when the first line names no kind or no head; exit 1 on a problem. It reads
   nothing on GitHub and posts nothing; the message names the rule and the shape, never the body.
3. **`conductor.py lease (--show | --take NAME | --release NAME)`.** The active-conductor marker is one comment on
   the plan issue that `plan_issue` of the `[flow]` table of agk.toml names, whose first line is `Conductor: active
   <time> <name>` (`<time>` as `YYYY-MM-DDTHH:MM:SSZ`), valid 50 minutes from `<time>`. A marker counts only when
   its author is in `verdict_authors` of `config/reviewers.yaml`, as `sweep` reads verdicts, so an unlisted account
   neither holds the lease nor has its comment edited by `--take`. Without the setting the
   lease is off: `--show` says so (exit 0) and `--take` and `--release` refuse (exit 1), naming the setting; a
   setting that is not an issue number is refused the same way. `--take NAME` edits the newest `Conductor:` comment
   in place, or posts the first one, so that the issue holds one marker (as the `Progress:` comment of session rule
   8), unless another name holds a valid lease (exit 3, `lease: held by <name> until <time>`, naming the setting);
   the holder renews its own lease the same way. It keeps NAME in `<git dir>/agk/lease`, never tracked, as this
   checkout's name. `--release NAME` edits the marker to `Conductor: released <time> <name>` when NAME holds it,
   refuses another name's valid lease (exit 3), writes nothing when the lease is already free, and removes the local
   name. `--show` prints `lease: held by <name> until <time>` or `lease: free` (GET only). This replaces the free-text
   line the conductor posted on the plan issue on 2026-11-06.
4. **`merge-queue` under the lease.** With `plan_issue` set, `merge-queue` reads the plan issue's comments first and
   refuses to run, the dry run too, while a valid lease is held by a name other than this checkout's (`merge-queue:
   held: another conductor holds the lease until <time> (setting: plan_issue in the flow table of agk.toml)`, exit
   3, nothing read or merged after it); a plan issue that cannot be read holds it (exit 1). Without the setting the
   queue runs as before and reads no plan issue. So the hourly run, whose fresh clone holds no name, never merges
   while a live conductor holds the lease, and a live conductor that took the lease merges as before.
5. **`session.py prompt --brief N [--session ID] [--follow-up TEXT]`.** It prints the builder's standing prompt from
   the kit's files, GET only (the brief and its comments), so that a project's scheduled builder and the conductor's
   re-fire use one text and nothing is kept by hand: the item line `[Session name: <ID>. ]Item: brief #<N>. Reserved:
   <numbers>.`, the numbers being the brief's `Reserved:` lines and the `reserves` of its takes (`none` without
   any); the stop on an existing pull request of `claude/brief-<N>`, which `--follow-up TEXT` (one line, never
   starting `Approve:`, `Confirmed:` or `Verdict:`) replaces with the follow-up for it; the files to read first, in
   order; the secret-scan deferral line, `prepush.DEFER_LINE` (ADR-0327), with the `prepush.py --body` run; the
   branch, tests-first and decision-record rules in short; the body lines of CLAUDE.md item 7 read from
   `config/core-rules.md` as they are written there (a file without the item fails the command), with `Brief:`,
   `Summary:`, `Finishes:` and `Closes`; and the session rules that bind a builder, quoted whole from
   `config/session-rules.md` (`BUILDER_RULES`: 2, 3, 7, 8, 17, 21, 27, 28, 31, 33, 34 and 36; a number the project's
   file lacks is one note on stderr, and the rest are printed). The title of a brief is data from an issue and never
   goes into the prompt (ADR-0154).
6. **The guard.** `.claude/hooks/conductor_guard.py` allows exactly `python3 scripts/agk/conductor.py rerun --pr
   <n>`, with `--apply` after it, `... check-verdict <path>` (one word that is not an option) and `... lease --show`,
   `... lease --take <name>` or `... lease --release <name>`, the project's own regular file, as the routines of
   ADR-0308; the shadow reviewer runs none of them. No `ask`, `allow` or `deny` entry of `.claude/settings.json`
   changes: none of these merges.
7. **The catch log.** Rows 18 and 19 of `docs/runs/conductor-catches-1.md` move from `pending (to be filed)` to the
   check `scripts/agk/conductor.py` (`rerun`); the reference guide's "Conductor routines" section describes the
   four commands. No rule line of `.claude/agents/conductor.md` changes (the rule budget stays).

## Consequences

Every routine the conductor runs is now a kit command a project gets too: a cancelled or skipped run is reread and
rerun with one command instead of a private script, a verdict is checked against the router's own reading before it
is posted, the hourly run and a live conductor never merge at once, and a project's scheduled builder starts from the
same prompt that this repository's does, read from the installed files. The lease costs one GET of the plan issue
per `merge-queue` run in a repository that sets `plan_issue`; this repository does not set it in this pull request
(Q-700-1). The prompt is long (about 2,000 words for this repository), because the rules are quoted and not copied.

## Residual

- 2026-11-07: Q-700-1, whether this repository sets `plan_issue = 661` in `agk.toml` and turns the lease on; a
  setting that turns a behaviour on is the owner's, so the build leaves it off and the owner adds the line.
- 2026-11-07: Q-700-2, whether the conductor's own name for `merge-queue` is the local mark that `lease --take`
  writes (decision 3) or an option; read as the mark, which needs no new form in the guard.
- 2026-11-07: the draft route of decision 1 rests on the runtime's example `(verify)`; the step is printed before it
  is taken, so a conductor reads it either way.
- 2026-11-07: Q-700-3, whether the generated prompt should carry a `Flow:` line (a practice of the delivery
  playbook, not a kit rule); left out until a check asks for it.
