# ADR-0091: the intake names its kit version and the final check accepts review answers (REQ-034, SPEC-0027), kit 0.52.0

- Status: Proposed
- Date: 2026-10-24
- Deciders: maintainers
- Related: ADR-0089, ADR-0070
- Requirements: REQ-034

Protected classes: `.claude-plugin/`, `agk.toml`, `docs/requirements.md`, `kit/`, `scripts/agk/`, `skills/`, `tests/kit_dev/`

## Context

SPEC-0027 (Approved, #152) makes the intake say which kit version it ran and refuse an older one, and gives an answer given at review, before approval, a true form that `check --final` accepts. The tests were
written first (`tests/kit_dev/test_intake_version.py` and `test_intake_forms.py`; on unchanged `main`: 23 failed, 22 passed).

## Decision

1. `intake.py` prints `intake: kit <version>` as the first line of every command (the `kit_version` of `kit/manifest.json` above `scripts/`; a manifest that cannot be read is a refusal naming the rule, never a
   guessed version). It refuses with `rule 2`, naming both versions, when the project's `agk.toml` records a newer dotted version, and prints one `note:` line when the script is newer. Equal versions, no recorded
   version and a version that is not dotted numbers are not compared. `ids` prints its JSON on the lines after the first. No network.
2. `ANSWERED` (SPEC-0020 rule 6) accepts three forms: `answered N question(s) before it was written` (N of 1 to 3) and the zero form, as before; `answered N question(s) at review, before approval` (N of 1 to 3);
   `gave N answer(s) before it was written` (any whole N from 1). Any other wording is refused as before. The rest of `check --final` is unchanged.
3. `skills/spec/SKILL.md` names the first line, the refusal and the three forms, and never a form for a question answered after approval. The tests that parse the output of the script (`test_intake.py`,
   `test_renumber.py`, `test_project_req_ids.py`, `test_end_to_end.py`) drop the first line through `without_version_line` in `tests/kit_dev/conftest.py`.
4. Amendment 48 (`docs/runs/proposed-spec-amendments-48.md`) is applied to SPEC-0012 and SPEC-0020. `docs/requirements.md` sets REQ-034 `done`.
5. **Kit 0.52.0**: the manifest `kit_version`, the hashes (`skills/spec/SKILL.md` is part of the plugin), the plugin version and `version` in this repository's `agk.toml`.

## Consequences

- An intake run from a plugin older than the project's kit stops with both versions named, instead of writing files the newer checks do not expect.
- A spec whose questions were answered at review, or whose answers came in a brief, can say so truthfully and pass `check --final`.

## Residual

None.
