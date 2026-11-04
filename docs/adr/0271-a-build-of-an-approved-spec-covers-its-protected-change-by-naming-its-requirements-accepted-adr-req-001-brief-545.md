# ADR-0271: A build of an Approved spec covers its protected change by naming its requirement's Accepted ADR (REQ-001, brief 545)

- Status: Proposed
- Date: 2026-11-04
- Deciders: maintainers
- Related: ADR-0247
- Requirements: REQ-001

## Context

Principle 1 ("A protected change requires an ADR in the same PR"), `CLAUDE.md item 3` (kept on
`config/core-rules.md` since ADR-0247) and `scripts/agk/check_protected_changes.py`
(`covering_adrs`, which counts only an ADR added or modified in the change set) make every build
write an ADR of its own. Plan #542 measures this as about a third of the document work of a build.
The owner ruled D1 on plan #542 (2026-11-04, comment 6635044641), quoted as data: "one ADR per
requirement, written at intake; a build records its decisions in the PR body and writes a new ADR
only when it changes a decision." This ADR is the decision that changes the rule, so it is written
in the old way.

## Decision

1. Principle 1 becomes: "A protected change requires an ADR in the same PR, or, for a build of an
   Approved spec, a `Covered-by:` line naming that spec's Accepted ADR, which names the class."
   `CLAUDE.md item 3` on `config/core-rules.md` carries the same clause after its own text. Nothing
   else in those files changes.
2. `check_protected_changes.py` reads the pull request body from `--body FILE`, or from the file
   that `AGK_PR_BODY` names (prepush passes the body that way). Without a body it works as before.
   With one, a change set that no ADR of its own covers still passes when all of these hold:
   - the body has exactly one line starting `Covered-by:`, and it is `Covered-by: ADR-nnnn`;
   - that ADR is a file `docs/adr/nnnn-*.md` on the merge base whose own first `- Status:` line
     (`common.STATUS_LINE`) is `Accepted` there (an ADR added in the change set, or one whose status
     the change set raises, never counts), and the change set does not delete or rename it;
   - its text on the merge base names every changed protected class as the whole name in
     backticks (`` `kit/` ``), as an ADR's `Protected classes:` line lists them; a passing mention
     (`myconfig/`, `` `tests/kit/` `` for `kit/`) does not name a class;
   - its `Requirements:` line names a requirement that the body's `Advances:` line also names;
   - no changed path is under `constitution/` or `.github/workflows/`, or is
     `config/reviewers.yaml`, the ruleset `kit/templates/ruleset.json` (which `scripts/agk/ruleset.py`
     applies) or `.github/CODEOWNERS`.
   Every other case fails as before, with one line naming what is missing (the rule or the path
   class, never a value). An ADR in the change set still counts as before.
3. The governance workflow passes the body file it already writes (`$RUNNER_TEMP/pr-body.md`) to
   the check with `--body`, and `prepush.py --body FILE` sets `AGK_PR_BODY` for its governance step.
   Because the step now reads the body, it becomes a body step (brief #216): it runs on an edited
   description too, and `full_run.py` lists it in `BODY_STEPS`, so a full run that failed only
   there is cured by editing the body and the partial run repeats the whole check and decides.
4. The constitution, `config/reviewers.yaml`, the workflows, the ruleset
   (`kit/templates/ruleset.json`) and `.github/CODEOWNERS` still need an ADR in the same PR. A build that changes a decision of its spec or ADR writes a new ADR. The `Decisions
   taken:` line of the PR body carries the build's decisions, and the verdict reads it.
5. The brief template and the session rules (new session rule 36) say when to use `Covered-by:` and
   when to write an ADR, in one paragraph. The conductor's agent file says that the `Final:` lines
   of a build that used `Covered-by:` name no ADR, so a verdict clears the head directly once green.

Protected path classes this pull request changes: `constitution/`, `config/`, `.claude/`,
`.github/`, `scripts/agk/`, `tests/kit/`.

## Consequences

A build of an Approved spec writes no ADR and makes no status commit for one. The check now reads
the PR body, so a `Covered-by:` line added by editing the body is read by the partial run of that
edit, which repeats the whole check on the same head. An Accepted intake
ADR must name every protected class its builds will change; one that does not leaves those builds
writing an ADR of their own, as today.

## Residual

- 2026-11-04: an intake ADR that names a class only in prose, not in backticks, covers no build;
  such builds write an ADR of their own, as today.
