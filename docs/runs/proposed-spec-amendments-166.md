# Proposed spec amendments 166 (SPEC-0043; REQ-050)

Date: 2026-11-12 (from `date -u`). Approved specs change only through a proposal like this one (principle 6). Written for
ADR-0472 (brief #1108), which stays `Proposed` for the maintainers' decision. The path:
`docs/specs/0043-a-project-s-plan-is-drafted-from-its-sources-and-tracked-with-calibrated-ranges.md`. The numbers 166 and
0472 are the ones brief #1108 reserved. This amendment is not applied to the spec text in this pull request, which the
brief limits to documents; the builds of item 6 write it into the text. The owner decides it with
`Approve: <head> SPEC-0043` on this pull request; no session posts that line.

The sentence (brief #1108): "An OpenSpec file, combined or as folders, is imported unchanged as a `Kind: openspec` source,
and its capabilities, requirements, scenarios, change status and cross-references become the plan draft's areas,
requirements and acceptance lines without invention."

The owner's direction, as the brief restates it (2026-11-12 18:45 to 18:53 IST): a customer project comes with a
click-through prototype and an OpenSpec functional file, and the kit should use the OpenSpec file to draft the specs and
the plan. The customer's file is confidential: nothing of it enters this repository, a brief, a test or a log. Every
example below uses the brief's invented words only (`Book loans`, `book-loans`, `loan-intake-rules`, `BRD 2.1`,
`a librarian`), and every fixture of the builds is invented (`example.com`) in the same shape.

## What is on the default branch today

Read in the code by this session on `origin/main` (0deb777):

- No file mentions OpenSpec (`grep -rliw openspec` over the tracked files: nothing).
- `scripts/agk/check_plan.py` `KINDS` (line 52) is `sow, brd, prd, design, charter, other`, and rule 1 needs the header
  `Source:`, `Kind:`, `Version:`, `Date:` on every file under `docs/sources/`, which `source_files` walks with `rglob`, so
  a subfolder of `docs/sources/` is already read. A location is `<file>:<line>` or `<file>#<heading>`
  (`location_problem`, line 231), the heading's text exactly, so a `Requirement:` or `Scenario:` heading is already a
  citable location.
- `scripts/agk/plan_intake.py` `FIELDS` (line 52): a requirement is `key, title, criteria, milestone, sources` and an area
  `name, requirements`; `validate` refuses an unknown or missing key. `render` writes each criterion as one acceptance
  line `- <criterion>` (line 356, `- (verify)` when there is none) and one Draft spec per area through
  `new_spec.make_spec` (line 459). `plan_intake.py` runs `guard.scan_text` (`scripts/agk/guard.py`) on each source
  before it reads a line of it (rule 3).
- Amendment 164 item 2 (ADR-0469, brief #1089, merged as #1097) proposes `personas`; its build (p) is not on the default
  branch. Amendment 163 items 4 and 5 count a `Kind: design` source's `<screen>/<state>` headings; the screen map of an
  imported version is `docs/design/imported/i<n>/map.md` (SPEC-0037 rule 15).

## The shape read (invented words)

- **Combined file.** One Markdown file of several capabilities. A capability is a heading (for example `### Book loans`)
  followed by an italic line ``*Capability `book-loans`. Defined by: `loan-intake-rules` (open, 12/30 tasks done).*``.
  Under it, headings `Requirement: <name>` (for example `#### Requirement: Loan limit`) whose text holds `SHALL` or
  `SHALL NOT` and may cite another source in parentheses (`(BRD 2.1, design option a)`); under each requirement,
  headings `Scenario: <name>` with bullet steps `- **WHEN** ...`, `- **THEN** ...`, bold or plain, and also `GIVEN` and
  `AND`.
- **Standard folder.** `openspec/specs/<capability>/spec.md` with `### Requirement:` and `#### Scenario:` headings, and
  `openspec/changes/<id>/` with `proposal.md`, `design.md`, `tasks.md` and delta specs under `specs/<capability>/`;
  `changes/archive/` holds finished changes.

## Items

1. **The documents of this pull request.** This file and ADR-0472 (Proposed). No code, no test, no workflow and no
   protected path change here.
2. **The source (rule 1, a new rule 2b; build (s)).**
   - Rule 1: the `Kind:` list becomes `<sow|brd|prd|design|charter|openspec|other>`.
   - New rule 2b: "`python3 scripts/agk/plan_intake.py openspec-import <path> --slug <slug>` imports an OpenSpec file.
     `<path>` is a combined Markdown file, or a folder that holds `specs/` (an `openspec/` folder). The command writes
     `docs/sources/openspec-<slug>/`: for a file, the one file under its own name; for a folder, every `.md` and `.txt`
     file at its path relative to `<path>`. Each written file is the rule 1 header (`Source: OpenSpec <relative path>`,
     `Kind: openspec`, `Version: sha256:<the SHA-256 of the original bytes>`, `Date: <YYYY-MM-DD from the clock in
     UTC>`), one blank line, and then the original bytes unchanged. Any other file of the folder is not copied and is
     printed as one line `skipped: <relative path> (rule 1: .md or .txt only)` (`Q-1108-4`). Before anything is
     written, `guard.scan_text` (rule 3) scans the whole text of every file to be copied; a finding refuses the whole
     import with exit 1 and one line per finding naming the file, the kind and `line <l>, column <c>`, never the matched
     text, and writes nothing. The command refuses with exit 2, writing nothing, when `docs/sources/openspec-<slug>/`
     exists (it never overwrites), when `--slug` is missing or is not lowercase letters, digits and hyphens starting
     with a letter or digit, when `<path>` is neither a `.md` file nor a folder with `specs/`, and when a file to copy
     is not UTF-8; each refusal names the setting or the path, never a value of a file. Nothing is fetched, run or
     opened; no network, no model." With `Version:` a digest, a re-import of a changed file is a new slug, and the
     person compares the two.
   - Rule 3 does not change: the guard has passed every imported file before any agent reads it, and in personal mode
     the folder lives in the private state.
3. **The reading (rule 4, a new rule 4b; build (t)).**
   - New rule 4b: "`python3 scripts/agk/plan_intake.py openspec-draft --slug <slug> --out FILE` reads
     `docs/sources/openspec-<slug>/` and writes a proposals file of rule 4 (`schema` 1) at `FILE`, outside `docs/`,
     never over an existing file (`Q-1108-7`). The reading is deterministic and free of heading level:
     - a **capability** is, in a combined file, the heading just before a line that starts `*Capability ` and names a
       slug in backticks, and in a folder each `specs/<slug>/` folder; its area `name` is the heading's text in a
       combined file and `<slug>` in a folder;
     - a **requirement** is any heading whose text starts `Requirement: `, in a capability, outside `changes/`; its
       statement is the text between that heading and its first `Scenario:` heading or the next heading, its lines
       joined with one space, exactly as written, `SHALL NOT` included;
     - a **scenario** is any heading whose text starts `Scenario: ` under a requirement, before the next requirement or
       capability heading;
     - a **step** is a bullet of a scenario whose text, after an optional `**`, starts `GIVEN`, `WHEN`, `THEN` or `AND`
       (any case), the word and its closing `**` removed; an `AND` joins the clause before it with ` and `.
     Each requirement becomes one draft requirement: `key` `R1`, `R2`, ... in reading order, `title` the name after
     `Requirement: `, `statement` the text above, `criteria` one per scenario
     `Given <given>, when <when>, then <then> (<location of its Scenario: heading>)`, `milestone` `null` for the skill to
     set, and `sources` the location of its `Requirement:` heading first. Each capability becomes one area with its
     requirements' keys. `milestones` and `briefs` are empty lists; `conflicts` is empty; `scope` holds only the open
     questions of item 4. A location is `<file>#<heading>`, or `<file>:<line>` of the heading when the same heading text
     appears more than once in that file (`Q-1108-3`)."
   - Rule 4 gains: "A requirement also has `statement`, its requirement text or `null`, and `changing`, `true` or
     `false` (`Q-1108-1`, `Q-1108-2`). When the sources hold a `Kind: openspec` source, the skill starts from the output
     of `openspec-draft`: it sets each `milestone`, adds `milestones` and `briefs`, and never rewrites a `title`,
     `statement` or criterion that the draft took from the file."
   - Rule 5 gains, to what `validate` refuses: "a requirement whose `sources` cite a `Kind: openspec` file and whose
     `statement` is `null`; a criterion that ends with a location in parentheses that does not resolve."
   - Rule 7 gains: "`render` writes a `Statement: <statement>` line in each requirement block whose `statement` is not
     `null`, before its criteria, and a `Changing: yes` line when `changing` is `true`."
4. **What OpenSpec does not settle (rule 6; build (t)).** Rule 6 gains, for a `Kind: openspec` source:
   - a requirement with no scenario gets the one criterion `(verify)` and one `scope.open_questions` item with `(verify)`
     at its `Requirement:` heading;
   - a capability whose `Defined by:` names a change with the status `open` (in a combined file, the word before the first
     comma inside the parentheses), or, in a folder, whose `<slug>` has a delta spec under `changes/<id>/specs/<slug>/`
     outside `changes/archive/`, gives its requirements `changing: true`; the skill keeps a `changing` requirement out of
     `M1`, or, to put it in `M1`, writes one open question with `(verify)` at its heading for the person; `validate`
     refuses a `changing` requirement in `M1` unless an item of `scope.open_questions` cites one of its locations
     (`Q-1108-2`);
   - a cross-reference in parentheses in a requirement's statement, split at commas, becomes a second location of that
     requirement's `sources` only when it reads `<kind> <number>` (for example `BRD 2.1`), exactly one file under
     `docs/sources/` has that `Kind:` (lowercased), and exactly one heading of it starts with `<number>` followed by a
     space or the end; any other cross-reference (for example `design option a`) is one open question with `(verify)` at
     the requirement's heading that names the cross-reference's position, never its text (`Q-1108-9`);
   - actors named in steps (for example `a librarian`) are persona candidates of amendment 164 item 2, each with the
     location of its scenario as its source; until build (p) is on the default branch, the skill writes each as one open
     question with `(verify)` instead (`Q-1108-10`);
   - each item of a `tasks.md` and each delta spec under `changes/` is a hint for the briefs and, where it states
     behaviour that no capability's requirement states, one open question with `(verify)` at its location; neither is
     ever a requirement, and `openspec-draft` writes no requirement from a file under `changes/`.
5. **Coverage (rules 10 and 11; build (u)).**
   - Rule 11's line gains, when a `Kind: openspec` source exists, after its counts:
     `, <a> of <b> scenarios have an acceptance line and <c> a test`, where `<b>` counts the `Scenario:` headings of the
     `Kind: openspec` sources outside `changes/`, `<a>` those whose location ends an acceptance line of
     `docs/plan/requirements-proposed.md` or `docs/requirements.md` in parentheses, and `<c>` those whose acceptance line
     is criterion n of a requirement `REQ-nnn` that a test marks `REQ-nnn ACn` (with `--facts FILE`, else `not read`, as
     rule 11's last counts) (`Q-1108-6`).
   - With an imported prototype (a `docs/design/imported/i<n>/map.md` of a signed-off version, else the newest), a
     scenario names a screen when a step contains that screen's name of the map as a whole word, case ignored;
     `check_plan.py` prints one line `unmatched scenario: <location>` for each scenario that names no mapped screen and
     one line `unmatched screen: <screen>` for each mapped screen that no scenario names, before the `ok plan:` line.
     These lines are listed and never fail the check (`Q-1108-5`).
6. **SPEC-0043 rule 27, the build order.** Add three builds, after amendment 164's (p), (q) and (r):
   - (s) **the OpenSpec import** (item 2): `scripts/agk/plan_intake.py` (`openspec-import`), `scripts/agk/check_plan.py`
     (`KINDS`), `tests/kit/test_plan_openspec_import.py`, and the rule 1 and 2b texts. No `Depends-on`: build (b) and the
     guard are on the default branch.
   - (t) **the reading and the draft** (items 3 and 4): `scripts/agk/plan_intake.py` (`openspec-draft`, `validate`,
     `render`), `skills/plan-intake/SKILL.md`, `tests/kit/test_plan_openspec_draft.py`, and the rule 4b, 4, 5, 6 and 7
     texts. `Depends-on` (s). Its persona candidates follow (p) once (p) merges; it does not wait for (p).
   - (u) **the scenario coverage** (item 5): `scripts/agk/check_plan.py`, `tests/kit/test_plan_openspec_coverage.py`, and
     the rule 10 and 11 texts. `Depends-on` (t).
   Each build is tests first, from the default branch, about 600 changed lines or fewer, with its own ADR naming the
   protected classes it changes and citing ADR-0269 and ADR-0472, one fragment under `changelog.d/` where it changes an
   installed file, and the person's `Approve: <head> SPEC-0043` on this pull request first.
7. **Tests (for the builds).** None in this pull request (documents only). Invented files only, in `tmp_path`, no
   network, in the shape above with invented capabilities (`Book loans`, `Book returns`) and `example.com` addresses:
   - (s): a combined file and an `openspec/` folder import with the header and the original bytes after it, `Version:`
     its SHA-256; a second import to the same slug exits 2 and leaves the folder byte for byte; a bad or missing `--slug`
     and a path without `specs/` exit 2; a non-`.md` file of the folder is skipped and printed; a file the guard flags
     refuses the import, writes nothing and prints the file, the kind and the position, never the matched text; a missing
     guard exits 2; `check_plan.py` passes `Kind: openspec`.
   - (t): the combined file and the folder give the same areas, requirements, statements and criteria; bold and plain
     steps read the same; `SHALL NOT` stays in the statement; heading levels 2 to 6 read the same; a requirement without
     a scenario gives `(verify)` and an open question; an `open` change marks `changing`, and `validate` refuses a
     `changing` requirement in `M1` without an open question citing it; `BRD 2.1` resolves to an invented `Kind: brd`
     source with a `2.1` heading and becomes an open question without one; a repeated scenario name gives `<file>:<line>`
     locations; nothing under `changes/` becomes a requirement; `render` writes `Statement:` and `Changing: yes`.
   - (u): the scenario count line with and without `--facts`; an invented map with one screen named in a step and one
     named nowhere prints the two `unmatched` lines and still exits 0.
8. **Not in this amendment.** SPEC-0043 rules 2, 3, 8, 9 and 12 to 26 do not change; nor do amendment 163's and 164's
   items. No workflow changes. No session confirms a plan, approves a spec or creates a GitHub object.

## Contexts

- kit: installed, so every customer project can start its plan from its OpenSpec file.
- github: no new workflow; documents only.
- local: the same commands on a laptop.
- personal: the same files, in the private state; nothing is posted.
- stacks: not applicable; no test or build step of a stack changes.

## Residual

- 2026-11-12: the reader knows the combined shape and the standard folder only; another dialect is free text for the
  skill until a person extends rule 4b (due 2026-12-31).
- 2026-11-12: a scenario names a screen only by the map's exact screen name; a scenario that says it another way is
  listed as unmatched for the person to judge (due 2026-12-31).
- 2026-11-12: the customer's OpenSpec text enters the customer project's `docs/sources/`, never the kit; the guard of rule
  3 scans it before any agent reads it (due 2026-12-31).

## Questions

Each reading is the most conservative one, and applies until a person rules.

- Q-1108-1: the brief's "statement the SHALL text" has no field: rule 4's requirement is `key, title, criteria,
  milestone, sources`, and `validate` refuses an unknown key. Reading: a new `statement` field (text or `null`), required
  for a requirement cited to a `Kind: openspec` source and written by `render` as a `Statement:` line.
- Q-1108-2: the brief's "marks its requirements `changing`" and "keeps them out of the first milestone or asks" name no
  field and no check. Reading: a `changing` field (`true` or `false`), and `validate` refuses a `changing` requirement in
  `M1` unless an open question cites it, so the asking is on the record.
- Q-1108-3: rule 1's heading location is the heading's text exactly, and scenario names may repeat across requirements.
  Reading: `<file>:<line>` of the heading when its text is not unique in the file.
- Q-1108-4: "copies ... byte for byte" and rule 1's `.md` or `.txt` only. Reading: only `.md` and `.txt` files are copied,
  each printed skip names the other files, and the original bytes follow the added header unchanged.
- Q-1108-5: "each scenario that names a screen is matched to the map, and an unmatched scenario or screen is listed".
  Reading: a step contains the map's screen name as a whole word, case ignored; the lists are printed and never fail.
- Q-1108-6: how an acceptance line is tied to its scenario. Reading: each criterion taken from a scenario ends with the
  scenario's location in parentheses, and rule 11 matches on it; `<c>` follows rule 11's facts rule.
- Q-1108-7: the brief names no command for the deterministic reading. Reading: `plan_intake.py openspec-draft`, which
  writes a partial proposals file the skill completes, so the reading is a tested script and not the model.
- Q-1108-8: the brief writes `Version:` as "the SHA-256 of the original". Reading: `sha256:<64 hex digits>`, so the value
  says what it is.
- Q-1108-9: which cross-references resolve. Reading: only `<kind> <number>` with exactly one source of that kind and
  exactly one heading starting with that number; every other one is an open question that names its position, not its
  text.
- Q-1108-10: amendment 164 item 2 (personas) is proposed and its build (p) is not on the default branch. Reading: actors
  are open questions with `(verify)` until (p) merges, then persona candidates cited to their scenario.
