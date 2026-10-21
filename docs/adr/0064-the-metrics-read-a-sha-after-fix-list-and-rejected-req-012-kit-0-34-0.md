# ADR-0064: the metrics read a sha after `Verdict: fix list` and `Verdict: rejected` (REQ-012, SPEC-0007), kit 0.34.0

- Status: Accepted
- Date: 2026-10-21
- Deciders: maintainers
- Related: ADR-0053, ADR-0060, ADR-0063
- Requirements: REQ-012

Protected classes: `scripts/agk/`, `tests/kit/`, `kit/`, `.claude-plugin/`, `agk.toml`

## Context

`docs/runs/method-weight-1.md` (finding 1) measured the method's weight and found the metrics blind to it: `review_rounds` was 0 for all 15 pull requests of REQ-021 to REQ-026 although 8 carried a fix-list
verdict, and `cost_class` was `S` for all 31 pull requests of the week. `metrics.VERDICT` accepts the first line of a comment only when it is exactly `Verdict: fix list` or `Verdict: rejected`, or
`Verdict: cleared <sha>`; the reviewers' fix lists carry the reviewed head, as the cleared line does (`Verdict: fix list c5ec2eb`), so none was read. The maintainers asked for it to be fixed before L2 of the
lighter path, because L3 adds a verdict form and has to be read by the same function. This ADR builds the fix tests first: the tests were written and run on unchanged `main` before the change (8 failed, 19
passed, the 19 being the unchanged forms and the lines that must stay refused; the output is in the pull request body).

## Decision

1. **The forms** (SPEC-0007 rule 4, amendment 31): `metrics.VERDICT` accepts `Verdict: cleared <sha>` as before, and `Verdict: fix list` and `Verdict: rejected`, each optionally followed by one space and a sha of
   4 to 40 lower-case hexadecimal characters. The sha, when present, is recorded in the `(kind, sha)` pair that `metrics.verdicts` returns (as for `cleared`).
2. **Nothing else is read:** no `Verdict on #n (head ...): fix list` form, no text after the sha or after the form, no upper-case or shorter or longer sha, no second space. The first line is stripped of its
   outer whitespace as before; the lines after the first are ignored.
3. **One function.** `facts.verdicts_of` already reads comments through `metrics.verdicts`, so the facts record the sha of a fix list and the report's At risk "sent back" count (two fix verdicts, or a
   rejection) follows with no change to `facts.py` or `product_report.py`. `review_rounds`, `cost_class` (rule 9: `S` needs no round, `M` at most two) and `rejected_verdicts` follow from `metrics.verdicts`.
4. **Amendment 31** (`docs/runs/proposed-spec-amendments-31.md`) is applied to SPEC-0007 rules 4 and 5. SPEC-0009 does not fix the text of a verdict line (it points to the rule of `metrics.VERDICT`) and is
   not amended.
5. **Tests** (`tests/kit/test_verdict_forms.py`, new): the forms with and without a sha (8 cases), the lines that stay refused (14 cases), `review_rounds` 2 and `cost_class` `M` on a recorded pull request with
   two `Verdict: fix list <sha>` comments, `rejected_verdicts` for `Verdict: rejected <sha>`, `Verdict on #n` counting nothing, the facts recording the sha, and the report's "was sent back 2 times".
6. **Kit 0.34.0**: the manifest `kit_version`, the hash of `scripts/agk/metrics.py`, the plugin version and `version` in this repository's `agk.toml` (ADR-0050 decision 7). No file is added to or removed from
   the manifest.

## Consequences

- With the fix, the W43 metrics read 11 pull requests as one round and class `M` where they read none and `S` (the totals line `cost S=32 M=0` becomes `S=21 M=11`), and 3 unknown cells become known. The W42
  report and the W43 report's At risk do not change: no pull request there was sent back twice (the numbers are in the pull request body).
- The verdict template (`kit/templates/playbook/verdict.md`) and `.claude/agents/architect.md` still name only the forms without a sha for fix list and rejected; the sha is optional, so they stay correct.
  They are not changed here (residual below).
- The older `Verdict on #n (head ...): fix list` comments of #92 to #94 stay unread by design; `docs/runs/method-weight-1.md` counts them by its own rule.
- The pilot gets this on its next `agk upgrade`, after its week W44 is scored on 2026-11-02.

## Questions

none

## Residual

- 2026-10-21: the verdict template and the architect role file say "`Verdict: fix list`" without the optional sha; say that a fix list or a rejection may carry the reviewed head, as a cleared line does (due 2026-12-31).
