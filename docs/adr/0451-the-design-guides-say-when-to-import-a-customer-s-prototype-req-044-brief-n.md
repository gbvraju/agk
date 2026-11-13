# ADR-0451: The design guides say when to import a customer's prototype, and doctor reports each imported version

- Status: Accepted
- Date: 2026-11-12
- Deciders: maintainers
- Related: brief #1064, SPEC-0037, amendment 161 (`docs/runs/proposed-spec-amendments-161.md`, #1057), ADR-0446, ADR-0448
- Requirements: REQ-044, REQ-036

Protected classes: `scripts/agk/`, `tests/kit/`, `skills/`

## Context

Amendment 161 to SPEC-0037, approved on #1057 (`Approve: c9bae51f452165b8f15283c470885e2d9a6f98bd SPEC-0037`),
lists four builds in its item 8. This is build (d), item 6: the guides, `/agk:design` and doctor. Build (a) (#1065,
ADR-0448) made `design.py import` and the check of `docs/design/imported/i<n>/`; until this build the spec text did not
carry the amendment, no guide named an import and doctor said nothing of an imported version.

## Decision

1. The text of SPEC-0037 carries amendment 161: items 1 to 3, 6 and 9 as a new rule 15 (the imported version, its
   screen map, its checks, both kinds in one project and what is unchanged), item 3's sentence in rule 13, item 4 in
   rule 9 and item 5 in rules 10 and 11, with the readings of Q-S0037-12 to Q-S0037-19 unchanged. The rules keep their
   numbers. The spec gains the `## Contexts` section that amendment 142 asks of an amended Approved spec, from the
   amendment's Contexts, and the amendment file gains its `## Applied` section, as amendment 145's build did (#954), so
   that `check_specs.py` finds the amendment that names the spec.
2. `docs/guides/product-owner.md`, `docs/guides/getting-started.md` (step 6) and `skills/design/SKILL.md` say when to
   import (the customer's prototype is the design: `/agk:design import <folder>`) and when to draw (no prototype yet:
   `/agk:design inventory`, then `/agk:design prototype`), and that what of a customer's prototype may be committed is
   the person's call before the import (the amendment's first residual). The skill gains an `/agk:design import`
   section and `import <folder>` in its argument hint.
3. `doctor.py` prints, after the skill lines and before the suite lines, one information line for each imported
   version: `design import: i<n> manifest matches the files|<n> problems|cannot be read; map complete|<n> problems|
   absent|not checked (<n> pages)`, ending `; check_design.py names each problem` when there is one. The counts are those
   of `design_import`'s own checks of the manifest and the map; the line names no file and no value. The JSON report
   carries the lines as `design_import`. It is not an entry of `CHECKS`: it adds no id, changes no summary count and no
   exit code, and a project with no imported version prints nothing new.

## Consequences

A person reading the guides or the skill knows which path fits the project before any file is written, and doctor
shows at a glance whether each imported version still matches its manifest and whether its map is complete. The rule
and the file of each problem stay with `check_design.py`, which fails them.

## Residual

- 2026-11-12: the doctor line counts the map's problems against the inventory but leaves the coverage of `yes` states
  across all versions to `check_design.py`, which is not per version (due 2026-12-31).
