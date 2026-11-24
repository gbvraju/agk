# ADR-0782: The charter passes check-start on the first try, from one kit template (REQ-020)

- Status: Proposed
- Date: 2026-11-24
- Deciders: maintainers
- Related: brief #1888, ADR-0043 (the start command), ADR-0075 (discovery and the Slice item), ADR-0101 (the vision step),
  ADR-0664 (the day-zero source in its own pull request), ADR-0759 (a clean project reads the kit from the plugin),
  ADR-0760 (every ADR the kit writes passes its check), plan #661
- Requirements: REQ-020

Protected classes: `skills/`, `kit/`, `scripts/agk/`, `tests/kit/`, `tests/kit_dev/`

## Context

Test plan #1769 IB-03 expects the charter that `/agk:start` and `/agk:vision` write to pass in at most one fix round; the
runs of 2026-11-22 and 2026-11-24 took three. `skills/start/SKILL.md` step 4 listed the charter's fields as prose, without
the `- ` that `check_adrs.FIELD_RE` reads, and in the same list as the `Protected classes:` line that
`playbook.charter_problems` reads bare at the start of a line; `skills/vision/SKILL.md` step 5 pointed to that step. No file
of the kit held the charter's form, and the census of ADR-0760 never scanned a skill, so the skill drifted unseen. An
untracked `docs/sources/day-zero.md` (`day_zero.py write` commits nothing) also rode onto the start branch, which
SPEC-0013 rule 4 limits to exactly two files.

## Decision

1. The checks are right and do not change: SPEC-0013 rule 5 hands the fields to `check_adrs`, which reads `- Field:`
   lines, and rule 4 names the `Protected classes:` line apart from the fields, as every kit writer writes it.
2. `kit/templates/charter-adr.md` is the one source of the charter's form: the five `- ` fields, the bare protected line
   naming `constitution/`, the sections, and the numbered items Discovery (six topics in SPEC-0023's order; the vision path
   adds the four of `engines.TOPICS`), Slice, Milestones, Non-goals and Done means, with closed `{{…}}` slots. Both layouts
   read it from the plugin (`${CLAUDE_PLUGIN_ROOT}`); no project gets a new file.
3. `skills/start/SKILL.md` step 4 and `skills/vision/SKILL.md` step 5 copy the template and fill it; the prose field list
   goes. Both skills say that a `docs/sources/day-zero.md` not yet on the default branch goes in its own pull request,
   merged first (ADR-0664 item 4).
4. `playbook.py start-ids` refuses, exit 1, when `git status --porcelain` lists any path: `rule 4: the work tree is not
   clean; the start branch holds only the vision and the charter`, naming the rule, never a path. Ignored files are not
   listed and are allowed.
5. `tests/kit_dev/test_playbook.py` holds the template to both checks (six topics, and through
   `tests/kit_dev/test_engines_vision.py` ten), and its `GOOD_CHARTER` is the template filled, so neither can drift. The
   census of `tests/kit/test_kit_adr_writers.py` lists the template, and scans `skills/*/SKILL.md`: a skill that names an
   ADR file it writes by hand must copy a template the census lists, and a new one fails, named, until review lists it.

## Consequences

The charter passes `check-start` and `check_adrs.py` with no fix round. A start begun on a dirty work tree stops before the
branch exists. No spec text changes, so amendment 228 stays unused. No workflow, label, setting or testing-map entry
changes.

## Residual

A `{{…}}` slot left in the text field of a topic still passes `check-start`; the template test and the skill's "fill every
`{{…}}`" hold it (Q-1888-1).
