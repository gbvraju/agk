# Proposed spec amendments 31 (SPEC-0007 rules 4 and 5)

Date: 2026-10-21 (from `date -u`). Approved specs change only through a proposal like this one (principle 6). Applied by ADR-0064. The path: `docs/specs/0007-metrics.md`.

1. **SPEC-0007 rule 4, the verdict forms.** The rule fixes the first line of a verdict comment as exactly one of `Verdict: cleared <short sha>`, `Verdict: fix list` or `Verdict: rejected`. The reviewers'
   fix lists and rejections carry the reviewed head, as the cleared line does (`Verdict: fix list c5ec2eb`), so the metrics read none of them and `review_rounds` was 0 (`docs/runs/method-weight-1.md`, finding 1).
   New wording: the last two forms are each optionally followed by one space and a sha of 4 to 40 lower-case hexadecimal characters, recorded when present; nothing else may follow on the line and no
   other form, such as `Verdict on #n (head ...): fix list`, is read. `Verdict: cleared <short sha>` is unchanged.
2. **SPEC-0007 rule 5, `review_rounds`.** "The number of `Verdict: fix list` comments" becomes "... with or without a sha". `cost_class` (rule 9) follows from it and is not amended.
