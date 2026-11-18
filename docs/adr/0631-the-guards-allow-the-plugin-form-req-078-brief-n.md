# ADR-0631: The role guards allow the plugin form of each kit command

- Status: Proposed
- Date: 2026-11-18
- Deciders: maintainers
- Related: brief #1500, SPEC-0071 rule 4, ADR-0611, ADR-0612
- Requirements: REQ-078

Protected classes: `.claude/`, `tests/kit/`, `agk.toml`

## Context

SPEC-0071 rule 4 ends: the guards allow the resolver's command forms in both layouts and nothing more. Build (b)
(ADR-0612 decision 5) left the forms out. In a clean project (`[kit] layout = "plugin"`) the conductor's and the
architect's guards allowed only `python3 scripts/agk/<script>`, the project's own file. A clean project has no such
file, so these guards refused the plugin's form and failed closed (Q-1454-2). Measured on main at 4783e4d on 2026-11-18:
`python3 "${CLAUDE_PLUGIN_ROOT}/scripts/agk/session.py" plan --json` was refused by `conductor_guard.py` in a clean
project. The steward's guard is a deny list. It allows any interpreter command and refuses `merge_cleared` in any form,
so it already allowed the plugin's form.

## Decision

1. **One table.** `architect_guard.py` holds the two forms of a kit command, and the conductor's guard imports them:
   `scripts/agk/<script>` (or `./scripts/agk/<script>`), and exactly `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/agk/<script>"`.
   The second form is the variable in braces inside double quotes, followed by a space or the end. `tokens_of` reads it as
   the words `python3`, `${CLAUDE_PLUGIN_ROOT}/scripts/agk/<script>` and the words of the rest, and judges the rest as it
   judges any command. Every other `$` still makes a command unreadable, so it is denied. That covers another variable,
   `$CLAUDE_PLUGIN_ROOT` without braces, single quotes, no quotes and `python` instead of `python3`.
2. **Only in a clean project.** The form is read only when the resolver (`kit_root.layout`) reads `plugin` for the
   project. An installed project, an unreadable `agk.toml` or a guard with no resolver keep today's behaviour: the
   plugin's form is refused.
3. **The same arguments.** Each check that names a script matches either form, with the same arguments as today. For the
   architect these are the read-only scripts, the evidence check, the review bundle and the slot and check-verdict steps.
   For the conductor they go through `own_script`. In both guards the plugin's form is read only when the plugin that the
   resolver finds (`kit_root.plugin_root`) holds the script as a regular file and not a link (`plugin_script`, checked in
   `tokens_of`, and again by the conductor's `own_script`); a missing script or a link is denied. The
   conductor's merge (`merge_cleared.py --pr N --sha S`, with `auto_merge` on in both places) passes in both forms and
   nothing else does.
4. **No absolute plugin path.** A resolved absolute path to the plugin's scripts is not the project's own file, so it
   stays refused, quoted or not.
5. The steward's guard is unchanged: tests show that it allows the plugin's form and refuses the merge in both forms.
6. `agk.toml` maps the architect's and the conductor's guards to their tests and the new
   `tests/kit/test_guard_plugin_forms.py`, and adds that test to the steward's guard entry.

## Consequences

A clean project's conductor, architect, review agent and steward can run the kit's commands in the plugin's form, and
every command refused today stays refused in that form (tested). Installed projects and personal mode are unchanged.
The conductor's clean-environment runs (`env -i ... python3 -I <scratch>/scripts/agk/...`) still name the scratch
clone's own scripts. A clean project's clone has none, so they still fail closed there.

## Residual

- 2026-11-18: ADR-0612 fact 4 found that the Bash tool's shell has no `CLAUDE_PLUGIN_ROOT`. The form allowed here then
  expands to `/scripts/agk/<script>`, which runs nothing in a normal machine's root, so it fails at run time rather than
  in the guard. Whether prompts print this form or the resolved folder is for the build that changes the prompts
  (Q-1500-2) (due 2027-01-31).
- 2026-11-18: the conductor's clean-environment runs in a clean project (decision above), left to the build that moves
  scratch runs to the resolver (due 2027-01-31).
