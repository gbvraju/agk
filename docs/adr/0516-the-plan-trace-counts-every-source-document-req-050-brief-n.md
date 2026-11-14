# ADR-0516: The plan trace counts every source document

- Status: Accepted
- Date: 2026-11-14
- Deciders: maintainers
- Related: SPEC-0043 rules 9 to 11, amendment 175, ADR-0457, ADR-0502, brief #1217, plan #661
- Requirements: REQ-050

## Context

Rule 11 of the plan check counts the locations listed under `In scope` in `docs/plan/scope.md` and the screen headings
of a `Kind: design` source, and rule 10 fails only those that no requirement cites. A document under `docs/sources/`
that no scope line lists therefore never enters the count. In a trial on kit 0.64.1 (both of the owner's scenarios:
planning from a vision, and planning from a working prototype) `check_plan.py --trace` reported 402 of 402 in-scope
source lines covered while five source documents had no requirement citing them, because the scope list held one line;
an independent review found about 570 gaps the trace had called covered.

## Decision

1. Once `docs/plan/` exists, `scripts/agk/check_plan.py` (rule 10) fails each file under `docs/sources/`, at any depth,
   that has no location cited by a requirement's `Source:` line and resolving (rule 1's location test), unless a list
   line under the `Out of scope` heading of `docs/plan/scope.md` names the file by its own path, a backticked span with
   no `:<line>` or `#<heading>`, and gives a reason, that is text beside its spans. The failure is one line,
   `FAIL plan: <file> is a source no requirement cites (list it out of scope or cite it)`, naming the file and never
   its text. A project with no `docs/plan/` is not checked (`ok plan (no plan)` as before).
2. `--trace` prints, after the matrix, one line per source file, `<file>: <a> of <b> headings or rows cited`. The units
   of a Markdown file are its headings outside fenced blocks and its table rows after a separator line; those of a text
   file are its non-blank lines after the header. A unit counts in `<a>` when a resolving `Source:` location is
   `<file>#<heading>` of it or `<file>:<line>` of its line. The line is information and never fails the plan.
3. Rule 11's coverage line is unchanged.
4. With the maintainers' answer to `Q-1217-1` ("count the components' and the OpenSpec acceptance citations as citing
   their file"), two more resolving locations cite a source, for items 1 and 2: a line of a requirement block ending
   with ` (<location>)` whose file is a `Kind: openspec` source (amendment 166's acceptance line), and a `Source:` line
   of a brief file under `docs/plan/briefs/` that carries a `Component:` line. `scripts/agk/plan_intake.py render`
   writes `Component: C<n>` on the one brief whose `component` names a shared component, and the component's `sources`
   as that brief's first `Source:` lines, so a plan rendered from an imported prototype cites its components file.

## Consequences

A plan whose requirements leave a whole source document uncited no longer passes as covered: the person cites it or
lists it out of scope with a reason, and a thinly cited document is visible in the trace. A plan rendered from an
imported prototype or an OpenSpec file passes as before, since the kit's own citations count (decision 4); an acceptance
line into another kind of source, a milestone's sources and a brief's `Source:` line without a `Component:` line do not.
Two existing tests, whose plans held only a `docs/plan/` folder and one source, gained an `Out of scope` line for it.
Protected path classes changed: `scripts/agk/` (`check_plan.py`, `plan_intake.py`), `tests/kit/`
(`test_check_plan_uncited.py` new; `test_check_plan_sources.py` and `test_check_plan_trace.py` fixtures;
`test_plan_slices.py` asserts the component's brief lines) and `agk.toml` (the test map's `check_plan.py` entry).

## Residual

- 2026-11-14: none (`Q-1217-1` answered by the maintainers on #1224).
