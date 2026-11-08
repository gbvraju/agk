# ADR-0370: The bill of materials of a commit and its offline check (REQ-061)

- Status: Proposed
- Date: 2026-11-08
- Deciders: maintainers
- Related: ADR-0349, ADR-0326, ADR-0328, SPEC-0054, SPEC-0052, brief #787, plan #661
- Requirements: REQ-061

Protected classes: `scripts/agk/`, `tests/kit/`, `kit/`, `agk.toml`

## Context

SPEC-0054 (Approved) rule 10 lists build (b): the bill of rules 2 to 4 and its check. ADR-0349 was to cover this build
with a `Covered-by:` line, but on the default branch it does not count as Accepted, so the line is refused (`Q-787-1`). The
answer on the brief is that this build writes its own ADR, citing ADR-0349 (session rule 36). This ADR changes no decision
of ADR-0349 or SPEC-0054.

## Decision

1. `scripts/agk/sbom.py make [--ref REF] --out FILE` and `check FILE [--ref REF]` are built as SPEC-0054 rules 2 to 4
   state: CycloneDX 1.6 JSON read from the commit with local `git`, the same bytes for the same commit, standard library
   only, installed with the kit. No governance step, `make governance` or `prepush.py` runs it.
2. The protected classes changed: `scripts/agk/` (`sbom.py`), `tests/kit/` (`test_sbom.py`), `kit/` (the script's entry
   in `kit/manifest.json`) and `agk.toml` (its one `[[testing.map]]` entry). `kit/hashes.json` and the version stay the
   release's (session rule 14).
3. Where the spec leaves a form open, the build reads it as follows. An action's `version` is its release tag comment
   and its SHA is in the package URL, or the SHA is the version when there is no comment. An unpinned component has no
   package URL, since the spec's forms all hold a version. A `scanner` is any `<NAME>_VERSION` stated with its
   `<NAME>_SHA256` in a workflow, whichever comes first. Python and CI tool names are normalized as package URLs need. The `kit-file`
   components are the files `kit_hashes.py` lists as written by an installer, templates by their source path. A
   repository with no `pyproject.toml` or `[project] name` is refused, because rule 2 refuses a file that cannot be read
   and only `kit/manifest.json` is conditional there.

## Consequences

Any commit can produce a bill, and a bill can be checked offline against its commit. Nothing runs it automatically, so a
release has no bill until build (e), and nothing scans the components until build (d).

## Residual

- 2026-11-08: CycloneDX 1.7 is the newest version (21 October 2025) and the bill stays at 1.6 as `Q-S0054-1` and ADR-0349
  rule; moving is a change to that spec for the maintainers (due 2027-01-31).
- 2026-11-08: an adopted repository without `pyproject.toml` cannot make a bill; whether it should list no `python`
  components and take its name from elsewhere is a point for the maintainers (due 2027-01-31).
