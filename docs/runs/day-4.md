# Run report: day 4, item 2 (PR #9, ADR-0006)

Date: 2026-10-14 (from `date -u`). Tests first: the new and changed tests were written before the code; the first
run was red (25 failures), then green.

## Action SHAs (rule: find from the official repository, record the source)

Source for each: `git ls-remote https://github.com/<owner>/<repo> refs/tags/<tag> refs/tags/<tag>^{}`, run from
this session on 2026-10-14. The tags are lightweight (no peeled `^{}` entry), so the listed SHA is the commit.

| Action | Tag | Commit SHA | Official repository |
| --- | --- | --- | --- |
| actions/checkout | v4.4.0 | 11d5960a326750d5838078e36cf38b85af677262 | github.com/actions/checkout |
| actions/setup-python | v5.6.0 | a26af69be951a213d495a4c3e4e4022e16d87065 | github.com/actions/setup-python |
| gitleaks/gitleaks-action | v2.3.9 | ff98106e4c7b2bc287b24eaf42907196329070c7 | github.com/gitleaks/gitleaks-action |

Each is the highest patch tag of the major the workflow used before (v4, v5, v2). Not checked: signatures,
attestations, or whether a newer major exists (checkout `v7`, setup-python `v7` and gitleaks-action `v3` tags were
seen in the listing and not adopted).

## Decisions taken

- Pin to the latest patch of the existing majors; do not jump majors in a pinning PR (ADR-0006 decision 1).
- `check_specs.py` counts any change to an Approved spec, including Status-only or deletion, as needing an amendment
  (decision 3).
- An amendment counts only when added or modified in the same PR and when its text contains the spec's path
  (decision 3).
- Installed `tests/kit/` gains `test_check_specs.py`; the manifest lists the new script and test; kit version 0.2.0.

## Questions

- Q-K1-16: should a newer major of an action be adopted at pinning time (checkout v7, setup-python v7, gitleaks-action
  v3 exist as tags)? I kept the existing majors; changing a major is a behaviour change for maintainers to approve.
- Q-K1-17: the `gitleaks-action` licence terms for organisations remain unconfirmed (ADR-0006 residual); the previous
  `(verify)` note on the workflow line is replaced by the tag comment. Keep it as a residual only?

## Verified

See the PR body.
