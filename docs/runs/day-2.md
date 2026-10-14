# Run report: day 2 (PR #5, spec for agk init)

Date: 2026-10-14 (from `date -u`). Docs only: `docs/specs/0001-agk-init.md` and this file.

## Decisions taken (each is a numbered rule in the spec)

- Manifest plus templates, not a copied `kit/` tree: the verbatim set points at the kit's own files, so law and tests
  cannot diverge; only project-specific text is duplicated (rules 6–9).
- Init writes nothing until every conflict check has passed; it never overwrites; equal files are unchanged (rules 15–17).
- Dates: first run from the UTC clock, later runs read `[tool.agk] installed`, so a second run is byte-identical (rule 14).
- `tests/kit/` is installed so `make test` is green in the target (rule 18).
- Init does not need git in TARGET, never calls git or gh, and refuses under Python 3.11 (rules 3–4).
- Seeded REQ-001..003 are `planned`; init marks nothing done (rule 11).

## Questions (continuing from Q-K1-1..4, all closed)

- Q-K1-5: the placeholder team `@REPLACE-ME`. A check that fails while it is present breaks REQ-009 AC2 ("governance
  green after init"). Options: (a) warn only (spec default); (b) `reviewers.py --check` warns and a separate
  `--strict` fails, run by the target's CI on `main` but not on the first PR; (c) fail, and make AC2 read "green after
  the placeholder is replaced". Recommendation: (b).
- Q-K1-6: marker namespace. Installed `tests/kit/` carries markers `REQ-001`..`REQ-012`, so a project requirement with
  one of those ids would count as traced. Options: reserve `REQ-001..099` for kit-defined ids and start project ids
  at `REQ-101` (spec default); or add an ignore list to `find_markers`. Recommendation: the reservation.
- Q-K1-7: is `kit/` (manifest, templates) a protected path and part of the `kit` reviewer class? Recommendation: yes;
  the implementation PR then carries ADR-0004 naming it.
- Q-K1-8: initial statuses: ADR-0001 as `Proposed` and REQ-001..003 as `planned`, so maintainers decide. Alternative:
  `Accepted` and `in-progress`. Recommendation: the spec's conservative choice.
- Q-K1-9: refusal scope. A target that already has `pyproject.toml`, `Makefile`, `CLAUDE.md` or `.gitignore` cannot
  be initialised in K1 even if only the stamp is missing; K2 `adopt` merges. Accept as a K1 limit, or add a
  `.gitignore` append mode now? Recommendation: accept.
- Q-K1-10: the verbatim `governance.yml` carries action major tags and gitleaks-action (licence terms for
  organisations were marked (verify) in ADR-0003's residual). Installed repositories inherit that residual. Accept
  until the K1-exit SHA pinning?

## Verified

- Docs only; `make governance`, `make test` and `ruff check .` results are in the PR body.
