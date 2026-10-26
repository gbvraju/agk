# ADR-0154: `/agk:launch` starts the planned sessions after a person confirms (REQ-039, brief 247 build (b), SPEC-0034 rule 16)

- Status: Accepted
- Date: 2026-10-26
- Deciders: maintainers
- Related: ADR-0124, ADR-0153
- Requirements: REQ-039

Protected classes: `kit/`, `scripts/agk/`, `skills/`, `tests/kit/`, `tests/kit_dev/`

## Context

Brief #247 (priority 1): starting each builder session is a manual step, and the guide's launcher contract (`session.py demand`) has no launcher behind it. A polling scheduled task costs runs while idle, and a CI launcher costs runner minutes and needs an API key. The maintainer wants one command, run by hand, that decides how many sessions the scope needs and starts them after a confirmation. Measured on 2026-10-26: a one-time scheduled task opened a fresh cloud session within a minute, and that session read the repository, ran `session.py demand` and posted on #204 (`Report: launcher-test`). Build (a), `session.py plan` (ADR-0153), is merged. This is build (b). The tests were written first.

## Decision

1. **The name is `/agk:launch`** (the ruling on Q-247-6, option (a)). `/agk:start` already drafts the vision and the project charter and stays as it is. The brief, the guide, this ADR and the amendment use `/agk:launch`.
2. **The skill** (`skills/launch/SKILL.md`). It runs `session.py plan` and `plan --json`, shows the plan, asks once `(yes/no)` and treats only a plain `yes` as consent; then it prints the prompts with `launch.py prompts` and starts the sessions through an adapter. A `Start 0` plan starts nothing. It creates no recurring task, holds no credential, starts nothing later and never merges. Running it again plans again.
3. **The script** (`scripts/agk/launch.py prompts --plan FILE|- [--adapter COMMAND]`, installed). It reads the plan that `session.py plan --json` printed and prints one standard builder prompt for each session to start (it names the session, the brief, `session.py claim` and `session.py after`, and points to `CLAUDE.md` and `config/session-rules.md`). The title of a brief is data from an issue and never goes into a prompt. With `--adapter` it calls the command once for each session, split into words and run without a shell, with the prompt on its standard input and `AGK_SESSION` and `AGK_BRIEF` in the environment; it stops at the first failure and says which session failed, never echoing what the adapter printed. A plan that is not a plan is refused naming the field. No network, no credential.
4. **The adapters.** In a runtime with one-time scheduled tasks (Claude's cloud) `(verify)`, one one-time scheduled task for each prompt, firing about a minute ahead (the runtime's granularity is one minute) `(verify)`, opening a new session in the same environment; no `cron_expression`. Anywhere else the prompts are printed, one for each session, or the team's own command is the adapter. The tool names and parameters of the cloud runtime are marked `(verify)` in the skill: the skill, not a script, calls them.
5. **The rule changes.** SPEC-0034 rule 6, "no session starts another", reads "only when a person runs `/agk:launch` and confirms its plan" (amendment 89, which also adds rule 16). The guide's launcher item (`docs/guides/getting-started.md`) says so, and `docs/guides/reference.md` lists the command.
6. **Readings taken where the brief leaves a point open** (the most conservative each, as questions on the pull request): the adapter for a cloud runtime lives in the skill, because the scheduled-task tools are tools of the runtime and not scripts; a failing adapter stops the run instead of trying the other sessions; the prompt asks the session to read `config/session-rules.md` instead of repeating it, so the rules have one home. Flow mode: fragment `changelog.d/launch-skill.md`; no version bump.

## Consequences

- A person runs one command, sees the plan, says yes, and the sessions start; from then on the conductor's hand-off runs them.
- A session still starts only because a person said yes: nothing here starts a session later, on a schedule or on its own.

## Residual

- 2026-10-26: the scheduled-task tool names and parameters of the cloud runtime, and whether a task can fire sooner than a minute, are `(verify)` until a live run of `/agk:launch` is recorded (due 2026-12-31).
