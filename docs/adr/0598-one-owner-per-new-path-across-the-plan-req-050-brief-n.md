# ADR-0598: One owner per new path across the plan

- Status: Proposed
- Date: 2026-11-17
- Deciders: maintainers
- Related: brief #1425, ADR-0189, ADR-0529, ADR-0548
- Requirements: REQ-050

Protected classes: `scripts/agk/`, `tests/kit/`

## Context

An adopted project filed its access-control briefs in batches whose folders were numbered by a counter local to the
batch (`gaps1`, `gaps2`), so a later milestone's batch reused the names of an earlier one. `touch_problems` refused an
`Adds:` entry only when it named a file of the default branch, and `file_conflict` held a brief back only from an open
pull request that adds the exact path, so two waiting briefs adding one folder were both offered and the clash showed
only when the second was built. A suggested fix repeated a name a running brief already used, and two `Adds:` lines
were refused without naming either line or the merge.

## Decision

1. A path a brief adds belongs to one brief from filing until it merges or closes. `plan_names.py` compares an `Adds:`
   entry with the default branch's tree, the `Adds:` of every other open brief (parked and taken ones included) and the
   files every open pull request adds; an exact or covering match (a folder against a file under it either way, a glob
   against a path it matches) is a clash. A match with another brief's `Touches:` alone is no clash: the plan orders
   them as before.
2. Paths compare after normalising `./`, a trailing `/` or `/**`, backslashes and repeated slashes, ignoring case. A
   Windows reserved name (`CON`, `PRN`, `AUX`, `NUL`, `COM1`-`COM9`, `LPT1`-`LPT9`) and a path over 200 characters are
   refused. The files every build adds by rule (`changelog.d/brief-<n>.md`, ADR and spec files, `docs/runs/decisions/`)
   are left out.
3. `check_brief.py --root` refuses a clashing entry, naming the holder and a free name, reading the open briefs from
   `--open-briefs FILE` or the plan's read cache and never by a request; `--number N` (the issue in `--event`) leaves
   the brief itself out. Two `Adds:`, `Touches:`, `Reserved:` or `Expected:` lines are refused naming both lines and
   the one line to use.
4. `session.py plan` lists two open briefs whose `Adds:` already clash as `CLASH: #a and #b both add <path>; rename in
   the one not taken (#n, free: <name>)` and starts neither while it stands; a taken one keeps running. With no clash
   the plan is as before.
5. Free names come from the feature: `plan_names.py next --base` returns the base or the base with `-2`, `-3` and so
   on, absent from all four sources; `batch` names a batch in one pass; `impact` lists every open brief and pull request
   that names a path and who renames it (the steward edits a brief not yet taken; a taken one gets a fix list). The
   convention is `<feature>-m<milestone>-<part>`. Existing briefs are renamed only to end a clash.
6. The CI event check takes the list only when the workflow passes `--open-briefs`, a workflow change for its own brief;
   until then the plan catches a clash at its next run.

## Consequences

A batch filed with `plan_names.py batch` cannot reuse an earlier batch's names, and a clash is caught at filing where
the open briefs are known, or at the next plan run otherwise. The check reads no network: with no saved list and no
cache it compares with the tree alone, as before.

## Residual

- The CI event check compares with the open briefs only once the brief workflow passes `--open-briefs` (decision 6),
  a workflow change for the owner by `/agk:workflow-apply` in its own brief.
- The conductor's fix-list lines and the steward's drafting (the `brief` skill) are prose: they are pointed at
  `plan_names.py` by `docs/guides/planning.md` and by Q-1425-1 and Q-1425-2, not checked by a script here.
