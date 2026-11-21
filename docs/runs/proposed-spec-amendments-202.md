# Proposed spec amendments 202 (SPEC-0072; REQ-079)

Date: 2026-11-21 (from `date -u`). Approved specs change only through a proposal like this one (principle 6). Written for
ADR-0674 (brief #1594), which stays `Proposed` for the maintainers' decision. The path:
`docs/specs/0072-each-work-type-playbook-carries-its-architecture-a-stack-sta.md` (rule 4 and the `## Tests` section).
Brief #1594 reserved amendment 202. This file proposes the lines and does not edit the spec. They are applied word for
word, on a person's `Approve: SPEC-0072`; no session posts it.

## Why

Rule 4 lists what the foundation writes and names no environment file, example settings, startup check, safe log,
health address, README or deploy step, and "deployable" is not defined (brief #1594, gaps G22 and G24).

## Items

1. **Rule 4, two sentences added at its end.**

   ```
   The foundation also writes each product's basics with `basics.py write` (brief #1594, ADR-0674), by
   `[delivery] work_type` (a web app and an API service a server, a data pipeline a report job) and for a chosen Python
   stack first, never over an existing file: the `.env` line of `.gitignore`, `.env.example` with names and
   placeholders only, a startup check that refuses to start naming a setting that is not set, a request or run log line
   with its id and no personal value (users see a plain message), a health address that answers ok while the app and
   its database are up (servers only; a report job exits non-zero on a failed run), `README.md` (what it is, one run
   command, the test command) and `docs/deploy.md` (where it runs, `local only` until a hosting option is chosen, and
   the written steps); with `mode = "adopt"` each missing part is proposed as one plain question and nothing is
   written. The first milestone ends with one working slice, one screen, address or job working end to end in the local
   profile with `docs/deploy.md` written: `plan-intake` proposes it as a `Kind: slice` brief after the foundation,
   `check_plan.py` refuses a foundation milestone without one, and a deploy is the person's own act, with no workflow
   or hosting setting changed.
   ```

2. **`## Tests`,** one line after the `Rule 4, the pins` line:

   ```
   - Rule 4, the basics: `tests/kit/test_skeleton_basics.py` on a sample web app, API service and report tool (the
     environment file ignored, a names-only example, a missing setting refused by name, an e-mail address left out of
     the log, the health address answering, the README's command running, an adopted sample proposed to and untouched,
     a plan with no slice brief refused); REQ-079 AC3.
   ```

3. **Unchanged:** rules 1 to 3 and 5 to 13, the Proof, the Residual and the Open questions.

## Questions (brief #1594), each with the reading this proposal takes

- Q-1594-1 (the brief's Q-1): the `.env` line goes into every project's ignore file, including existing ones on upgrade,
  as the marked block of `kit/templates/gitignore`; a tracked `.env` is named and never removed (as recommended).
- Q-1594-2 (the brief's Q-2): where the person has not said, `docs/deploy.md` says `local only` and names choosing a
  hosting option as the next step (as recommended); the stack record holds no hosting option yet.
- Q-1594-3: the brief maps three shapes to work types only by name ("web app", "API service", "data/report tool").
  Reading: `web-app`, `api-service` and `data-pipeline`; every other work type is said plainly and waits for its pack.
