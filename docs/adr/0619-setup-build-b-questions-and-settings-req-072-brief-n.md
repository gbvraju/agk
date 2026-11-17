# ADR-0619: /agk:setup build (b): at most five plain questions, and the project settings proposed as one change

- Status: Proposed
- Date: 2026-11-17
- Deciders: maintainers
- Related: SPEC-0065, ADR-0618, ADR-0577, SPEC-0064, SPEC-0041, brief #1461, plan #661
- Requirements: REQ-072

## Context

SPEC-0065 (Approved) names eight builds of `/agk:setup` (rule 18); this is build (b): the questions (rule 4) and the
project-settings change with its ADR (rule 9). Build (a) (ADR-0618) reads, sizes and prints and asks nothing. The study
behind brief #1461 counted four hand-made protected changes for a solo Windows setup; this build replaces them with one
reviewed change.

## Decision

1. **`setup.py ask`** prints at most five questions, each only when the machine and the project leave it unset: where
   the AI work runs (no `execution` at the top of `agk.toml`), one person or a team (no `review_mode`), autopilot off,
   assist or on (no `[autopilot]` table), the container engine (the project uses containers and the machine has
   neither Podman nor Docker) and, on Windows, native or WSL 2 (no `launch_adapter`). Each is one line in plain words,
   with its choices and `I recommend ...` and a reason, and passes the steward's owner-question check
   (`steward_owner.question_problem`, SPEC-0059 rule 5's kit terms); `--json` prints `questions` (`id`, `text`,
   `choices`, `recommend`).
2. **Answers** come back as `--answer <id>=<choice>`; one outside the choices is a usage error (exit 2). `plan` names
   the settings the answers map to only in its last line, `For the developer: ...`, within eight lines.
3. **`setup.py settings --yes`** writes the change; without `--yes` it refuses and writes nothing. The settings, each
   only when the project does not already hold that value: `execution` (`hosted` or `local`; `hybrid` and `pool` are
   kept, Q-S0065-6), `review_mode`, `pr_mode = "flow"` when more than one builder runs under one login, `[flow]
   max_builders` (this machine's figure, only for one person and only when unset: a team's cap is not one machine's
   figure), `[flow] builder_memory_gb` (rule 6's figure, when unset, Q-S0065-7), `[flow] launch_adapter` (the Windows
   or WSL adapter from the Windows answer; on Linux in local mode the background adapter, when unset) and
   `[autopilot] mode` (when the table is absent). A commented `[models.names]` placeholder is added when the change is
   made and the project names no models; the kit ships no model name.
4. **One change on a new branch** `agk/setup-settings-<date>`: `agk.toml`, the project's next ADR (Proposed, naming
   `agk.toml`, `REQ-001`) and the body in `<git dir>/agk/pr-body-setup.md`; the command commits, pushes and merges
   nothing and prints the commit, `prepush.py --record`, push and `wsl.py open` commands the person runs (SPEC-0005
   rule 8, Q-S0065-10). When every setting already matches it writes nothing and says no pull request is needed. For
   "for me only" (personal mode, rule 16) it writes nothing to the project. Uncommitted changes to `agk.toml` or
   `docs/adr/`, or an existing branch of that name, refuse naming the path class.
5. **The skill** asks the questions (the steward or Claude asks them as given) and runs `settings --yes` only after the
   person's yes to the plan.

## Consequences

One reviewed change, made by the person, sets the project's settings. The engine answer is recorded for builds (c)
and (d), which install it. Protected path classes changed: `scripts/agk/` (`setup.py`), `skills/`
(`skills/setup/SKILL.md`), `tests/kit/` (`test_setup_settings.py`) and `agk.toml` (the `[[testing.map]]` entry). No
workflow, ruleset, required check or secret changes.

## Residual

- 2026-11-17 (verify): `setup.py settings` has not run on native Windows or WSL 2; the pull request reports
  `Verified: (verify) run on Windows` until a person runs it.
