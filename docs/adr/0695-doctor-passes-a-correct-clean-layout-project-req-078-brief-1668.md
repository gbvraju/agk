# ADR-0695: doctor passes a correct clean-layout project

- Status: Proposed
- Date: 2026-11-21
- Deciders: maintainers
- Related: ADR-0613, ADR-0616, ADR-0683, SPEC-0071, brief #1668, plan #661
- Requirements: REQ-078

## Context

A project started or adopted with `--layout plugin` (ADR-0683) keeps only the files SPEC-0071 rule 2 names, but
`scripts/agk/doctor.py` compared it as an installed project: a fresh clean init and an adopted one each gave
`summary: 32 ok, 3 fail, 20 cannot-check`. `drift-workflow-file` failed on the absent `.github/workflows/drift-audit.yml`,
`vendored-missing` listed every manifest file the layout never writes, and `vendored-differs` failed the short
`CLAUDE.md`. `CLEAN_KEEPS` and `CLEAN_KEEPS_UNDER` already named the kept files, for the `kit-in-repository` warning only
(ADR-0616).

## Decision

1. A new doctor line `layout` (error): `ok (layout: installed)` when `[kit] layout` is absent or `installed`,
   `ok (layout: plugin)` for `plugin`, and a fail naming the setting `layout`, never the value, for any other value. With
   another value every other check runs as for the installed layout.
2. With `[kit] layout = "plugin"`, `drift-workflow-file` is `ok ... or is absent (layout: plugin)` when the file is
   absent (the drift audit runs from the plugin or not at all); a present file is checked as before and fails without a
   scheduled cron. The installed layout fails on an absent file as before.
3. With `[kit] layout = "plugin"`, `vendored-missing` and `vendored-differs` compare only the manifest files of
   `CLEAN_KEEPS` and `CLEAN_KEEPS_UNDER`, each as today (adopt's `.gitignore` inside its block). `CLAUDE.md` is compared
   to `kit/templates/clean-claude.md` with `{{kit_version}}` as the installed version and `{{project}}` as any one-line
   name: for init, and for adopt with no markers, the file starts with it, so the project's own rules may follow, as
   the template asks; for adopt with markers, the block is exactly it. A missing one is `vendored-missing`.
4. Doctor's kept list stays equal to `upgrade.py`'s `CLEAN_KEPT` and `init.py`'s, less `agk.toml`, by test.
5. Settings: `mode` init and adopt, `execution` local and hosted and `review_mode` solo and team give the same lines;
   `plugin_version` that does not match the running plugin is refused at start by the existing pin line (ADR-0613),
   naming `plugin_version`. Personal mode's checks are unchanged. A kit file planted in a clean project keeps the
   `kit-in-repository` warning.

## Consequences

A correct clean project ends with no `fail` line, and the doctor's check count rises from 55 to 56. Tests:
`tests/kit/test_doctor_clean.py` and `tests/kit/test_doctor.py`. Protected path classes changed: `scripts/agk/`
(`scripts/agk/doctor.py`), `tests/kit/` (`tests/kit/test_doctor_clean.py`, `tests/kit/test_doctor.py`).

## Residual

- 2026-11-21: `.gitattributes`, a file the kit renders for the project, whose block adopt compares in the installed
  layout, is not compared in the clean layout, as the brief's answer 1 names only the kept files.
