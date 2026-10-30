# ADR-0188: the kit reports which of its checks and rules ever fired (REQ-011, brief 328)

- Status: Proposed
- Date: 2026-10-30
- Deciders: maintainers
- Related: ADR-0177
- Requirements: REQ-011

Protected classes: `scripts/agk/`, `tests/kit/`, `tests/kit_dev/`

## Context

Brief #328 (priority 2): brief #278 wants a smaller kit core, but retiring a check without evidence risks losing the one that
catches a rare, costly mistake. Before any rule is merged or retired, the kit needs a measured list of which checks ever failed
a pull request, which rules a verdict ever cited, and which never fired. This is a report only: it changes no rule and no check.
The tests were written first (`tests/kit/test_core_audit.py`, 27 failed at the first checkpoint of the pull request).

## Decision

1. **`scripts/agk/core_audit.py [--since DATE] [--json] [--write]`** (answer 1). It reads with `gh api` GET only (through the
   reader of `metrics.py`), or saved responses with `--api-dir` named as in SPEC-0007 rule 20, and the files of the
   repository. It writes only to stdout, posts nothing and runs no model. `--authors` overrides the `verdict_authors` of
   `config/reviewers.yaml`; `--repo` the repository of the `origin` remote; `--today` the date from `date -u`.
2. **The checks.** A governance check is a named step of `.github/workflows/governance.yml` whose `run:` calls a kit script,
   `agk.mk` or the secret scanner, in workflow order (the header of that workflow names one step per check). For each, the
   number of pull requests opened in the period whose `governance` check run failed on that step, counted once per pull
   request over all its commits, read from the steps of the run's job. A failed step that is no check of the current workflow
   (renamed or removed) is listed apart, never dropped. A `proof` failure is not counted.
3. **The rules.** For each session rule (`config/session-rules.md`) and each spec rule (the numbered items of the `## Rules`
   section of `docs/specs/NNNN-*.md`), the number of `Verdict:` comments by a listed author that cite it, as `session rule N`,
   `session rules N and M`, `rule N of the session rules`, `SPEC-NNNN rule N` or `SPEC-NNNN rules N, M and K`; a verdict counts
   once per rule. A cited rule that the current text no longer has is still listed.
4. **What never fired, and the totals.** The checks and rules with zero refusals in the period, and the numbers of ADRs, specs,
   requirements and scripts.
5. **Never zero when unread (answer 3).** A pull request whose commits, check runs, failed job or comments cannot be read, a
   pull request with no governance run at all, and a failed run whose job shows one combined step, are counted as unread. With
   any unread pull request a count is `at least N`, a zero is `cannot-check`, and neither is listed as never fired; an
   unreadable list of pull requests makes every count `cannot-check`.
6. **The page (answer 2).** Only `--write` writes `docs/runs/core-audit-<date>.md`, whose first paragraph says it is evidence
   for #278, not a decision; it never overwrites the page of a day (exit 1). The person files any follow-up.
7. **Not installed in projects.** The script audits the kit itself: it is listed with the kit-only scripts of
   `tests/kit_dev/test_kit_manifest.py`, not in `kit/manifest.json`, so nothing changes for a project.
8. **Readings taken where the brief leaves a point open** (questions on the pull request): the period counts pull requests by
   the date they were opened; the guide line in `docs/guides/reference.md` waits for the answer to Q-328-1, since open pull
   request #323 changes that file. Flow mode: fragment `changelog.d/core-audit.md`; no version bump.

## Consequences

- A maintainer can choose a smaller core from a measured list, and a check that never fired can be named with evidence.
- A live run reads each pull request's commits, check runs, failed jobs and comments: about three seconds a pull request
  (26 pull requests in 87 seconds on 2026-10-30), so the whole history takes several minutes.

## Residual

- 2026-10-30: GitHub keeps workflow runs for a limited time, so the oldest pull requests read as `cannot-check`, never zero;
  a bare `rule N` with no spec or `session` before it, and a citation in a solo-mode `Confirmed:` comment, are not counted
  (due 2026-12-31).
