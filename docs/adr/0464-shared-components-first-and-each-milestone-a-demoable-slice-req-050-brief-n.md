# ADR-0464: Shared components first, and each later milestone a demoable slice of screens

- Status: Proposed
- Date: 2026-11-12
- Deciders: maintainers
- Related: SPEC-0043, SPEC-0037, SPEC-0038, ADR-0269, ADR-0454, ADR-0462, ADR-0463, ADR-0469, amendment 164,
  brief #1092, brief #1089, brief #1090, brief #1091, plan #661
- Requirements: REQ-050, REQ-044

## Context

Amendment 164 items 3 (the plan side) and 4 (ADR-0469) add shared components and demoable slices to SPEC-0043 rules 4,
5 and 7. On the default branch at 9ce67c5 the proposals of `plan_intake.py` (ADR-0456, ADR-0462) hold no components, a
brief names no screens, a milestone names no screens, `render` writes no `Demo:` line, and the web-app playbook's
`[milestones] batch_by` is printed by `playbook.py split` (SPEC-0038 rule 7) but read by no plan.
`design_import.py components` (build (q), ADR-0463) writes the components source. This is build (r).

## Decision

1. The proposals may hold `components`, a top-level key after `personas`, treated as an empty list when absent
   (`Q-1092-1`): each item `key` (`C1`, `C2`, ... in order), `name`, `screens` (inventory screen names), `pattern` (a
   pattern name or `null`) and `sources` (locations of rule 1). A brief may hold `component` (a component's key) and
   `screens` (inventory `<screen>/<state>` pairs); a milestone may hold `screens` (the same pairs). The `schema` stays 1.
2. `validate` refuses, naming the rule and the keys, never a text: a component key out of order; a component whose
   `screens` names fewer than two different screens or a screen that `docs/design/inventory.md` does not list; a
   component with no brief, or more than one, whose `component` names it, or whose brief is not in `M1`; a brief's
   `component` that names no component; `M1` not titled `Foundation` while `components` is not empty; and a brief whose
   `screens` include a screen of a component whose brief its `depends_on` does not name directly (`Q-1089-3`), naming
   the brief, the component and the component's brief.
3. When `docs/sources/` holds a `Kind: design` source with at least one `## <screen>/<state>` heading, `validate` also
   refuses a milestone after `M1` without `screens`; a milestone with `screens` whose `exit` does not contain
   `design_compare.py`, the word `match` and a version that has a `design` row in `docs/design/signoffs.md`; a pair of
   a milestone's `screens` that the inventory does not list; and a `<screen>/<state>` heading of such a source that no
   milestone's `screens` lists (`Q-1089-6`), naming the location. Without such a source none of these applies and a
   plan is validated as before.
4. `render` writes one `Demo:` line per milestone block after `Exit:`: `Demo: <screen>/<state>, ...` for a milestone
   with `screens`, `Demo: none (foundation)` for `M1` titled `Foundation`; and a `Screens: <version> <screen>/<state>,
   ...` line in each brief with `screens`, `<version>` the last `design` row of `docs/design/signoffs.md`, else
   `(verify)` (`Q-1092-3`). With a design source, `render` prints `Milestone order for the person: <batch_by>
   (playbook <file>)`, read from the declared playbook through `playbook_format.split`, or `Milestone order for the
   person: no playbook declares batch_by`; the order itself is the person's to judge (amendment 164 item 4).
5. `check_plan.py` rule 10 fails a `### M<n>` block of `docs/plan/milestones.md` after `M1` with no `Demo:` line when
   `docs/sources/` holds a `Kind: design` file, naming the milestone.
6. A component's `sources` resolve as every item's do (rule 1): a component the skill takes from the inventory's
   pattern lines cites the `## <screen>/<state>` headings of its screens in the prototype source, since the inventory
   is not a location of rule 1 (`Q-1092-2`).

Protected path classes changed: `scripts/agk/` (`plan_intake.py`, `check_plan.py`), `tests/kit/`
(`test_plan_slices.py`), `tests/kit_dev/` (`test_plan_intake_skill.py`) and `skills/` (`plan-intake/SKILL.md`).

## Consequences

A plan drafted from a prototype builds what its screens share in `M1 Foundation`, makes every screen brief wait for the
components it uses, and ends each later milestone with screens a person can click through, proved by
`design_compare.py`. A plan with no design source, and a proposals file without `components`, validates and renders as
before.

## Residual

- 2026-11-12: `components` is optional, not required as `personas` is, so that a plan with no design source is unchanged
  (`Q-1092-1`) (due 2026-11-30).
- 2026-11-12: an inventory line is not a location of rule 1; an inventory-derived component cites its screens' headings
  (`Q-1092-2`) (due 2026-11-30).
- 2026-11-12: the order of the milestones by `batch_by` and whether a slice is worth a demo are the person's judgment;
  only the words of the exit are checked (due 2026-12-31).
- 2026-11-12: the texts of SPEC-0043 rules 4, 5 and 7 are not written into the spec here; the brief's `Touches:` does not
  name the spec, as for builds (p) and (q) (`Q-1091-2`) (due 2026-12-31).
