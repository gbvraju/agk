# ADR-0472: An OpenSpec file is a structured plan source whose requirements and scenarios are read exactly

- Status: Proposed
- Date: 2026-11-12
- Deciders: maintainers
- Related: SPEC-0043, SPEC-0042, SPEC-0037, ADR-0269, ADR-0454, ADR-0469, amendment 163, amendment 164, amendment 166, brief #1108, plan #661
- Requirements: REQ-050

## Context

A customer project can arrive with an OpenSpec functional file: capabilities, each with requirements written as `SHALL`
or `SHALL NOT` text and scenarios written as `GIVEN`, `WHEN`, `THEN` and `AND` steps, either combined in one Markdown
file or as the standard `openspec/` folder of `specs/<capability>/spec.md` files and `changes/<id>/` proposals (brief
#1108). SPEC-0043 (Approved, REQ-050, ADR-0269) drafts a plan from `docs/sources/`, but its rule 1 allows only the kinds
`sow`, `brd`, `prd`, `design`, `charter` and `other`, and its skill reads every source as free text, so a file that already
states each requirement and its acceptance scenarios would be read again by a model, with room to drop or reword them. No
file on the default branch mentions OpenSpec. The rule 1 location `<file>#<heading>` already cites a `Requirement:` or a
`Scenario:` heading, and the proposals already carry requirements with criteria and areas with requirement keys
(`plan_intake.py`), which `render` writes as acceptance lines and Draft specs.

## Decision

1. `Kind:` gains `openspec`. `plan_intake.py openspec-import <path> --slug <slug>` copies a combined file or an
   `openspec/` folder under `docs/sources/openspec-<slug>/`, each file's original bytes unchanged after the rule 1
   header it adds (`Version:` the SHA-256 of the original), never over an existing folder, and only after the data guard
   of SPEC-0043 rule 3 has passed every file (amendment 166 item 2).
2. A script, not the model, reads the imported files: each capability becomes one area, each `Requirement:` heading
   one requirement whose `statement` is its `SHALL` text exactly as written, and each `Scenario:` heading one criterion
   `Given ..., when ..., then ...` that ends with its location; the skill starts from that draft and adds only
   milestones, briefs and what the reading leaves open (item 3).
3. What OpenSpec does not settle is never filled in: a requirement without a scenario gets a `(verify)` criterion; a
   requirement of a capability whose change is open is marked `changing` and stays out of `M1` unless the person is
   asked; a cross-reference becomes a second source location only when it resolves exactly, else an open question;
   actors in steps are persona candidates of amendment 164 item 2, and tasks and change deltas are hints and open
   questions, never requirements (item 4).
4. Rule 11 counts scenarios beside source lines, `<a> of <b> scenarios have an acceptance line and <c> a test`, and with
   an imported prototype lists each scenario that names no mapped screen and each mapped screen that no scenario names
   (item 5).
5. The builds run (s) the import, (t) the reading and the draft after (s), and (u) the coverage after (t); the persona
   candidates of (t) wait for amendment 164's build (p) (item 6).

## Consequences

A project that starts from an OpenSpec file gets a plan draft whose requirements and acceptance lines are the file's own,
each traced to its heading, and the person sees every point the file leaves open as a question rather than a guess. The
customer's file stays in the customer project's `docs/sources/` (or, in personal mode, the private state), guarded before
any agent reads it; nothing of it enters the kit. This pull request changes documents only: no code, no test, no workflow
and no protected path class. Each build of item 6 writes its own ADR naming the protected classes it changes, after the
owner's `Approve: <head> SPEC-0043` on this pull request.

## Residual

- 2026-11-12: the reader follows the shape the brief describes and the standard OpenSpec layout; another dialect (other
  step words, a capability without the italic line) reads as free text until a person extends the rule (due 2026-12-31).
- 2026-11-12: a cross-reference resolves only by an exact kind and heading-number match; a looser one is an open
  question for the person (due 2026-12-31).
- 2026-11-12: the readings of `Q-1108-1` to `Q-1108-10` are the owner's to rule (due 2026-11-30).
