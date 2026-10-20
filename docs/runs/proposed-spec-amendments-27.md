# Proposed spec amendments 27 (SPEC-0009 rule 8)

Date: 2026-10-20 (from `date -u`). Approved specs change only through a proposal like this one (principle 6). Applied by ADR-0058. The path:
`docs/specs/0009-facts.md`.

1. **SPEC-0009 rule 8, the fields of a `requirements` row.** SPEC-0017 (Approved) gives each requirement row a field `done_on`, but names no amendment of the spec that lists the row's fields. The row
   shape is documented in SPEC-0009, so the field is added there, in one clause, and nothing else of rule 8 changes: "`done_on` (when the status is `done`, the UTC date `YYYY-MM-DD` of the commit on the
   first-parent history that last set it to `done`, else `\"unknown\"`; `null` when the status is not `done`; SPEC-0017 rule 1)". `kit/facts-schema.json` (SPEC-0009 rule 19) gets the optional property in the same change. Conservative reading (Q-K4-213): `schema` stays 1 (SPEC-0017 rule 2) and
   the field is optional for a reader, as `path`, `proof_reason` and `kit_version` are.
