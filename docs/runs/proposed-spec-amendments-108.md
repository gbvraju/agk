# Proposed spec amendments 108 (SPEC-0037; REQ-044)

Date: 2026-11-01 (from `date -u`). Approved specs change only through a proposal like this one (principle 6). Written for ADR-0248
(brief #455), which stays `Proposed` for the maintainers' decision. The path:
`docs/specs/0037-a-project-s-design-phase-delivers-a-click-through-prototype.md`. The number 108 is the one the brief names. It
needs a person's `Approve: SPEC-0037`; no session posts it. It records in the spec the seven builds that the conductor filed as
briefs #455 to #461 (the field note of 2026-11-01 on #365, its reading 6) in place of the eight of rule 14; no other rule
changes with it, and no rule's behaviour changes.

1. **SPEC-0037 rule 14, build (a)** drops `kit/templates/design-theme.md` from its files: the theme template moves onto the
   standard in build (c), which writes the first version and moves a theme (rule 12), so (a) changes no file that `design.py`
   reads.
2. **SPEC-0037 rule 14, build (c)** gains `kit/templates/design-theme.md` among its files.
3. **SPEC-0037 rule 14, build (e)** (reflow and screenshots, rule 8) is folded into build (h): (h) gains
   `scripts/agk/design_render.py` (new, kit-only), the `screenshots` command of `scripts/agk/design.py`,
   `tests/kit_dev/test_design_render.py` and the reading of `screenshots/reflow.json` in
   `scripts/agk/design_prototype_check.py`, and its `Depends-on` becomes (c) and (g) (it renders the pages that (c) writes and
   reads the `Screens:` line and `[design]` settings of (g)). Build (e) is removed.
4. **SPEC-0037 rule 14, build (g)** (the `Screens:` line, rule 10) depends on (b) instead of (f): the brief's version must be
   listed in `docs/design/signoffs.md`, whose rows and reading (b) makes; and (g) also changes
   `.claude/hooks/conductor_guard.py`, so that the conductor's guard allows the reads the `Screens:` check needs.
5. **SPEC-0037 rule 14**, the opening sentence "these builds" reads "these seven builds", and the list keeps the letters (a),
   (b), (c), (d), (f), (g) and (h), so that the briefs and ADRs that cite a letter stay true.

The builds, as filed: #455 (a), #456 (b), #457 (c), #458 (d), #459 (f), #460 (g), #461 (h, with (e)). Chain: #455 -> #456 ->
#457 -> #458 -> #459; #460 after #456; #461 after #457 and #460.
