# ADR-0249: the design inventory, its check and the sign-off record (REQ-044, brief 456)

- Status: Proposed
- Date: 2026-11-02
- Deciders: maintainers
- Related: ADR-0204, ADR-0248, SPEC-0037
- Requirements: REQ-044

Protected classes: `kit/`, `scripts/agk/`, `skills/`, `tests/kit/`, `tests/kit_dev/`

## Context

SPEC-0037 (Approved; ADR-0204) lists every screen and state of a product before anything is drawn (rule 3), and freezes
what the person agreed by a digest recorded in `docs/design/signoffs.md` (rule 9). Brief #456 is build (b) of rule 14,
the second of the seven design-phase builds (#455 to #461); ADR-0248 (#455, merged) fixed the standard's names that this
build reads (`design_standard.PATTERNS` and `REQUIRED_STATES`). The prototype (#457), the sign-off counting (#459) and the
`Screens:` line (#460) read the inventory and the record that this build defines. The readings the conductor took where
the spec is open are the field note of 2026-11-01 on #365. ADR-0204 decision 3 names the classes the builds change; this
ADR names the ones this build changes, because the protected-path check counts only an ADR of the same pull request
(`Q-S0037-9`).

## Decision

1. **The shape (answer 1).** `kit/templates/design-inventory.md` fixes it: a `## Requirements` part with one
   `### REQ-<n> — <title>` section each, holding `- Specs: <ids>` and `- Screens: <ids>` or
   `- Screens: no screen: <reason>`; and a `## Screens` part with one `### <screen>` section (a lower-case slug) each,
   holding `- Flow:`, `- Pattern:` (one of `design_standard.PATTERNS`), `- Links to:` and one `- State <state>:` line for
   `default`, each of `design_standard.REQUIRED_STATES` and any state a spec names, whose text is `yes` or
   `n/a: <reason>`. A slot is a `- <field>:` line with nothing after the colon; a screen that links nowhere reads
   `- Links to: none`.
2. **The skeleton (answer 2).** `scripts/agk/design.py inventory` (kit-only, files only, no model) writes
   `docs/design/inventory.md` from the template: one section for each requirement that `common.parse_requirements` reads
   from `docs/requirements.md`, its `- Specs:` filled from the `Requirements:` lines of `docs/specs/*.md` (`none` when no
   spec names it), every other slot empty, and an empty `## Screens` part. It refuses, naming rule 3, when the file exists
   or `docs/requirements.md` cannot be read; it never fills a slot.
3. **The check (answer 3).** `scripts/agk/design_inventory.py` (new, installed: `verbatim` in `kit/manifest.json`, in
   sorted order) holds `inventory_problems(root)`, which returns
   `rule 3: docs/design/inventory.md: <screen or REQ id>: <what>` for an empty slot, a requirement without a section or
   with neither screens nor a `no screen:` reason, a screen named by a requirement with no section, a pattern not in the
   standard, a link to an unknown screen, a screen missing `default` or a required state, a state that is neither `yes`
   nor `n/a: <reason>`, a section for no requirement, a screen id that is not a slug, a screen listed twice, a missing
   part and a field the shape does not have. It names the rule and the screen (or the requirement), never a value: a
   pattern, a link target, a state text or an id that is not a slug is never printed. `check_design.py` `cmd_check`
   calls it when the file exists, and a project with only an inventory is no longer "no design record".
4. **The digest (answer 4).** `scripts/agk/design_signoff.py` (new, installed: `verbatim`) holds `digest(root, paths)`,
   the SHA-256 (lower-case hex) of the sorted lines `<path> <SHA-256 of the file>`, each ended by a newline, where
   `<path>` is the file's path from the project root with `/`; `version_digest(root, version)` applies it to every file
   under `docs/design/prototype/<version>/` except its `screenshots/` folder, and refuses a version that is not
   `v<n>` or a folder that does not exist; `inventory_digest(root)` applies it to `docs/design/inventory.md`. It writes
   nothing.
5. **The record (answer 5).** `kit/templates/design-signoffs.md` holds one table
   `| kind | version | digest | head | date | comment |`. `rows(root)` returns its rows in file order (none when the file
   does not exist) and refuses, as `rule 9: docs/design/signoffs.md: row <n>: the <column> ...`, a row whose kind is not
   `inventory` or `design`, whose version is not `-` for an inventory row or `v<n>` for a design row, whose digest is not
   64 lower-case hex digits, whose head is not a full commit ID (40 or 64 lower-case hex digits), whose date is not a
   real YYYY-MM-DD, whose comment is not an `https://` link, or that has not six cells; a file without the table is
   refused as such. It never prints a value.
6. **The skill (answer 6).** `skills/design/SKILL.md` gains the inventory step: run `design.py inventory`, fill the slots
   from the requirements and specs only (or the design engine of `[engines]`), run `check_design.py`, and leave the
   agreement to the person's `Approve: inventory <full head ID>` line, which no session posts.
7. **Tests first (answer 7)** in `tests/kit_dev/test_design_inventory.py`, `tests/kit/test_design_inventory_check.py` and
   `tests/kit/test_design_signoff_digest.py`; one fragment `changelog.d/design-inventory.md` (answer 8).

## Consequences

A project can list its screens and states and have the check tell it, by rule and screen, what is still missing. The
sign-off record and its digest exist for #457, #459 and #460 to read; nothing yet counts a row or refuses a prototype for
want of one (#459, #457). An existing theme, mockup folder or project without an inventory is checked exactly as before.

## Residual

- 2026-11-02: Q-456-1 to Q-456-6 record the conductor's six readings of 2026-11-01 on #365; readings 1 to 3 concern the
  standard (#455) and are not touched here; reading 4 (a version's screens come from its frozen pages) leaves the inventory
  free to change after sign-off, which is why the `inventory` row carries its own digest; reading 5 (counting the
  `Approve:` line stays with `check_final_clearance.py`) is why `rows` only reads; reading 6 (seven builds) makes this
  build (b) of the seven.
- 2026-11-02: Q-456-7 to Q-456-15 are this build's own conservative readings, listed in the pull request body: the
  digest's path form (7), `none` for a requirement no spec names (8) and for a screen that links nowhere (11), a stale or
  repeated requirement section failing (9), the closed shape (10), where a problem is named and what is never echoed
  (12), the row format (13), retired requirements and unlisted screens (14), and an inventory alone being a design
  record (15).
