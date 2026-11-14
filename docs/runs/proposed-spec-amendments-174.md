# Proposed spec amendments 174 (SPEC-0043; REQ-050)

Date: 2026-11-14 (from `date -u`). Approved specs change only through a proposal like this one (principle 6). Written for
ADR-0515 (brief #1216), which stays `Proposed` for the maintainers' decision. The path:
`docs/specs/0043-a-project-s-plan-is-drafted-from-its-sources-and-tracked-with-calibrated-ranges.md`. Brief #1216
reserved ADR-0515 and amendment 174. This pull request does not edit the spec: the owner decides the lines below with
`Approve: <head> SPEC-0043` on a pull request that applies them; no session posts that line.

The sentence (brief #1216): "A project that starts from an idea reaches a published plan by the same path as one that
starts from a prototype: its vision, charter, signed-off kit design and accepted stack become planning sources."

## What is on the default branch today

Read in the code by this session on `origin/main` (76fcd1b):

- `scripts/agk/design_import.py` `main` refuses any `--version` that is not an imported version `i<n>` (exit 2), so a
  kit version `docs/design/prototype/v<n>/` signed off by SPEC-0037 rule 9 cannot become a source.
- No script writes a `docs/sources/` file from `constitution/vision.md`, the charter ADR of SPEC-0013 or the stack ADR;
  rule 1 lets a session cite only the charter's `#Milestones` item in place.

## Items

1. **Rule 2a, one amendment line.** "`design_import.py source` also takes a kit version `--version v<n>`: it writes once
   `docs/sources/<slug>-prototype-v<n>.md` with the header `Source: kit prototype v<n>`, `Kind: design`,
   `Version: v<n> <the version's sign-off digest>`, `Date:`, then one `## <screen>/<state>` heading per page
   `<screen>--<state>.html` of the version folder, in file-name order, with the page's visible text as above; it
   refuses, writing nothing, a version that is not there, one with no `design` row of `docs/design/signoffs.md` that
   records the digest its folder has now, and one with no such page."
2. **A new rule 2b, the vision and architecture sources.** "`python3 scripts/agk/plan_sources.py vision` writes once,
   as a new file only, `docs/sources/vision.md` (`Source: vision and project charter ADR-<n>`, `Kind: charter`,
   `Version: ADR-<n> <digest>`, `Date:`) holding `constitution/vision.md` and then the Accepted charter ADR
   `docs/adr/<n>-project-charter.md`, both unchanged; `plan_sources.py architecture` writes once
   `docs/sources/architecture.md` (`Source: stack ADR-<n>`, `Kind: other`) holding the Accepted stack ADR
   `docs/adr/<n>-stack-options.md` unchanged. The ADR read is the highest-numbered file of that name. Each refuses with
   exit 1, naming the rule and the file and writing nothing, an ADR that is not Accepted, a missing ADR or vision and
   an existing target file."
3. **No other change.** Rules 1 and 3 to 27 stay as they are: the three files are ordinary sources, so the data guard of
   rule 3 scans them first, `plan_intake.py states` reads the kit source's headings and `check_plan.py` checks the
   headers. `components` (SPEC-0037 rule 16) still takes an imported version only.
4. **Tests.** `tests/kit/test_design_import_source.py`: a signed-off `v1` becomes a design source; an unsigned one, one
   changed after its sign-off, a missing one and an existing file are refused. `tests/kit/test_plan_sources.py`: the
   vision and architecture sources are written once; a Proposed, missing or newer Proposed ADR and a missing vision
   are refused; `plan_intake.py states` and `check_plan.py` read the three sources.
