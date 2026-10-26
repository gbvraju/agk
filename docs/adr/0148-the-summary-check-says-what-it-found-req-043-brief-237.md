# ADR-0148: the Summary check says what it found (REQ-043, brief #237)

- Status: Accepted
- Date: 2026-10-26
- Deciders: maintainers
- Related: ADR-0140
- Requirements: REQ-043

Protected classes: `scripts/agk/`, `tests/kit/`

## Context

Brief #237, seen on #233: a body's `Summary:` text was 156 characters against a limit of 120, and the message only said "one 'Summary:' line of 1 to 120 characters is required". It was unclear that the line was there and only too long, and whether the limit counts the `Summary:` prefix. The conductor assigned the brief to `builder-b` on #204 with this ADR number reserved. The tests were written first (`tests/kit/test_pr_summary.py`: 11 failed on the unchanged tree).

## Decision

1. **One message for each case** (`scripts/agk/check_pr_body.py`, `summary_problem`), each naming SPEC-0036 rule 1:
   - no line: `the 'Summary:' line is missing`;
   - more than one: `there are N 'Summary:' lines; exactly one is required` (with the count);
   - an empty one: `the 'Summary:' line is empty`;
   - one too long: `the text after 'Summary:' is N characters; at most 120`.
2. The limit and what it counts stay as they are: the text after the label, trimmed, of 1 to 120 characters; the label does not count. A message carries the rule, the case and a number, never a sha, a file or a word of the body.
3. No spec text changes: SPEC-0036 rule 1 already says the check names the rule and never the text; a count of lines or characters is not text (Q-K4-325, no amendment).
4. Flow mode: no version bump, the fragment `changelog.d/ccr-7649d887-m9hvn7-sl.md`, `CHANGELOG.md` and `kit/hashes.json` as on main.

## Consequences

- A builder reads in the failing check which of the four cases it is and fixes the line in one push.
- The old single message is gone; the exit code and the other messages of the check are unchanged.

## Residual

None.
