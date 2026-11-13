# ADR-0456: The plan is drafted from the sources as proposals, and validate refuses anything invented

- Status: Accepted
- Date: 2026-11-12
- Deciders: maintainers
- Related: SPEC-0043, SPEC-0042, SPEC-0018, SPEC-0013, ADR-0269, ADR-0454, ADR-0455, amendment 163, brief #1075, brief #1081, plan #661
- Requirements: REQ-050

## Context

SPEC-0043 (Approved, REQ-050, ADR-0269) drafts a project's plan from `docs/sources/`. Build (b) (brief #1074, ADR-0455)
checks the sources and gives `check_plan.location_problem`. Rule 27's build (c) is split in two (brief #1075, the owner,
2026-11-12): this build, (c1), is rules 3 to 6 and the skill; (c2), brief #1081, is `render` (rule 7). On the default
branch at 3e38560 there is no `scripts/agk/plan_intake.py` and no `skills/plan-intake/`.

## Decision

1. `scripts/agk/plan_intake.py` (new, installed: `verbatim` in `kit/manifest.json`; files only, no network) has
   `validate --proposals FILE [--root DIR]` and `states [--root DIR]`. Every command first checks that the data guard is
   installed (rule 3): it exits 2 with `data guard not installed: <path>` when `scripts/agk/guard.py` or
   `.claude/hooks/data_guard.py` is absent under the root. Then it runs `guard.scan_text` on the whole text of every file
   under `docs/sources/` and of every cited charter, before any location is resolved; a finding refuses with exit 1 and
   one line per finding naming the file, the kind and `line <l>, column <c>`, never the matched text.
2. `validate` refuses, with exit 1 and one line per problem naming the rule and the item's `key` or `id`, never its text
   (rules 4 to 6): a proposals file under `docs/`; `schema` other than 1; an unknown or missing key; a value of the wrong
   type; a repeated key; a milestone `id` out of the order `M1`, `M2`, ...; an empty `sources`; a location that
   `check_plan.location_problem` does not resolve (imported, not copied); an `exit` that fails `MEASURABLE`; a `size` or
   `expected` that fails `common.ESTIMATE_LINES` (imported) or a range whose low is above its high; a `milestone`,
   `advances`, `depends_on` or area requirement that names nothing; a `depends_on` cycle; a milestone with no brief; an
   open question without `(verify)`; a `target` date, size or `expected` range that no cited location supports, printed
   as an open question; and a milestone, requirement or brief that cites both sides of a conflict without `settled`.
   With none it prints `ok proposals`.
3. A value is supported when the text at one of the item's own locations (the line, the section under the heading, or
   the charter's `Milestones` item) holds it: the `target` date as written, `size <S|M|L>` (or `size: <S|M|L>`, any case
   of the word), and `expected` as written (`<low>-<high> hours`). A conflict is `{"locations": [two], "description"}`
   with an optional `"settled": "Settled: <location>"` naming one of its two locations. A scope item is
   `{"key", "text", "sources"}`.
4. `MEASURABLE` is the pattern of `playbook.py check-start`. `playbook.py` is kit-only, so an installed script cannot
   import it: the pattern is kept in `plan_intake.py` and a test holds its text and flags equal to the playbook's, as
   ADR-0455 does for `CHARTER_NAME`.
5. `states` prints, for each `<screen>/<state>` heading of a `Kind: design` source, the states that
   `docs/design/inventory.md` gives that screen as `yes` (`design_import.inventory_states`, imported) and no heading
   covers, one line `<location> <state>`, the location being the screen's first heading (amendment 163 item 5, written
   as ADR-0454 decision 4); the skill makes each one open question with `(verify)`.
6. `skills/plan-intake/SKILL.md` (`/agk:plan-intake`, model invocation off) reads the sources only after `states` or
   `validate` has passed the guard, writes one proposals JSON file at a path the person names outside `docs/`, runs
   `validate` until it prints `ok proposals`, and never writes a requirement, spec, brief or GitHub object.

Protected path classes changed: `scripts/agk/` (`plan_intake.py`), `skills/` (`plan-intake/SKILL.md`), `tests/kit/`
(`test_plan_intake.py`), `tests/kit_dev/` (`test_plan_intake_skill.py`, and `test_distribution.py`'s list of skills and
of the skills that write), `kit/` (`kit/manifest.json`, one `verbatim` row) and `agk.toml` (one `[[testing.map]]` entry).

## Consequences

A session can draft a plan as data, and nothing in it reaches a person without a cited location that resolves, a
measurable exit, a sized and ranged brief whose estimate a source states, and every disagreement between the sources
shown. Until `render` (#1081) merges, the proposals stay a file the person reads.

## Residual

- 2026-11-12: support is textual: a location that holds the date or the range supports it, whatever the sentence says
  around it; the person reads the cited lines (due 2026-12-31).
- 2026-11-12: a source rarely states a brief's size, so most drafted briefs print an open question until the person or
  the estimator of build (e) gives one (`Q-1075-2`) (due 2026-12-31).
