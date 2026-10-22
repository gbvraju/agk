# ADR-0076: the shadow record and the counting script (REQ-030 part c, SPEC-0023), kit 0.42.0

- Status: Proposed
- Date: 2026-10-22
- Deciders: maintainers
- Related: ADR-0073, ADR-0074, ADR-0075
- Requirements: REQ-030

Protected classes: `scripts/agk/`, `tests/kit_dev/`, `kit/`, `.claude-plugin/`, `agk.toml`

## Context

SPEC-0023 (Approved, #124) measures the catch rate of the review agent against a person's before any claim is made. Its build is split in three; this part (c) builds the shadow record template and the counting
script (rules 8 and 9; AC7 and AC8). The tests were written first and run on unchanged `main` (the output is in the pull request body).

## Decision

1. **The template**: `kit/templates/playbook/shadow-record.md` (kit-only) holds the instructions of the shadow session (post nothing on the pull request; do not read its comments; `gh api` GET reads the head, the
   diff, the specs and the checks; the first line is `Shadow verdict: <kind> <sha>`, never `Verdict:`; the maintainers paste both verdicts after the person's is posted, in batches), what the numbers may say
   (the measured rate and nothing more; below the person's rate "a second reader", not "an architect"), and for each pull request the two verdicts in fenced blocks and the findings as
   `- <by> <mark> <where>: <text>`.
2. **The counting script**: `scripts/agk/shadow_count.py FILE` (kit-only) reads that file only and prints the pull requests, the catches by both, by the person only and by the shadow only, the false findings by
   each, the findings with no `<where>` and the lines with no mark (both count for nothing) and the number of pasted verdicts that lack a line of the shape of SPEC-0023 rule 4 (reported, never failed). It uses no
   network and no model; a bad call exits 2. `Shadow verdict:` does not match `metrics.VERDICT`, so nothing counts it as a verdict.
3. **Amendment 39** (`docs/runs/proposed-spec-amendments-39.md`) is applied to SPEC-0003 rule 23: the shadow record of the reviewer agent is not the one of the architect's review agent.
4. **Tests, first** (`tests/kit_dev/test_shadow_count.py`, new, kit-only): the template's sections and instructions; the script on a record with each case; no other file read; no network or model import; the
   usage. `tests/kit_dev/test_playbook.py` counts eight templates and `tests/kit_dev/test_kit_manifest.py` lists the script as kit-only.
5. **Kit 0.42.0**: the manifest `kit_version`, the hashes, the plugin version and `version` in this repository's `agk.toml` (ADR-0050 decision 7).

## Consequences

- The maintainers can record the next ten pull requests and total them with one command; no claim about the review agent is made by this change. REQ-030 is marked done by the maintainers, not here.
- L3b (kit 0.43.0) follows.

## Questions

| Id | Question | Reading taken |
| --- | --- | --- |
| Q-K4-228 | SPEC-0023 rule 4 says the counting script "reports" the shape of a verdict; what does it report? | The number of pasted verdicts (the fenced blocks under the two verdict headings) that lack one of `Read:`, `Rules:`, `Not proven:`, `Lens:`, `Gaps:`, `Checklist:` as the start of a line, in that order; information only, it never fails. Proposed for ruling. |

## Residual

None.
