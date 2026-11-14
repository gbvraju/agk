# ADR-0530: Adapter-started builders run on their kind's model (REQ-052)

- Status: Accepted
- Date: 2026-11-14
- Deciders: maintainers
- Related: ADR-0525, ADR-0528, SPEC-0045, SPEC-0053, brief #1252, plan #661
- Requirements: REQ-052

Protected classes: `kit/`, `scripts/agk/`, `tests/kit/`

## Context

`launch.py` already maps each entry's kind to a tier and an effort (`config.MODEL_DEFAULTS`: design and build on
`strongest`, small and mechanical on `mid`; a stopped builder resumes one tier up) and hands the launch adapter
`AGK_KIND`, `AGK_TIER`, `AGK_EFFORT` and, when `[models.names]` names the tier, `AGK_MODEL`. The two adapter templates
the kit installs (ADR-0525) ignored them and ran `claude` with the prompt alone, so every builder started on the
machine ran on the person's default model whatever its kind, and `[models.names]` was named nowhere a project sets up
local mode. The owner (2026-11-14) asked that each kind of work run on the model it needs. No Accepted ADR covers this
change to these protected classes, so the build writes its own (session rule 36) with the brief's reserved number.

## Decision

1. Both adapter templates (`kit/templates/start-session-local.sh`, `kit/templates/start-session-windows.ps1`) pass
   `--model "$AGK_MODEL"` to `claude` when `AGK_MODEL` is set, and `--effort "$AGK_EFFORT"` beside it when `AGK_EFFORT`
   is set too. Without `AGK_MODEL` they pass no flag, effort included: today's command, unchanged, for a project with no
   `[models.names]` (`(verify: the --model and --effort flags and the effort levels low, medium and high are read from
   claude --help of Claude Code 2.1.325, not from the runtime's documentation)`). The values travel as arguments of the
   adapter's wrapper, as the session and the brief do, because a terminal tab may start from the terminal's environment
   rather than the adapter's.
2. `docs/guides/local-mode.md`, "Running unattended", names `[models.names]` as the one setting that routes builders by
   kind, with placeholder names, and says the conductor itself runs on the strongest model because it reviews.
3. `doctor.py` reports `model-names` (severity `warn`): with `auto_start` on and `launch_adapter` set, no
   `[models.names]` is one line naming the table; a refused `[models]` table names its setting, never a value.

## Consequences

A project that sets `[models.names]` gets small and mechanical builders on its mid model and design and build work on
its strongest, with no hand setting per start. A project that sets nothing sees no change but doctor's warning. The
guide's Windows example and this repository's own `scripts/start-session-windows.ps1` carry the same wrapper, since
their tests require the guide's wrapper unchanged in both.

## Residual

- 2026-11-14: the conductor and reviewer starts of `conductor.py` set `AGK_TIER=strongest` but no `AGK_MODEL`; they keep
  the person's default model until a brief maps them through `[models.names]` too.
