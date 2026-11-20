# ADR-0662: Every session the kit starts names its agent

- Status: Proposed
- Date: 2026-11-20
- Deciders: maintainers
- Related: brief #1582, SPEC-0066 rules 5 and 11 (build (a)), Q-S0066-4, Q-S0066-5, SPEC-0061 rule 7, SPEC-0064, plan #661
- Requirements: REQ-073

## Context

SPEC-0066 makes the steward the default agent of a project in build (d), in a later release. Until then a session the
kit starts must name its own agent, or a builder started after build (d) would run as the steward. Today both adapters
start `claude` with `--model` and `--effort` only, `launch.py` sets `AGK_AGENT` for `role` starts alone, the
conductor's own starts set none, there is no builder agent file, and `ROLE_PROMPT` asks a running session to start
itself with `claude --agent`, which it cannot do.

## Decision

1. **The adapters.** `kit/templates/start-session-local.sh` and `kit/templates/start-session-windows.ps1` (and this
   repository's `scripts/start-session-windows.ps1` and the guide's copy) start `claude --agent "$AGK_AGENT"` with
   `--model` and `--effort` after it as before. Without `AGK_AGENT` they print one line naming the setting
   (`setting: AGK_AGENT`), start nothing and exit 1. The Windows wrapper takes the agent as its sixth argument, before
   the optional model and effort. The POSIX lines use no GNU-only flag.
2. **Every start sets `AGK_AGENT`.** `launch.start_with` (builders and fix jobs, also those `autopilot.py` starts)
   sets `builder`; `launch.py role` the role (`steward`, `conductor`); `conductor.py`'s watchdog and supervisor
   conductor jobs `conductor`; its reviewers `architect-review` as today. `AGK_ROLE` keeps its meaning (Q-S0066-4).
   No kit path starts a `shadow` session today, so none sets it.
3. **`ROLE_PROMPT`** says the session runs as the `<role>` agent of `.claude/agents/<role>.md`, passed by the adapter,
   and no longer asks it to start itself.
4. **The builder agent.** `.claude/agents/builder.md` names the builder's rules by reference (`config/session-rules.md`,
   SPEC-0061 rule 7, `kit/templates/runtime/builder.txt`), never a second copy; it adds no permission and no guard of
   its own (Q-1582-2, the brief's recommendation). `kit/manifest.json` ships it verbatim and `.claude-plugin/plugin.json` lists it with the other agents.
5. **The cloud task texts** name their agent on their first line: `builder.txt` the builder; `conductor.txt` and
   `launcher.txt` the conductor, since the launcher is the cloud form of the watchdog's conductor job (SPEC-0064
   rule 13). How a cloud task sets the agent of its session is marked `(verify)` there (Q-S0066-5); until it is
   confirmed, the session follows the role file the line names.
6. **A project's own adapter.** `doctor.py`'s `launch-adapter` check warns, naming `flow.launch_adapter` and never the
   command, when a script file the setting names starts `claude` without `--agent` (Q-1582-1, the brief's
   recommendation); nothing is refused here. SPEC-0066 rule 11's upgrade refusal belongs to build (d).
7. **The scan.** `tests/kit/test_agent_named.py` fails when an adapter, a runtime text, `launch.py`, `conductor.py`,
   `autopilot.py` or a documented command in `docs/guides/` starts `claude -p` without `--agent`, and when a start of
   those scripts hands the adapter a session without `AGK_AGENT`.

Protected path classes changed: `kit/` (both adapter templates, the three runtime texts, `kit/manifest.json`, the `gitattributes` template),
`scripts/agk/` (`launch.py`, `conductor.py`, `doctor.py`), `.claude/` (`.claude/agents/builder.md`), `.claude-plugin/` (the agent listed in `plugin.json`), `tests/kit/`
(`test_agent_named.py` and the adapter tests whose expected arguments now begin with `--agent`), `config/` (the builder agent's line in
`config/rule-budget.txt`), `agk.toml` (a `[[testing.map]]` entry), `docs/adr/` (this file) and `changelog.d/` (one fragment).

## Consequences

A kit start names its agent on every path, so build (d) can set the steward as the default agent without a builder,
conductor or reviewer starting as the steward. A person's own adapter that reads no `AGK_AGENT` keeps working, with
one warning. An installed adapter that predates this change still starts sessions without an agent until
`/agk:upgrade` rewrites it (the adapters are templates written only where absent).

## Residual

- 2026-11-20 (verify): how a cloud scheduled task sets the agent of its session, and that `--agent` given on the
  command line overrides a plugin's default agent, are read from a recorded run before build (d) lands (due 2027-01-31).
- 2026-11-20 (verify): the clean layout's plugin agent name (`agk:builder`, SPEC-0071 rule 4) is recorded by the first
  run of a clean project (due 2027-01-31).
- 2026-11-20: an adapter template already installed is not rewritten by `upgrade` (written only where absent); build
  (d)'s upgrade refusal covers it (due 2027-01-31).
