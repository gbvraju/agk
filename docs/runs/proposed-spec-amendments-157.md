# Proposed spec amendments 157 (SPEC-0045; REQ-052, REQ-060)

Date: 2026-11-09 (from `date -u`). Approved specs change only through a proposal like this one (principle 6). Written for
SPEC-0053 build (b) (brief #763), covered by ADR-0344. The path: `docs/specs/0045-each-kind-of-work-runs-on-the-model-it-needs.md`.
The number 157 is the next free one: 139, reserved on brief #763, was taken on the default branch by the amendment of
brief #765 (SPEC-0039). This amendment is not applied to the spec text in this pull request (SPEC-0053 rule 10); the owner decides it, and
it needs a person's `Approve: SPEC-0045`; no session posts it.

1. **Rule 3, the one place.** After "and nowhere else (`Q-S0045-1`)." rule 3 gains: "An optional `[models.providers]`
   table (SPEC-0053 rule 3) lists, per tier, the labels of that tier's providers in the order of trial. It names no
   second model for a tier's first choice: where `[models.names].<tier>` is set, the list's first label equals it. The
   kit's `agk.toml` and its templates carry no `[models.providers]`, as they carry no `[models.names]`."
2. **Rule 2, the table's refusal of unknown keys.** The `[models]` table accepts `providers` beside `names` and the five
   kinds; any other key stays refused as today (`setting: models.<key>`). A malformed `[models.providers]` is refused
   naming `setting: models.providers` or `setting: models.providers.<tier>`, never the value (SPEC-0053 rule 3).
3. **Tests.** The tests of rules 1 to 3 gain: a `[models.providers]` table leaves every kind's tier and effort as the table
   and defaults set them; `providers` is not read as a kind; no provider list is in the kit's `agk.toml` or templates.
