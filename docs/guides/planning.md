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
- The estimator, the milestone status, the baseline with its scope changes and the ceremonies (SPEC-0043 builds (e) to
  (h)) read the project's own history. Until it has enough there is no estimate: the first iterations are
  uncalibrated, and a milestone's `Target:` is your own date or `(verify)`.
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
6. **Render, once.** `python3 scripts/agk/plan_intake.py render --proposals FILE` (the plugin's copy works the same)
   prints the conflicts and then the open questions for you, and writes, as new files only, `docs/plan/scope.md`,
   `docs/plan/milestones.md`, `docs/plan/requirements-proposed.md`, one Draft spec per feature area under `docs/specs/`
   and one brief per brief under `docs/plan/briefs/M<n>/`. From then on these files are yours. The requirements enter
   `docs/requirements.md` through your own intake pull request, and you replace each brief's `Advances:` key with its
   `REQ-n` number. Once they are in, run `python3 "$AGK/scripts/agk/design.py" inventory` once: it keeps every line of
   `docs/design/inventory.md` and adds a section for each new requirement, so you fill only the new `- Screens:` slots,
   which the requirements' `Source:` lines point at; the kit's own requirements already read
   `no screen: a rule of the kit`.
7. **Trace and count.** `python3 scripts/agk/check_plan.py --trace` prints one row per source location: the requirement,
   the spec rule, the brief, the merged pull request (with `--facts FILE` and `--numbers FILE`) and the test, `none` where
   a link is missing. It ends with the coverage line, `ok plan: <a> of <b> in-scope source lines have a requirement, ...`.
   Each heading of a prototype source counts as one in-scope location, so `<a> of <b>` shows every mapped screen and
   state has a requirement. The trace is printed, never committed. The kit's own requirements (REQ-001 to REQ-099 of
   `docs/requirements.md`) have no project source, so the check, the trace and the counts leave them out unless one
   carries a `Source:` line. Each open question and unsettled conflict is also in the `Questions for business` section
   of `docs/plan/scope.md`, with the keys of the requirements and briefs it blocks on its `Blocks:` line, which you may
   edit.
8. **Approve.** On the plan's pull request, an account listed in `spec_approvers` of `config/reviewers.yaml` posts
   `Approve: plan <full head ID>`. A session never posts it; in solo mode it is part of your `Confirmed:` comment.
9. **Publish.** Save the pull request's comments as a file and run
   `python3 scripts/agk/plan_intake.py publish --comments FILE --head SHA [--numbers FILE]`. Without the approval it exits
   2. It prints one `gh api` command per milestone, then per brief in dependency order, and runs none. A brief waits until
   `--numbers` (a JSON object from key to number, which you save from the commands you ran) names its milestone and every
   brief it depends on, so each `Depends-on:` names `#<n>`. Run `publish` again after each round until nothing is
   withheld. Before the briefs it prints one issue command per question of that section, labelled
   `agk-business-question` and never `agk-brief`, and each brief a question blocks waits for its number and then names it
   with `Blocked-by: #<n>`, so `session.py plan` holds it as `waits for question #<n>` until business answers in the
   issue and closes it (ADR-0508). In personal mode it writes the questions and the briefs through the file forge
   instead. Once nothing is withheld, run
   `/agk:board --yes` on your own machine: it makes the plan's GitHub Project board once and adds every brief with its
   milestone, size and expected hours, and each later run adds only the new ones (ADR-0506). Each brief issue shows a
   `Persona: <key> <name>` line, the persona of the requirement it advances, and the board is one business can sign
   off from (ADR-0507):
   - **The template board, made once.** In GitHub, make one Project (your template) with three views: `Sign-off`, a
     board grouped by Status; `Questions`, a table; and `Roadmap`, a roadmap by Milestone. Then put its
     `<owner>/<number>` in `[plan] board_template` of `agk.toml` (or pass `--template OWNER/NUMBER`): each project's
     first `/agk:board --yes` copies it, with its views and columns. Without a template the command creates an empty
     board and prints the three views to make once.
   - **The fields.** The command adds `Persona`, `Requirement` (the `REQ-n` numbers), `Screens` and `Sign-off`
     (Pending, Signed off, Changes asked) when the board lacks them, fills them on each new card from the brief issue
     and sets `Sign-off` to Pending; it never changes a value a person set.
   - **How business signs off.** The business reader opens a card, reads its `What`, `Acceptance`, persona and screens
     in plain words, and sets `Sign-off` to Signed off, or to Changes asked with a comment on the issue. An open
     question is an issue of its own, so it shows in the `Questions` view.
   - **The formal gate.** The board's `Sign-off` is a reading aid, not a record: the plan's gate stays the owner's
     `Approve: plan <full head ID>` line of step 8.

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
   `<a> of <b> scenarios have an acceptance line and <c> a test`: `<c>` counts a scenario whose acceptance line is
   criterion n of a requirement `REQ-nnn` that a test marks `REQ-nnn ACn`, and reads `and a test: not read` without
   `--facts FILE`. With the prototype source it prints, before the coverage line, one `unmatched scenario: <location>`
   line per scenario whose steps name no screen of the map and one `unmatched screen: <screen>` line per screen that no
   scenario names; with `--trace` it also prints one `info plan: scenario <location>: ...` line per scenario, naming the
   screens and states it is matched to. These lines are information, not failures: read each one with the person before
   the plan is confirmed.
7. **Approve and publish.** The approver posts `Approve: plan <full head ID>`, and
   `python3 scripts/agk/plan_intake.py publish --comments FILE --head SHA [--numbers FILE]` prints the commands, as in
   steps 8 and 9 above.

## Sprints and ceremonies

Once the plan has its baseline (`docs/plan/baseline.json`), it runs in iterations of `[plan] iteration_days` working days,
Monday to Friday (10 by default, a whole number from 1 to 30), numbered from 1 from the baseline's date (SPEC-0043 rules 23
and 24). Four commands print the text of each ceremony from the facts (`facts.py --weeks N`); you paste it, post it or save
it under `docs/plan/iterations/<n>/`. AGK runs no meeting, posts nothing and files nothing.

- `python3 scripts/agk/plan_ceremony.py planning --facts FILE` proposes the open briefs for the next iteration, in
  milestone, then `Depends-on`, then priority order, up to the measured capacity (the P50 of briefs closed per past
  iteration), or `capacity unknown` while uncalibrated, with the estimator's forecast. You accept or change the list.
- `python3 scripts/agk/plan_ceremony.py daily --facts FILE --stalls FILE` prints at most ten lines: what finished since
  the previous working day, what is in progress, and what is blocked and why, from a saved `stalls.py --json` output.
- `python3 scripts/agk/plan_ceremony.py review --facts FILE --matches FILE` lists, per milestone touched in the iteration,
  its exit criterion with the merged pull requests, requirements done and proof, or `no evidence yet`; the signed-off
  design version; and each `Demo:` screen and state with the `Design match:` line of a merged pull request and the persona
  whose story it completes. `--matches` is a JSON file you save: pull request number to its `Design match:` lines.
- `python3 scripts/agk/plan_ceremony.py retro --facts FILE --stalls FILE` prints measured facts only (estimates within
  range by size, median waits, rework, stalls by kind) and at most three candidate briefs, printed for you and never filed.

Estimates are ranges from this project's own history, not promises; AGK drafts from the sources and the person owns scope.
The first iterations are uncalibrated, AGK never contacts the customer, and it never reads a source you did not provide.

## When a step refuses

Every refusal names the rule and the file, the item's key or the setting, never a value. Fix the source, the map or the
proposals file and run the step again; never edit a check to make it pass. `docs/guides/reference.md` lists each command
with its options.
