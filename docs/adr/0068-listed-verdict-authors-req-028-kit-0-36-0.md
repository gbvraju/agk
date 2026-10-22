# ADR-0068: only a listed author's comment is a verdict (REQ-028, SPEC-0021), kit 0.36.0

- Status: Accepted
- Date: 2026-10-21
- Deciders: maintainers
- Related: ADR-0067, ADR-0064
- Requirements: REQ-028

Protected classes: `scripts/agk/`, `tests/kit/`, `kit/`, `.claude-plugin/`, `agk.toml`

## Context

On a public repository anyone can post a comment that starts `Verdict: cleared <sha>`, and the metrics, the facts and the report count it, because SPEC-0007 rule 4 reads a verdict from "any author". SPEC-0021
(Approved, #118) makes a verdict count only when its author is a listed verdict author, and splits its build in three by the maintainers' rule of about 600 changed lines of code and tests. This is the first part,
L3a: rules 5 and 6 and criteria AC4 and AC5. The covered final commit and its check are L3b, the measured clearance is L3c. The tests were written first and run on unchanged `main` (21 failed, 2 passed, the 2 being
the guards; the output is in the pull request body).

## Decision

1. **The list** (SPEC-0021 rule 5): `reviewers.verdict_authors(root)` returns the listed authors, lower case without `@`: the optional top-level `verdict_authors` list of `config/reviewers.yaml` when present
   (a flow list of user handles, with or without `@`), otherwise the user handle of the team `maintainers`. A team handle (`@org/slug`) lists nobody, as does an unreadable or invalid file (fail closed). The
   installed placeholder `@REPLACE-ME` is never a listed author, in the list or as the maintainers handle, because `REPLACE-ME` is a valid GitHub login a stranger could own (Q-K4-221, ruled not as read).
2. **The reader** (`metrics.verdicts(comments, authors)`): with a list, only a comment whose `user.login` is listed (compared without regard to case) is a verdict; a comment with no readable author is not;
   an empty list returns `None`, which every caller reads as unknown. Without the argument nothing is filtered (the unit tests of the forms, and any caller that has no list). `metrics.py` passes the list read
   from the repository root; `facts.py` passes the same list (`metrics.verdict_authors`) and reads `"unknown"` for `verdicts` when nobody is listed (SPEC-0021 rule 6). `review_rounds`, `rejected`,
   `rejected_verdicts`, `merged_head_cleared` and `cost_class` follow from the reader, so the existing `Verdict: cleared` reading has the gap closed too.
3. **The check** (`reviewers.py`): the top level accepts a flow list (a mapping is still refused); `verdict_authors` must be a list of user handles (no `/`, no spaces); `--check` fails naming the setting
   `verdict_authors`, never a handle, when nobody is listed, the placeholder included. The schema check of `validate` and the other modes (`--codeowners`, `--check-codeowners`) are unchanged, so only
   `--check` (and the governance step that runs it) fails while the placeholder stands.
4. **Amendment 33** (`docs/runs/proposed-spec-amendments-33.md`) is applied to SPEC-0001 rule 12, SPEC-0007 rule 4, SPEC-0009 rules 14 and 16, and SPEC-0011 rule 5. The getting-started guide gains the sentence
   a project with a team handle needs.
5. **Tests, first** (`tests/kit/test_verdict_authors.py`, new; then 7 more for the placeholder, run red on the first head): the three verdict forms by a listed and an unlisted author, case and `@`, a comment with no author, the unfiltered call, the metrics with a listed author and
   with a stranger alone, the facts, the list, the user handle, the team handle, a missing and an unreadable file, `unknown` in the metrics and the facts when nobody is listed, `--check` with a list, with a user
   handle and (5 cases) naming the setting, and a top-level mapping still refused. The tests that install the kit and run governance set a real handle first, as step 4 of the getting-started guide does (`set_handle` in `tests/kit_dev/conftest.py`). The recorded fixtures of the facts gain a listed author (`verdict_authors: [reviewer]`) and a `user` in their comments; their goldens
   change only in the commit and in nothing else.
6. **Kit 0.36.0**: the manifest `kit_version`, `kit/hashes.json` (the hashes of `metrics.py`, `facts.py` and `reviewers.py`), the plugin version and `version` in this repository's `agk.toml` (ADR-0050 decision 7). No
   file is added to or removed from the manifest.

## Consequences

- A project whose `maintainers` is a team handle, or still the placeholder, must add `verdict_authors` or a real handle before its next `make governance` passes (`reviewers.py --check` names the setting);
  until then its verdict fields read `unknown`. This repository (a user handle) needs no change. Getting-started step 4 and its troubleshooting line say so.
- The pilot gets this on its next `agk upgrade`; its team handle, if it is one, needs the list first.
- The author rule keeps strangers out; it cannot tell the implementation session from the maintainers when both post from one account (SPEC-0021 residual).

## Questions

| Id | Question | Reading taken |
| --- | --- | --- |
| Q-K4-221 | The installed `config/reviewers.yaml` maps `maintainers` to the placeholder `@REPLACE-ME`; is it a listed author? | Ruled by the maintainers (the #119 verdict), not as read: never. `REPLACE-ME` is a valid GitHub login a stranger could own. With the placeholder nobody is listed, the verdict fields read `unknown` and `reviewers.py --check` fails naming the setting. |

## Residual

None.
