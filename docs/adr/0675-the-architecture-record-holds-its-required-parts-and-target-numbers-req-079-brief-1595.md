# ADR-0675: The architecture record holds its required parts and target numbers (REQ-079, REQ-055)

- Status: Proposed
- Date: 2026-11-21
- Deciders: maintainers
- Related: brief #1595, SPEC-0029, SPEC-0072, SPEC-0048, amendment 203, amendment 204, amendment 205, ADR-0668, brief #1588, plan #661
- Requirements: REQ-079, REQ-055

Protected classes: `scripts/agk/`, `tests/kit/`, `tests/kit_dev/`, `kit/`, `skills/`, `config/`

## Context

On the default branch at 11fa8bc8 (2026-11-21) `front_door.py` `design_problems` checks that a
`docs/design/architecture/<slug>.md` has one `Research:` line and a fenced Mermaid or text diagram, and nothing else
(SPEC-0048 rule 7); `docs/architecture.md` (SPEC-0072 rule 5, brief #1588) holds the layers, the allowed directions and
the stack record's number only; nothing links the two records; `engines.py` `QUESTIONS` asks `scale` with no numbers
and nothing on cost or on what is logged (gaps G19 and G23, brief #1595).

## Decision

1. SPEC-0029 rule 4, SPEC-0072 rule 5 and SPEC-0048 rule 7 change only through amendments 203, 204 and 205, which this
   build writes. Amendments 203 and 204 were applied word for word on the maintainer's answers on this pull request,
   "Maintainer answer: amendment 203 approved" and "Maintainer answer: amendment 204 approved" (2026-11-21).
   Amendment 205 was approved the same way ("Maintainer answer: amendment 205 approved") and waits for Q-1595-3:
   SPEC-0048 has no `## Contexts` section, which amendment 142 requires of an amended Approved spec.
2. **The needs question.** The `scale` topic keeps its id and asks one question with a recommended answer: how many
   use it at the busiest hour, how long it may be down each month and what it may cost each month. The busiest hour is
   in people (the default), in calls per minute for `api-service` and `mcp-server`, and in runs per day with the
   largest input file for `data-pipeline`, a missed run read as down time. The recommended numbers are invented
   defaults for the maintainers to accept or change: up to 200 at once (600 calls per minute; 24 runs per day and a
   100 MB file), at most one hour down a month, under 50 dollars a month. The answer is quoted in the charter
   (`- scale:`) or the discovery document; `- needs:` is read the same. `default.toml`'s `non-functional` question no
   longer repeats scale and uptime and asks for recovery time and what is logged.
3. **The record's required parts.** `kit/templates/architecture.md` gains `## Context`, `## Parts`, `## Data stores`,
   `## Outside services`, `## Needs` (`- Busiest hour:`, `- Downtime:`, `- Cost:`, `- Recovery time:`, `- Logged:`) and
   `## Diagram` beside `## Layers`; `layers.py --write-record` writes the chosen option's `External services:` into
   `## Outside services` and the diagram, so the record it writes passes.
4. **The `architecture-record` step.** `front_door.py` `record_problems`, run by `check-design` and by the runner of
   brief #1586 as a step of the composed `[architecture]` where the record exists
   (`scripts/agk/gates/architecture_record.py`), fails a missing section, a diagram that is not a fenced block, a
   service of the chosen option missing from `## Outside services`, an outside service missing from the diagram, a
   missing `Needs` line, and a number of the first three `Needs` lines that the quoted answer does not give (or with no
   quoted answer). Each failure names the rule, the section and the line key, never a value (principle 8). A record
   with none of the new sections was written before this change: `not run` until its next edit, never `ok`
   (principle 11).
5. **One record.** A front-door design is a slice document with one line `Architecture: docs/architecture.md`.
   `check-design` refuses a design named on its command line (an edit) without it, or with a wrong or repeated line;
   a design read with the whole folder is a warning until its next edit (brief Q-2).

## Consequences

A product has one architecture record with its parts, stores, outside services, target numbers and a diagram; the
person is asked one plain needs question with a recommended answer. Hosted, local and personal modes run the same
check; customer projects' records hold numbers only.

## Residual

- `mode = "adopt"`: drafting the record from `front_door.py detect` and the survey, marked `(proposal)` until the
  person's yes, is not built here (due 2027-01-31).
- The `scale` id is kept rather than renamed `needs` (Q-1595-1); a rename across the charter checks follows only on the
  maintainers' word (due 2027-01-31).
