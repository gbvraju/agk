# ADR-0770: A new theme is filled from discovery and its Evidence line may name an imported version (REQ-044)

- Status: Proposed
- Date: 2026-11-23
- Deciders: maintainers (the owner's word, quoted below)
- Related: brief #1840, ADR-0104, ADR-0107, ADR-0248, ADR-0252 (changed here), ADR-0408, ADR-0446, ADR-0448,
  ADR-0745, brief #1757, IB-08 of #1769, PB-05 of #1770, plan #661
- Requirements: REQ-044

Protected classes: `scripts/agk/`, `skills/`, `tests/kit/`, `tests/kit_dev/`

## Context

`design_prototype.theme_for` wrote a new `docs/design/theme.md` from `kit/templates/design-theme.md` with only the
evidence line set, so the brand record stayed in brackets although the discovery document keeps the person's `brand`
answer word for word (IB-08). A brand colour too light to read at 4.5:1 failed rule 7 with no colour proposed, and
`check_design.EVIDENCE` accepted only a mockup folder or a kit version, so a project that starts from a customer's
prototype could not point its theme at the imported version it signs off, and had no command that writes a theme
(PB-05). The owner's word (2026-11-23, the steward chat, quoted as data): "Go ahead and file by thinking project lense
and helping AGK to reach the exceptional product delivery from Day 0", and "Yes, go ahead".

## Decision

1. A kit-only module `scripts/agk/design_brand.py` reads the given `brand` answers of `docs/discovery/*.md` (the
   words between the answer markers) and fills `name`, `primary` and `font` of the template's brand record only where
   it reads them without guessing (brief #1840 answers 1 and 8), each with the source line
   `source: docs/discovery/<file>.md (brand, given: <where>)`. Every other value keeps its bracketed placeholder; the
   logo line is always the template's. Documents that give different brand answers fill nothing and print one note.
2. With a `primary`, the theme block's `--color-accent` of each mode is the colour as given when it passes every
   `design_standard.CONTRAST_PAIRS` row it meets on the standard's roles of that mode, else the first shade mixed in
   one per cent steps toward black (light) or white (dark) that passes; `--color-on-accent` is the candidate with the
   higher contrast on it among `#ffffff`, the mode's standard text colour and the mode's standard on-accent colour. A
   changed mode carries the comment
   `/* a shade of the brand primary for 4.5:1 (proposed; the person's sign-off confirms it) */`, and the command
   prints one `ask the person:` line naming no value. The brand record keeps the colour as given. No check changes:
   `check_design.py` still fails a hand-set accent below 4.5:1 (Q-1840-3).
3. `design_prototype.theme_for` (no theme yet) and a new `design.py theme [--root DIR]` write the theme through
   `design_brand`. `theme` names the newest kit version, else the newest imported version, in the Evidence line, needs
   no `Approve: inventory` row, and refuses an existing theme (rule 2) and a project with no version (rule 7), writing
   nothing. Neither writer rewrites an existing theme. The theme text is read by `guard.scan_text` before it is
   written; a finding refuses it naming rule 14 and the path. Nothing of `docs/design/imported/` is read for a value
   (SPEC-0037 rule 13).
4. As the reading of SPEC-0037 rule 12 beside rules 9 and 15 (Q-1840-2), `check_design.EVIDENCE` also accepts
   `Evidence: docs/design/imported/i<n>/`, resolved by `design_signoff.folder_of` and approved by
   `design_signoff.signed_off(root, "i<n>")`. A missing folder fails
   `the evidence line points to no mockup, prototype or imported folder`.
5. `tests/kit_dev/test_design_theme_brand.py` holds the class closed: only `design_prototype.write` and
   `design.cmd_theme` write the theme and both fill it through `design_brand`, and the version kinds
   `check_design.EVIDENCE` accepts equal those `design_signoff.folder_of` knows.

Path classes changed: `scripts/agk/` (`design_brand.py`, `design_prototype.py`, `design.py`, `check_design.py`),
`skills/` (`skills/design/SKILL.md`), `tests/kit/` (`test_check_design.py`) and `tests/kit_dev/`
(`test_design_theme_brand.py`); `docs/guides/reference.md` is not protected. `check_design.py` is installed; the
others are kit-only. No workflow, check name or label changes.

## Consequences

A new theme carries the brand values discovery already holds, with their source, and a low-contrast brand colour is
met with a compliant shade for the person to confirm. The import path gets a passing theme in one command. A new
writer of the theme, or a new kind of signed-off version, fails the kit's tests until it follows this decision.

## Residual

Discovery does not ask for design inspiration (Q-1840-1, its own brief if the owner says yes). The rule 12 text still
names only a mockup folder or a prototype version; the reviewers may propose the amendment.
