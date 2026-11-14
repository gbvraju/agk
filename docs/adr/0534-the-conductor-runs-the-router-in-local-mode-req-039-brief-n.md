# ADR-0534: The conductor runs the router in local mode

- Status: Accepted
- Date: 2026-11-14
- Deciders: maintainers
- Related: SPEC-0030, SPEC-0032, SPEC-0039, ADR-0513, brief #1212, brief #1263, plan #661
- Requirements: REQ-039

## Context

ADR-0513 made `route.py` read local evidence in local mode and left one residual: the conductor's guard does not allow
`python3 scripts/agk/route.py --all`, and neither the conductor agent nor the review-pass skill runs it, so in local mode
the `agk:` labels move only when a person runs the router by hand. A customer project on v0.64.2 (local mode, two builder
pull requests) showed both pull requests with no `agk:` label. The same project showed a second cost: `route.py --all`
took one to two minutes over two pull requests, because `record_open` paged every open issue (693, with full brief bodies)
to find the record issue although `agk.toml` said `execution = "local"`, and the open pull request list was read again for
the pipeline document. In CI mode the router workflow pays the same paging on every pull request and comment event.

## Decision

1. `.claude/hooks/conductor_guard.py` allows, without `--shadow`, exactly `python3|python scripts/agk/route.py --all` and
   `... route.py --pr <n>` (digits only), the project's own regular file and never a link, and only while the project is in
   local mode as `route.py` decides it: the guard calls `route.record_open` (no copy of the reading). In CI mode the same
   command is refused with the message `the router runs from its workflow unless the project is in local mode (setting:
   execution, or the one local-mode record issue)`, because the router workflow moves the labels there. `--dry-run`,
   `--branch`, `--health`, any other option, path or script stays denied; the shadow reviewer gets nothing new.
2. `.claude/agents/conductor.md` and `skills/review-pass/SKILL.md`: in local mode the conductor runs
   `python3 scripts/agk/route.py --all` once at the end of each pass that posted a verdict or found a new head, and once
   after each `merge_cleared.py` line; an unchanged fingerprint runs nothing. Its output lines go in the pass's last lines.
3. `docs/guides/local-mode.md`: the conductor runs it on each pass; a person runs it only when no conductor is alive.
4. `scripts/agk/route.py` decides local mode with `merge_cleared.local_mode` itself: `execution = "local"` in the
   checkout's `agk.toml` answers with no issue read; only otherwise the record issue is looked for, with one search call
   (`search/issues?q=repo:<repo> is:issue is:open in:title "Local mode since"`), never by paging the open issues.
5. The search is one call that never waits on a rate limit (the search limit is not the core limit `session.gh` waits
   for). When it fails or is limited (403, 422, 429 or any other failure), that run falls back to today's paging of the open
   issues; a failed search is never read as "no record issue" or as "record issue open". The search index can lag a
   just-opened issue by a few minutes; that is accepted, because a project going local sets `execution = "local"`.
6. One run reads the open pull request list once and reuses it for `--all`, the sweep, the merger's start and the
   pipeline document, keeping it true with the labels the run sets; the label list is read once, as before (`Labels`).
   A run that changed a label reads the list once more for the pipeline document, so what it shows a person carries the
   labels as GitHub now has them.

No workflow file, ruleset or `constitution/` file changes; CI labels are judged from check runs exactly as before.

## Consequences

In local mode the labels move on every review pass without a person, and `route.py --all` over two pull requests makes 16
GitHub calls in the recorded double (test (h) bounds it at 18) instead of paging every open issue. The conductor role file stays at its rule budget (4499 words, 37
rules): the new sentence is paid for by dropping the list of review reasons that `skills/review-pass/SKILL.md` already
gives. Tests:
`tests/kit/test_conductor_guard.py` (a) to (d) and `tests/kit/test_route_local.py` (f) to (j); the two older unit tests of
`record_open` now make the search fail (no network) and so test the fallback. Protected path classes changed: `.claude/`
(`.claude/hooks/conductor_guard.py`, `.claude/agents/conductor.md`), `skills/` (`skills/review-pass/SKILL.md`),
`scripts/agk/` (`route.py`), `tests/kit/` (`test_conductor_guard.py`, `test_route_local.py`) and `agk.toml`
(`tests/kit/test_conductor_guard.py` joins the test map of `route.py`, which it now names, as
`tests/kit/test_always_full_infra.py` requires).

## Residual

- 2026-11-14: the guard now makes a network read for the router command when `execution` is not `"local"` (one search,
  or the paging fallback). A guard that cannot reach GitHub refuses the command, which is the closed side (due 2026-12-31).
