# Proposed spec amendments 155 (SPEC-0009, SPEC-0011, SPEC-0022; REQ-063)

Date: 2026-11-09 (from `date -u`). Approved specs change only through a proposal like this one (principle 6). Written for
SPEC-0056 build (d), brief #889, `Covered-by: ADR-0372`. The paths: `docs/specs/0009-facts.md`,
`docs/specs/0011-inbox-and-report.md`, `docs/specs/0022-*.md`. The number 155 is the one brief #889 reserved. Nothing here is
applied to a spec in this pull request; the owner decides it, and it needs a person's `Approve:`; no session posts it.

## SPEC-0009 (`docs/specs/0009-facts.md`)

1. **Rule 3, the top-level keys.** Add `measures` to the list. Like `flow` and `shadow`, it is optional in the schema, so a
   document written before it stays valid.
2. **Rule 15, a new section.** Add: "*`measures`:* for the full ISO week before `today`, the object `{"week": "YYYY-Www",
   "restore": {...}, "run_minutes": {"minutes", "per_merged"}}`. `restore` has the keys `red default branch` (the issues
   titled as `scorecard.py` reads for `restore_hours`, opened to closed), `actions blocked` (the `Local mode since` records,
   opened to closed) and `leaked secret` (the issues with the label `agk-secret-leak`, `Detected:` to `Revoked:`; the body is
   read for those two lines and nothing else), each `{"closed", "median_hours", "open"}`: the number closed in the week, the
   median of their hours to 0.1, and the number open now. `median_hours` is `none` when nothing closed in the week and
   `unknown` when one of the times cannot be read: a line that is missing, repeated or not `YYYY-MM-DDTHH:MM:SSZ`, or a
   `Revoked:` before its `Detected:`. `minutes` is `minutes.estimate` over the week, as `scorecard.py` computes it, and
   `per_merged` is that divided by the pull requests merged in the week, to 0.1, `unknown` when none merged or `pull_requests` is
   `unknown`. A list that cannot be read makes its own figures `unknown`; when no list can be read the section is `unknown`.
   It holds no title, body text, login or log."
3. **Rule 19, the schema.** Add: "`measures` is optional in `kit/facts-schema.json`, as `flow` and `shadow` are, and `schema`
   stays 1: no released consumer requires the key, and a renderer given a document without it prints `unknown`."

## SPEC-0011 (`docs/specs/0011-inbox-and-report.md`)

4. **Rule 2, what is computed.** Add: "The figures of the `measures` section are computed by `facts.py`, because the renderer
   has no list of issues or runs; the renderer prints them. The section holds one week, so a report of another week, or a
   document without the section, prints `unknown` for them."
5. **Rule 10, Cost.** Add: "After the lines above, always, also in a week with no merge: one line per kind in the order
   `red default branch`, `actions blocked`, `leaked secret`: `restore <kind>: <n> closed, median <h> hours, <k> open`, then one
   line `run minutes: <m> this week, <p> per merged pull request`, each from the `measures` section and ending with its link
   (rule 11): the repository's issues and its Actions runs. `## Cost` therefore no longer prints `nothing this week`."

## SPEC-0022 (the report's structure)

6. **Rules 3, 5 and 7, two kinds and the number.** This item is beyond the five SPEC-0056 rule 14 lists (Q-889-1): `report.json`
   is built from the structure alone and a new kind raises the number, so the lines above need it. Add to the table of kinds
   `restore` (`of`, `closed`, `median_hours`, `open`) and `run-minutes` (`minutes`, `per_merged`), both in `cost`, and raise
   `schema` from 7 to 8 in `report.json` and `kit/report-schema.json`.
