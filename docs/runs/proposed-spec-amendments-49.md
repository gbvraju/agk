# Proposed spec amendments 49 (SPEC-0012, SPEC-0013; issue #156)

Date: 2026-10-24 (from `date -u`). Approved specs change only through a proposal like this one (principle 6). Applied by ADR-0092. The paths: `docs/specs/0012-intake.md`, `docs/specs/0013-playbook.md`.

1. **SPEC-0012, `ids` and the Draft spec.** When `origin/<default branch>` cannot be read, `intake.py ids` (and every command that reads the numbers from it) refuses with
   `origin/<branch> cannot be read; steps 6 and 7 need the repository's remote`, and not with the missing-requirements message, which stays for a readable ref without `docs/requirements.md`.
   The shape of the Draft spec (rule 7) is the shape of `docs/specs/TEMPLATE.md`, which has `## Proof` and `## Residual` between `## Tests` and `## Open questions`.
2. **SPEC-0012, the skill.** `skills/spec/SKILL.md` says to write `answered no questions` only when a person confirmed that the sentence needs none; with nobody to ask, the intake stops before writing any file and says so.
3. **SPEC-0013, `start-ids`.** `playbook.py start-ids` refuses with the same message as item 1 when `origin/<default branch>` cannot be read.
