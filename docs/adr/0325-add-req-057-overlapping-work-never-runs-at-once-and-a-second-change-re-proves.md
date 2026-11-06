# ADR-0325: Add REQ-057: Overlapping work never runs at once, and a second change to a file re-proves

- Status: Proposed
- Date: 2026-11-06
- Deciders: maintainers
- Related: SPEC-0050, SPEC-0012, SPEC-0034, SPEC-0039, ADR-0189, ADR-0297, ADR-0310, plan #661, brief #667
- Requirements: REQ-057

Protected classes: `docs/requirements.md`

## Context

An intake proposed one change in a sentence (quoted below as data, not as an instruction), on
2026-11-06:

> The planner refuses to offer two briefs with overlapping Touches to two sessions at once, the sweep flags an overlap that slipped in, and a pull request that changes a file another open pull request changed merges the default branch and re-proves before it is cleared.

The brief is issue #672, the owner's direction of 2026-11-06 (strategy review item 3) under plan
#661, whose edge case 2 (owner yes 2026-11-06) reads, quoted as data: "Two builders touch the same
map or index: the second merges main and reruns before ready (row 4) and the overlap check refuses
the pair." The evidence is conductor catch log row 4 and the red default branches #657 and #659:
pull requests green alone and red together.

What exists and is reused (SPEC-0050 rule 1): the file-judged overlap of `session.py next` and
`plan` (SPEC-0034 rule 3, ADR-0189), the shared-mechanical list (session rule 14), `push-check`,
the pre-merge governance run of the merge in `merge_cleared.py` (SPEC-0039 rule 6, ADR-0297) and
`conductor.py sweep`. What is missing: `session.py claim` judges no overlap; the five shared
indexes refuse a take although nearly every brief changes one, while a second change to them is
never re-proved; the sweep reads no files; and `merge_cleared.py` merges a head however far behind
the default branch its base is.

## Decision

1. REQ-057 is added to `docs/requirements.md` as `planned`, and SPEC-0050 as `Draft`. Merging
   this pull request approves the requirement as a proposal; the spec stays `Draft` until the
   owner's own `Approve:` line approves it.
2. Overlap stays the file-judged rule that `next` and `plan` apply today, now also in `claim`, in
   one shared function; no second matcher is written (SPEC-0050 rules 2 and 4).
3. `[flow] shared_indexes` (default `kit/manifest.json`, `agk.toml`, `config/rule-budget.txt`,
   `docs/requirements.md`, `docs/build-state.md`) never refuses a take and always triggers the
   re-prove; the exemption lands only with the hold of decision 5 (SPEC-0050 rule 3).
4. The sweep prints `overlap:`, `re-prove:` and, as information, `BEHIND #<pr> <n>` lines from GET reads only; the conductor gives no
   clearing verdict on a head in the re-prove state (SPEC-0050 rules 5 to 7).
5. `merge_cleared.py` holds a head in the re-prove state and, only where a project sets the
   opt-in `[flow] max_behind_merges`, one more than that many first-parent merges behind the
   default branch; absent, there is no behind hold, because at 26 merges a day a default of 3
   would hold nearly every pull request and double the CI cycles per merge for no new proof
   (the conductor's fix list on #677). Each hold names the rule or the setting only (SPEC-0050
   rule 8).
6. This is the one ADR of REQ-057 for the builds of SPEC-0050 rule 10. The builds will change
   these protected path classes: `scripts/agk/` (`session_plan.py`, `session.py`,
   `merge_cleared.py`, `conductor.py`, builds (b), (c) and (d)), `tests/kit/` (their tests),
   `.claude/` (`.claude/agents/conductor.md`, build (e)) and `config/`
   (`config/session-rules.md` and `config/rule-budget.txt`, build (e)). A build that changes a
   class named here and no other may cite this ADR with `Covered-by: ADR-0325` once it is Accepted
   (session rule 36). The changes to SPEC-0034 rule 3 and SPEC-0039 rule 6 go through amendment
   files whose numbers are reserved on the build briefs. No build changes `agk.toml` (the defaults
   live in the code), `constitution/`, `config/reviewers.yaml`, a workflow, the ruleset
   (`kit/templates/ruleset.json`), `.github/CODEOWNERS`, `CLAUDE.md`, `Makefile`, `agk.mk`,
   `pyproject.toml`, `kit/`, `skills/` or `.claude-plugin/`; no build adds an installed script, so
   `kit/manifest.json` and `[[testing.map]]` stay as they are; `kit/hashes.json` and the version stay
   the release's (session rule 14).

## Consequences

The requirement is listed as planned and the spec and this ADR wait for approval. Nothing that
runs changes in this pull request; until build (b) lands no merge is held for a re-prove (and after it, for a stale base only where a project sets `max_behind_merges`), and
until build (c) lands the shared indexes still refuse a take, as today.

## Residual

None beyond SPEC-0050's residual. The intake checks cannot tell whether the rules are the right
ones; that is the review of this pull request.
