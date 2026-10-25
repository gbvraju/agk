# ADR-0127: every flip of a spec needs a person, for one text (REQ-039 build (f), SPEC-0032 rule 5)

- Status: Accepted
- Date: 2026-10-25
- Deciders: maintainers
- Related: ADR-0122, ADR-0110
- Requirements: REQ-039

Protected classes: `.github/`, `scripts/agk/`, `tests/kit/`

## Context

Build (c) of SPEC-0032 (ADR-0122) made a covered `Final:` line that sets a spec to `Approved` count only with an `Approve:` line by a person. While reviewing it the conductor recorded two gaps on #179: a spec
flipped to `Approved` in an ordinary commit passes governance (`check_specs` lets the Draft to Approved flip pass), so only the router's `agk:approve` label and the person's merge stop it; and the sha of
`Approve: <sha> SPEC-<n>` is compared with nothing, so an approval stays valid after later commits change the text. This build (f) closes both. ADR-0127 and amendment 65 were reserved on #179. The tests were
written first (`tests/kit/test_spec_flip_approval.py`); on the unchanged `check_specs.py` 11 of its 14 cases failed.

## Decision

1. **Every flip needs a person.** `check_specs.py --comments FILE [--reviews FILE]` reads the saved comments and review bodies of the pull request. For each spec file the diff adds as `Approved` or whose status
   line it changes to `Approved` (the condition the open-question rule already uses), it fails with `SPEC-<n>: rule 5: no Approve line by an account in spec_approvers` unless a listed person's first line
   `Approve: <sha> SPEC-<n>` is there. `reviewers.approval_shas` returns the shas by spec; `person_approvals` keeps its meaning and now uses it.
2. **For one text.** The approval counts only if the spec file at the head equals the spec at `<sha>` (resolved with `git rev-parse`) apart from its `- Status:` line; otherwise the failure is
   `SPEC-<n>: rule 5: the spec changed after the approved sha`. A `<sha>` that is not a commit counts for nothing. Any one matching line is enough.
3. **No comments file.** Without `--comments` (a local run) the approval is not checked and `check_specs` prints `specs: no comments file; an approval of a spec is not checked`. The governance workflow passes the
   files it already saves (`comments.json`, `reviews.json`); on a push there is no base ref, `check_specs` is skipped as before, and the files are the empty lists the workflow writes.
4. Amendment 65 (`docs/runs/proposed-spec-amendments-65.md`) is applied to SPEC-0032 rule 5 and SPEC-0021 rule 4. A flow-mode fragment `changelog.d/req-039-f-spec-flip.md` records it; no version bump;
   `CHANGELOG.md` and `kit/hashes.json` are as on `main`. The manifest is unchanged.
5. **Readings taken where the brief leaves a point open** (questions in the pull request, the most conservative reading each): "the same as at the approved sha" is read as equal apart from the status line, because
   the status commit itself changes that line; the covered-fix-list check of `check_final_clearance` is not changed (it still demands the line, and `check_specs` now demands the text rule for it too); a spec
   added already `Approved` counts as a flip.

## Consequences

- A person's `Approve:` is for the text they read; a pull request that edits the spec after it needs a new line.
- A flip by an ordinary commit no longer passes governance without the line.

## Residual

- 2026-10-25: until accounts are separated (lane F) a session and a person share one account, so a session could post the `Approve:` line itself; the conductor role file forbids it and the check cannot tell (due 2026-12-31).
- 2026-10-25: the text rule compares whole files apart from the status line, so a reformatting commit after the approval asks for a new line (due 2026-12-31).
