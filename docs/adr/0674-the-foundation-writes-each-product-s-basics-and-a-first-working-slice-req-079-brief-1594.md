# ADR-0674: The foundation writes each product's basics and the first milestone ends with a working slice (REQ-079)

- Status: Proposed
- Date: 2026-11-21
- Deciders: maintainers
- Related: SPEC-0072, SPEC-0041, brief #1594, brief #1587, brief #1593, brief #1597, plan #661, ADR-0667, ADR-0673, amendment 202
- Requirements: REQ-079

Protected classes this pull request changes: `scripts/agk/` (the new `basics.py`, `check_plan.py`, `plan_intake.py`),
`kit/` (the new `kit/templates/skeleton/`, `kit/templates/project-settings-example.txt`,
`kit/templates/project-readme.md` and `kit/templates/deploy.md`; `kit/templates/gitignore`,
`kit/templates/gitattributes` and `kit/manifest.json`), `tests/kit/` (the new `test_skeleton_basics.py`), `skills/`
(`skills/plan-intake/SKILL.md`) and `agk.toml` (`[[testing.map]]` entries). `kit/hashes.json` is not edited by hand.

## Context

SPEC-0072 rule 4 lists what the foundation writes (the folder skeleton, the architecture record, the pack configuration
and the check steps) and names no environment file, no example settings, no startup check, no safe log, no health
address, no README and no deploy step; "deployable" is not defined (brief #1594, gaps G22 and G24). The `secrets` and
`environment-settings` checks of brief #1593 already read `.env.example`.

## Decision

1. The foundation runs `python3 scripts/agk/basics.py write`. By `[delivery] work_type` it picks the shape: `web-app`
   (package `backend/`) and `api-service` (package `api/`) are servers; `data-pipeline` (package `job/`) is a report job.
   The package folders are the playbooks' layer names. Other work types print `not written: basics: no skeleton for
   this work type yet (setting: work_type)` and get theirs with their pack.
2. For a chosen Python stack (the Accepted stack record, as `pins` reads it) it writes from `kit/templates/`, never over
   an existing file: (a) the `.env` line of `.gitignore`, also added to `kit/templates/gitignore` for every project and
   so appended by adopt and upgrade as a marked block (brief `Q-1`, as recommended); (b) `.env.example` from
   `project-settings-example.txt`, names and `<placeholder>`s only, kept LF by `.env.example text eol=lf` in
   `kit/templates/gitattributes`; (c) `<package>/settings.py`, which stops the app naming the first setting of
   `.env.example` that the environment or `.env` does not set, never a value; (d) `<package>/logs.py`, one line per
   request or run with its id, an e-mail address or phone number replaced, no query string, and errors shown to users
   as a plain message with the request id; (e) for servers, `<package>/app.py` with `/health`, ok while the app and its
   database answer, and `python3 -m <package> --check` to ask it once; (f) `README.md` from `project-readme.md`: what
   it is, the one run command for bash and PowerShell after `.env` is filled in, and the test command; (g)
   `docs/deploy.md` from `deploy.md`: `Where it runs: local only` and the written steps. Standard library only, so the
   `pins` step has no new dependency.
3. A report job has no health address: it writes one run line and exits 1 on a failed run, and the README runs it on
   the invented `samples/example.csv`. An API service's `/health` is listed in its contract by the contract brief
   (brief #1597); this build does not edit `contracts/`.
4. "Deployable": the first milestone ends with one working slice (one screen, one address or one job, end to end in the
   local profile, with `docs/deploy.md` written). `plan-intake` proposes it as a brief with `"slice": true`, `render`
   writes `Kind: slice`, and `check_plan.py` refuses, naming `SPEC-0072 rule 4` and the setting, a work-type plan whose
   foundation milestone holds no `Kind: slice` brief. A deploy is the person's own act: the kit writes the steps and
   changes no workflow and no hosting setting.
5. Where the product runs when the person has not said: `local only`, and choosing a hosting option is the next step
   the deploy file names (brief `Q-2`, as recommended). No hosting is chosen silently.
6. `mode = "adopt"`: nothing is written; each missing part is printed as one plain question, for example `Your project
   has no health check. Shall I add one? Yes (recommended) · later`. A tracked `.env` is named as a path class and never
   removed. No work type: `basics: not run`. Personal mode: the files are the product's own and are written only on the
   developer's yes (SPEC-0041); this ADR adds no personal path.
7. SPEC-0072 rule 4 and its `## Tests` gain this by amendment 202, proposed for the spec's approver.

## Consequences

A new web app, API service or report tool starts with its basics written and tested, and its first milestone ends in a
working slice. The kit's own repository declares no work type, so its output is unchanged. No workflow, ruleset,
required check, hosting setting or `agk.mk` changes.

## Residual

- 2026-11-21: other stacks' skeletons (`node` first) and other work types' shapes come with their packs (due 2027-03-31).
- 2026-11-21: the stack record holds no hosting option yet, so `docs/deploy.md` says `local only` until one does.
