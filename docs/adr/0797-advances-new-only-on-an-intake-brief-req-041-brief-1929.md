# ADR-0797: `Advances: new` passes the brief check only on an intake brief (REQ-041)

- Status: Proposed
- Date: 2026-11-25
- Deciders: maintainers (the owner's word, quoted below)
- Related: brief #1929, SPEC-0034 rule 2, SPEC-0012 rules 4 and 11, ADR-0450, ADR-0459, ADR-0714, principle 10
- Requirements: REQ-041

Protected classes: `scripts/agk/`, `tests/kit/`

## Context

SPEC-0034 rule 2 says `Advances: new` is for an intake brief, but `check_brief.py` accepted `new` on any brief.
`check_pr_body.py` requires a REQ id on every pull request (principle 10), so a build brief with `new` passed at filing
and its build could not land: two builders of an adopted project stopped at `FAIL pr-body` after their work was done
(v1 acceptance plan 3, AD-08). An intake build always modifies `docs/requirements.md` (SPEC-0012 rule 11 C2), so its
`Touches:` names that file. The owner's word (2026-11-25, the steward chat, quoted as data): "Yes, file draft briefs 1
to 5 and the first slices of SPEC-0073 and SPEC-0074".

## Decision

1. **`new` only on an intake.** `check_brief.body_problems` fails a brief whose `Advances:` line is `new` and whose
   `Touches:` line does not name `docs/requirements.md` as an exact entry, with `rule 2: Advances: new is only for an
   intake brief, whose Touches names docs/requirements.md (SPEC-0034 rule 2)`. A glob that covers the file (`docs/*`)
   or a longer name (`docs/requirements.md.bak`) does not count. The rule reads no root. `Advances: REQ-n` is unchanged.
2. **Where it bites.** The one function is the reading of `check_brief.py FILE`, `--event` (the `agk-brief` job labels
   such a brief `agk-brief-invalid` on `opened`, `edited` or `labeled`, never by a sweep), `session.py next` through
   `brief_result`, and `steward_owner.py file-brief`, which is refused before it posts anything.
3. No spec text changes: SPEC-0034 rule 2 already says it. `check_pr_body.py` is not changed.

## Consequences

A build brief that names no requirement is refused at filing, not after its build. In a project with no requirement yet
the first product brief waits for an intake (`Q-F2-1`, the conservative reading).

## Residual

An open brief already carrying `new` without the file is labelled only when it is next edited. Recorded 2026-11-25.
