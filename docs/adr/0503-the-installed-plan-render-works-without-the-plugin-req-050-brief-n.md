# ADR-0503: The installed plan render works without the plugin

- Status: Accepted
- Date: 2026-11-13
- Deciders: maintainers
- Related: brief #1184, plan #661, SPEC-0043 rule 7
- Requirements: REQ-050

Protected classes: `scripts/agk/`, `tests/kit/`, `tests/kit_dev/`, `kit/`, `agk.toml`

## Context

`docs/guides/planning.md` step 6 tells a person to run `python3 scripts/agk/plan_intake.py render --proposals FILE`,
the copy installed in the project. `render` imports `new_spec.make_spec` from beside itself, and `new_spec.py` was
kit-only: `kit/manifest.json` installed `plan_intake.py` in `verbatim` but not `new_spec.py`. In the co-owner's trial
run of 2026-11-13 (a fresh `init.py --unreleased` project, invented example.com sources) the installed copy printed
`render needs new_spec.py: scripts/agk/new_spec.py` and exited 2; it worked only from the kit checkout. A cloud session
does not load the plugin, so a cloud builder or conductor could not render a plan at all.

## Decision

1. `scripts/agk/new_spec.py` is installed in projects: it is listed in `verbatim` of `kit/manifest.json` and is no
   longer kit-only. It is standard library only and imports no kit module; the templates it reads
   (`docs/specs/TEMPLATE.md`, `docs/adr/TEMPLATE.md`, `docs/briefs/TEMPLATE.md`) are already installed, so nothing
   else is added.
2. The plugin's skills keep running the plugin's own copy against the repository; both copies are the same file.
3. Planning guide step 6 keeps the installed path and says the plugin's copy works the same.
4. `tests/kit/test_plan_render_installed.py` pins it: a fresh project holds `new_spec.py`, and its own
   `plan_intake.py render` on an invented proposals file exits 0 and writes the plan and the Draft spec.

## Consequences

`render` works in every project, in a cloud session or on a laptop, with or without the plugin. A project now also
carries `new_spec.py spec|requirement|brief`, which writes new files only and refuses to overwrite, so nothing that
was refused before is now allowed. `upgrade.py` installs it into existing projects as any other verbatim file.

## Residual

- 2026-11-13: none known; the trial's other steps worked as the guides say.
