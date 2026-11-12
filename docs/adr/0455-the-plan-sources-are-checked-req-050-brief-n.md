# ADR-0455: The plan's sources are checked, and a project with no plan passes

- Status: Proposed
- Date: 2026-11-12
- Deciders: maintainers
- Related: SPEC-0043, ADR-0269, ADR-0454, amendment 163, brief #1074, brief #1073, plan #661
- Requirements: REQ-050

## Context

SPEC-0043 (Approved, REQ-050, ADR-0269) drafts a project's plan from the source documents under `docs/sources/`, and
amendment 163 (brief #1073, ADR-0454) orders its plan path: (b) the sources first, then (c), (d) and (k) in parallel. On
the default branch at 05cc7f0 there is no `scripts/agk/check_plan.py`, so nothing checks that a source carries the header
of rule 1, that a design link of rule 2 is complete, or that a location of rule 1 resolves. This is build (b).

## Decision

1. `scripts/agk/check_plan.py` (new, installed: `verbatim` in `kit/manifest.json`; files only, no network, nothing
   written) fails, naming the rule and the file and never a value:
   - rule 1: a file under `docs/sources/` (any depth) that is not `.md` or `.txt` or not UTF-8 text; a header line
     `Source:`, `Kind:`, `Version:` or `Date:` that is missing or empty; the four lines out of order; a `Kind:` outside
     `sow`, `brd`, `prd`, `design`, `charter`, `other`; a `Date:` that is not a real `YYYY-MM-DD` date; and a header that
     is not followed by one blank line;
   - rule 2: a `docs/sources/design-links.md` whose `Kind:` is not `design`, that has no table with the columns `Name`,
     `Link`, `Version` and `Frames`, or a row of it with an empty value or a `Link` that does not start with `https://`,
     naming the row by its number. No link is opened.
2. With no problem it prints `ok plan (no plan)` when `docs/plan/` does not exist (rule 10), so a project without a plan
   sees no change, and `ok plan sources` when it does: the plan's own rules 9 to 11 are build (d)'s.
3. `check_plan.header(text)` returns a source's four header values (or `None`), and
   `check_plan.location_problem(root, location)` resolves a location of rule 1: `<file>:<line>` (a line of the file),
   `<file>#<heading>` (the exact text of a Markdown heading of a `.md` file, outside a fenced block), each with the file
   under `docs/sources/`, and a charter's `docs/adr/<NNNN>-project-charter.md#Milestones` (the file name of
   `playbook.py` `CHARTER_NAME`, with a numbered `**Milestones**` item in its Decision). Builds (c) and (d) import both.
   `playbook.py` is kit-only, so the pattern is kept in `check_plan.py` and a test holds it equal to the playbook's.
4. `agk.mk`'s `agk-governance` target runs it. The governance workflow runs each check as its own step; its step after
   `check_design` is the owner's commit (`Q-1074-1`), since a builder never changes a workflow.

Protected path classes changed: `scripts/agk/` (`check_plan.py`), `tests/kit/` (`test_check_plan_sources.py`),
`agk.mk` (one line of `agk-governance`) and `kit/` (`kit/manifest.json`, one `verbatim` row; `kit/hashes.json` as
`kit_hashes.py` prints it). `.github/` (the workflow step) changes only by the owner's commit.

## Consequences

A source without its header, or a design link without its version, frames or `https://` address, fails governance
before any plan is drafted from it, and every later build resolves a location through one function. A project with no
`docs/sources/` and no `docs/plan/` prints one `ok` line and nothing else changes for it.

## Residual

- 2026-11-12: until the owner adds the workflow step, CI's governance job does not run the check; `make governance`
  and `prepush.py` do (due 2026-11-30).
- 2026-11-12: a `.gitkeep` or other non-text file under `docs/sources/` fails rule 1 as written (due 2026-12-31).
