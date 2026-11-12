# ADR-0449: An imported design version is signed off and frozen by its digest

- Status: Proposed
- Date: 2026-11-12
- Deciders: maintainers
- Related: SPEC-0037, ADR-0446, amendment 161, brief #1062, plan #661
- Requirements: REQ-044, REQ-036

## Context

Amendment 161 to SPEC-0037 (approved on #1057, ADR-0446) adds imported design versions `i<n>`, a customer's
click-through prototype copied unchanged into `docs/design/imported/i<n>/`. Its item 4 says how one is signed off and
frozen. On the default branch `reviewers.py` `APPROVE_DESIGN` and `design_signoff.py` `VERSION` read only `v<n>`, and
`design_signoff.py` freezes only `docs/design/prototype/v<n>/`, so an imported version could be neither signed off nor
frozen. This is build (b) of the amendment's item 8; build (a), the import and the map check, runs in parallel.

## Decision

1. `APPROVE_DESIGN` (`scripts/agk/reviewers.py`) and `design_signoff.VERSION` (`scripts/agk/design_signoff.py`) accept
   `i<n>` beside `v<n>`. `Approve: design i<n> <full head ID>` by an account of `spec_approvers`, on the head it names,
   counts as for a kit version, inside a solo-mode `Confirmed:` comment too; a session never posts it.
2. `design_signoff.imported_digest(root, i<n>)` is rule 9's formula (the SHA-256 of the sorted
   `<path> <SHA-256 of the file>` lines) over every file of the whole folder `docs/design/imported/i<n>/`: `files/`,
   `manifest.json`, `map.md` and `external.txt`. It reads the files itself and does not need build (a)'s
   `design_import.py`. `version_digest` reads an `i<n>` through it, so `signed_off` and `frozen_problems` serve both kinds.
3. A `design` row of `docs/design/signoffs.md` may carry `i<n>` and that digest; `check_final_clearance.py` counts a row
   the pull request adds only with the person's line naming its kind, version and head, as before.
4. A signed-off imported folder that changes, gains or loses a file fails
   `rule 9: docs/design/imported/i<n>: a signed-off version changed`, naming the rule and the version, never a digest; a
   corrected map or a new delivery is a new version `i<n+1>`.

Protected path classes changed: `scripts/agk/` (`reviewers.py`, `design_signoff.py`, `check_final_clearance.py`),
`tests/kit/` (`test_design_signoff.py`) and `agk.toml` (the `[[testing.map]]` entries of `check_final_clearance.py` and
`reviewers.py` list `tests/kit/test_design_signoff.py`, which now tests them; the verdict on 0c34a82);
`kit/hashes.json` is unchanged (`kit_hashes.py` prints `ok kit-hashes`).

## Consequences

An imported version is held by its digest exactly as a kit version is, and the same sign-off record, approval line and
clearance check serve both. `design_compare.py` and `design_render.py` now pass an `i<n>` through `VERSION` and refuse it
at its folder, which is still read under `docs/design/prototype/`; build (c) gives the comparison its imported reading.

## Residual

- 2026-11-12: the spec text of SPEC-0037 does not yet carry amendment 161; build (d) writes it (due 2026-11-30).
- 2026-11-12: build (a)'s `design_import.py` may later share `imported_digest` (due 2026-11-30).
