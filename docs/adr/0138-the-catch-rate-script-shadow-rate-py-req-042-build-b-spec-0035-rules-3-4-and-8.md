# ADR-0138: the catch-rate script shadow_rate.py (REQ-042 build b, SPEC-0035 rules 3, 4 and 8)

- Status: Accepted
- Date: 2026-10-25
- Deciders: maintainers
- Related: ADR-0129, ADR-0136, ADR-0076
- Requirements: REQ-042

Protected classes: `scripts/agk/`, `kit/`, `tests/kit/`

## Context

SPEC-0035 (Approved, ADR-0129) rule 9 makes build (b) the script that counts the marks and prints the conductor's catch rate; the conductor assigned it on #207 with this ADR number and amendment 74 reserved, and `builder-b` took it on #207. The tests were written first (`tests/kit/test_shadow_rate.py`: 17 tests).

## Decision

1. **The name.** `scripts/agk/shadow_count.py` already exists (SPEC-0023 rule 8, ADR-0076: the totals of the architect's shadow record, with `tests/kit_dev/test_shadow_count.py`). It and its tests are not touched. The new script is `scripts/agk/shadow_rate.py`, installed verbatim and listed in `kit/manifest.json`, because the weekly report of build (c) will read it in an installed project. Amendment 74 records the new name against SPEC-0035 rules 4, 5 and 9 (Q-K4-308, answered on #207: the existing script and its tests stay unchanged).
2. **The input.** Recorded GitHub responses in `--api-dir`, named as in SPEC-0007 rule 20: `pulls.json`, `comments-<n>.json` for each merged pull request and `comments-<issue>.json` for the `agk-shadow` issue (`--shadow-issue N`). No network, no model; a missing `pulls.json` or shadow-issue file is exit 2, a pull request whose comments are missing is counted as `unread pull requests`, never as zero.
3. **The findings.** A conductor finding is a numbered item (`1.`) of a `Verdict:` comment of a listed author, id `C<sha7>-<n>`; a shadow finding is an `S<n>.` line of a `Shadow: #<pr> <sha> ...` comment of a listed author, id `S<sha7>-<n>`. A head is reviewed by both when a verdict and a `Shadow:` comment name the same pull request and the same first seven characters of the sha; a `Shadow:` comment matching no verdict head is `unpaired`. Only findings of heads reviewed by both are counted (reading 2 of Q-K4-308, accepted on #207); only comments of a listed verdict author count, and `Marks:` also of the pull request's author (reading 1); `both` is counted once per pair, from the mark on the conductor's finding (reading 3).
4. **The marks.** `Marks:` comments of a listed author or of the pull request's own author; one line `<id> right|wrong|both`; a later line for the same id wins (a person may change a mark). A line that names no finding of its pull request is refused (exit 1, rule 3, naming the pull request and never the line); where the accounts of the verdicts and of the `Shadow:` comments differ, a mark by the author of the finding it marks is refused; with one account for both nothing is refused (the residual of SPEC-0035). A head whose pull request has no `Marks:` comment is `unmarked`; a finding without a mark in a pull request that has one is an `unmarked finding`; neither is ever zero or wrong (Q-K4-309).
5. **The count.** Per ISO week of the merge and in total: heads reviewed by both, right findings of the conductor only, of the shadow only, of both (once per pair, from the mark on the conductor's finding), the wrong findings of each, the unmarked heads and findings, and the catch rate, the right conductor findings (`right` or `both`) over those plus the right shadow-only findings, printed as `n/m (p%)` or `none` when there is no right finding. The total also prints `unpaired shadow comments` and `unread pull requests`.
6. Flow mode: no version bump, the fragment `changelog.d/ccr-7649d887-m9hvn7-sf.md`, `CHANGELOG.md` and `kit/hashes.json` as on main. Amendment 74 (`docs/runs/proposed-spec-amendments-74.md`) is for SPEC-0035 rules 4, 5 and 9.

## Consequences

- The conductor's catch rate can be computed from fixtures today; no number is stated about the conductor until the sample of ten exists and the report line (build c) follows its portal reader.
- The architect's shadow record keeps its own script; the two names differ.

## Residual

- 2026-10-25: no command yet saves the recorded responses for this script; the report (build c) or a person saves them with `gh api` GET until a build adds the command (due 2026-12-31).
- 2026-10-25: a rate over the findings the pair marked right says what the pair finds, not all defects; the marks of the first ten pull requests are the maintainer's (Q-S0035-3) (due 2026-12-31).
