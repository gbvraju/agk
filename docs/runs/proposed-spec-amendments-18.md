# Proposed spec amendments 18 (SPEC-0011 and SPEC-0009; found while building the renderer, SPEC-0011 (a))

Date: 2026-10-17 (from `date -u`). Approved specs change only through a proposal like this one (principle 6). The paths:
`docs/specs/0011-inbox-and-report.md`, `docs/specs/0009-facts.md`.

**Not applied.** The readings `Q-K4-136` and `Q-K4-137` of ADR-0029 stand until the maintainers rule on them.

## SPEC-0011 (`docs/specs/0011-inbox-and-report.md`)

1. **Rule 10 (iv), the kinds in the drift line.** The rule prints `D1` to `D6`. Proposed: the line prints every kind that the facts'
   `drift.counts` holds (`D1` to `D7` today, as amended for SPEC-0009 rule 15 by the proposal 17), in order, so that a kind added to
   the audit is shown without a change to the renderer.

## SPEC-0009 (`docs/specs/0009-facts.md`)

2. **Rules 10 and 11 (the `specs` and `adrs` fields), a `path`.** The inbox and the Delivered, Proven and Needs-you lines link a spec or an ADR
   to the file. The facts carry `id` and `title` but no path, so the renderer links the directory. Proposed: each `specs[]` and
   `adrs[]` object also holds `path` (the repository path of the file, as the engine already reads it), `schema` stays `1` by the same
   reasoning as proposal 17, item 3 (no consumer reads the document yet outside this renderer), and `kit/facts-schema.json` changes.
