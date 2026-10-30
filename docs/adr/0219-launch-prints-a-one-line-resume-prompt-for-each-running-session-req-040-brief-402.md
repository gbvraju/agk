# ADR-0219: launch prints a one-line resume prompt for each running session (REQ-040, brief 402)

- Status: Proposed
- Date: 2026-10-30
- Deciders: maintainers
- Related: ADR-0190
- Requirements: REQ-040

Protected classes: `scripts/agk/`, `tests/kit/`

## Context

Brief #402, split from #286 (parts 3 and 6). In a pilot a guide session wrote every resume prompt the person pasted after a
usage limit, an account switch or a closed tab. `launch.py prompts` writes only start prompts, for the briefs the plan names
in `start`; a session that already holds a take or an open pull request gets none. The brief names no `Measured:` line. The
tests were written first (`tests/kit/test_launch.py`, the resume section: 20 failed, 33 passed at the first checkpoint).

## Decision

1. **`launch.py prompts --plan FILE|- --resume` (answer 1).** It reads the plan's list `running`, one entry per session that
   holds work: `session` and `brief` as in `start`, and optionally `build`, `pull_request` (a whole number, 1 or more) and
   `author` (a GitHub login). It prints, for each entry in the plan's order, one prompt of one line, separated as the start
   prompts are, that starts `You are session <id>,` and names its work (`brief #n` or `build (x) of brief #n`) and its pull
   request (`pull request #p`, or `no pull request yet`). The prompt tells the session to read `CLAUDE.md` and
   `config/session-rules.md`, then to run `python3 scripts/agk/session.py queue --role builder --author <login>` and
   `python3 scripts/agk/session.py inbox --session <id>` first (session rule 11), and then to carry on: with a pull request,
   `python3 scripts/agk/session.py resume --pr <p>` and its `next:` step on the same branch and pull request (session rule
   9); with a take only, the brief from a fresh default branch, which is already its own and is not claimed again. It never
   claims, never carries a title (a title is data written in an issue) and ends with the `after` command and "never merge".
   The `start` list is not read for prompts with `--resume`, and `running` is not read without it.
2. **No running session.** A plan without `running`, with `null` or with an empty list prints nothing and exits 0. A
   `running` that is not a list, an entry that is not valid, or one session named twice is refused before anything is
   printed or started, naming the field and never its value.
3. **The adapter (answer 2).** With `--resume --adapter COMMAND` the adapter is called once per running session as today:
   the resume prompt on its standard input, `AGK_SESSION`, `AGK_BRIEF` and, for a build, `AGK_BUILD` in its environment,
   split into words and run without a shell, a failure reported once with `not started:` for the rest. `capacity.slots` is
   not required, since the running sessions already hold their slots; `[flow] max_builders` still caps the run (Q-402-3).
4. **The plan's `running` list (Q-402-1).** `session.py plan --json` prints today only the count `capacity.running`, not the
   sessions. Producing the list belongs to `scripts/agk/session_plan.py`, outside the brief's `Touches:`; this change reads
   the list when a plan carries it and leaves the producer to a brief or a correction.
5. **The author (Q-402-2).** An entry without `author` gets `queue --role builder` without `--author`, which lists every
   builder's labels, rather than a placeholder the person would have to fill in.
6. **Tests (answer 3).** `tests/kit/test_launch.py`: a session with a pull request; one with a take and no pull request; no
   running session (nothing printed, exit 0); the adapter called once per session with no shell; invalid entries; usage.
7. **Flow mode.** One fragment `changelog.d/launch-resume.md`; no version bump; `kit/hashes.json` not edited.

## Consequences

- After a usage limit, an account switch or a closed tab, a person runs one command and pastes one line per builder; the
  session re-derives its state from GitHub alone.
- Until the plan carries `running`, the command prints nothing for a plan that `session.py plan --json` printed today.
- The conductor's guard allows only the exact `prompts --plan <file>` forms, so `--resume` stays a person's command.

## Residual

- 2026-10-30: Q-402-1 to Q-402-3 asked on the pull request; the readings above are the most conservative ones.
