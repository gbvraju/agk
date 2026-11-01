# ADR-0244: The small weekly-report specs become sections of SPEC-0011, by one spec amendment (REQ-039, brief 385)

- Status: Proposed
- Date: 2026-11-01
- Deciders: maintainers
- Related: ADR-0021, ADR-0050, ADR-0051, ADR-0057, ADR-0058, ADR-0063, ADR-0070, ADR-0078
- Requirements: REQ-039

Protected classes: `tests/kit/`. Unprotected classes named by the brief: `docs/specs/` (the amendment
`docs/runs/proposed-spec-amendments-108.md`).

## Context

SPEC-0014, 0015, 0016, 0017, 0019, 0022, 0024 and 0026 each amend the weekly product report of SPEC-0011: its footer, a busy
week's list, the At risk lines, Delivered, the facts artifact, `report.json` and its counts. Together they hold 72 rules, of
which the core audit (brief #328) found 6 ever cited by a verdict, and a reader of the report has to follow nine specs. The
person accepted row 9 of the decision table of plan #278 on 2026-11-01: these eight specs fold into SPEC-0011. The rule for
every merge of that plan: never renumber; a merged number stays as a pointer line. No safety rule weakens.

## Decision

1. **One amendment (answer 1).** `docs/runs/proposed-spec-amendments-108.md` moves each rule of the eight specs into
   SPEC-0011 as a numbered rule of a new section per spec, `### From SPEC-NNNN: <title>`, in the order the specs were approved
   (by their ADRs 0050, 0051, 0057, 0058, 0063, 0070, 0078, then SPEC-0026), numbered 24 to 95 after SPEC-0011's own rules 1
   to 23, the text after the number unchanged. A line under each heading says that a bare `rule N` there is the old spec's
   rule N, so a moved rule keeps its meaning without a word of it changing.
2. **Pointers (answer 2).** Each of the eight files keeps its number, its name, its status and its other sections; its
   `## Rules` section holds one line per old rule, `N. Now SPEC-0011 rule M.`. No spec number is reused or deleted.
3. **Word for word (answer 3).** The schema rules of `report.json` (SPEC-0022) move word for word. No script, workflow,
   golden or schema file changes; nothing about the report's output changes.
4. **Approval (answer 4).** SPEC-0011 keeps its `Approved` status line; a person approves it after the change (SPEC-0032),
   by `Approve: SPEC-0011` on the pull request. The pull request approves nothing.
5. **Tests first (answer 5).** `tests/kit/test_core_report_specs.py` pins the SHA-256 of every old rule's text after its
   number and asserts it at the new number in SPEC-0011, reads the digests back from the base commit where the history holds
   it, asserts that each pointer line names a rule that exists, and runs `check_specs.py` with and without the amendment.
6. **Classes (answer 6).** The change touches `docs/specs/` (by the amendment), `docs/runs/`, `docs/adr/`, `changelog.d/` and
   the protected class `tests/kit/` (the new test, kit-only and not installed). No kit version is bumped and
   `kit/hashes.json` is unchanged.

## Consequences

A reader finds every rule of the weekly report in SPEC-0011. Every existing citation of an old rule still resolves through
its pointer line. Later amendments to the report change SPEC-0011 only.

## Residual

- 2026-11-01: Q-385-1: no amendment number was reserved; 108 is the next free number on the default branch, and if a
  parallel brief takes it first this proposal moves to the next free one (due 2026-11-15).
- 2026-11-01: Q-385-2: the amendment files that amend these specs without rewriting their text (46, 55, 58, 66, 78 and
  later ones) are not folded into the moved text; they keep applying at the new numbers (due 2026-12-31).
