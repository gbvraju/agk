---
name: plan-intake
description: Draft a project's plan from its source documents under docs/sources/ as one proposals file (scope, milestones, requirements, feature areas, briefs, conflicts), every item citing a source location, and validate it. Writes that one file outside docs/ only; never a requirement, spec, brief or GitHub object.
disable-model-invocation: true
argument-hint: "<path for the proposals file, outside docs/>"
---

# /agk:plan-intake

Turn the person's source documents (`docs/sources/`, SPEC-0043 rule 1) into one proposals file that the person reads, and
that `render` later turns into draft files the person owns. Run it from the repository root. It writes one JSON file at a
path the person names outside `docs/`, never committed (principle 5). It never writes a requirement, a spec, a brief or a GitHub object.

1. **The guard first.** Before any source is read, run:

```
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/agk/plan_intake.py" states
```

   With exit 2 (`data guard not installed: <path>`) stop and tell the person that the data guard must be installed
   first (SPEC-0043 rule 3). With exit 1 a source holds a secret or personal data: show the lines (file, kind, line and
   column; never a value) and stop until the person cleans that source. Read no source before this step passes. With
   exit 0 each line `states` prints is one `scope.open_questions` item to add: the inventory gives that screen the state
   as `yes` and the prototype does not show it (amendment 163 item 5).

2. **Read the sources.** Read only the files under `docs/sources/` (and a charter's `#Milestones` item), only after step
   1 passed. A location is `<file>:<line>` or `<file>#<heading>` (the exact heading text).

3. **Write the proposals file** at the path the person names, outside `docs/`:

```
{"schema": 1,
 "scope": {"in": [ITEM], "out": [ITEM], "assumptions": [ITEM], "constraints": [ITEM], "open_questions": [ITEM]},
 "milestones": [{"id": "M1", "title": "", "exit": "", "acceptance": "", "target": null, "sources": []}],
 "requirements": [{"key": "", "title": "", "criteria": ["Given ..., when ..., then ..."], "milestone": "M1", "sources": []}],
 "areas": [{"name": "", "requirements": []}],
 "briefs": [{"key": "", "milestone": "M1", "title": "", "size": "S|M|L", "expected": "<low>-<high> hours",
             "advances": [], "touches": [], "depends_on": [], "sources": []}],
 "conflicts": [{"locations": ["<one side>", "<the other side>"], "description": ""}]}
```

   where `ITEM` is `{"key": "", "text": "", "sources": []}`. Every item of `scope`, `milestones`, `requirements` and
   `briefs` has `sources`, a non-empty list of locations. Milestone ids run `M1`, `M2`, ... in order; each `exit` is
   measurable (a number, `all`, `every`, `none` or `zero`); every milestone has a brief.

   Nothing is invented (SPEC-0043 rule 6): a point the sources do not settle is a `scope.open_questions` item whose text
   ends `(verify)`, with its location where the sources fall silent, never a value made up. A `target` date, a `size`
   or an `expected` range is written only when one of the item's own locations states it (the date as written,
   `size M`, `4-8 hours`); otherwise `target` is `null` and the size and range are open questions. Two sources that
   disagree are one `conflicts` item; no item cites both sides until the person settles it, by adding
   `"settled": "Settled: <location>"` (the side that holds) to that conflict.

4. **Validate** until it prints `ok proposals`:

```
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/agk/plan_intake.py" validate --proposals "<the proposals file>"
```

   Each line names the rule and the item's key or id. Fix the file, never the sources. A line
   `rule 6: open question: ...` is a value no source supports: remove it and add the open question.

5. **Tell the person** the file's path, the conflicts first, then the open questions, then the counts of milestones,
   requirements and briefs. The person decides every conflict and every open question.
