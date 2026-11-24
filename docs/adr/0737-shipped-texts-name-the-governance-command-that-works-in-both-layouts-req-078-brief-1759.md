# ADR-0737: Shipped texts name the governance command that works in both layouts

- Status: Accepted
- Date: 2026-11-22
- Deciders: maintainers
- Related: brief #1759, brief #1758, ADR-0611, ADR-0631, ADR-0736, SPEC-0071, plan #661
- Requirements: REQ-078

Protected classes: `skills/`, `.claude/`, `kit/`, `tests/kit_dev/`

## Context

A clean project (`[kit] layout = "plugin"`) has no `Makefile` and no `agk.mk`, so `make governance` fails there with
`No rule to make target`. The resolver's `python3 <kit>/kit_root.py governance` runs the plugin's checks in a clean
project and `make -f agk.mk agk-governance` in an installed one (ADR-0611); the code that runs the gate already uses it.
Measured on main at 58972e2 on 2026-11-22: 14 shipped files (by the plugin's `snapshot`) under `skills/`,
`.claude/agents/`, `docs/guides/` and `kit/templates/` told a session to run the make form without saying it is the
installed project's, and three guides the skills cite (`planning.md`, `testing.md`, `getting-started.md`) were not in
the `snapshot`, so a clean project could not read them.

## Decision

1. **One command.** Each shipped skill names `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/agk/kit_root.py" governance` in
   place of the make form, with the clause that it runs `make -f agk.mk agk-governance` in an installed project. A
   guide and a template written into a product name `python3 <plugin>/scripts/agk/kit_root.py governance`, `<plugin>`
   the plugin's folder, with the same clause: they are installed files, which never name the plugin's variable
   (ADR-0630). The runtime builder prompt names it through its `<kit>` placeholder.
2. **Role files.** The architect's, the review agent's and the conductor's files name `kit_root.py governance` in place
   of `make governance`, word for word, so their rule budgets do not grow; the guards already allow it in both layouts
   (ADR-0736) and keep allowing `make governance`. They do not name the variable form, which their guards refuse
   (ADR-0736 decision 4, Q-1758-1).
3. **Installed-only texts.** A text that describes the installed project only keeps its make form and says so: the
   getting-started guide in one sentence at its top, the local-mode guide beside each command.
4. **The three guides.** `docs/guides/getting-started.md`, `docs/guides/planning.md` and `docs/guides/testing.md` join
   the `snapshot` of `kit/manifest.json`. `kit/hashes.json` is not edited (session rule 14).
5. **Kept true.** `tests/kit_dev/test_shipped_governance_command.py` fails when a shipped text of those four classes
   names `make governance` or `make -f agk.mk agk-governance` without the words `installed project` within 300
   characters (or the getting-started sentence), and when a shipped skill cites a `docs/guides/` file outside the
   `snapshot`. Each failure names the path class and the file, never the line.

## Consequences

In a clean project every governance step a shipped text gives runs; an installed project runs the same make recipe as
before. New products get the corrected templates; a product made before keeps its own records as written. No setting is
added and no check logic changes. `config/session-rules.md` rule 4 still names `make governance`: the rule file is the
maintainers' and outside this ADR's classes, so it is asked as Q-1759-1.

## Residual

- 2026-11-22: session rule 4 names the make form (Q-1759-1, due 2027-01-31).
- 2026-11-22: `skills/upgrade/SKILL.md` and `kit/templates/runtime/builder.txt` also name `make lint`, which a clean
  project lacks; outside this brief (due 2027-01-31).
