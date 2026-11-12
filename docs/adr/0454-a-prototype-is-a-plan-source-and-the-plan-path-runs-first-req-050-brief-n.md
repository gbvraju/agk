# ADR-0454: An imported prototype is a plan source, and SPEC-0043's plan path runs first

- Status: Proposed
- Date: 2026-11-12
- Deciders: maintainers
- Related: SPEC-0043, SPEC-0037, ADR-0269, ADR-0446, amendment 161, amendment 163, brief #1073, plan #661
- Requirements: REQ-050, REQ-044

## Context

The owner wants a milestone-based development plan in GitHub from a customer's prototype (brief #1073). SPEC-0043
(Approved, REQ-050, ADR-0269) specifies how a plan is drafted from `docs/sources/`, traced and published, but none of its
builds (b) to (j) is on the default branch, and rule 27 orders the estimator, the status, the baseline and the ceremonies
(e) to (h) before `publish` (i). SPEC-0037 rule 15 as amendment 161 proposes it (approved on #1057, ADR-0446) imports a
customer's prototype unchanged as `docs/design/imported/i<n>/` with a map of every page to a screen and state of the
inventory, and its import, map check and sign-off are built (ADR-0448, ADR-0449). Nothing turns that imported version
into a source: no source location can cite one of its screens, and no rule asks for the states it does not show.

## Decision

1. `design.py source --version i<n> --slug <slug>` writes once `docs/sources/<slug>-prototype-i<n>.md`, a `Kind: design`
   source with rule 1's header and one `## <screen>/<state>` heading per mapped row, under it the page's visible text read
   from its HTML as text, or `picture: <file>` for a picture page; it refuses a version whose import or map check fails
   and never runs or opens a page (amendment 163 item 2, a new SPEC-0043 rule 2a).
2. SPEC-0037 rule 13 gains one exception, that file under `docs/sources/` only, which SPEC-0043 rule 3's guard scans before
   any agent reads it (item 3).
3. Each heading of a `Kind: design` source is one in-scope source location of rule 11's coverage, so `<a> of <b>` proves
   that every mapped screen and state has a requirement (item 4).
4. The skill lists, for each screen of such a source, the inventory's `yes` states that no heading covers, each one
   `scope.open_questions` item with `(verify)`; `render` prints them under `Open questions for the person`. Nothing is
   invented (item 5).
5. The plan path runs in this order: (b) the sources; then (c) the draft, (d) the trace and coverage and (k) the prototype
   source in parallel; then (i) `publish`, `Depends-on` (c) only; then (j) the guide. Builds (e) to (h) stay specified,
   run later and are not needed for `publish`; a milestone's `Target:` stays the person's date or `(verify)` (item 6).

## Consequences

A person with an imported, mapped prototype gets a drafted plan, traced to each screen and state, with the missing
states asked as open questions and its milestones and briefs printed as `gh api` commands, before any estimator exists.
Until (e) to (h) merge, a plan has no calibrated range, status, baseline or scope-change control. This pull request
changes documents only: no code, no test, no workflow and no protected path class. Each build of item 6 writes its own
ADR naming the protected classes it changes, after the owner's `Approve: <head> SPEC-0043` and
`Approve: <head> SPEC-0037` on this pull request.

## Residual

- 2026-11-12: the source file carries a customer's visible text out of `docs/design/imported/`; the guard finds secrets
  and personal data by pattern only, so the rest is the person's call before the plan is drafted (due 2026-12-31).
- 2026-11-12: a state that neither the inventory nor the prototype names is not asked (due 2026-12-31).
- 2026-11-12: the slug, the message elements, the asked states and (d)'s order are the owner's (`Q-1073-1` to
  `Q-1073-4`) (due 2026-11-30).
