# ADR-0809: Each web and mobile screen lists the ten usability heuristics, and accessibility targets WCAG 2.2 AA

- Status: Proposed
- Date: 2026-11-25
- Deciders: maintainers
- Related: SPEC-0073, SPEC-0038, SPEC-0037, ADR-0793, ADR-0801, brief #1953, brief #1933, plan #661
- Requirements: REQ-080

Protected classes: `scripts/agk/`, `config/`, `kit/`, `skills/`, `tests/kit/`, `docs/specs/`, `agk.toml`

## Context

SPEC-0073 (Approved) rule 8, "Design: usability and accessibility" (`Q-S0073-10`), and rule 15 build (i), with
amendment 237 items 2 and 3 approved on #1920 (comment 7159666133). On the default branch at 312343b no file held a
usability heuristic: `check_design.py` checked an inventory's states (each `yes` or `n/a: <reason>`), so a deferred state
passed, as the three v1 pilots showed (CM-12), and neither `accessibility` gate named a standard.

## Decision

1. The record is `docs/design/usability.md`, outside `docs/design/prototype/<version>/`: one `## <version>` section per
   prototype or imported version (`v<n>` or `i<n>`), in it one `### <screen id>` per screen of the inventory, each with
   ten lines `- <heuristic>: pass | finding: <text> | not applicable: <reason>`. The ids are one tuple `HEURISTICS` of
   the new installed `scripts/agk/design_usability.py`: `status`, `real-world`, `control`, `consistency`,
   `error-prevention`, `recognition`, `flexibility`, `minimal`, `error-recovery`, `help`. The form is
   `kit/templates/usability.md`, read from the kit root as `kit/templates/glossary.md` is and not a `templates` entry of
   `kit/manifest.json`, so no install writes a record. The design skill writes the new version's section before its
   check.
2. `design_usability.problems(root)` runs inside `check_design.cmd_check`'s inventory branch, only when the declared
   `[delivery] work_type` is one of `SCREEN_WORK_TYPES = ("web-app", "mobile")`. It fails a missing record, no section
   for the newest version (the last kit version, else the last imported one), a screen of the inventory with no
   section, a heuristic missing, twice or not one of the ten, a value outside the three forms or with no text, and a
   screen the inventory does not hold. Each failure names `SPEC-0038 rule 10`, the path, the version and the screen,
   never a finding's text (principle 8). An older section is read for its form only (`Q-73I-1`); no version folder is
   read or written (SPEC-0037 rule 9). A refused declaration fails with `playbook_format.declaration`'s own line,
   naming `work_type`. A `finding:` never fails by itself.
3. Any other work type, a derived playbook or none prints `design: usability not applicable (work type)` once and checks
   nothing; an inventory with no version prints `design: usability waits for a prototype version`.
4. The `accessibility` gate text of `config/playbooks/default.toml` and `config/playbooks/web-app.toml` names WCAG 2.2
   level AA unless the discovery's accessibility answer names another standard. Gate ids, kinds and `owner_only` are
   unchanged, so no composition result is weakened (SPEC-0038 rule 5). Amendment 237 items 2 and 3 are applied word for
   word to SPEC-0038 rule 10 and SPEC-0037 rule 7.

## Consequences

Every web and mobile screen is read against the ten heuristics before its version is signed off, and the accessibility
gate has a target. A project with no inventory, or of another work type, is unchanged. One file read per design check;
no network, no workflow, label, required check or step list changes; `kit/hashes.json` and the version stay the
release's.

## Residual

- 2026-11-25: a non-text contrast check (3:1 for interface parts) is not built (`Q-73I-2`); the owner's to file.
- 2026-11-25: an imported design's external font (`Q-73I-3`) and an `offline` required state (`Q-73I-4`) are not this
  build's.
