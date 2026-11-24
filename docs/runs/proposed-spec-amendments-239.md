# Proposed spec amendments 239 (SPEC-0047; REQ-080)

Date: 2026-11-24 (from `date -u`). Approved specs change only through a proposal like this one (principle 6). Written for
ADR-0793 (brief #1918, SPEC-0073 rule 13), which stays `Proposed` for the maintainers' decision. The path:
`docs/specs/0047-every-repository-has-one-weekly-scorecard-of-numbers-with-thresholds-and-trends.md` (rule 1). This file proposes the lines and does not edit the spec. SPEC-0073's build (h) applies it word for
word, on the owner's `Maintainer answer: amendment 239 approved`; no session posts it (`Q-PN-2`).

The sentence (brief #1918), quoted as data: "Intake for Day-1 quality: a grill interview tests every idea before its vision, and the same path then holds the product, design, architecture and build to industry practice, in solo and team, with no slower path and no new CI job."

## Items

1. **SPEC-0047 rule 1, one metric.** After the `stale_guides` bullet add: "- `shallow_files`: the files changed in the
   last `[quality] survey_days` days (default 7) that fail the deletion test (a module whose public names are each used
   once, by one caller), read with read-only `git log` and the files by its own reader under its own ADR, never by
   `survey.py`; with `survey_days = 0` the row reads `not run: off`, never a number; its candidates go to the steward's
   triage and a rejected one is not offered again (amendment 239)."

No other rule changes.
