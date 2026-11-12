# ADR-0473: An OpenSpec file is imported unchanged and read by a script into the plan draft

- Status: Proposed
- Date: 2026-11-12
- Deciders: maintainers
- Related: SPEC-0043, ADR-0269, ADR-0472, ADR-0462, ADR-0461, ADR-0456, amendment 166, amendment 164, brief #1109,
  brief #1108, brief #1081, brief #1090, plan #661
- Requirements: REQ-050

## Context

Amendment 166 (ADR-0472, brief #1108) makes an OpenSpec functional file a structured plan source. On the default
branch at 7a27983 no file reads one: `check_plan.py` `KINDS` is `sow, brd, prd, design, charter, other`, and the
`/agk:plan-intake` skill reads every source as free text. Since then amendment 164's personas (build (p), ADR-0462) have
merged, so every requirement of the proposals names a `persona` and a `story`. Brief #1109 builds amendment 166 items 2
to 4 in one pull request, as build (a) of the brief, under the command names `openspec-import` and `openspec`.

## Decision

1. `check_plan.py` `KINDS` gains `openspec`, before `other` (rule 1).
2. `plan_intake.py openspec-import PATH --slug SLUG` is amendment 166 item 2 (rule 2b) as written: a combined `.md`
   file, or a folder that holds `specs/`, whose `.md` and `.txt` files are copied under
   `docs/sources/openspec-<slug>/` at their relative paths, each the rule 1 header (`Source: OpenSpec <relative path>`,
   `Kind: openspec`, `Version: sha256:<digest of the original bytes>`, `Date:` from the clock in UTC), one blank line
   and the original bytes unchanged. Another file, or a link, is printed `skipped: <path> (...)`. `guard.scan_text`
   passes every file before anything is written; a finding exits 1 naming the file, the kind and the position. A slug
   outside `[a-z0-9][a-z0-9-]*`, an existing target folder, a path that is neither, and a file that is not UTF-8 exit
   2, writing nothing.
3. `plan_intake.py openspec --slug SLUG --out FILE` is amendment 166 item 3 (rule 4b), with `openspec-draft`, the
   amendment's name, accepted as the same command. It scans every source first (rule 3), refuses an `--out` inside
   `docs/` or over an existing file, and writes a proposals file that `validate` accepts: each capability one area (the
   heading before a `*Capability ` line in a combined file, `<slug>` of `specs/<slug>/` in a folder), each
   `Requirement: ` heading one requirement (`R1`, `R2`, ... in reading order) with `statement` its text exactly, lines
   joined by one space, and each `Scenario: ` heading one criterion `Given ..., when ..., then ... (<location>)` of
   its `GIVEN`, `WHEN`, `THEN` and `AND` steps, bold or plain, any heading level. A location is `<file>#<heading>`, or
   `<file>:<line>` when the heading repeats in its file. Nothing under `changes/` is a requirement.
4. What the file does not settle is never filled in (item 4): a requirement without a scenario has the criterion
   `(verify)` and an open question; `changing` is `true` for a capability whose `Defined by:` status is `open`, or whose
   slug has a delta spec under `changes/<id>/specs/` outside `changes/archive/`; each live change is one open question
   at its `proposal.md`; a cross-reference `<kind> <number>` in the statement's parentheses becomes a second source only
   when exactly one source has that kind and exactly one heading of it starts with that number, and any other is an
   open question naming its position, never its text.
5. Persona candidates (brief answer 2, since build (p) is on the default branch): the `a <word>` or `an <word>` that
   starts a requirement's first `WHEN` step is a persona, keys `P1`, `P2`, ... in order of first appearance, each with
   `goals` `["(verify)"]` and its first scenario as its source; requirements whose steps name no actor share one persona
   named `(verify)`, with one open question. Each `story` is `As <name>, I want (verify), so that (verify)`, the form
   amendment 164 checks, for the skill or the person to complete from a location.
6. A requirement's `milestone` may be `null` in `validate`; `render` refuses a requirement whose `milestone` is `null`
   (`rule 7: requirements <key>: milestone is not set`), so the skill sets every milestone before any file is drafted.
7. `statement` (text or `null`) and `changing` (`true` or `false`) are optional requirement keys, so that a proposals
   file without them validates as before. `validate` refuses a requirement cited to a `Kind: openspec` source whose
   `statement` is `null`, a criterion ending with a `(docs/...)` location that does not resolve, and a `changing`
   requirement in `M1` without an open question citing one of its sources. `render` writes `Statement: <text>` and
   `Changing: yes` after a block's `Story:` line.
8. A heading inside a capability, after its first requirement, that is no capability, requirement or scenario is
   printed `ignored: <file>:<line>: ...` and its bullets are no steps; a heading before the first requirement (a
   title, `Purpose`, `Requirements`) is not read and not printed.
9. The skill imports the file first and, when a `Kind: openspec` source exists, starts from the output of `openspec`,
   adding only milestones, briefs, sizes and screens and never rewriting a requirement the file defines.

Protected path classes changed: `scripts/agk/` (`plan_intake.py`, `check_plan.py`), `tests/kit/`
(`test_plan_openspec.py`, `test_check_plan_sources.py`) and `skills/` (`plan-intake/SKILL.md`). `kit_hashes.py`
reports no change to `kit/hashes.json`.

## Consequences

A customer project that starts from an OpenSpec file gets a plan draft whose requirement texts and acceptance lines are
the file's own, each traced to its heading, and every point the file leaves open is an open question for the person.
The file stays in the customer project's `docs/sources/`, guarded before any agent reads it; nothing of it enters the
kit, whose tests use invented files only. A proposals file without an OpenSpec source validates and renders as before,
except that a requirement's `milestone` may now be `null` until `render`.

## Residual

- 2026-11-12: an actor is only the `a <word>` or `an <word>` that starts a `WHEN` step; a `WHEN` step that starts
  another way gives the `(verify)` persona, for the person to name (due 2026-12-31).
- 2026-11-12: amendment 166 item 5 (scenario coverage in rule 11, build (u)) is not in this build (due 2026-12-31).
- 2026-11-12: the amendment's rule texts are not written into SPEC-0043 here, since the brief's `Touches:` does not name
  the spec; the maintainers' approval of amendment 166 places them (due 2026-11-30).
