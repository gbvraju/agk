# Proposed spec amendments 204 (SPEC-0072; REQ-079)

Date: 2026-11-21 (from `date -u`). Approved specs change only through a proposal like this one (principle 6). Written for
ADR-0675 (brief #1595), which stays `Proposed` for the maintainers' decision. The path:
`docs/specs/0072-each-work-type-playbook-carries-its-architecture-a-stack-sta.md` (rule 5 and the `## Tests` section).
Brief #1595 reserved amendment 204. This file proposes the lines and does not edit the spec. They are applied word for
word, on a person's `Approve: SPEC-0072`; no session posts it.

## Why

On the default branch at 11fa8bc8 (2026-11-21) `kit/templates/architecture.md` (brief #1588) holds only the layers, the
allowed directions and the stack record's number; nothing requires the parts, the stores, the outside services, the
target numbers or a diagram (gap G19, brief #1595).

## Items

1. **Rule 5, two sentences added at its end.** "The record also holds `## Context`, `## Parts`, `## Data stores`,
   `## Outside services` (each service of the chosen option's `External services:`), `## Needs` (`- Busiest hour:`,
   `- Downtime:`, `- Cost:`, `- Recovery time:`, `- Logged:`, the first three's numbers those of the quoted needs answer
   of SPEC-0029 rule 4) and `## Diagram` (a fenced Mermaid or text block that draws each outside service). The
   `architecture-record` step (`scripts/agk/gates/architecture_record.py`, the check of `front_door.py`, which
   `check-design` also runs) fails a missing section, an outside service missing from the record or its diagram, and a
   `Needs` number the quoted answer does not give, naming the rule and the section, never a value; a record with none of
   these sections, written before them, is `not run` until its next edit." (answer 2)
2. **The `## Tests` section, one line added after the "Rules 5 and 6" line.** "- Rule 5, the required parts: a record missing a
   section, with an outside service not in its diagram, or with a `Needs` number other than the quoted one is red, the
   record the foundation writes is green, and a record written before is `not run`, never `ok`; REQ-079 AC1."
3. **Unchanged:** rules 1 to 4 and 6 to 13, the Proof, the Residual and the Open questions.
