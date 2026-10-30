# ADR-0189: the session plan waits only for real file overlap and ignores stale claims (REQ-041, brief 330)

- Status: Proposed
- Date: 2026-10-30
- Deciders: maintainers
- Related: ADR-0124, ADR-0153, ADR-0155
- Requirements: REQ-041

Protected classes: `kit/`, `scripts/agk/`, `tests/kit/`

## Context

Brief #330 (priority 1). On 30 Oct 2026 the conductor planned a wave of six parallel builders by hand while `session.py plan` on the same state printed "Start 0": seven ready briefs waited for #322 only because their `Touches:` named the same folder (`docs/guides/`), although each changed a different file, and #263 was "taken by builder-f" from a claim days old whose builder had ended (an open pull request of another build of #263 kept that take live). The hand plan ran six builders without a single file conflict. The tests were written first.

## Decision

1. **Overlap is judged by files** (answer 1, as corrected by the verdict on 1f1969e). An entry of `Touches:` is a folder entry when it is `dir/`, `dir/**` or `**`, or a path without a wildcard that is a folder of the repository (`docs/guides` is `docs/guides/`); every other entry names files (a path, or a glob such as `scripts/agk/*.py`).
   - **A folder entry covers every file under it,** unless the same brief also names files under that folder; then only those files count for it.
   - Two entries that name files overlap on a file they both name: the same path, or a path that the other entry's glob matches; two globs overlap when one's fixed part starts with the other's.
   - Between two briefs, a covering folder entry overlaps an entry of the other brief that names a file under it (`docs/guides/` against `docs/guides/a.md` waits; `docs/guides/` with `docs/guides/b.md` against `docs/guides/a.md` does not). Two folder entries overlap when one is above or below the other, as before.
   - Against an open pull request, whose overlap is its changed files: a modified, renamed (also by its old name) or removed file overlaps a brief when an entry that names files matches it or a covering folder entry holds it (`tests/kit/` waits for a pull request that modifies `tests/kit/test_x.py`). An added file overlaps only an exact path, as before.
   - Shared mechanical files (changelog fragments, the `merge=union` files) never overlap, as before.
2. **A stale claim holds nothing** (answer 2). A claim is stale when its session has posted nothing for `[flow] claim_stale_hours` (a whole number of 1 or more, 24 by default, refused otherwise naming the setting) and has no open pull request. The posts of a session are its `taken:` and `released:` comments on the open briefs, the opening and merge of the pull requests that may be its work, and its `Progress:`, `Report:` and `Request:` comments (the verdict on 1f1969e, item 3): on the open briefs and on the open issue labelled `agk-conductor` those whose text names the session as a whole word (all sessions post from one account), and on a pull request that may be its work every such comment. Those comments are read only for a session that would otherwise be stale, and a read that fails keeps the session fresh. A pull request may be a take's work when it has `Brief: #<n>` and the take is of the whole brief, or its title names the take's build (`build (c)` or `build c`), or its title names no build; a title that names another build is another session's work. A stale claim does not hold its brief, is not running work and is not named in a `taken by` skip; the plan lists it in `stale_claims` (`brief`, `session`, `build`, `hours`, `why`) and in words `Stale: #263 (stale claim by builder-f, 3 days).`, so that the conductor can reassign it. The name of a stale session is not offered to a new session.
3. **Every wait names the file** (answer 3): `both touch docs/guides/a.md`, `it changes docs/guides/x.md`; for two folder entries, the narrower folder.
4. **Readings taken where the brief leaves a point open**: only `session.py plan` changes; `session.py next` keeps its overlap and claims as SPEC-0034 rules 3 and 5 say until its own brief (Q-330-1). Two folder entries name the narrower folder (Q-330-3). The tests of ADR-0153 keep their cases; their waits now name the file (`both touch scripts/agk/x.py`). No spec rule changes its words: SPEC-0034 rule 15 says a brief waits when its `Touches:` overlap running work, and this decision says what overlap means. Flow mode: fragment `changelog.d/plan-file-overlap.md`; no version bump; `kit/templates/agk.toml` documents the optional setting as a comment.

## Consequences

- Briefs that each name a different file under one folder start in the same wave; a brief that names only the folder still waits for work on any file in it.
- A claim left by a session that ended no longer holds a brief; the plan says whose it was and how old.

## Residual

- 2026-10-30: `docs/guides/getting-started.md` still describes the plan's overlap in the words of ADR-0153; an open pull request (#335) changes that guide, so it is not edited here (due 2026-12-31).

## Log

- 2026-10-30: the verdict on 1f1969e corrected answer 1 (a folder entry that names no file under it covers every file under it; a folder of the repository written without its slash is a folder) and answer 2 (a session's own `Progress:`, `Report:` and `Request:` comments are posts). Q-330-1: `next` gets the same rules in its own brief, which the conductor files. Q-330-2: answered by the correction of answer 2. Q-330-3: naming the narrower folder is acceptable.
