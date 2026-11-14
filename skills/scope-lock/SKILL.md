---
name: scope-lock
description: Write the plan's business scope lock, docs/plan/scope-lock.md, in plain words for readers who are not technical - per milestone the screens it makes work, what a person can do there, its dates and estimated hours; the go-live date; after go-live; not included, with reasons; the decisions; the questions with the date each is needed by; the risks with their answers. Runs the plan check, prints the text of a scope lock issue and creates no issue. Run by the person.
disable-model-invocation: true
argument-hint: "[project name]"
---

# /agk:scope-lock

A plan ends in a scope lock that business can read (brief #1219, ADR-0518, SPEC-0043 amendment 176): what is delivered
at each milestone, by screen and date, what comes after go-live, what is excluded and why, and the questions with their
dates. Run it from the repository root after `plan_intake.py render` has written the plan. It writes one file,
`docs/plan/scope-lock.md`, and commits nothing; the person reads it, edits it and commits it.

1. **Read the plan.** Read only these files:
   - `docs/plan/scope.md`: `In scope`, `Out of scope`, `Assumptions`, `Constraints` and the `Questions for business`
     section (each question with its `Blocks:` line);
   - `docs/plan/milestones.md`: each `### M<n>` milestone with its `Exit:`, `Demo:` and `Target:` lines;
   - the brief files of `docs/plan/briefs/`: each one's `Milestone:`, `Expected:` and `Screens:` lines;
   - `docs/design/inventory.md`, when it exists: each screen's plain name and what a person does there;
   - `docs/plan/baseline.json`, when it exists: its `date`, the start of the first milestone.

   Stop and tell the person when `docs/plan/scope.md` or `docs/plan/milestones.md` is missing: the plan is
   rendered first (`docs/guides/planning.md`, step 6).

2. **Write `docs/plan/scope-lock.md`** in plain words, with these sections in this order:

   - `# Scope lock: <project name>`, then one line with today's date from `date -u`.
   - `## Milestone <n>: <title>`, one per milestone in order. Under it: its start and end dates (the start is the end of
     the milestone before it, or the baseline's date for the first; the end is its `Target:`), its estimated hours (the
     sum of the low and of the high ends of its briefs' `Expected:` ranges, written `about <low> to <high> hours`), and
     one line per screen it makes work (its `Demo:` screens, else its briefs' `Screens:`), each with the screen's plain
     name and what a person can do there, in the person's words of the inventory.
   - `## Go-live`: the date the last milestone before go-live ends.
   - `## After go-live`: what the plan puts after go-live, in plain words.
   - `## Not included`: each `Out of scope` item, each with the reason the plan or its sources give.
   - `## Decisions`: the assumptions, the constraints and each settled conflict, in plain words.
   - `## Questions`: each question of `Questions for business`, with the date it is needed by: the start of the first
     milestone that holds a brief its `Blocks:` line names.
   - `## Risks`: each risk the plan or its sources name, with its answer; a risk without an answer is a question.

   Nothing is invented: a date, a figure or a reason the plan does not state is written `to be agreed`, never made up.
   Write for a reader who is not technical. Never write a requirement number, a file path, a brief key, the name of a
   tool, or how the work is done or by whom: no builder count, no pull request figure, no PR rate.

3. **Check it** until it passes:

```
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/agk/check_plan.py"
```

   Each `rule 10: docs/plan/scope-lock.md:<line>: <kind>` line names a line of the scope lock that holds a requirement
   number, a file path, a brief key or a builder or pull request figure. Rewrite that line in plain words and run the
   check again. Fix the scope lock, never the check.

4. **Print the issue text.** Print, for the person to copy, the title `Scope lock: <project name>` and a body in the
   same words as the file, section by section. This command creates no issue and posts nothing: the person opens the
   issue in GitHub, or sends the text to the business readers, as they choose.

5. **A PDF, only if the person asks.** Look for an installed browser with `command -v` for `chromium`,
   `chromium-browser`, `google-chrome`, `microsoft-edge` and `msedge` (on Windows, `where`). When one is found, write
   the same text as one plain HTML file at a path the person names outside `docs/`, never committed, and name the
   command for the person to run:

```
<browser> --headless --print-to-pdf="<file>.pdf" "<file>.html"
```

   When none is found, say that any browser prints the HTML file to PDF from its print dialog. This command never
   installs a browser or any other tool.

6. **Tell the person** the file's path, the count of milestones, questions and risks, each `to be agreed` the file
   holds, and that the scope lock is theirs to edit and commit; the plan's formal gate stays the `Approve: plan` line.
