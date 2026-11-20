# Proposed spec amendments 191 (SPEC-0007; REQ-012)

Date: 2026-11-20 (from `date -u`). Approved specs change only through a proposal like this one (principle 6). Written for
ADR-0659 (brief #1557), which stays `Proposed` for the maintainers' decision. The path: `docs/specs/0007-metrics.md`.
Brief #1557 reserved amendment 191. This file proposes the lines and does not edit the spec. They are applied word for
word, on a person's `Approve: SPEC-0007`; no session posts it.

## Why

SPEC-0007 fixes one window, the ISO week before `--today` (rule 12), and one unit, the closed pull request (rule 2).
Brief #1557 asks for the measures of each delivered feature over a chosen range. `measures.py` adds them without changing
any rule of SPEC-0007 or the weekly report. Amendment 142 (`check_specs.py` `contexts_failures`) refuses any change to an
Approved spec without a `## Contexts` section, and SPEC-0007 has none, so item 2 supplies one.

## Items

1. **A section "Measures for a date range" (new),** after rule 24 and before `## Tests`:

   ```
   ### Measures for a date range

   25. **One command, read-only.** `measures.py --from YYYY-MM-DD --to YYYY-MM-DD [--json] [--repo OWNER/REPO]
       [--api-dir DIR | --sidecar DIR]` reads with GET only, writes no file and posts nothing. The range is UTC days,
       both included, at most 92; any other range is refused naming the option. The same input gives the same bytes.
   26. **The unit is the feature.** A feature is a brief whose finishing pull request (`Finishes: #n`, else the last
       merged one with `Brief: #n` once the brief is closed) merged in the range. One row per feature, then the range
       totals, then one row for the merged pull requests tied to no brief. The rows reuse the records of rules 2 to 9.
   27. **The figures.** Per feature: hours from brief to merge (queue, build, the builder's turns of SPEC-0049 rule 6),
       rework (fix rounds, rejections, corrections, reopens, follow-ups, first-review pass), backstop escapes, tokens
       (SPEC-0049 rule 5), Actions minutes, and the owner's part (hand and guarded merges, a person's lines, owner
       questions and their wait). Rule 10 holds: a missing input is `unknown`; a mode that keeps no such record prints
       `none (local mode)` or `none (personal mode)`. No cost and no owner's minutes are estimated.
   28. **Numbers only.** The output holds dates, numbers, counts, hours, minutes and tokens, never a title, body text,
       login, branch, path, label, repository or host name; a test asserts it on invented names.
   ```

2. **A `## Contexts` section (new),** after `## Tests` and before `## Residual`:

   ```
   ## Contexts

   - kit: `metrics.py` and `measures.py` are installed in every project with the kit and read only its own records
   - github: the weekly workflow files one issue a week (rules 11 to 15), and `measures.py` reads with GET only and posts nothing
   - local: the records are read the same way, and the Actions figures read `none (local mode)` (rule 27)
   - personal: the sidecar's `forge/` files are read through the same names (SPEC-0041 rule 6), and the Actions, escape and owner figures read `none (personal mode)`
   - stacks: not applicable: no test or build step of a stack runs
   ```

No existing rule changes.
