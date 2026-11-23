# ADR-0772: Each role file names the governance command its own guard allows in both layouts

- Status: Proposed
- Date: 2026-11-23
- Deciders: maintainers
- Related: brief #1841, brief #1758, brief #1759, ADR-0612, ADR-0631, ADR-0736, ADR-0737, SPEC-0071, plan #661
- Requirements: REQ-078

Protected classes: `.claude/`, `tests/kit_dev/`, `config/`

## Context

A clean project (`[kit] layout = "plugin"`) has no `agk.mk` and no `Makefile` (SPEC-0071 rule 2). The conductor's
bounded run named only the `make -C <scratch>` forms and called `agk.mk` "the kit's own file in every project", so a
conductor or a shadow following it in a clean project ran a target that is not there (CM-09 on #1772). The other roles
with Bash named `kit_root.py governance` without the form their guard allows. The guards already decide the forms
(ADR-0631, ADR-0736): the architect's and the review agent's allow `python3 <kit>/kit_root.py governance` with `<kit>`
`scripts/agk` or the plugin's folder written out, the conductor's and the shadow's the same only inside
`env -i PATH="$PATH" HOME=<scratch>` run in that scratch, and all four refuse the variable typed into the shell
(ADR-0612 fact 4). `tests/kit_dev/test_shipped_governance_command.py` did not see the conductor's split code spans.

## Decision

1. **One line per role.** Each file under `.claude/agents/` whose tools include Bash (a file with no `tools:` line has
   every tool) holds one line starting `Governance:` that names, in code spans, the installed form first and then the
   clean form, each the one form its guard allows: `python3 scripts/agk/kit_root.py governance` and
   `python3 "<plugin>/scripts/agk/kit_root.py" governance` for the steward, the builder, the architect and
   the review agent; `cd <scratch> && env -i PATH="$PATH" HOME=<scratch> python3 -I scripts/agk/kit_root.py governance`
   and the same with the plugin's path for the conductor and the shadow. `<plugin>` is the plugin's folder written out,
   never the variable typed into the shell: no shipped file but the resolver names the variable (ADR-0630), as for the
   installed texts of ADR-0737 decision 1.
2. **The conductor's scratch list.** The bounded run names the `kit_root.py governance` form first and keeps the
   `make -C <scratch>` forms for an installed project only; the words "the kit's own file in every project" go. No
   other rule of the bounded run changes; the shadow keeps the run "word for word" and gains its own line.
3. **Kept true.** `tests/kit_dev/test_agent_governance_form.py` fails when a role file with Bash has no such line, and
   runs each named form through that role's guard: the installed form in a stub installed project as the frontmatter
   hook runs it, the clean form, `<plugin>` the stub plugin's folder, in a stub clean project made by `init.py --layout plugin --rehearsal` through
   `plugin_hooks.py pre` with `agent_type` `agk:<role>`. Each must be allowed, and the variable typed in its place must stay denied
   for the architect, the review agent, the conductor and the shadow. `MAKE_FORM` of
   `test_shipped_governance_command.py` also matches `make -C <...>` followed in the same sentence by a separate
   `-f agk.mk` span. Each failure names the path class and the file, never the line.

## Consequences

A conductor or a shadow in a clean project runs the head's governance on the first try; every Bash role names a gate
its guard allows, and the test fails when a role file and its guard drift apart. No guard, setting or check logic
changes. The six added lines raise the word counts of `config/rule-budget.txt` for those six files, each within ten
percent and with no rule line added, under the owner's standing ruling (ADR-0583, Q-1841-1 answered on #1853).

## Residual

- 2026-11-23: `docs/guides/local-mode.md` names `make -C <scratch> -f agk.mk agk-governance` in one span without the
  installed-project clause; outside this brief (due 2027-01-31).
- 2026-11-23: Q-HJ-2 (`agk-project-test` has no clean form) and Q-HJ-3 (session rule 4, the builder prompt) stay open
  as the brief reads them (due 2027-01-31).
