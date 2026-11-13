# ADR-0332: check_brief refuses a UI brief without a Screens line (REQ-044, brief 460)

- Status: Accepted
- Date: 2026-11-07
- Deciders: maintainers
- Related: ADR-0204, SPEC-0037, ADR-0170
- Requirements: REQ-044

Protected classes: `scripts/agk/`, `.claude/`, `kit/`, `tests/kit/`, `tests/kit_dev/`

## Context

SPEC-0037 rule 10 (build (g) of rule 14) says that a brief that changes UI names the signed-off
prototype version and the screens and states it builds in one `Screens:` line, and that
`check_brief.py` refuses one without it. REQ-044 AC5 holds the clause. The project says what UI is
through `ui_paths` (`Q-S0037-8`). ADR-0204 added REQ-044 and SPEC-0037; the protected-path check
counts only an ADR added in the same pull request, so this build adds its own, citing ADR-0204
(`Q-S0037-9`). It changes no decision of the spec.

## Decision

1. **The `[design]` table.** `kit/templates/agk.toml` and `kit/templates/agk.adopt.toml` carry a
   commented `[design]` table with `ui_paths = []`, `render = ""` and `pixel_tolerance = 0.01`,
   each with one comment line. Only `ui_paths` is read by this build.
2. **A UI brief.** With `--root DIR`, `check_brief.py` reads `ui_paths` through
   `common.config_source`. A brief is a UI brief when a glob of its `Touches:` line and a glob of
   `ui_paths` meet: either read as a path against the other with `fnmatch`, or the literal part of
   one (before its first `*`, `?` or `[`) starting with the other's when neither part is empty (a
   glob that starts with a wildcard meets only by `fnmatch`). Only a line that starts `Screens:` is
   read as the line. No table or an empty list means
   no UI briefs; a value that is not a list of strings is refused naming `ui_paths`.
3. **The line.** A UI brief needs exactly one line `Screens: v<n> <screen>/<state>, ...`, where
   `<state>` may be `*`. The function `screens_problems(body, root)` refuses, naming rule 10 and
   never a value: no line; a line of another shape or a second line; a version without a `design`
   row in `design_signoff.rows`; a screen or state with no page `<screen>--<state>.html` in the
   version's frozen folder. `*` is every state of the screen that has a page there. `check` calls it
   after `absent_requirements`; `session.py` `brief_problems` does not change.
4. **The conductor's guard.** `conductor_guard.py` `brief_checked` calls `screens_problems` too, so
   the conductor files no UI brief without the line; an unreadable setting files nothing.
5. **Doctor.** `doctor.py` gains the entry `design-ui-paths`, a warning-class line that is always
   `ok`: `absent` when `docs/design/prototype/` exists and `ui_paths` is unset or empty, `set`
   when it is set, `not needed` without a prototype. It never fails and never prints a glob.
6. **The day brief template.** `kit/templates/playbook/brief-day.md` names the line, when it is
   needed and that `*` means every state.
7. **The doctor counts.** The tests of `tests/kit/` that count the doctor's entries count one more.

## Consequences

A UI build names what it implements from the frozen version before it starts, so that the
comparison of build (h) and the conductor know what to hold it to. A project without `ui_paths`
sees no change. Whether a `design` row counts by the person's `Approve:` line stays the sign-off
check's question; this check reads the listed rows only.

## Residual

- 2026-11-07: `render` and `pixel_tolerance` are written into the templates but read by nothing
  until build (h) (`design_compare.py`, brief #461).
- 2026-11-07: a screen id that itself holds `--` is read by splitting a page name at its last
  `--`, as the states of the shipped inventory hold none; build (h) may tighten it.
