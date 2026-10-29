# ADR-0177: the drift audit runs optional unused-code and coverage commands (REQ-039, brief 244 build (b), SPEC-0004 rule 25)

- Status: Proposed
- Date: 2026-10-29
- Deciders: maintainers
- Related: ADR-0151, ADR-0172
- Requirements: REQ-039

Protected classes: `agk.toml`, `.github/`, `kit/`, `scripts/agk/`, `tests/kit/`

## Context

Brief #244 (priority 2, the maintainer's question of 2026-10-26, before a pilot on an existing codebase) asks that a project see each
week, when it opts in, which code nothing uses and how much of its code no test runs. Build (a), ADR-0151, added `retired` and the
untagged-test finding D8. This is build (b): answers 5 to 8. The brief named ADR-0152 and amendment 87; the conductor reserved
ADR-0177 for this build (brief #244, 2026-10-29), and amendment 87 is still free. The tests were written first.

## Decision

1. **Two settings** (`common.DEFAULT_CONFIG`): `unused_code` and `coverage`, empty by default, each a shell command like
   `project_tests`. `agk.toml`, `kit/templates/agk.toml` and `kit/templates/agk.adopt.toml` carry both, empty, with a comment. The
   kit ships no tool and installs none.
2. **Finding D9** (`drift_audit.d9`, SPEC-0004 rule 25). When a setting is set, the report run of the drift audit runs it, in the
   checkout, through `proof.execute` (its own process group, ended on a timeout), within `proof_timeout`, reading the standard
   output alone, and adds one finding D9 whose subject is the setting's name. It never blocks and never shows the command.
   - `unused_code`: `<n> unused-code findings: <line>; <line>` (up to 20 lines, then `and N more`), whatever the exit status,
     because the usual tools (`vulture`, `knip`) exit non-zero when they find something.
   - `coverage`: `covered <p>%, change since the previous audit: <+d|-d|unknown>`. The last non-empty line must be a number from
     0 to 100 (a `%` sign allowed) and the command must exit 0.
   - A command that runs too long reads `unknown: the command did not finish within proof_timeout (<n> s)`; one that fails or
     prints nothing readable reads `unknown: the command failed or printed nothing readable`; never zero.
3. **The previous audit.** `drift_audit.py --previous FILE` takes the body of the open audit issue, and the coverage change is the
   number now less the `covered <p>%` of that body; with no such body or number the change reads `unknown`. The workflow reads
   the body with the read-only `gh issue list --json number,body` (no new `gh` verb, SPEC-0004 rule 21) into `$RUNNER_TEMP`.
4. **Only the report run starts a command.** `--print-action` and `--print-title` start none: a set command always gives the report
   one D9 finding, so the action is `create` or `update N` whenever one is set. `audit()`, which the facts call, starts none, so the
   facts never run a project command; D9 is in `COMMAND_CODES`, not in `CODES`, and the facts' drift counts are unchanged. The
   report's summary line carries `D9=<n>` after `D8=<n>`.
5. **`proof.execute`** gains `merge_stderr` (default `True`, so proof is unchanged); the audit passes `False`. The drift audit itself
   still imports no process module; its import test now allows `proof` beside `common` and `reviewers`.
6. **The guide** (`docs/guides/existing-codebase.md`, step 3) gives examples for Python (`vulture`, `coverage`) and TypeScript
   (`knip`, `vitest`), says the kit installs none, that a failing or silent command reads `unknown`, and how a cleanup pull request
   reads; `docs/guides/getting-started.md` points to it.
7. **Readings taken where the brief leaves a point open** (the most conservative each):
   - one code, D9, for both commands, with the setting as subject, keeps the codes one digit and sorted;
   - an unused-code command that prints no line reads `unknown`, as the brief's "prints nothing readable" says, even when it exits
     0: its output cannot tell a clean run from one that never ran (Q-U244-1 asks whether a clean run should read 0 instead);
   - the time limit is `proof_timeout`, since the brief adds only two settings;
   - "since last week" is since the previous audit, the body of the open audit issue, which is last week's on the schedule;
   - answer 7: the weekly report would need more than an optional field: the facts would have to run the project's commands or read
     the audit issue's body, which they do not, and the drift object of the report schema admits no new property. So the drift audit
     issue alone carries the two figures, and the report change is a later brief.
   Amendment 87 (`docs/runs/proposed-spec-amendments-87.md`) proposes SPEC-0004 rule 25 and the changes to rules 3, 11, 15, 19 and 21.
   Flow mode: fragment `changelog.d/cleanup-commands.md`; no version bump.

## Consequences

- A project that opts in sees its unused code and its coverage on the weekly audit issue, never blocking, and an `unknown` when a
  command cannot be read.
- The audit's report run now starts the project's own commands, as proof starts `project_tests`; what they write stays in the
  workflow's checkout.

## Residual

- 2026-10-29: the weekly report does not show the coverage number or the unused-code count until a later brief teaches the facts (due 2026-12-31).
