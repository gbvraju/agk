# Proposed spec amendments 16 (SPEC-0009; found while building the facts engine)

Date: 2026-10-16 (from `date -u`). Approved specs change only through a proposal like this one (principle 6). Nothing here is
applied. The path: `docs/specs/0009-facts.md`.

## SPEC-0009 (`docs/specs/0009-facts.md`)

1. **Rule 14, "the window is a field `weeks`".** Rule 3 fixes the top-level keys and makes `pull_requests` an array of pull
   requests, so the window has no place in the document (`Q-K4-111` in ADR-0023). Taken in the build: `--weeks` selects the
   window and nothing records it. Options for the maintainers: (a) delete the sentence (a consumer that needs the window
   recomputes it from `today` and the default 8); (b) make `config` carry `weeks` (it then changes rule 7's "no other key is
   copied"); (c) add a sixteenth key (a schema change that raises `schema` to 2).
2. **Rule 7, `inbox_hours`.** The build adds `inbox_hours` (default 48) to `common.DEFAULT_CONFIG`, because `load_config` returns
   only the keys listed there (`Q-K4-110`). Proposed: say so in rule 7 and in rule 17, as a fourth behaviour-preserving change to
   `common.py`.
3. **Rule 5, the missing `agk.toml`.** The build reads "never a default" as: with no `agk.toml` and no `[tool.agk]`, `config`,
   `markers` and `drift` are `"unknown"` (`Q-K4-112`). Proposed: state it in rule 5.
