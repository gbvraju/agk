# ADR-0736: The reviewing roles run the resolver's governance command in a clean project

- Status: Accepted
- Date: 2026-11-22
- Deciders: maintainers
- Related: brief #1758, SPEC-0071 rule 4, ADR-0611, ADR-0612, ADR-0631, plan #661
- Requirements: REQ-078

Protected classes: `.claude/`, `tests/kit/`

## Context

A clean project (`[kit] layout = "plugin"`) has no `Makefile` and no `agk.mk`, so `make governance` fails there. The
resolver's command `python3 <plugin>/scripts/agk/kit_root.py governance` runs the plugin's checks in a clean project
and `make -f agk.mk agk-governance` in an installed one. Measured on main at b4a865c on 2026-11-22: the architect's
guard (both modes) and the conductor's guard (both modes) refused it, so no reviewing role could run governance in a
clean project (brief #1758). ADR-0631 gave the guards the plugin's form of each kit command, but `kit_root.py` is not
on the architect's read-only list and the conductor's scratch run names only `make` and the scratch's own scripts.

## Decision

1. **The architect and the review agent.** `architect_guard.py`, in both modes, allows exactly
   `python3 <kit>/kit_root.py governance`, where `<kit>` is one of the two forms of ADR-0631 (`scripts/agk`, or in a
   clean project the plugin's folder written out in full as the resolver finds it), optionally after one leading
   `AGK_BASE=<value>` (a ref or sha: letters, digits, `.`, `_`, `/` and `-`, not starting with `-`). No other argument,
   no option of `python3`, no second segment, wrapper or redirect is allowed, and `make governance` stays allowed.
2. **The conductor and the shadow.** `conductor_guard.py`, in both modes, allows the same command inside its clean
   environment, `env -i PATH="$PATH" HOME=<scratch> [AGK_BASE=<sha>] python3 [-I] <kit>/kit_root.py governance`, when
   the command runs in that scratch folder: the hook's `cwd` is that scratch folder, or the command is that one form
   after exactly `cd <scratch> && `. The scratch is the run's `HOME`, so the cd and the clean environment name one
   folder. The `env -i` prefix stays required: in an installed scratch the resolver runs the pull request's own
   `agk.mk`, so no token or stored credential may reach it, as for the `make -C <scratch>` forms, which stay allowed.
3. **One rule in both layouts.** The command is allowed in an installed and in a clean project; in an installed one
   `<kit>` is only `scripts/agk` (the plugin's form is read only in a clean project, ADR-0631 decision 2).
4. **The variable stays refused.** `${CLAUDE_PLUGIN_ROOT}` in the command, quoted or not, stays refused, as ADR-0631
   decision 4 records from the maintainers' answer to Q-1500-3 (a): the Bash tool's shell has no such variable
   (ADR-0612 fact 4), so the command would run another file than the one the guard checked. The brief's answer 1 names
   that form; it is asked as Q-1758-1 and not built.
5. **No heavy lock form.** The conductor's role file asks for the heavy-step lock only for the governance run after a
   merge (`make governance` on the default branch), not for scratch runs, so no `lock.py run` form is added.

## Consequences

In a clean project the architect, the review agent, the conductor and the shadow can run governance as they do in an
installed project, and every neighbouring form (a second segment, another folder, another argument, the variable, a
missing clean environment) stays refused (tested). Installed projects gain the same command, which runs the same make
recipe they already allow. Personal mode is unchanged.

## Residual

- 2026-11-22: if the maintainers answer Q-1758-1 for the variable form, the guards need the variable resolved to the
  checked folder, which ADR-0631 decision 4 refuses today (due 2027-01-31).
