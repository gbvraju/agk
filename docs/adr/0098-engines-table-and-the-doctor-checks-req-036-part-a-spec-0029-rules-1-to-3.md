# ADR-0098: the engines table and the doctor checks (REQ-036 part a, SPEC-0029 rules 1 to 3)

- Status: Proposed
- Date: 2026-10-24
- Deciders: maintainers
- Related: ADR-0097, ADR-0096
- Requirements: REQ-036

Protected classes: `kit/`, `scripts/agk/`, `skills/`, `tests/kit/`

## Context

SPEC-0029 (Approved, #166) is lane C of the conductor plan (issue #164). Its build is measured first and split: (a) engines and doctor (rules 1 to 3), (b) vision and stack, (c) design. This is (a). The tests were
written first (`tests/kit/test_engines.py`; on unchanged `main`: 16 failed, 1 passed, the one being the existing protected-path check of `agk.toml`).

## Decision

1. **The table** (rule 1): `[engines]` in `agk.toml`, keys `vision`, `stack`, `design` and `review`, each the name of a skill or absent. No value is pinned: `kit/templates/agk.toml` holds a commented example only, and this
   repository's `agk.toml` is unchanged. The change of the table is the change of `agk.toml`, which is already a protected path, so the existing protected-path check requires an ADR naming it; no new check.
2. **Doctor** (rule 2): five checks at the end of the report, all `warn`: `engines-keys` (the table has only the four keys) and `engine-vision`, `engine-stack`, `engine-design`, `engine-review`. An engine is `present`
   (`.claude/skills/<name>/SKILL.md` of the project, `~/.claude/skills/<name>/SKILL.md` of the user, as ruled on Q-K4-257, or `skills/<name>/SKILL.md` of the plugin exists; only the existence of the file is tested), `absent` (the key is not set; the kit's template is used, and the check is ok) or `missing` (named, not found: a
   failure). A value that is not a name of lower-case letters, digits and hyphens is `invalid`. A name of another plugin (`other:name`), or any name with no `--kit-root`, reads `cannot-check` (`plugin-unreadable`,
   `no-kit-root`), never `ok`. Messages name the setting (`engines.vision`), never the skill's name or the key outside the four. Doctor remains read-only, with no network and no model.
3. **The engine's place** (rule 3): stated in the new section "Engines" of `docs/guides/reference.md`, in `skills/doctor/SKILL.md` and in the commented example of the template. Nothing enforces it beyond the existing
   checks: an engine writes through the kit's template, and its output passes the checks every file passes.
4. **Tests** (`tests/kit/test_engines.py`, new, not installed): absent, present (project and plugin), missing (four keys), no kit root, another plugin's skill, four invalid values, an extra key, the order of the report,
   a read-only run, the protected-path check with and without an ADR, the guide section, and that no engine is pinned in `agk.toml`, the template, the adopt template, the manifest or the plugin. `test_doctor.py` counts
   the checks: 22 becomes 27.
5. **No version bump** (flow mode, SPEC-0028): a line under `## Unreleased` of `CHANGELOG.md`, and `kit/hashes.json` refreshed.

## Consequences

- An owner can name an engine and see whether the session finds it; nothing consumes the names yet (parts b and c).
- `doctor.py` is installed verbatim, so a project gets the checks on its next upgrade; a project without an `[engines]` table sees five `ok` lines with `absent`.

## Residual

- 2026-10-24: another plugin's skills are not read, so such an engine reads unchecked; how Claude Code lists plugin skills is not confirmed (verify) (due 2026-12-31).
