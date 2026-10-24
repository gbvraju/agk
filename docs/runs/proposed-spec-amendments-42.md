# Proposed spec amendments 42 (SPEC-0007 rule 8; SPEC-0009 rule 14; SPEC-0011 rule 10; REQ-028 part L3c)

Date: 2026-10-23 (from `date -u`). Approved specs change only through a proposal like this one (principle 6). Applied by ADR-0080. The paths: `docs/specs/0007-metrics.md`, `docs/specs/0009-facts.md` (the file of SPEC-0009), `docs/specs/0011-inbox-and-report.md`.

1. **SPEC-0007 rule 8, `merged_head_cleared`.** Also `yes` when the merged head is the covered commit of the latest verdict by a listed author (SPEC-0021 rules 3 and 7), read from the commit record `commit-<sha>`
   (one parent that starts with the reviewed sha, the files and their patches); `unknown` for a change to `docs/requirements.md` and for an unreadable record.
2. **SPEC-0009 rule 14, `pull_requests`.** A merged pull request also has the optional `head_cleared` (`yes`, `no` or `unknown`, the value of `merged_head_cleared`); `schema` stays 1.
3. **SPEC-0011 rule 10, At risk (v).** A merged pull request whose `head_cleared` is `yes` prints no "merged before its last commit was cleared" line.
