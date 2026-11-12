# Proposed spec amendments 163 (SPEC-0043, SPEC-0037; REQ-050, REQ-044)

Date: 2026-11-12 (from `date -u`). Approved specs change only through a proposal like this one (principle 6). Written for
ADR-0454 (brief #1073), which stays `Proposed` for the maintainers' decision. The paths:
`docs/specs/0043-a-project-s-plan-is-drafted-from-its-sources-and-tracked-with-calibrated-ranges.md` and
`docs/specs/0037-a-project-s-design-phase-delivers-a-click-through-prototype.md`. The number 163 is the one brief #1073
reserved. This amendment is not applied to the spec texts in this pull request, which the brief limits to documents; the
builds of item 5 write it into the texts. The owner decides it with `Approve: <head> SPEC-0043` and
`Approve: <head> SPEC-0037` on this pull request; no session posts either line.

The sentence (brief #1073): "An imported prototype becomes a `Kind: design` source with one location per mapped screen and
state, the skill asks for the states a prototype does not show, and SPEC-0043's plan path (sources, draft, trace, publish,
guide) runs without its estimator and ceremonies."

The owner's direction, quoted as data (brief #1073, 2026-11-12 10:31 to 10:39 IST): "the immediate next goal is, when I
give prototype, it should give all milestone based development plan in GitHub with no edge case spec or brief to AGK
agents"; "file it wave 7, just read and understand the code, file realistic needs here".

## What is on the default branch today

Read in the code by this session on `origin/main` (b1c6676):

- SPEC-0043 (Approved, REQ-050) specifies the sources (rules 1 to 3), `/agk:plan-intake` with `validate` and `render`
  (rules 4 to 8), the trace and the coverage (rules 9 to 11) and `publish` (rule 25), but none of its builds (b) to (j)
  exists: there is no `scripts/agk/check_plan.py`, no `scripts/agk/plan_intake.py` and no `skills/plan-intake/`.
- What SPEC-0043 reuses is there: `scripts/agk/guard.py` (`scan_text`) and `.claude/hooks/data_guard.py` (brief #538),
  so rule 3's guard is installed and its `(verify)` on #538 is settled; `scripts/agk/forge.py` `FilesForge` (brief #536),
  the file forge of rule 25; `scripts/agk/playbook.py` `MEASURABLE`; `scripts/agk/new_spec.py` `make_spec`; the
  `Expected` pattern of `scripts/agk/common.py`; `scripts/agk/traceability.py`. `.github/workflows/governance.yml` runs
  each check as its own step (`check_design.py` is one), so build (b) needs one workflow line, which only the owner commits.
- SPEC-0037 rule 15 as amendment 161 proposes it (approved on #1057, ADR-0446) is partly built: `scripts/agk/design_import.py`
  (`import_folder`, `imported_problems`, `inventory_states`, the manifest's `digest` and `pages`) and
  `scripts/agk/design.py import` (brief #1061, ADR-0448), and the sign-off of an `i<n>` version (brief #1062, ADR-0449).
  `design_import.py` has no command line of its own: every design command is a subcommand of `scripts/agk/design.py`
  (`write`, `prototype`, `inventory`, `import`, `screenshots`).
- SPEC-0043 rule 1 allows `Kind: design`, and rule 2 turns a design link into a source file only through a session's
  design connector. Nothing turns an imported prototype into a source, so no source location can cite one of its screens,
  and no rule asks for the states that a prototype does not show.

## Items

1. **The documents of this pull request.** This file and ADR-0454 (Proposed). No code, no test, no workflow and no
   protected path change here.
2. **SPEC-0043, a new rule 2a, the prototype source (build (k)).** "`python3 scripts/agk/design.py source --version i<n>
   --slug <slug>` writes once, as a new file only and never over an existing one, `docs/sources/<slug>-prototype-i<n>.md`
   with the header of rule 1: `Source: imported prototype i<n>`, `Kind: design`, `Version: i<n> <the manifest's digest>`,
   `Date: <YYYY-MM-DD from the clock in UTC>`, then one blank line. Then, for each row of the version's `map.md` that is
   not `out:`, in the map's order, one heading `## <screen>/<state>` and under it the page's visible text, read from its
   HTML as text only: the `<title>`, the headings, the labels, the texts of buttons and links, the names and placeholders
   of fields, and the texts of elements marked as messages (`role="alert"` or `role="status"`), one per line, in document
   order, each with its white space collapsed, empty ones left out (`Q-1073-2`). A row whose file is a picture page gets
   the one line `picture: <file>`. Nothing is run or opened, no network, no model (SPEC-0037 amendment 161 item 3). The
   command refuses, with exit 1 naming the rule and the version and writing nothing, a version that is not on the branch
   and a version for which `design_import.imported_problems` reports a problem (the import check or the map check); it
   refuses an existing target file naming the file, and a missing or malformed `--slug` with exit 2 naming `--slug`
   (`Q-1073-1`). The text is the person's to clean: SPEC-0043 rule 3's guard scans the whole file before any agent reads
   it, as for every source." The function goes in `scripts/agk/design_import.py` (`source_text`), the subcommand in
   `scripts/agk/design.py`.
3. **SPEC-0037 rule 13, one exception (build (k)).** After amendment 161's sentence that "nothing of an imported version
   (no text, no value, no file) is copied into a theme, the inventory, a fixture, a test or a kit prototype version", add:
   "The one exception is the source file that `design.py source` writes under `docs/sources/` (SPEC-0043 rule 2a), which
   carries the visible text of the version's mapped pages and nothing else; SPEC-0043 rule 3's guard scans it before any
   agent reads it, and nothing of it is copied on into a theme, the inventory, a fixture, a test or a kit version."
4. **SPEC-0043 rule 11, coverage counts the prototype (build (d)).** Add: "In a source whose header says `Kind: design`,
   each `## <screen>/<state>` heading is one in-scope source location (`<file>#<screen>/<state>`, the location form of
   rule 1) and is counted in `<b>`, whether or not `docs/plan/scope.md` lists it; it counts in `<a>` when a requirement's
   `Source:` line cites it. So `<a> of <b>` proves that every mapped screen and state has a requirement." Rule 10 gains,
   for the same headings: "a `## <screen>/<state>` heading of a `Kind: design` source that no requirement cites" fails,
   naming the rule and the location, as an uncited `In scope` line does.
5. **SPEC-0043 rule 6, the states a prototype does not show (build (c)).** Add: "For each screen that a heading of a
   `Kind: design` source names, the skill lists the states that `docs/design/inventory.md` gives that screen as `yes` and
   that no heading of the source covers (for example `error`, `empty`, `loading`, `no-permission`), and each becomes one
   `scope.open_questions` item with the mark `(verify)` and the location of that screen's first heading in the source
   (`Q-1073-3`). A state the inventory marks `n/a: <reason>` is not asked again. Nothing is invented: the skill writes no
   requirement, criterion or brief for such a state until the person answers. `render` prints these items under
   `Open questions for the person`, after `Conflicts for the person`." `validate` checks them as every open question:
   a non-empty `sources` list whose location resolves.
6. **SPEC-0043 rule 27, the build order for this path.** Add build (k) and replace the `Depends-on` lines so:
   - (b) **the sources**, as rule 27 says. The builds of brief #538 that it named are on the default branch (`guard.py`,
     `.claude/hooks/data_guard.py`), so it declares no `Depends-on` for them (session rule 3).
   - then, in parallel, each `Depends-on` (b):
     - (c) **proposals, validation, render and the skill**, with item 5;
     - (d) **the trace and the coverage**, with item 4; its tests write their own `docs/plan/` fixtures, so it does not
       wait for (c)'s `render` (`Q-1073-4`);
     - (k) **the prototype source** (items 2 and 3): `scripts/agk/design.py` (`source`), `scripts/agk/design_import.py`
       (`source_text`), `tests/kit/test_design_source.py`, and the SPEC-0037 rule 13 text.
   - then (i) **`publish`**, which `Depends-on` (c) only: the file forge of brief #536 is on the default branch
     (`forge.py` `FilesForge`), and rule 25 reads only rule 7's rendered files.
   - then (j) **the guide**, `Depends-on` (i), whose walk (`docs/runs/plan-walk-<date>.md`) runs every rule of this path
     on an invented project with an invented imported prototype (`example.com`), from `design.py import` to the printed
     `publish` commands.
   - Builds (e) to (h) (the estimator, the status and the report, the baseline and scope changes, the ceremonies) stay
     specified and are not needed for this path: rule 25's `publish` does not wait for them, and a milestone's `Target:`
     stays the person's date or `(verify)` (rule 6). Each runs later, in the order rule 27 gives, (e) then (f), (g), (h).
   Each build is tests first, from the default branch, about 600 changed lines or fewer, with its own ADR naming the
   protected classes it changes and citing ADR-0269 and ADR-0454, one fragment under `changelog.d/` where it changes an
   installed file, and the person's `Approve: <head> SPEC-0043` (and for (k) `Approve: <head> SPEC-0037`) on this pull
   request first.
7. **Tests (for the builds).** Invented pages and sources only, `example.com`, in `tmp_path`, no network:
   - (k): a fixture version `i1` with a complete map gives `docs/sources/<slug>-prototype-i1.md` with the four header lines
     in order, one heading per mapped row in the map's order, the page's title, headings, labels, button and link texts,
     field names, placeholders and `role="alert"` texts one per line, no script or style text, `picture: <file>` for a
     picture page and nothing for an `out:` row; a second run refuses the existing file and leaves it byte for byte; a
     version with a missing file, an unmapped page or an unknown state is refused naming the rule and writes nothing; a
     missing or malformed `--slug` exits 2 naming `--slug`; no test opens a page; `check_plan.py` (once (b) merged)
     passes the written header;
   - (d): a `Kind: design` source with three headings and requirements citing two prints `2 of 3` in-scope source lines
     and fails naming the uncited location; the same headings in a source of another kind are not counted;
   - (c): a source covering `form/default` and an inventory with `form` `error` and `empty` `yes` and `loading`
     `n/a: <reason>` gives exactly two open questions with `(verify)` and the screen's location; `render` prints them
     under `Open questions for the person` after the conflicts; `validate` refuses one with an empty `sources`;
   - (i): `publish` runs with no estimator file and prints its commands; (j): the guide walks the path.
8. **Not in this amendment.** Rules 12 to 24 of SPEC-0043 and SPEC-0037's rules 1 to 12 and 14 do not change. No workflow
   changes here; build (b)'s one governance step is the owner's commit. No session confirms a plan, approves a spec or a
   design, or creates a GitHub object: `publish` prints `gh api` commands and runs none (rule 25).

## Contexts

- kit: installed, so every project can turn its sources and its imported prototype into a plan.
- github: `check_plan.py` is one governance step; `publish` prints `gh api` commands and runs none.
- local: the same commands on a laptop.
- personal: the same files, and `publish` writes through `forge.py` `FilesForge`.
- stacks: not applicable; no test or build step of a stack changes.

## Residual

- 2026-11-12: the source file copies a customer's visible text out of `docs/design/imported/`; the guard of rule 3 finds
  secrets and personal data by pattern only, so what remains is the person's call before the plan is drafted
  (due 2026-12-31).
- 2026-11-12: a state the prototype does not show becomes an open question only if the inventory lists it `yes`; a state
  that neither the inventory nor the prototype names is not asked (due 2026-12-31).
- 2026-11-12: without builds (e) to (h) a published plan carries no estimate, status or scope-change control; its targets
  are the person's dates or `(verify)` (due 2026-12-31).

## Questions

Each reading is the most conservative one, and applies until a person rules.

- Q-1073-1: the brief names `docs/sources/<slug>-prototype-i<n>.md` but no setting holds a project slug. Reading: the
  person gives it with `--slug`, a lower-case slug (`[a-z0-9][a-z0-9-]*`), required, with no default.
- Q-1073-2: which elements are "messages". Reading: elements with `role="alert"` or `role="status"` only; any other text
  of the page is left out, so nothing is read in that the brief did not list.
- Q-1073-3: which states are asked. Reading: the states the inventory gives the screen as `yes` that no heading covers;
  a state marked `n/a: <reason>` was settled by the person's `Approve: inventory` and is not asked again.
- Q-1073-4: rule 27 has (d) `Depends-on` (c); the brief runs them in parallel. Reading: parallel, both `Depends-on` (b),
  which they share `check_plan.py` with; (d)'s tests use their own fixtures of rule 7's file shapes.

## Applied

2026-11-12 (from `date -u`), brief #1079, ADR-0460: items 2 to 6 are written into the texts of
`docs/specs/0043-a-project-s-plan-is-drafted-from-its-sources-and-tracked-with-calibrated-ranges.md` (rule 2a and the
additions to rules 6, 10, 11 and 27, and a `## Contexts` section, amendment 142) and
`docs/specs/0037-a-project-s-design-phase-delivers-a-click-through-prototype.md` (rule 13). Two changes from the text
above, each following a ruling or the code: rule 2a reads every visible text of a page (all text outside `script`,
`style` and `template` elements, in document order), the owner's answer to `Q-1073-2` on #1080
(https://github.com/gbvraju/agk/pull/1080#issuecomment-6815621344), which came before this file merged; and the command
is `design_import.py source`, as build (k) built it (ADR-0458), where item 2 wrote `design.py source`.
