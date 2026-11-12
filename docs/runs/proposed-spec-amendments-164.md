# Proposed spec amendments 164 (SPEC-0043, SPEC-0037; REQ-050, REQ-044)

Date: 2026-11-12 (from `date -u`). Approved specs change only through a proposal like this one (principle 6). Written for
ADR-0469 (brief #1089), which stays `Proposed` for the maintainers' decision. The paths:
`docs/specs/0043-a-project-s-plan-is-drafted-from-its-sources-and-tracked-with-calibrated-ranges.md` and
`docs/specs/0037-a-project-s-design-phase-delivers-a-click-through-prototype.md`. The number 164 is the one brief #1089
reserved; its ADR number is 0469, as the brief's `Correction:` of 2026-11-12 08:36 UTC sets it (0461 is brief #1081's).
This amendment is not applied to the spec texts in this pull request, which the brief limits to documents; the builds of
item 5 write it into the texts. The owner decides it with `Approve: <head> SPEC-0043` and `Approve: <head> SPEC-0037` on
this pull request; no session posts either line.

The sentence (brief #1089): "The plan names personas and user stories from the sources, builds shared components first in
a Foundation milestone, and makes each later milestone a demoable slice proved against the signed-off prototype."

The owner's direction, quoted as data (brief #1089, 2026-11-12 13:46 to 13:49 IST): "Can AGK understands reusable
components, personas to streamline and plan the development strategy so we have visible outcomes like agile"; "File it
with deeper thought through".

## What is on the default branch today

Read in the code by this session on `origin/main` (3e38560):

- No spec or script plans with personas: SPEC-0043 rule 4's proposals hold `scope`, `milestones`, `requirements`,
  `areas`, `briefs` and `conflicts`, and a requirement has `key`, `title`, `criteria` (Given, when, then) and `milestone`,
  with no user it serves.
- `docs/design/inventory.md` (SPEC-0037 rule 3) gives each screen its flow, the pattern of
  `kit/templates/design-patterns.md` it uses (`app shell and navigation`, `list with filter and sort`, `detail`, ...) and
  its states (`default` and the six required ones, or `n/a: <reason>`).
- `scripts/agk/design_import.py` (`pages`, `manifest`, `imported_problems`, `inventory_states`) lists an imported version's
  pages and checks its map, but finds nothing that repeats across pages. On `origin/main` it has no command line;
  brief #1077's open pull request #1086 gives it one (`design_import.py source`, its `Q-1077-1`), which item 3 follows.
- `config/playbooks/web-app.toml` sets `[milestones] shape = "per-batch"` and `batch_by = "demo value: the joins that show
  the most in a demo come first"`; `playbook.py split` prints it (SPEC-0038 rule 7), but no plan uses it.
- SPEC-0037 rule 11 already compares a build with an imported version (`design_compare.py --version i<n>`, one line
  `match`, `drift: pixels|text` or `pixels: not run` per screen and state; amendment 161 item 5).
- SPEC-0043 rules 12 to 24 (the estimator, the status and the report, the baseline and scope changes, the iterations and
  the four ceremonies) are Approved and unbuilt, builds (e) to (h). Wave 7 (briefs #1075, #1076, #1077, #1081, #1078,
  #1079) builds the draft, the trace, the prototype source and `publish` (amendment 163, ADR-0454).

## Items

1. **The documents of this pull request.** This file and ADR-0469 (Proposed). No code, no test, no workflow and no
   protected path change here.
2. **Personas and user stories (SPEC-0043 rules 4 to 7 and 9; build (p)).**
   - Rule 4 gains: "The proposals also hold `personas`, each `key` `P1`, `P2`, ..., `name`, `goals` (a non-empty list of
     plain sentences) and `sources` (non-empty, locations of rule 1). Each requirement also has `persona` (a persona's
     `key`) and `story`, one sentence `As <name>, I want <capability>, so that <outcome>`, where `<name>` is that
     persona's `name`, beside its Given, when, then criteria."
   - Rule 5 gains, to what `validate` refuses: "a requirement without `persona` or `story`, or whose `persona` names no
     persona; a story that does not start `As <the persona's name>, I want ` or has no `, so that ` after it
     (`Q-1089-4`); a persona whose `sources` is empty, as for every item."
   - Rule 6 gains: "A user that the sources only imply (named by no location as a user, a role or a customer) is an item
     of `scope.open_questions` with `(verify)` and the location where the sources fall silent, never a persona the skill
     made up."
   - Rule 7 gains: "`render` also writes `docs/plan/personas.md`, one `### P<n> <name>` block per persona with one
     `Goal:` line per goal and one `Source: <location>` line per location, and adds a `Persona: P<n> <name>` line and a
     `Story: <story>` line to each requirement block of `docs/plan/requirements-proposed.md`, before its criteria."
   - Rule 9 gains: "The trace has a persona column after the requirement: the requirement's `Persona:` key, `none` where
     a requirement has none."
3. **Shared components (a new SPEC-0037 rule 16, SPEC-0037 rule 13, and SPEC-0043 rules 4 and 5; build (q) for the
   command, build (r) for the proposals).**
   - SPEC-0037, new rule 16: "`python3 scripts/agk/design_import.py components --version i<n> --slug <slug>` writes once,
     as a new file only and never over an existing one, `docs/sources/<slug>-components-i<n>.md` with the header of
     SPEC-0043 rule 1: `Source: shared components of imported prototype i<n>`, `Kind: design`,
     `Version: i<n> <the manifest's digest>`, `Date: <YYYY-MM-DD from the clock in UTC>`, then one blank line. A mapped
     page is a file of a row of the version's `map.md` that is not `out:` and is a page, not a picture page. The
     structure of an element is its tag, its class names in the order written, and the tags of its child elements in
     order; its text, its other attributes and its children's own structure are left out. A structure is listed when it
     appears on two or more different mapped pages, the element has at least one child element or one class name, and it
     is not inside another listed structure that appears on exactly the same pages (`Q-1089-5`). Each listed structure is
     one heading `## <name>`, in the order of its first appearance (the map's order, then document order), where the
     name is its first class name, else its tag path from the page's `body` joined with `>` (never `/`, so a heading is
     never read as a `<screen>/<state>` location of SPEC-0043 rule 11), with `-2`, `-3`, ... added to a name already
     used; under it one line `structure: <tag>.<class>...: <child tags>` and one line per mapped row it appears on,
     `- <screen>/<state>`, in the map's order. When no structure is listed, the file holds the header and the one line
     `none: no element structure appears on two or more mapped pages`. Nothing is run or opened, no network, no model
     (amendment 161 item 3). The command refuses, as `design_import.py source` does (brief #1077), a version that is not
     on the branch, a version for which `imported_problems` reports a problem, an existing target file, and a missing or
     malformed `--slug`."
   - SPEC-0037 rule 13: amendment 163 item 3's one exception (the source file of `design_import.py source`) gains the
     components file of rule 16, which carries tag and class names and screen and state names only, no text of a page.
   - SPEC-0043 rule 4 gains: "The proposals also hold `components`, each `key` `C1`, `C2`, ..., `name`, `screens` (the
     inventory screens that use it, two or more), `pattern` (a pattern name of `kit/templates/design-patterns.md` when the
     inventory gives every one of those screens that pattern, else `null`) and `sources`. The skill takes them from the
     components files of SPEC-0037 rule 16 (a heading `<file>#<name>` is the location) and from the inventory's pattern
     entries that two or more screens share (the inventory line is the location). Each component has exactly one brief
     in `M1`, whose `component` names its `key`; when `components` is not empty, `M1` is titled `Foundation`. A brief
     that implements screens names them in `screens` (inventory `<screen>/<state>` pairs), which `render` writes as the
     brief's `Screens: <version> <screen>/<state>, ...` line of SPEC-0037 rule 10, with the signed-off version
     (`Q-1089-2`)."
   - SPEC-0043 rule 5 gains, to what `validate` refuses: "a component whose `screens` names fewer than two screens or a
     screen the inventory does not list; a component with no brief in `M1`, or with more than one; a `component` that
     names no component; and a brief whose `screens` include a screen of a component whose brief its `depends_on` does
     not name, directly (`Q-1089-3`)."
4. **Demoable slices (SPEC-0043 rules 4, 5, 7 and 24, SPEC-0038 rule 7; build (r)).**
   - Rule 4 gains: "Every milestone after `M1` has `screens`, the inventory `<screen>/<state>` pairs it makes demoable,
     and its `exit` says that every screen and state of `screens` reads `match` in `design_compare.py` against the
     signed-off version (SPEC-0037 rule 11), naming that version. The skill orders the milestones after `M1` by the
     project playbook's `[milestones] batch_by` where it has one (for web apps: demo value first), and says the order's
     reason in each milestone's `acceptance`."
   - Rule 5 gains, when `docs/sources/` holds a `Kind: design` source with at least one `## <screen>/<state>` heading:
     "a milestone after `M1` with no `screens`; a milestone whose `exit` does not contain `design_compare.py`, the word
     `match` and a version that has a `design` row in `docs/design/signoffs.md` (SPEC-0037 rule 9); a pair of `screens`
     that the inventory does not list; and a `<screen>/<state>` heading of such a source that no milestone's `screens`
     lists (`Q-1089-6`)." The order by `batch_by` is free text and is the person's to judge, not `validate`'s.
   - Rule 7 gains: "`render` writes one `Demo:` line per milestone block after `Exit:`: `Demo: <screen>/<state>, ...` for
     a milestone with `screens`, and `Demo: none (foundation)` for `M1` when it is `Foundation`."
   - Rule 24's **review** output gains: "for a milestone with `screens`, each screen and state with the `Design match:`
     line of the merged pull request that names it (SPEC-0037 rule 11) as its evidence, and `no evidence yet` where no
     merged pull request has one."
   - SPEC-0038 rule 7 does not change: a milestone still groups pull requests and never merges them (CLAUDE.md item 2).
5. **SPEC-0043 rule 27, the build order.** Add three builds, after the Wave 7 builds that amendment 163 orders:
   - (p) **personas and stories** (item 2): `scripts/agk/plan_intake.py` (`validate`, `render`),
     `scripts/agk/check_plan.py` (the trace's persona column), `skills/plan-intake/SKILL.md`,
     `tests/kit/test_plan_personas.py`. `Depends-on` #1081 (render) and #1076 (the trace).
   - (q) **component detection** (item 3, the command): `scripts/agk/design_import.py` (`components`),
     `tests/kit/test_design_import_components.py`, and the SPEC-0037 rule 13 and 16 texts. `Depends-on` #1077 (the
     command line of `design_import.py`).
   - (r) **components and slices in the draft** (items 3 and 4, the proposals): `scripts/agk/plan_intake.py`,
     `skills/plan-intake/SKILL.md`, `tests/kit/test_plan_slices.py`. `Depends-on` (p) and (q).
   - Then, as rule 27 orders them, (e) **the estimator**, `Depends-on` #1075 (the proposals and `validate`), then (f)
     **status and report**, (g) **baseline and scope change** and (h) **iterations and ceremonies**, which also waits for
     (r) (its review output reads the `Demo:` screens).
   None of them changes a rule that Wave 7's builds implement; each adds fields and refusals beside them. Each build is
   tests first, from the default branch, about 600 changed lines or fewer, with its own ADR naming the protected classes
   it changes and citing ADR-0269, ADR-0454 and ADR-0469, one fragment under `changelog.d/` where it changes an installed
   file, and the person's `Approve: <head> SPEC-0043` (and for (q) `Approve: <head> SPEC-0037`) on this pull request
   first.
6. **Tests (for the builds).** None in this pull request (documents only). Invented pages and sources only, `example.com`,
   in `tmp_path`, no network:
   - (p): proposals with two personas and requirements citing them pass and render `personas.md` and the `Persona:` and
     `Story:` lines; a requirement without `persona`, with an unknown key, or with a story naming another persona's name or
     lacking `, so that ` fails naming the rule and the key, never the text; a persona with empty `sources` fails; the
     trace prints the persona column and `none`;
   - (q): a fixture version `i1` with three mapped pages sharing a `nav.app-nav` with three `a` children on two pages and a
     `table.results` on all three gives one heading each, in first-appearance order, with their `<screen>/<state>` lines; an
     element on one page only, a leaf `span` without a class and a `li` inside the listed `nav` on the same pages are not
     listed; a picture page and an `out:` row are not read; no page's text appears in the file; a second run refuses the
     existing file and leaves it byte for byte; a version with a map problem is refused and writes nothing; a missing or
     malformed `--slug` exits 2; no test opens a page;
   - (r): a component whose brief a screen brief's `depends_on` omits fails naming both keys; a component with one screen,
     or with no `M1` brief, fails; with a `Kind: design` source, a later milestone without `screens`, an `exit` without
     `design_compare.py` or naming an unsigned version, and a source heading in no milestone each fail; without a design
     source none of these applies; `render` prints `Demo:` lines and the `Screens:` line of each screen brief.
7. **Not in this amendment.** SPEC-0043 rules 1 to 3, 8, 10 to 23 and 25 to 26, and SPEC-0037 rules 1 to 12, 14 and 15
   do not change; nor do amendment 163's items. No workflow changes. No session confirms a plan, approves a spec or a
   design, or creates a GitHub object.

## Contexts

- kit: installed, so every project plans with personas, shared components first and demoable slices.
- github: no new workflow; documents only.
- local: the same commands on a laptop.
- personal: the same files; nothing is posted.
- stacks: not applicable; no test or build step of a stack changes.

## Residual

- 2026-11-12: component detection compares structure only; two pages that render the same component with different
  markup are not matched, and a repeated structure that is not a component (a plain list) may be listed. The person
  edits the proposals' `components` before `render` (due 2026-12-31).
- 2026-11-12: class names of a customer's prototype enter `docs/sources/`; they carry no page text, and SPEC-0043 rule 3's
  guard scans the file before any agent reads it (due 2026-12-31).
- 2026-11-12: a later milestone's `exit` can be checked for its words only; whether the slice is worth a demo is the
  person's judgment at confirmation (rule 8) (due 2026-12-31).
- 2026-11-12: without a design source a plan has no `screens` to slice by, and its milestones follow rule 4 as before
  (due 2026-12-31).

## Questions

Each reading is the most conservative one, and applies until a person rules.

- Q-1089-1: the brief's `Reserved: ADR-0461` was also brief #1081's; settled by the owner's `Correction:` on #1089
  (ADR-0469).
- Q-1089-2: rule 4's briefs have no field for the screens they implement, which item 3's refusal needs. Reading: an
  optional `screens` list on a brief, rendered as SPEC-0037 rule 10's `Screens:` line, and a `component` key on a
  component's brief.
- Q-1089-3: "a screen brief whose screens use a component that its `depends_on` does not name". Reading: the component's
  brief must be named in `depends_on` directly, not only through another brief's dependence.
- Q-1089-4: how much of the story `validate` checks. Reading: its form only (`As <name>, I want `, then `, so that `);
  the capability and the outcome are the person's to judge.
- Q-1089-5: which repeated elements are components. Reading: an element with a child element or a class, on two or more
  different mapped pages, not nested inside a listed structure that appears on exactly the same pages, so that one
  navigation bar is one heading and not one per link.
- Q-1089-6: "a screen and state that no milestone lists". Reading: each `<screen>/<state>` heading of a `Kind: design`
  source; a state that only the inventory gives is an open question of amendment 163 item 5 until the person answers.
