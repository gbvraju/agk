# ADR-0786: The uninstall knows every setting the kit reads, and removes reviewers.yaml only when the kit wrote it (REQ-009)

- Status: Proposed
- Date: 2026-11-24
- Deciders: maintainers (the owner's word, quoted below)
- Related: brief #1892, ADR-0203 (the uninstall, whose rule 4 this redefines), ADR-0604 (the lines left), ADR-0615 (the
  clean uninstall, unchanged), ADR-0527 (`TABLE_KEYS` and misplaced settings), ADR-0669 (`project_lint_paths`), ADR-0773
  (`touched_files`), ADR-0764 (the history scan's record under `config/agk-baseline/`), plan #661
- Requirements: REQ-009

Protected classes: `scripts/agk/`, `tests/kit_dev/`, `agk.toml`

## Context

Test plan 3 (AD-10 of comment 7120904046 on #1771) ran `uninstall.py . --write` on an adopted web project and the uninstall
kept two files the kit wrote. `agk.toml` was reported to hold "settings the kit does not read: project_lint_paths",
although `config.project_lint_paths` reads it (ADR-0669); `config/reviewers.yaml` "differs from every released copy",
although it was the adopt template with `@REPLACE-ME` replaced by the person's login, as `init.apply_setup` writes it.
`config/agk-baseline/` was not named at all. ADR-0203 rule 4 built the list of the settings the kit reads from
`DEFAULT_CONFIG`, five extra names and the `key =` lines of the two agk.toml templates, so a setting that no template
writes as `key =` was foreign: an AST scan of the 63 `config_source(...)` reads found 11 names missing (`project_lint_paths`,
`rule_tags_from`, `personal`, `proof`, `capacity`, `caps`, `failures`, `scorecard`, `checklist`, `cost`, `tidy`). The same
parse counted table keys (`queue`, `strongest`, `auto_merge`) as top-level names. The owner's word (2026-11-24, the steward
chat, quoted as data): "Yes, draft the test briefs and post the runs".

## Decision

1. **One list.** `config.py` holds `TOP_KEYS` (the top-level keys a reader takes that `DEFAULT_CONFIG` lacks),
   `OTHER_TABLES` (the tables read by name with no `TABLE_KEYS` row) and
   `KIT_SETTINGS = DEFAULT_CONFIG | TOP_KEYS | TABLE_KEYS | OTHER_TABLES`, each name with its reader in a comment. It
   replaces ADR-0203 rule 4's definition of "a setting the kit reads": `uninstall.kit_settings` returns it, and the
   template parse and `MORE_SETTINGS` go, so a template's comment no longer decides (`Q-UL-1`).
2. **Keys inside a known table.** In a table with a key set (`TABLE_KEYS` and `[personal]`'s `common.PERSONAL_KEYS`) a key
   outside the set is the person's own; other tables are judged by name. A table key standing at the top level (misplaced,
   ADR-0527) is the person's own too (`Q-UL-2`).
3. **agk.toml with the person's own keys** is kept, never edited, and named by key only: `changed agk.toml (path class
   agk.toml: settings the kit does not read: <name>, <table>.<key>; kept for you to decide)`, never a value. With only kit
   names it is deleted as before; a changed value of a kit setting is still the kit's setting, and no reader runs.
4. **reviewers.yaml.** `config/reviewers.yaml` is an unchanged kit file also when its `teams.maintainers.github_team` is
   one `@<handle>` and the text with every occurrence of that handle put back to `@REPLACE-ME` has the digest of a
   released template of the file (ADR-0203 rule 3's match). Anything else (a second approver, an edited class, a handle
   that also appears in a comment, a file `reviewers.parse` refuses) is kept as before (`Q-UL-3`). `.github/CODEOWNERS` is
   decided as before, from the file as it stands.
5. **config/agk-baseline/** is named once, `kept config/agk-baseline/ (path class config/agk-baseline/: ...)`, when it
   holds a file, and nothing in it is deleted: it holds the project's own counts and the history scan's record (`Q-UL-4`).
6. **The guard.** `tests/kit_dev/test_uninstall_settings.py` walks `scripts/agk/**/*.py` and fails naming any literal or
   module-constant name read from `config_source(...)` that `KIT_SETTINGS` lacks, and checks every top-level key and table
   of both templates against it, so a new setting cannot be missed again. It is listed in this repository's `agk.toml`
   map entries of `scripts/agk/uninstall.py` and `scripts/agk/config.py`.

SPEC-0071 rule 9 and REQ-078 are unchanged; `upgrade.clean_plan`, which classifies verbatim kit files only, is unchanged.

## Consequences

An uninstall of a project that holds only the kit's settings and a reviewers file the kit wrote leaves neither, and says
why it leaves `config/agk-baseline/`. A reader that takes a name through a helper the walk cannot follow (the lock's
`settings`, the guard's table) is listed by hand, as `lock_dir`, `lock_stale_minutes`, `guard` and `engines` are. One
existing assertion of `tests/kit_dev/test_uninstall.py` that expected a rendered reviewers file to be kept now expects
it deleted.

## Residual

- 2026-11-24: the leaked-secret runbook that a clean project lacks (`Q-UL-5`) and the leftovers scan of ignored files
  (`Q-UL-6`) are separate briefs.
- 2026-11-24: Windows itself is not run; names are compared as text and the folder is printed with `/` (verify).
