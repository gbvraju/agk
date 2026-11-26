# Proposed spec amendments 253 (SPEC-0050; REQ-057)

Date: 2026-11-26 (from `date -u`). Approved specs change only through a proposal like this one (principle 6). Written for
ADR-0818 (brief #1969), which stays `Proposed` for the maintainers' decision. The path:
`docs/specs/0050-overlapping-work-never-runs-at-once-and-a-second-change-re-proves.md` (rule 7a). Brief #1969 reserved
amendment 253. This file proposes the lines and does not edit the spec. They are applied word for word, on a person's
`Approve: SPEC-0050`; no session posts it.

## Why

In local mode the merger needs local evidence for the head it merges (SPEC-0039 rule 4), and the light re-prove made a
head with none, so every first verdict on it only asked a builder for a record (brief #1969's measurement: 0 of 32).

## Items

1. **SPEC-0050 rule 7a, the Report.** After "and posts `Report: <new head> merge of main (light re-prove, SPEC-0050
   amendment 171)`" insert "; in local mode (SPEC-0039 rule 4) it first runs `prepush.py --quick --record` and
   `evidence.py check --head <new head>` in a scratch worktree of the new head, and that `Report:` carries the
   `Evidence:` line, `Local evidence: <new head> <the Evidence check line> (the conductor's light re-prove record)` and
   the record in one fenced `json` block, or, when either run fails, `Local evidence: none (<step or reason>)`, no
   record, and the re-prove goes back to a builder (amendment 253)".
   Class: behaviour

SPEC-0039 rule 4 is unchanged. No other rule changes.
