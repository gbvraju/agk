# ADR-0326: Parity: every kit discipline reaches a project, and the exception list only shrinks (REQ-020, brief 680)

- Status: Proposed
- Date: 2026-11-06
- Deciders: maintainers
- Related: ADR-0052, ADR-0307, ADR-0310, SPEC-0001, SPEC-0005
- Requirements: REQ-020

Protected classes: `config/`, `scripts/agk/`, `tests/kit/`, `kit/`, `agk.toml`

## Context

The owner asked on 2026-11-06 that every discipline AGK brings to its own development reaches a
project that adopts AGK (brief #680). Nothing listed which of the kit's own scripts, agent files,
configuration files and logs a project gets, so a discipline could stay in the kit repository
without anyone deciding that it should. On the default branch on 2026-11-06, 20 of the 76
`scripts/agk/*.py` are in no entry of `kit/manifest.json`; 10 of them a skill runs from the plugin
root (SPEC-0005 rule 6).

## Decision

1. **The disciplines (answer 1).** A kit discipline is each `scripts/agk/*.py`, each
   `.claude/agents/*.md`, each file directly under `config/` (the files the checks and the agents
   read; the whole folder, so a new file there is never missed), and each `docs/runs/` log that a
   file under `.claude/agents/` names, with a placeholder (`N`, `<n>`, `<...>`) read as `*`.
2. **How a project gets it (answer 1).** `installed`: the path is in `verbatim`, `experimental`
   or `rendered`, or is a destination of `templates` or `adopt.templates`, of
   `kit/manifest.json`; a log is also installed when an installed script names the part of its
   pattern before the first `*` (that script reads or writes the log in a project). `plugin`: a
   `skills/*/SKILL.md` runs it as `${CLAUDE_PLUGIN_ROOT}/<path>` (SPEC-0005 rules 5 and 6), or a
   script the plugin runs imports it (the plugin root is this repository, so the module is there).
   `kit-only (<reason>)`: a line `<path> <reason>` of `config/kit-only.txt`.
3. **The command (answer 1).** `python3 scripts/agk/parity.py report` prints one line per
   discipline, sorted. `parity.py check` fails naming each discipline in none of the three, and
   each line of the list that names an installed or plugin discipline (remove it), names nothing,
   has no reason or repeats a path. A tree without `kit/manifest.json` (an installed project)
   has nothing to check. No network. The script is installed (`kit/manifest.json`), so a project
   carries the same command; it checks only where the kit's manifest is.
4. **The list (answer 2).** `config/kit-only.txt` is seeded with every discipline that reaches no
   project today. A line whose reason is a true exception says it; a line whose reason could not be
   stated in this build says `gap:` and names its question (`Q-680-n`), so it is a move a
   follow-up brief makes (plan #661). Seeded on 2026-11-06 with 10 lines: 4 exceptions (the list itself,
   the kit's type baseline, its tag check and its release hash table) and 6 `gap:` lines
   (Q-680-2 to Q-680-7). The kit test `tests/kit/test_parity.py` holds the count of
   lines as a ceiling: a count above it fails ("install it or ship it instead"), a count below it
   fails until the ceiling is lowered in the same pull request, as the rule budget does (ADR-0310).
5. **Where it runs.** `kit/agk-kit.mk` wires no governance check today (it defines `agk-test`
   only), and `agk-governance` in `agk.mk` must equal the steps of the governance workflow
   (SPEC-0007 rule 13), which this build may not change. So the check runs in CI and in
   `make test` as the kit test that runs `parity.py check` on this repository, and wiring it into
   `make governance` is question Q-680-1.
6. **Unchanged (answer 3).** No listed script changes its behaviour; nothing is moved. The moves
   are follow-up briefs filed from the report.

## Consequences

A new script, agent file, configuration file or log that the kit uses on itself fails the kit
tests until it is installed, shipped through a skill, or listed with its reason in a protected
file that a reviewer must accept. Each follow-up move removes a line and lowers the ceiling.

## Residual

- 2026-11-06: the `gap:` lines of `config/kit-only.txt` are answered by follow-up briefs of plan
  #661, one per discipline (due 2026-12-31).
- 2026-11-06: Q-680-1, the check's place in `make governance` (due 2026-11-30).
