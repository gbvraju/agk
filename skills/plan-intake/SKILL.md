---
name: plan-intake
description: Draft a project's plan from its source documents under docs/sources/ as one proposals file (scope, personas, milestones, requirements with their user stories, feature areas, briefs, conflicts), every item citing a source location, and validate it. Writes that one file outside docs/ only; never a requirement, spec, brief or GitHub object.
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

   When `docs/design/imported/` has no version with more than one page and `docs/sources/` holds no `Kind: design`
   file, say so to the person before drafting: a prototype drawn by script on one page is captured screen by screen and
   imported first (step 0 of "From a prototype and an OpenSpec file" in `docs/guides/planning.md`, brief #1204).

   **An OpenSpec file** (SPEC-0043 amendment 166, ADR-0473). When the person brings one, a combined `.md` file or an
   `openspec/` folder that holds `specs/`, import it first; it is copied unchanged under its header, after the guard:

```
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/agk/plan_intake.py" openspec-import "<the file or folder>" --slug <slug>
```

   When `docs/sources/` holds a `Kind: openspec` source, start from its reading, never from your own:

```
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/agk/plan_intake.py" openspec --slug <slug> --out "<the proposals file>"
```

   It writes the proposals file of step 3 with the file's areas, requirements (each `statement` exactly as written and
   `changing` when its change is open), one Given, when, then criterion per scenario ending with its location, persona
   candidates and open questions, and `milestone` `null`. Then add only what it leaves: set each requirement's
   `milestone`, add `milestones`, `briefs` with their sizes, and `screens` where a prototype exists, and replace a
   `(verify)` story or goal only from a location. Never rewrite a `title`, `statement` or criterion that the file
   defines; keep a `changing` requirement out of `M1`, or put it there only with an open question that cites it. Each
   `ignored:` line it prints is a heading it did not read: tell the person.

3. **Write the proposals file** at the path the person names, outside `docs/`:

```
{"schema": 1,
 "scope": {"in": [ITEM], "out": [ITEM], "assumptions": [ITEM], "constraints": [ITEM], "open_questions": [ITEM]},
 "personas": [{"key": "P1", "name": "", "goals": [""], "sources": []}],
 "components": [{"key": "C1", "name": "", "screens": ["<screen>", "<screen>"], "pattern": null, "sources": []}],
 "milestones": [{"id": "M1", "title": "", "exit": "", "acceptance": "", "target": null, "sources": [],
                 "screens": ["<screen>/<state>"]}],
 "requirements": [{"key": "", "title": "", "criteria": ["Given ..., when ..., then ..."], "milestone": "M1",
                   "persona": "P1", "story": "As <name>, I want <capability>, so that <outcome>", "sources": [],
                   "statement": null, "changing": false}],
 "areas": [{"name": "", "requirements": []}],
 "briefs": [{"key": "", "milestone": "M1", "title": "", "size": "S|M|L", "expected": "<low>-<high> hours",
             "advances": [], "touches": [], "depends_on": [], "sources": [],
             "component": "C1", "screens": ["<screen>/<state>"]}],
 "conflicts": [{"locations": ["<one side>", "<the other side>"], "description": ""}]}
```

   where `ITEM` is `{"key": "", "text": "", "sources": []}`. Every item of `scope`, `personas`, `milestones`,
   `requirements` and `briefs` has `sources`, a non-empty list of locations. Milestone ids run `M1`, `M2`, ... in order;
   each `exit` is measurable (a number, `all`, `every`, `none` or `zero`); every milestone has a brief.

   **Personas and stories** (SPEC-0043 amendment 164 item 2). A persona is a user, a role or a customer that a location
   names: persona keys run `P1`, `P2`, ... in order, each with its `name`, its `goals` (at least one plain sentence) and
   the locations that name it. Every requirement names the `persona` it serves by key and has one `story` that starts
   `As <that persona's name>, I want ` and goes on `, so that <outcome>`, beside its Given, when, then criteria. A user
   that the sources only imply, named by no location as a user, a role or a customer, is never a persona you make up: it
   is a `scope.open_questions` item whose text ends `(verify)`, with the location where the sources fall silent.

   **Shared components first** (SPEC-0043 amendment 164 item 3). With a prototype, take `components` from the
   components file that `design_import.py components --version i<n> --slug <slug>` wrote (`Kind: design`, one
   `## <name>` heading per structure; `<file>#<name>` is the location) and from the inventory's `- Pattern:` lines that
   two or more screens of `docs/design/inventory.md` share (cite those screens' `## <screen>/<state>` headings of the
   prototype source, since the inventory is not a location). Component keys run `C1`, `C2`, ... in order; each names two
   or more inventory `screens` and its `pattern` (a pattern of `kit/templates/design-patterns.md` when the inventory
   gives every one of its screens that pattern, else `null`). Each component has exactly one brief, in `M1`, whose
   `component` names its key; with any component, `M1` is titled `Foundation`. A brief that builds screens names them
   in `screens` (`<screen>/<state>` pairs of the inventory) and names in `depends_on`, directly, the brief of every
   component those screens use. Without a prototype leave `components`, `component` and `screens` out.

   **Demoable slices** (SPEC-0043 amendment 164 item 4). When a `Kind: design` source has `## <screen>/<state>`
   headings, every milestone after `M1` lists in `screens` the screens and states it makes demoable, its `exit` says
   that each of them reads `match` in `design_compare.py` against the signed-off version and names that version, and
   every `<screen>/<state>` heading of the source is in some milestone's `screens`. Order the milestones after `M1` by
   the declared playbook's `[milestones] batch_by`, which `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/agk/playbook.py" split`
   prints and `render` prints again (for web apps: demo value first), and say the reason for the order in each
   milestone's `acceptance`.

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
