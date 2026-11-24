# Proposed spec amendments 225 (SPEC-0039, SPEC-0064; REQ-046)

Date: 2026-11-24 (from `date -u`). Approved specs change only through a proposal like this one (principle 6). Written for
ADR-0778 (brief #1879), which stays `Proposed` for the maintainers' decision. The paths:
`docs/specs/0039-the-conductor-merges-a-cleared-pull-request-through-one-guarded-command.md` (rules 2 and 9) and
`docs/specs/0064-an-autopilot-supervisor-per-machine-runs-every-ai-session-as-a-short-job.md` (rule 4). This file
proposes the lines and does not edit the specs. A later pull request applies them word for word, on the owner's
`Maintainer answer: amendment 225 approved`; no session posts it.

The sentence (brief #1879): "A fix list holding only Final lines that accept an ADR on the current head is no builder
event: no fix job, no `nothing to change` Report, and the conductor merges it in the same act as posting it, as for
`Verdict: cleared`, saving a builder wake and 2 to 14 minutes."

## Items

1. **SPEC-0039 rule 2, after "in the same act as posting `Verdict: cleared <sha>`".** Add: "or a covered fix list on
   `<sha>` whose every `Final:` line accepts an ADR (SPEC-0021 rule 3a)".
2. **SPEC-0039 rule 9, after "whose latest verdict is `Verdict: cleared <its head>`".** Add: "or a covered fix list on
   its head whose every `Final:` line accepts an ADR (rule 3a)".
3. **SPEC-0064 rule 4, after "then one job per fix list".** Add: "(a verdict that clears the head, `Verdict: cleared` or
   a SPEC-0021 rule 3a fix list, starts no builder job, extending `Q-1391-1`)".

No other rule changes.
