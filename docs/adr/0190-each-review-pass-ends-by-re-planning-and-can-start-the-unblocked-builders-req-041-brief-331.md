# ADR-0190: each review pass ends by re-planning and can start the unblocked builders (REQ-041, brief 331)

- Status: Proposed
- Date: 2026-10-30
- Deciders: maintainers
- Related: ADR-0154, ADR-0155, ADR-0175, ADR-0187, ADR-0189, ADR-0195
- Requirements: REQ-041

Protected classes: `scripts/agk/`, `.claude/`, `skills/`, `kit/`, `tests/kit/`, `tests/kit_dev/`

## Context

Brief #331 (parts 1 and 3 of #286). On 30 Oct 2026 the conductor ran its waves by hand: a dependency map, re-checked on every
pass, and each builder started the moment its blocker merged. The kit already had the parts, `session.py plan` (waves, capacity,
merge queue) and `launch.py prompts --adapter` (start sessions through a command), but nothing called them after a pass, so a
ready brief waited for a person to notice. The tests were written first.

## Decision

1. **The re-plan (answer 1).** `/agk:review-pass` gains a last step before its last lines, **Re-plan**: the conductor runs
   `python3 scripts/agk/session.py plan --json` and prints, in the pass's last lines, one `Start <n>: <session> takes #<brief>, ...`
   line (or `Start 0: <why>`) and one `#<brief> waits for ...` line per wait, in the plan's words. It posts nothing new. The
   conductor's guard allows `session.py plan --json` (read-only, GET) beside the queue commands; `session.py plan` without
   `--json` stays denied.
2. **The settings (answer 2).** Two optional settings of the `[flow]` table of `agk.toml`: `auto_start` (a boolean, `false` by
   default) and `launch_adapter` (the project's command, a string; empty means unset, as `unused_code = ""` is off). Both are a protected change (`agk.toml`). They are
   read by one function, `launch.launch_settings`, which refuses a value of the wrong kind naming the setting, never the value.
3. **Off (answer 2).** With `auto_start` off, the pass prints the ready-to-paste prompts as `/agk:launch` does: it writes the
   plan it read into a regular file of its scratch directory and runs `python3 scripts/agk/launch.py prompts --plan <that file>`,
   which the guard allows; it starts nothing.
4. **On (answer 2).** When `auto_start = true` and `launch_adapter` are both set, and the plan names sessions to start, the pass
   runs `python3 scripts/agk/launch.py prompts --plan <that file> --adapter <launch_adapter>`. The guard allows exactly that: the
   project's own `launch.py` (the regular file of the project directory, never a link or another copy), the plan a regular file
   of a scratch directory, and the adapter word equal to the configured `launch_adapter`, where both settings say so, with the
   same adapter, in the conductor's checkout and in `agk.toml` at `origin/<default_branch>` as last fetched (read with git, no
   network call), so turning `auto_start` off on the default branch stops a conductor whose checkout is older. Any other adapter, an extra word, an
   option in another order, `--plan -`, a pipe or a redirection, and the shadow mode stay denied, and an `agk.toml` that cannot be
   read or holds a setting of the wrong kind allows no adapter. `launch.py` splits the adapter into words and runs it without a
   shell, once per session.
5. **The bounds (answer 4).** `launch.py` refuses, before it prints or starts anything, a plan whose `start` list is longer
   than its `capacity.slots`, a `capacity.slots` that is not a whole number of 0 or more, with `--adapter` a plan that has no
   `capacity` at all, and a plan that names one brief (with its build) or one session twice. It starts or prints no more than
   `[flow] max_builders` (3 by default) of the folder it runs in, and prints `not started: <session> #<brief> (max_builders is
   <n>)` for each one past it. The plan never names a taken brief, and each started session takes its brief with its own
   `session.py claim`, whose `taken:` comment is the record of the start; the conductor posts no `taken:` and its guard refuses
   `claim` and `next`.
6. **A refused adapter (answer 5).** `launch.py` stops at the first adapter that fails or cannot be run, prints
   `FAIL launch: the adapter failed for <session>` and one `not started: <session> #<brief>` line for each session after it, and
   never calls it again; the pass quotes those lines and a `NEEDS-YOU:` line in its last lines and does not run the command again
   in that pass.
7. **The guide (answer 3).** `docs/guides/getting-started.md` documents two example adapters, each a short script the project
   owns and marked `(verify)` for the person's setup: a local terminal one (a new terminal tab running `claude` with the prompt)
   and a cloud one (a one-time cloud session). The kit installs neither.
8. **Readings taken where the brief leaves a point open:** the settings live in the `[flow]` table beside the plan's other
   settings (Q-331-1); the plan reaches `launch.py` as a scratch file the conductor writes, not `--plan -`, because the guard
   refuses a pipe (Q-331-2); the guard also allows the read-only `plan --json` and the printing-only `prompts --plan <file>`,
   which answers 1 and 2 need (Q-331-3). Flow mode: fragment `changelog.d/review-pass-replan.md`; no version bump.
9. **The spec (Q-331-4).** SPEC-0034 rule 6, as amendment 89 worded it, gains the exception of this ADR by
   `docs/runs/proposed-spec-amendments-103.md`: with `auto_start = true` on the default branch and in the checkout, the conductor
   may start the sessions the plan names, within `capacity.slots` and `max_builders`, through the one configured adapter.

## Consequences

- A ready brief no longer waits for a person to notice: every pass names it, and with `auto_start` on it starts at once,
  within the plan's capacity.
- The conductor still decides nothing: the plan decides what starts, the person decides by the protected settings whether a
  pass starts it, and the started session claims its own brief.

## Residual

- 2026-10-30: the adapter runs with no time limit, so an adapter that blocks holds the pass (an optional item of the verdict on
  2d53a5d, not built here; due 2026-12-31).
- 2026-10-30: the conductor writes the plan file itself, so `launch.py` cannot prove the file is the plan `session.py` printed;
  the bounds of decision 5, the guard's fixed adapter and each session's own `claim` (which refuses a taken brief) hold, and a
  digest of the plan is a later brief (due 2026-12-31).

## Log

- 2026-10-30: the conductor's verdict on 2d53a5d (#364) answered Q-331-3 (yes: exactly the two read or print forms and the one
  adapter command, nothing else) and Q-331-4 (yes: the spec needs a proposal; amendment 103, decision 9, which needs a person's
  `Approve: SPEC-0034`), and asked for a plan without `capacity` to start nothing with an adapter and for the `max_builders` cap
  (decision 5), for the settings to be read on the default branch too (decision 4), and for the role and the skill to end an
  empty pass the same way (`queue empty`, then the re-plan's lines).
