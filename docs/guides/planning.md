# Planning: from a prototype and documents to an approved plan in GitHub

This page shows how a project's own documents and a customer's prototype become a plan: a scope, milestones,
requirements, one Draft spec per feature area and one brief per piece of work, every line traced to the place in a source
it came from, and then, after your approval, milestones and brief issues in GitHub. It follows SPEC-0043 (REQ-050) with
amendment 163 and SPEC-0037 rule 15 (REQ-044). One recorded walk on an invented project runs every step below end to end:
`docs/runs/plan-walk-2026-11-12.md` (brief #1079, ADR-0460).

## Honest limits

Read these first.

- Estimates are ranges from this project's own history, not promises; AGK drafts from the sources and the person owns
  scope. AGK proposes; you decide what is in and out, and every file it renders is yours to edit.
- There is no estimate on this path yet. The estimator, the milestone status, the baseline with its scope changes and the
  ceremonies (SPEC-0043 builds (e) to (h)) are specified but not built, so a milestone's `Target:` is your own date or
  `(verify)`, and the first iterations, once the estimator exists, are uncalibrated until the project has its own history.
- AGK never contacts the customer, and it never reads a source the person did not provide. Never forward a source AGK
  should not read: you choose which documents and which prototype folder go into the repository, and you clean them first.
  The data guard finds secrets and personal data by pattern only, so what it cannot tell from invented text is your call.
- No command here creates anything on GitHub. `publish` prints `gh api` commands; you run them with your own `gh`.

## The path

Run each command from the repository root. `$AGK` is the plugin root (`${CLAUDE_PLUGIN_ROOT}` in a session) or the kit
checkout; the other scripts are installed under `scripts/agk/`.

1. **Import the prototype** (SPEC-0037 rule 15). `/agk:design import <folder>` runs
   `python3 "$AGK/scripts/agk/design.py" import <folder>`, which copies the customer's prototype byte for byte into the next
   imported version `docs/design/imported/i<n>/` with its manifest, and opens no page. You write (the skill drafts)
   `docs/design/imported/i<n>/map.md`: one row per page, `<file> -> <screen>/<state>` with a screen and state of
   `docs/design/inventory.md`, or `<file> -> out: <reason>`. Every state the inventory marks `yes` must be covered by a
   row or a kit version.
2. **Turn the prototype into a source** (SPEC-0043 rule 2a).
   `python3 scripts/agk/design_import.py source --version i<n> --slug <slug>` writes once
   `docs/sources/<slug>-prototype-i<n>.md`: a `Kind: design` source with one `## <screen>/<state>` heading per mapped row
   and under it the page's visible text (all text outside `script`, `style` and `template` elements, in document order,
   with the names and placeholders of fields), or `picture: <file>` for a picture page. It refuses a version whose import
   or map check fails, and an existing file. Read the file before anything else reads it: it carries the customer's text.
3. **Add your documents** under `docs/sources/`, one Markdown or text file each, converted and cleaned by you, each
   starting with `Source:`, `Kind:` (`sow`, `brd`, `prd`, `design`, `charter`, `openspec` or `other`), `Version:` and `Date:` and a
   blank line (rule 1). `python3 scripts/agk/check_plan.py` checks the headers and prints `ok plan (no plan)` while there
   is no `docs/plan/`.
4. **Draft the proposals.** `/agk:plan-intake <path outside docs/>` first runs `python3 scripts/agk/plan_intake.py states`:
   the data guard scans every source before any line is read (exit 2 when the guard is not installed, exit 1 on a finding,
   naming the file, the kind and the place, never the text), and each line it prints is a state the inventory gives as
   `yes` that the prototype source does not show, which becomes an open question. The skill then reads the sources and
   writes one proposals file: scope, milestones, requirements, feature areas, briefs and conflicts, every item citing a
   location (`<file>:<line>` or `<file>#<heading>`). A point no source settles is an open question marked `(verify)`,
   never a made-up value.
5. **Validate.** `python3 scripts/agk/plan_intake.py validate --proposals FILE` prints `ok proposals` or one line per
   problem, naming the rule and the item's key, never its text. A size, a range or a date that no cited location states
   is refused as an open question.
6. **Render, once.** `python3 scripts/agk/plan_intake.py render --proposals FILE` prints the conflicts and then the open
   questions for you, and writes, as new files only, `docs/plan/scope.md`, `docs/plan/milestones.md`,
   `docs/plan/requirements-proposed.md`, one Draft spec per feature area under `docs/specs/` and one brief per brief under
   `docs/plan/briefs/M<n>/`. From then on these files are yours. The requirements enter `docs/requirements.md` through
   your own intake pull request, and you replace each brief's `Advances:` key with its `REQ-n` number.
7. **Trace and count.** `python3 scripts/agk/check_plan.py --trace` prints one row per source location: the requirement,
   the spec rule, the brief, the merged pull request (with `--facts FILE` and `--numbers FILE`) and the test, `none` where
   a link is missing. It ends with the coverage line, `ok plan: <a> of <b> in-scope source lines have a requirement, ...`.
   Each heading of a prototype source counts as one in-scope location, so `<a> of <b>` shows every mapped screen and
   state has a requirement. The trace is printed, never committed.
8. **Approve.** On the plan's pull request, an account listed in `spec_approvers` of `config/reviewers.yaml` posts
   `Approve: plan <full head ID>`. A session never posts it; in solo mode it is part of your `Confirmed:` comment.
9. **Publish.** Save the pull request's comments as a file and run
   `python3 scripts/agk/plan_intake.py publish --comments FILE --head SHA [--numbers FILE]`. Without the approval it exits
   2. It prints one `gh api` command per milestone, then per brief in dependency order, and runs none. A brief waits until
   `--numbers` (a JSON object from key to number, which you save from the commands you ran) names its milestone and every
   brief it depends on, so each `Depends-on:` names `#<n>`. Run `publish` again after each round until nothing is
   withheld. In personal mode it writes the briefs through the file forge instead.

## From a prototype and an OpenSpec file

When the customer gives a click-through prototype and an OpenSpec functional file (capabilities, each `Requirement:` with
its `SHALL` text and each `Scenario:` with its `GIVEN`, `WHEN`, `THEN` and `AND` steps, in one Markdown file or as an
`openspec/` folder with `specs/` and `changes/`), the file's own requirements and scenarios become the plan's, read by a
script and never rewritten by a model (SPEC-0043 amendment 166, ADR-0472, ADR-0473, ADR-0474).

A customer's file is processed only where the customer's contract allows it, and never enters the kit's repository. It
goes into the customer project's own `docs/sources/` (in personal mode, the private state), and every example and test of
the kit uses invented files only.

1. **Import the prototype** with `/agk:design import <folder>`, write its map, and turn it into a source with
   `python3 scripts/agk/design_import.py source --version i<n> --slug <slug>`, as in steps 1 and 2 above.
2. **Import the OpenSpec file.** `python3 scripts/agk/plan_intake.py openspec-import <file or folder> --slug <slug>`
   runs the data guard over every file first, then copies each one unchanged under its `Kind: openspec` header into
   `docs/sources/openspec-<slug>/`, never over an existing folder.
3. **Read it.** `python3 scripts/agk/plan_intake.py openspec --slug <slug> --out FILE` (with `FILE` outside `docs/`)
   writes the partial proposals file: one area per capability, one requirement per `Requirement:` heading with its text
   exactly, one acceptance line per scenario ending with its location, persona candidates, and an open question for each
   point the file leaves open, such as a requirement without a scenario or an open change.
4. **Complete the draft.** `/agk:plan-intake <FILE>` starts from that file and adds only milestones, briefs, sizes and
   screens; it never rewrites a requirement the file defines.
5. **Validate and render** with `python3 scripts/agk/plan_intake.py validate --proposals FILE` and
   `python3 scripts/agk/plan_intake.py render --proposals FILE`, as in steps 5 and 6 above.
6. **Trace and count.** `python3 scripts/agk/check_plan.py --trace` adds, after the first count of the coverage line,
   `<a> of <b> scenarios have an acceptance line and <c> a test`. With the prototype source it also prints one
   `info plan: scenario <location>: ...` line per scenario, naming the screens and states whose screen its steps name, or
   `names no screen`, and one `info plan: screen <location>: no scenario names it` line per screen no scenario names.
   These lines are information, not failures: read each one with the person before the plan is confirmed.
7. **Approve and publish.** The approver posts `Approve: plan <full head ID>`, and
   `python3 scripts/agk/plan_intake.py publish --comments FILE --head SHA [--numbers FILE]` prints the commands, as in
   steps 8 and 9 above.

## When a step refuses

Every refusal names the rule and the file, the item's key or the setting, never a value. Fix the source, the map or the
proposals file and run the step again; never edit a check to make it pass. `docs/guides/reference.md` lists each command
with its options.
