# ADR-0196: a project can pause the kit and resume it (REQ-009, brief 348 build a)

- Status: Proposed
- Date: 2026-10-30
- Deciders: maintainers
- Related: none
- Requirements: REQ-009

Protected classes: `scripts/agk/`, `tests/kit/`, `.github/`, `.claude/`, `config/`, `kit/`

## Context

Brief #348 asks for a safe way out of the kit: first pause it, so that no check blocks and no session acts, then remove it in one
reviewable pull request. The conductor split it into two builds: (a) pause and resume (answers 1 and 5 and their tests), and (b)
the removal (answers 2 to 4 and 6). This record is build (a). Before it, the only way to stop the kit was to delete or disable its
workflows by hand.

## Decision

1. **One setting (answer 1).** `paused = true`, a top-level line of `agk.toml`, pauses the kit; an absent line or `false` does not.
   A line inside a table (`[flow]`, say) is not the setting. Any other value is refused with a message that names the setting
   (`setting: paused in agk.toml`), never the value. `agk.toml` is a protected path, so the line is added, and removed, with an ADR
   in the same pull request. `common.py` reads it (`paused(root, ref=None)`); with a ref it reads `agk.toml` at that commit, and a
   commit without `agk.toml` is not paused.
2. **The doctor answers and reports it (answers 1 and 5).** `python3 scripts/agk/doctor.py --paused [--ref REF] [ROOT]` reads only
   that file, calls no `gh`, and prints `agk paused` or `agk not paused` (exit 0), or a refusal (exit 1, 3 when the file is not
   TOML or the ref cannot be read). The full report of a paused project is the state `paused` on its own: the header, one line
   `paused agk paused: ...` that says how to resume, and `summary: paused` (with `--json`: `"state": "paused"` and no checks),
   exit 0; it reads nothing from GitHub. Removing the line brings the usual report back.
3. **Governance and proof report success with the one line (answer 1).** In both workflows a step `Paused` (id `paused`) runs after
   the checkout, the base step and the Python setup, and every later step carries `steps.paused.outputs.paused != 'true'` in its
   condition, so a paused run prints `agk paused` (also in the job summary), skips the rest and ends green; the required job names
   do not change. In proof, `outcome: skipped` also runs while paused, so the job still reports exactly one outcome. On a pull
   request the step reads the setting at the base of the merge ref (`AGK_BASE`), never at the head: the pull request that adds
   `paused = true` is still checked in full, its ADR included, so the line cannot be used to skip the checks of the change that
   adds it. On a push to the default branch it reads the commit pushed. A value that is not a boolean fails the step and so the job.
4. **The router writes no label (answer 1).** `route.py`, whatever it is asked to route, prints `agk paused`, reads nothing and
   writes nothing (no label, no issue, no comment) while the checkout it runs from (the default branch) is paused.
5. **The roles stop with the line (answer 1).** A new session rule 33: a session runs `python3 scripts/agk/doctor.py --paused`
   before anything else and on every wake, and when it prints `agk paused` it stops with that line, posts nothing and starts no
   watch. The conductor role reads `agk.toml` (with Read, which its guard allows) at its start and on each wake and stops the same
   way when the file holds the top-level line `paused = true`.
6. **Resume.** Removing the line resumes everything; nothing is deleted or rewritten while paused. The kit template of `agk.toml`
   lists the setting as a commented optional line.
7. **Tests first.** `tests/kit/test_pause.py` covers the setting, the doctor's query and report, the router, the two workflows
   (their step order and conditions, and the `Paused` step's script run against a repository whose base is and is not paused),
   the session rule and the conductor role.

## Consequences

A person can stop the kit in one reviewed pull request and start it again by removing the line. While paused, the checks still
report, green, so the ruleset's required check does not block merging; no label changes, so a session that still runs sees no new
state. The command that writes the pause pull request (`/agk:uninstall --pause`) comes with the removal tool in build (b)
(Q-348-1).

## Residual

- 2026-10-30: Q-348-1, Q-348-2 and Q-348-3 (in the pull request) wait for the conductor's answer.
