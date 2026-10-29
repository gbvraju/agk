# ADR-0175: a conductor session reviews on its own cadence, without a person prompting it (REQ-039, brief 284)

- Status: Proposed
- Date: 2026-10-29
- Deciders: maintainers
- Related: ADR-0170, ADR-0173
- Requirements: REQ-039

Protected classes: `.claude/`, `tests/kit/`, `tests/kit_dev/`

## Context

Brief #284 (priority 1), from a project pilot on 2026-10-27: the conductor ran as `claude --agent conductor`, its tool list
(`Read, Grep, Glob, Bash, Write`) had no scheduling tool, so `/loop` replied that neither `CronCreate` nor `ScheduleWakeup` was
available, and its guard refused `session.py watch`; every verdict waited for a person's prompt. Since #306 (ADR-0173) the
read-only command a pass needs is `python3 scripts/agk/session.py review-queue [--all | --fingerprint]`, and Q-306-1 left
allowing it in the guard to this brief. Measured by the builder before the change, on 0ba1aa0's parent (origin/main 4aa264c):
the guard printed `conductor guard rule 6: this command is not on the conductor's list` for both
`python3 scripts/agk/session.py review-queue` and `python3 scripts/agk/session.py queue --role conductor`, and the role's
`tools:` line had no self-wake tool. The `/loop` half of the measurement is the pilot's and was not repeated here `(verify)`.
The tests were written first (`tests/kit/test_conductor_guard_queue.py`, 10 failed at checkpoint 60f34e0).

## Decision

1. **Both answers 1 and 2, each in its smallest form.** The guard alone cannot give a cadence: nothing it could allow wakes a
   session on a timer (`session.py watch` waits on one pull request, not on the queue, and a background `sleep` is not a read),
   and the tool alone would leave every pass reading the queue by hand with many `gh api` GETs. The two together are still small:
   one tool name and four exact command forms. This works the same in a terminal and in a cloud session, because neither depends
   on the machine; a headless `-p` session cannot wake itself and keeps the timed loop of ADR-0173.
2. **The tool (answer 1).** `.claude/agents/conductor.md` gains `ScheduleWakeup` in `tools:` and nothing else. It is the tool
   that `/loop` uses for a self-paced loop and wakes only this session; `CronCreate` (recurring tasks) is not added. The guard's
   matcher is unchanged, and the guard allows a tool it does not know, as before. The name is read from the pilot's message on
   the brief, not from the runtime's documentation `(verify)`.
3. **The guard (answer 2).** Without `--shadow` the guard allows exactly `python3 scripts/agk/session.py review-queue`, with
   `--all` or `--fingerprint` or neither, and `python3 scripts/agk/session.py queue --role conductor`, both GET only. The script
   must be the regular file `scripts/agk/session.py` of the project directory (`CLAUDE_PROJECT_DIR`), named relative to the
   working directory of the call (the hook input's `cwd`, else the hook's own working directory `(verify)`) or by its full path,
   and never through a link: a copy in a pull request's worktree never runs with the session's token. `session.py watch` is not
   allowed (decision 1 makes it unneeded); `queue` is allowed only for the conductor's role, with no `--author`; every other
   command of the script, another interpreter, a flag such as `-I`, a variable before the command and any operator stay denied.
   The shadow mode gets none of them.
4. **The cadence (answer 3).** The role says: start the session with `/loop` and no interval; every 10 minutes by default (or the
   person's N), read `review-queue --fingerprint`, post nothing when it is unchanged, otherwise run the pass on `review-queue
   --all`; keep the cadence while the queue holds a pull request at `agk:review` or a new head since the last verdict; after two
   passes in a row with an empty queue, schedule no further wake and end with `queue empty`. An unchanged fingerprint after an
   empty pass counts as another empty pass, so the session stops after two in a row without running `review-queue` again
   (verdict on de043e0, item 1). A person who wants another interval writes it in the prompt, for example
   `/loop review every 5 minutes`, because a fixed `/loop 5m` interval needs a recurring-task tool that this role does not
   have (verdict on de043e0, item 2) `(verify)`.
5. **The other limits (answer 4)** are unchanged: no merge, no push, no PATCH, PUT or DELETE, no write outside the comment POST
   and the brief creation, and the bounded run as before. The tests repeat those denials next to the new allowed forms.
6. **The Windows field note on the brief.** A comment `POST` whose `body=@` file is not an absolute path (as a backslash path
   becomes in Git Bash) is refused with a message that names the likely cause and asks for forward slashes, naming no value.
   It only changes the message of a refusal that already happened; it allows nothing.
7. **Tests (answer 5).** `tests/kit/test_conductor_guard_queue.py`: each allowed form, the full path, every other form and command
   of the script, another interpreter or copy, a link, a missing script, operators, the shadow mode, the other limits, the
   path message, and the role's tool list and cadence. `tests/kit_dev/test_conductor_role.py`, outside the brief's `Touches:`,
   changes its expected tool set by the one new name, because it pins that set.
8. **Flow mode.** Fragment `changelog.d/conductor-cadence.md`; no version bump; `kit/hashes.json` is not edited (session rule
   14). `skills/review-pass/SKILL.md` still says that a person pastes the queue's output (its `(verify: Q-306-1 ...)` note); it is
   outside the brief's `Touches:` and is left for the conductor to decide (Q-284-2).

## Log

- 2026-10-29, verdict on de043e0: Q-284-1, the residual stays: the hook input documents `cwd`, so the guard's fallback to its own
  working directory is a safety net; whether `ScheduleWakeup` is `/loop`'s self-wake tool is confirmed by a person running
  `/loop` in a conductor session.
- 2026-10-29, verdict on de043e0: Q-284-2, `skills/review-pass/SKILL.md` is not changed here (outside `Touches:`); pointing its
  `(verify: Q-306-1 ...)` note at this ADR is a later small change.
- 2026-10-29, verdict on de043e0: Q-284-3, the refusal message for a `body=@` path that is not absolute stays in this pull
  request: it allows nothing new, is tested, and is in a file the brief touches.
- 2026-10-29, verdict on de043e0: items 1 and 2 built (decision 4).

## Consequences

- A conductor started by hand reviews again within its interval without a prompt, posts nothing while the queue is unchanged,
  and ends by itself when the queue stays empty.
- The guard's list grows by four exact read-only forms of one project script; the account boundary stays the real enforcement.

## Residual

- 2026-10-29: the guard trusts the project's own `scripts/agk/session.py`; a conductor whose checkout is not the default branch
  runs that branch's script with its token. The role and the guide start the conductor from the default branch (due 2026-12-15).
- 2026-10-29: whether `ScheduleWakeup` is the self-wake tool of `/loop` in every runtime, and whether the hook input carries
  `cwd`, is not confirmed by the builder `(verify)`; a person finds out by running `/loop` in a conductor session (due
  2026-12-15).
- 2026-10-29: that a person's interval written in the prompt (`/loop review every 5 minutes`) paces a self-paced `/loop` is not
  tried yet `(verify)`; a person confirms it in a conductor session (due 2026-12-15).
- 2026-10-29: the identity residual of ADR-0173 stands: the conductor runs with the person's own GitHub identity (due
  2026-12-15).
