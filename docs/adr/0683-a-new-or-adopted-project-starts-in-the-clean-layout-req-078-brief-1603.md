# ADR-0683: A new or adopted project starts in the clean layout, held by the rehearsal's proof

- Status: Proposed
- Date: 2026-11-20
- Deciders: maintainers
- Related: brief #1603, SPEC-0071, ADR-0614, ADR-0617, ADR-0679, plan #661, amendment 211
- Requirements: REQ-078

## Context

SPEC-0071 (Approved) rule 2 says `[kit] layout = "plugin"` is "written only by the migration of rule 8". So `init.py`
installs the kit's files into a new product and `adopt.py` into an existing one before `upgrade.py --clean-repo` can
remove them, and rule 9 keeps them in the product's history until the printed clean-up, which only the repository owner
runs. Read on main at deae41f5 (2026-11-20): neither script has a layout option, and `rehearsal.py check` reports the
proof of rule 11 as not held.

## Decision

1. `init.py` and `adopt.py` take `--layout plugin [--rehearsal]`. With it they write only the files the migration of
   rule 8 leaves: every file the kit renders for the project (its records and settings, from `kit/templates/`), and of
   the manifest's kit files only `upgrade.py`'s `CLEAN_KEPT` (`.gitignore`, `LICENSE-AGK`, the issue and pull request
   templates under `.github/`). No kit script, hook, agent, workflow, playbook or guide is written. `CLAUDE.md` is the
   short file of `kit/templates/clean-claude.md` (adopt appends it as its marked block, as it does today), and
   `agk.toml` gets `execution = "local"` and `[kit] layout = "plugin"` with `plugin_version` at the plugin's
   `kit_version` (rule 6).
2. The refusals are the migration's, before any write, naming the setting or the proof and never a value: a `[personal]`
   table in TARGET's `agk.toml` (setting `forge`), an `execution` other than `local` there (setting `execution`), and,
   until `rehearsal.proof_held` is true, any run without `--rehearsal` (the proof of rule 11). `--layout` takes only
   `plugin`; `--rehearsal` alone is a usage error.
3. Without `--layout`, init and adopt behave exactly as before.
4. Amendment 211 proposes the rule 2 text for the owner's approval: the layout is written by the migration of rule 8, or
   by `init` and `adopt` with `--layout plugin`. The code follows that reading and is unreachable for a customer project
   until the proof holds.
5. The steward's offer at setup (brief answer 3) is not built here: the brief's `Touches:` does not name `steward.py`
   (`Q-1603-1`).

Protected path classes changed: `scripts/agk/` (`init.py`, `adopt.py`), `tests/kit/` (`test_clean_init.py`), `skills/`
(`init/SKILL.md`) and `agk.toml` (the `[testing]` map entries of `init.py`, `adopt.py` and `rehearsal.py`).

## Consequences

Once the rehearsal's figures are accepted, a new or adopted project can begin clean, so no kit file ever enters its
history and rule 9's clean-up has nothing to remove. The kept file list now lives in three scripts (`upgrade.py`,
`doctor.py`, `init.py`); a test keeps `init.py`'s equal to the others. Writing `execution = "local"` is part of choosing
the layout, since rule 5 allows it nowhere else.

## Residual

- 2026-11-20: the code reads rule 2 as amendment 211 proposes before the approval; if the owner rejects it, a later
  brief removes `--layout` from init and adopt (due 2027-03-31).
- 2026-11-20: the steward's offer of the clean start (brief answer 3) waits for its own brief (due 2027-01-31).
