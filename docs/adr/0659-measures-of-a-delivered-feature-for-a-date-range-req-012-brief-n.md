# ADR-0659: The measures of a delivered feature for a date range (REQ-012)

- Status: Proposed
- Date: 2026-11-20
- Deciders: maintainers
- Related: brief #1557, SPEC-0007, amendment 191, SPEC-0046, SPEC-0049 rules 5 and 6, SPEC-0041 rule 6, brief #1459
- Requirements: REQ-012

Protected classes: `scripts/agk/`, `tests/kit/`, `kit/`, `agk.toml`

## Context

`metrics.py` (SPEC-0007) gives one record per closed pull request for the ISO week before `--today` (rule 12), and
nothing joins a brief to its pull requests. A delivery run is judged per feature and over a chosen range: the time from
brief to merge, the rework, the defects after merge, the model spend, the Actions minutes and the owner's part. Every
input already has a reader: `metrics.build_record` and `ci_fields`, `metrics.escape_of`, `caps.hours_used` and
`caps.tokens_used`, `minutes.estimate`, `common.finished_brief` and `common.MERGED_BY`, and `forge.FilesForge` in
personal mode. Options weighed: (A) a range option on `metrics.py` (changes rule 12's fixed window and the weekly
issue); (B) a new read-only script that reuses those readers and changes no output of `metrics.py`.

## Decision

(B) is chosen.

1. `scripts/agk/measures.py --from YYYY-MM-DD --to YYYY-MM-DD [--json] [--repo OWNER/REPO] [--api-dir DIR | --sidecar
   DIR]` is read-only: GET only through `metrics.Gh`, `metrics.ApiDir` or `forge.FilesForge`; it writes no file and posts
   nothing. The range is UTC days, both included; a date that does not parse, `--to` before `--from` or a range over 92
   days (Q-1557-2) is refused naming the option, with exit 2. The same input gives the same bytes.
2. A feature is a brief whose finishing pull request merged in the range: the first merged one with `Finishes: #n`,
   else, once the brief is closed, the last merged one with `Brief: #n`. Its pull requests are those of the brief closed
   at or before that merge; one merged later is a follow-up. A merged pull request with no `Brief: #n` goes to one row
   "not tied to a brief". Only the pull requests closed since `--from` are listed, so a build merged earlier is not read.
3. Per feature: `lead_hours`, `queue_hours` (to the brief's first `taken:`), `build_hours`, `builder_hours`
   (`caps.hours_used` per pull request, up to its close); `fix_rounds`, `rejected` (rejected verdicts plus pull requests
   closed unmerged), `corrections`, `reopened` (`issues/<n>/events`), `follow_ups`, `first_review_pass`; `escapes`,
   `red_pushes` and `escapes_unknown` (`metrics.escape_of`); `tokens` (`caps.tokens_used`, a pull request with no figure
   counted as `not-reported`, never 0); `cost` reads `not priced`, since no reader knows the tier of a `Report:`
   (Q-1557-4); `minutes`, `pool_minutes` and `reruns` (`ci_fields`, summed); `hand_merges` and `guarded_merges` (the
   merge commit's message read by local git, `MERGED_BY`), with ` (auto_merge off)` when the setting is off;
   `owner_lines`, `owner_questions` and `owner_wait_minutes`. Minutes of the owner's own time are not estimated (Q-1557-1).
4. A comment is a person's when it was not posted through an app of `agent_apps`. When a pull request's own author posts
   without an app mark, a person's line cannot be told from an agent's and `owner_lines` reads `unknown (no app mark)`
   (Q-1557-6).
5. Totals: the count of features, the median `lead_hours`, the sums, the first-review pass as `<yes>/<features>`, the
   `found-bug` issues opened in the range and how many of those are closed (a defect is tied to a feature only by a
   stated line, Q-1557-3), and `billed_minutes` (`minutes.estimate` over every run created in the range).
6. `execution = "local"` gives `none (local mode)` for the minutes; personal mode gives `none (personal mode)` for the
   minutes, the escapes and the owner lines. The output holds numbers only: no title, body text, login, branch, path,
   label, repository or host name.
7. `metrics.py` does not change, nor its weekly report or issue.

## Consequences

One command gives the measured results of a delivery run from GitHub alone, on any machine of a team. Brief #1459 can
take lead time per brief, tokens per merged pull request and the first-review pass from it (Q-1557-7). SPEC-0007 gains a
section only by amendment 191, applied on the owner's `Approve: SPEC-0007`.

## Residual

- The local-mode record issue's `Local merge:` and `Auto merge:` lines, the "this machine" cost of `metrics.py --cost`,
  the sums by kind and personal mode's `defects_before_push` are not read yet; a later brief adds them (due 2026-12-20).
