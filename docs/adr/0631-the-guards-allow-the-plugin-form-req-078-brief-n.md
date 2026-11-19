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

The maintainers answered Q-1500-3 (a) on pull request #1516 (2026-11-18): the guards allow the plugin's folder written out
in full, the path the guard has checked, in place of the variable. The variable form of the brief's answer 1 is
refused: by ADR-0612 fact 4 the Bash tool's shell has no `CLAUDE_PLUGIN_ROOT`, so a command that names it runs another
file than the one a guard could check.

1. **One table.** `architect_guard.py` holds the two forms of a kit command, and the conductor's guard imports them:
   `scripts/agk/<script>` (or `./scripts/agk/<script>`), and `python3 "<plugin>/scripts/agk/<script>"`, where `<plugin>`
   is exactly the folder the resolver finds (`kit_root.plugin_root`, the form `kit_root.py --form` prints with the
   variable unset). `tokens_of` returns that script word as `${plugin}/scripts/agk/<script>`. No command can carry that
   word, because a command with a `$` is never read. Every check matches it as it matches `scripts/agk/<script>`, and the
   rest of the command is judged as before. Quoting does not matter: the guards judge the words bash passes.
2. **Only in a clean project.** The form is read only when the resolver (`kit_root.layout`) reads `plugin` for the
   project. An installed project, an unreadable `agk.toml` or a guard with no resolver keep today's behaviour: the
   plugin's path is refused.
3. **The same arguments.** Each check that names a script matches either form, with the same arguments as today. For the
   architect these are the read-only scripts, the evidence check, the review bundle and the slot and check-verdict steps.
   For the conductor they go through `own_script`. The plugin's path is read only when the plugin holds the script as a
   regular file and not a link (`plugin_file`, checked in `tokens_of` and again by the conductor's `own_script`); a
   missing script or a link is denied. The conductor's merge (`merge_cleared.py --pr N --sha S`, with `auto_merge` on in
   both places) passes in both forms and nothing else does. Only `python3` takes the plugin's form.
4. **Nothing else.** `${CLAUDE_PLUGIN_ROOT}` and every other variable, another folder holding a copy of the scripts, a
   link to the plugin's folder, a `..`, a doubled `/` and a `./` inside the path are refused (tested).
5. The steward's guard is unchanged: tests show that it allows the plugin's form and refuses the merge in every form.
6. `agk.toml` maps the architect's and the conductor's guards to their tests and the new
   `tests/kit/test_guard_plugin_forms.py`, and adds that test to the entries of the steward's guard and of the scripts it
   names.
7. SPEC-0071 rule 4 says the guards allow "the resolver's command forms"; this ADR records that in a clean project the
   allowed form is the resolved folder, not the variable. The wording of the Approved spec is its reviewers' to patch
   (principle 6); this pull request changes no spec.

## Consequences

A clean project's conductor, architect, review agent and steward can run the kit's commands in the plugin's form, and
every command refused today stays refused in that form (tested). Installed projects and personal mode are unchanged.
The conductor's clean-environment runs (`env -i ... python3 -I <scratch>/scripts/agk/...`) still name the scratch
clone's own scripts. A clean project's clone has none, so they still fail closed there.

## Residual

- 2026-11-18: `kit_root.py --form` still prints `"${CLAUDE_PLUGIN_ROOT}/scripts/agk"` when the variable names the plugin,
  a form the guards now refuse; the build that changes the prompts makes them print the resolved folder (Q-1500-2) (due
  2027-01-31).
- 2026-11-18: the conductor's clean-environment runs in a clean project (Consequences), left to the build that moves
  scratch runs to the resolver (due 2027-01-31).
