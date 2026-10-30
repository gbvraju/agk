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

1. **Overlap is judged by files** (answer 1). An entry of `Touches:` is a folder entry when it is `dir/`, `dir/**` or `**`; every other entry names files (a path, or a glob such as `scripts/agk/*.py`).
   - Two entries that name files overlap on a file they both name: the same path, or a path that the other entry's glob matches; two globs overlap when one's fixed part starts with the other's.
   - A folder entry overlaps another folder entry above or below it, as before (`docs/guides/` and `docs/guides/` still overlap).
   - A folder entry against an entry that names a file under it overlaps only when the folder's brief names that file too, which the first rule finds.
   - An open pull request's overlap is its changed files. A modified, renamed (also by its old name) or removed file overlaps a brief only when an entry of the brief that names files matches it; a folder entry alone never does. An added file overlaps only an exact path, as before.
   - Shared mechanical files (changelog fragments, the `merge=union` files) never overlap, as before.
2. **A stale claim holds nothing** (answer 2). A claim is stale when its session has posted nothing for `[flow] claim_stale_hours` (a whole number of 1 or more, 24 by default, refused otherwise naming the setting) and has no open pull request. The posts of a session are its `taken:` and `released:` comments on the open briefs and the opening and merge of the pull requests that may be its work. A pull request may be a take's work when it has `Brief: #<n>` and the take is of the whole brief, or its title names the take's build (`build (c)` or `build c`), or its title names no build; a title that names another build is another session's work. A stale claim does not hold its brief, is not running work and is not named in a `taken by` skip; the plan lists it in `stale_claims` (`brief`, `session`, `build`, `hours`, `why`) and in words `Stale: #263 (stale claim by builder-f, 3 days).`, so that the conductor can reassign it. The name of a stale session is not offered to a new session.
3. **Every wait names the file** (answer 3): `both touch docs/guides/a.md`, `it changes docs/guides/x.md`; for two folder entries, the narrower folder.
4. **Readings taken where the brief leaves a point open** (the most conservative each, as questions on the pull request): only `session.py plan` changes; `session.py next` keeps its overlap and claims as SPEC-0034 rules 3 and 5 say (Q-330-1). The posts counted are those the plan already reads, with the pull requests of the session's takes as signs of work; the `Request:` comments on the conductor issue are not read (Q-330-2). Two folder entries name the narrower folder, where the brief asks for a file (Q-330-3). The tests of ADR-0153 that waited on a folder against a file under it now use two folders or file globs, as answer 1 reverses that case. No spec rule changes its words: SPEC-0034 rule 15 says a brief waits when its `Touches:` overlap running work, and this decision says what overlap means. Flow mode: fragment `changelog.d/plan-file-overlap.md`; no version bump; `kit/templates/agk.toml` documents the optional setting as a comment.

## Consequences

- Briefs that each change a different file under one folder start in the same wave.
- A claim left by a session that ended no longer holds a brief; the plan says whose it was and how old.

## Residual

- 2026-10-30: `docs/guides/getting-started.md` still describes the plan's overlap in the words of ADR-0153; an open pull request (#335) changes that guide, so it is not edited here (due 2026-12-31).
