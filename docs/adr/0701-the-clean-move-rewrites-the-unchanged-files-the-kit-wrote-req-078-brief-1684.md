# ADR-0701: The clean-layout move rewrites the unchanged files the kit wrote

- Status: Proposed
- Date: 2026-11-22
- Deciders: maintainers
- Related: brief #1684, SPEC-0071, ADR-0614, ADR-0683, plan #661
- Requirements: REQ-078

## Context

SPEC-0071 (Approved) rule 8 has `upgrade.py --clean-repo` remove the released kit files, write the short `CLAUDE.md`
and the `[kit]` table, and prove that no remaining tracked file names a removed path. Read on main at ad938271
(2026-11-22): a v0.64.8 `init.py` install that the person never changed, set to `execution = "local"`, is refused with
9 files and 52 lines, every one written by the kit itself (`.gitattributes`, `.github/CODEOWNERS`, `LICENSE-AGK`,
`agk.toml`, `config/protected-paths.txt`, `config/reviewers.yaml`, `docs/adr/0001-adopt-agk.md`, `docs/runs/flakes.md`,
`pyproject.toml`). The brief's evidence that a clean `init.py --layout plugin` writes these files in a clean form does
not hold: it writes them byte for byte as the installed init does, so there was no target text to copy (Q-1684-3). The
maintainers' answer to Q-1684-3 (on pull request #1688) set the rule below.

## Decision

1. Each kept file the kit wrote (the templates of the project's `mode`, adopt's `.gitattributes` block and
   `.github/CODEOWNERS`) that equals what this plugin renders for the project, line ends aside, is rewritten line by
   line and listed as `edit <file> (the clean layout's form)`:
   - in a comment or prose line (`#` lines, `docs/runs/flakes.md`) each removed path `P` becomes
     `${CLAUDE_PLUGIN_ROOT}/P`, the form the proof already excepts;
   - an entry line of `.gitattributes` or `.github/CODEOWNERS` that names a removed path is dropped;
   - a removed path leaves a one-line list value (`config/reviewers.yaml` `paths:`, `pyproject.toml` `pythonpath`), and
     a `key = []` left empty is dropped.
   A file with adopt's markers is compared and rewritten inside its block only, so the person's lines around it stay.
   An init install's `.gitattributes` the person added lines to has only the template's own lines rewritten and every
   other line kept; its lines are independent patterns (Q-1684-4).
2. In `agk.toml` only the lines that are the kit's own (lines of the template) are rewritten that way; a line the person
   set is kept and the proof names it (Q-1684-1); the detail names each key dropped (`lint_paths` when every path in it
   is removed).
3. `LICENSE-AGK`, `config/protected-paths.txt` and `docs/adr/0001-adopt-agk.md` keep their text and are excepted from the
   proof, as the plugin's own paths are; a removed path stays protected (Q-1684-3). The move's ADR names them as kept.
4. A changed file, or one the person deleted, is not rewritten: a changed one that names a removed path is still listed
   and refused, and a deleted one is not recreated.
5. The proof and the rewrite read a word as a path through one function that takes off only a leading `./` or `/`. Before,
   `lstrip("./")` also took the dot off `.claude/hooks`, so a line naming a removed dot path passed the proof (#1695). The
   proof is stricter by that (principle 11: changed by this ADR), and `lint_paths` is dropped once every path in it is
   removed.
6. Read as part of rule 8's removal (Q-1684-2): editing these unchanged kit-written files is part of the move; if the
   architect reads rule 8 otherwise, an amendment follows.

Protected path classes changed: `scripts/agk/` (`upgrade.py`), `tests/kit/` (`test_upgrade_clean_repo.py`: the
protected list is now excepted, ruled by Q-1684-3) and `tests/kit_dev/` (`test_upgrade.py`).

## Consequences

An untouched install of a release, in init or adopt mode, now moves to the clean layout with
`proof: no tracked file names a removed kit path`. The proof is narrower by the three record files above, by the
maintainers' answer, and stricter by dot paths (decision 5); both are changes of a check by this ADR (principle 11).

## Residual

- 2026-11-22: `init.py --layout plugin` writes the same kit-written files with the same removed paths; giving the clean
  start the clean form waits for its own brief (due 2027-01-31).
- 2026-11-22: `config/reviewers.yaml` with a real handle in place of the template's placeholder counts as changed, so it
  is listed and refused, not rewritten; the person tidies it (due 2027-01-31, with the brief above).
- 2026-11-22: the rewritten `CODEOWNERS` header names `${CLAUDE_PLUGIN_ROOT}/scripts/agk/reviewers.py`, which
  `reviewers.py --check-codeowners` does not render; the clean project's governance reads it once that check runs from
  the plugin (due 2027-01-31).
