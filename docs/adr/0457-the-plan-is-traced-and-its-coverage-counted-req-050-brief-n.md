# ADR-0457: The plan is traced to its sources, and its coverage is counted

- Status: Accepted
- Date: 2026-11-12
- Deciders: maintainers
- Related: SPEC-0043, ADR-0269, ADR-0454, ADR-0455, amendment 163, brief #1076, brief #1074, plan #661
- Requirements: REQ-050

## Context

SPEC-0043 (Approved, REQ-050, ADR-0269) rules 9 to 11 trace a project's plan from each source location to its
requirement, spec rule, brief, pull request and test, fail the gaps, and end with coverage counts. Amendment 163 item 4
(brief #1073, ADR-0454) counts each `## <screen>/<state>` heading of a `Kind: design` source as one in-scope location.
Build (b) (brief #1074, ADR-0455) added `scripts/agk/check_plan.py` with the sources and the no-plan pass; nothing on
the default branch at 3e38560 prints a trace or a count. This is build (d), run beside build (c), so its tests write
their own `docs/plan/` files in the shapes of rule 7.

## Decision

1. When `docs/plan/` exists, `check_plan.py` fails, naming the rule and the item and never its text (rule 10):
   - a requirement block, `### <key> <title>` in `docs/plan/requirements-proposed.md` or `### REQ-nnn` in
     `docs/requirements.md`, with no `Source:` line that resolves through `location_problem`;
   - a location of an `In scope` list line of `docs/plan/scope.md` that no requirement's `Source:` line cites, naming
     the line number and the location, and an `In scope` line with no location; a line's locations are its backticked
     spans that start with `docs/`;
   - a `## <screen>/<state>` heading (level two, one `/`, outside a fenced block) of a `Kind: design` source that no
     requirement cites, naming the location (amendment 163 item 4);
   - a `### M<n>` milestone of `docs/plan/milestones.md` that no brief file `docs/plan/briefs/**/<key>.md` names in
     its `Milestone:` line.
   The scope-change check of rule 22 is build (g)'s. A project with no `docs/plan/` still prints `ok plan (no plan)`.
2. It ends with one line `ok plan: <a> of <b> in-scope source lines have a requirement, <c> of <d> requirements have a
   brief, <e> of <f> briefs have a merged pull request, <g> of <h> requirements have a test`, or `plan: ...` after a
   failure (rule 11). `<b>` counts each in-scope location once (a screen heading also listed in scope is one) and each
   `In scope` line with no location. Without `--facts FILE` the last three read `<what>: not read`; with facts whose
   `pull_requests` is `unknown`, the third does.
3. `--trace` prints, before the checks, a table `Location | Requirement | Spec rule | Brief | Pull request | Test`, one
   row per in-scope location and per other cited location, `none` where a link is missing (rule 9). A spec rule is
   `SPEC-nnnn rule N` for each numbered rule under `## Rules` of a spec whose `Requirements:` names the requirement and
   whose text names it, or `SPEC-nnnn` when no rule does. A test is a file of `common.markers_for`, the reading that
   `traceability.py` prints, not a copy. A pull request is `#n` of a merged pull request of the facts whose `brief` is
   the brief's issue number, read from `--numbers FILE`, rule 25's key-to-number object; without `--facts` it is
   `not read`. Nothing is written: the trace is printed only (principle 5).
4. A `--facts` or `--numbers` file that cannot be read as the right JSON exits 2 naming the option, never its text.

Protected path classes changed: `scripts/agk/` (`check_plan.py`) and `tests/kit/` (`test_check_plan_trace.py`, new,
and `test_check_plan_sources.py`, one expectation: with `docs/plan/` the last line is the coverage line, no longer
`ok plan sources`). `kit/` (`kit/hashes.json`) only as `kit_hashes.py` prints it.

## Consequences

A project with a plan sees, on every governance run, which source lines, mapped screens and milestones have nothing
planned for them, and a count that proves it; `--trace` shows the whole chain on demand. A project without a plan sees
no change. Build (c)'s `render` must write the shapes item 1 reads.

## Residual

- 2026-11-12: with a plan, every block of `docs/requirements.md` needs a `Source:` line, including requirements written
  before the plan (due 2026-12-31).
- 2026-11-12: the requirement-to-brief and requirement-to-test counts read `not read` without `--facts`, as rule 11
  says, though both come from files (`Q-1076-1`) (due 2026-11-30).
- 2026-11-12: the scope line's location form and the requirement block heading are this build's reading of rule 7,
  for build (c) to match (`Q-1076-2`) (due 2026-11-30).
