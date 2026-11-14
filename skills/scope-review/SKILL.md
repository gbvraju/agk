---
name: scope-review
description: Before a plan is approved, compare every source document and imported prototype version with the requirements and briefs in a fresh session, without reading the plan's own scope files, and write one report of uncovered items and conflicts outside docs/. A second step, started by the person, triages each finding into docs/plan/scope-triage.md.
disable-model-invocation: true
argument-hint: "<path for the report, outside docs/>"
---

# /agk:scope-review

An independent check of a drafted plan's scope, run by the person before `Approve: plan` (`docs/guides/planning.md`,
ADR-0517). It reads the sources as they are and the plan only through its requirements and briefs, so a gap the plan's
own scope files hide still shows. Run it from the repository root.

## Step 1: the report

1. **A fresh session.** Run this in a fresh session: one that did not draft the plan and has not read its scope files.
   If this session drafted the plan, ran `/agk:plan-intake` or read one of the files below, stop and tell the person to
   start a fresh session and run the command there.

   Do not read these, at any point of step 1, even when another file points at them:
   - `docs/plan/scope.md`;
   - `docs/plan/prototype-coverage.md`;
   - a planning report: the proposals file of `/agk:plan-intake`, a plan walk under `docs/runs/`, or the printed output
     of `plan_intake.py render` or `check_plan.py --trace`.

2. **The guard first.** Before any source is read, run:

```
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/agk/plan_intake.py" states
```

   With exit 2 (`data guard not installed: <path>`) stop and tell the person that the data guard must be installed
   first (SPEC-0043 rule 3). With exit 1 a source holds a secret or personal data: show the lines it prints (file, kind,
   line and column; never a value) and stop until the person cleans that source. Read no source before this passes.

3. **Read the sources.** Read every file under `docs/sources/`, and every imported design version under
   `docs/design/imported/` (each `i<n>/` folder: its `map.md` and its pages). A location is `<file>:<line>` or
   `<file>#<heading>` (the exact heading text).

4. **Read what the plan covers.** Read `docs/requirements.md` (each requirement, its criteria and its `Source:` line)
   and every brief under `docs/plan/briefs/` (its `What`, `Acceptance` and `Advances:` lines). Nothing else of the plan.

5. **Compare.** For each source, list each screen, state, field, rule, role or requirement that it states and that no
   requirement or brief covers, with its location. List each conflict: two places that cannot both hold (two sources, a
   source and a requirement, or a source and a brief), with both sides, each with its location. Never settle a conflict
   and never guess a value: a point no location states is not a finding.

6. **The report.** It goes to the path the person names, outside `docs/` (best outside the repository), never committed.
   One `## <source file>` section per source, then a `## Conflicts` section, then one count line:
   `<g> uncovered, <c> conflicts, <s> sources read`. Each finding is one line: its kind (screen, state, field, rule,
   role or requirement), what it is in a few words, and its location. Step 1 changes no file in the repository: it
   writes the report and nothing else. Tell the person where the report is, and that step 2 runs only when they ask.

## Step 2: the triage

Run this only when the person asks for it, after they have read the report. Read the report and, to place each
finding, `docs/requirements.md`, `docs/plan/briefs/` and `docs/plan/milestones.md`. Each finding becomes one of four
outcomes, one line each, with the finding's location:

- **covered**: a requirement already covers it; name the requirement (`REQ-n` or its key).
- **gap**: nothing covers it; propose a requirement (a title and one criterion from the location) and a brief in the
  milestone of its area.
- **out of scope**: the person rules it out; cite the source location that says so, or `person <date>` from `date -u`.
- **decision**: a conflict or a choice the person must make; give both sides with their locations and a recommendation.

Ask the person where a finding's outcome is not clear from a location; never decide it for them. Write the result to
`docs/plan/scope-triage.md` and to no other file: one `## <outcome>` section per outcome and the count of each. The
triage writes no requirement, brief, milestone or GitHub object. The person brings each gap into the plan through their
own intake pull request, and the triage file is theirs to edit and commit.
