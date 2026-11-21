# Proposed spec amendments 203 (SPEC-0029; REQ-079)

Date: 2026-11-21 (from `date -u`). Approved specs change only through a proposal like this one (principle 6). Written for
ADR-0675 (brief #1595), which stays `Proposed` for the maintainers' decision. The path:
`docs/specs/0029-a-product-owner-starts-from-a-brief-idea-the-vision-the-stac.md` (rule 4 and the `## Tests` section).
Brief #1595 reserved amendment 203. This file proposes the lines and does not edit the spec. They are applied word for
word, on a person's `Approve: SPEC-0029`; no session posts it.

## Why

On the default branch at 11fa8bc8 (2026-11-21) `engines.py` `QUESTIONS` asks `scale` as "What scale is expected, in
users, volume and growth?" with no number required and nothing on cost, and nothing on what is logged (gap G19,
brief #1595).

## Items

1. **Rule 4, one sentence added at its end.** "The `scale` topic is the one needs question, asked in plain words with
   its recommended answer: how many use it at the busiest hour (people for a web app, calls per minute for an API
   service, runs per day and the largest input file for a data or report tool, a missed run counted as down time), how
   long it may be down each month and what it may cost each month, recommended `up to 200 at once, at most one hour
   down a month, under 50 dollars a month`; the answer is quoted word for word in the charter or the discovery
   document, and the topic keeps its id, so an answer given before still passes." (answer 1)
2. **The `## Tests` section, one line added after the rule 4 line.** "- Rule 4, the needs: `engines.py questions`
   asks the needs question once, with its recommendation, in the words of the work type's shape; REQ-079 AC1."
3. **Unchanged:** rules 1 to 3 and 5 to the last, the Proof, the Residual and the Open questions.
