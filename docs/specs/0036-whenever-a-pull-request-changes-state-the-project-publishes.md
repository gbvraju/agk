# SPEC-0036: The router publishes what waits for a person as a small pipeline document in plain words, and every builder pull request says in one sentence what it does for a person

- Status: Draft
- Owner: reviewer group (a team from config/reviewers.yaml)
- Requirements: REQ-043

Status is `Draft` or `Approved`. An Approved spec is owned by its reviewer group; agents propose patches.
Written by the intake of one sentence (SPEC-0012): "Whenever a pull request changes state, the project publishes one small pipeline document saying, in plain words a non-developer understands, which pull requests are ready to merge, which specs wait for approval and how many pull requests are in each state." It is generic and project-agnostic: it names no project, no runtime and no reader, and a GitHub repository, its workflow and `GET` are all it needs. The brief of issue #213 gives six answers; they are the conductor's proposals, and the maintainer ruled only the principle behind them, which the brief records: what a person sees must be in business meaning, never a raw verdict line or a sha. Every other point that needs the maintainer's ruling is a question under `## Open questions`, not a decision. The router knows the state of every pull request the moment it changes (one `agk:` label each, SPEC-0032), but nothing outside GitHub can read it, and the weekly report is a week late for work that is ready now. The first reader of the document is a portal that is not built yet. Negative cases: a missing or over-long summary fails the body check, an unreadable summary or count is `unknown` and never 0, the document holds no sha and no raw verdict text, a failed upload fails no routing, and the router posts no comment and merges nothing.

## Rules

1. **The summary line.** Every builder pull request body (a body with a line `Brief: #<n>`, not a draft) has one line `Summary: <one plain sentence>` that says what the change does for a person, not how. `check_pr_body.py` fails a body without it, with an empty one or with one over 120 characters, naming the rule and never the text.
2. **The pipeline document.** `route.py` writes `pipeline.json` after each routing it does. `kit/pipeline-schema.json` defines schema 1, and the document holds: `schema` and `as_of`; `ready`, one item for each open pull request labelled `agk:ready` with `number`, `summary` (from its `Summary:` line, or `unknown`) and `url`; `approve`, one item for each open pull request labelled `agk:approve` with `number`, `spec` (`SPEC-<n>`, from the verdict's `Approval:` line), `spec_title` (the title of the spec file at the head) and `url`; and `counts`, exactly `review`, `fix`, `ci-red`, `conflict`, `approve` and `ready`, each an integer or `unknown`.
3. **Plain words.** The document holds no sha and no raw verdict text. The words a person reads are the `Summary:` line and the spec title.
4. **What cannot be read.** A summary, a spec title or a count that cannot be read is `unknown`, never 0 and never an empty string. A failed write of the file, or a failed upload, fails no routing: the labels are set first.
5. **The artifact.** The workflow of the router uploads `pipeline.json` as the artifact `agk-pipeline` with a retention of 7 days, overwritten by the next run. The router stays the only writer of state and still runs no agent, merges nothing and posts no comment; the document is derived from the labels, the bodies and the verdicts and is never read back by the router.
6. **The conductor.** `.claude/agents/conductor.md` says a clearing verdict is not given while the summary is missing or written for developers.
7. **Readers.** The document is new and the first reader is a portal intake that is not built yet, so no build waits for a reader. A later change of the schema raises its number and follows the rule for the report schemas (a `Readers:` line).
8. **No network, no names.** The checks read files and saved responses only; messages name the rule, never a summary. Nothing in the files names a project.
9. **How it changes.** Intake first (REQ-043, this spec and ADR-0131, approved by the maintainer's `Approve:` line, SPEC-0032 rule 5), then builds of about 600 changed lines each: (a) the `Summary:` line and its check, with the conductor's role file and the session rules; (b) `pipeline.json`, its schema and the artifact step.
10. **Tests.** Saved responses and fixtures, no network: a body with and without `Summary:` and an over-long one; a pipeline document from fixture pull requests in each label; an `unknown` summary; the schema check; a failed upload that leaves the label set; the texts of the role file and the workflow.

## Tests

- Rule 1: a body with a `Brief:` line and no `Summary:`, an empty one and one of 121 characters fail naming the rule, one of 120 passes, and a draft is ignored; REQ-043 AC1.
- Rules 2 and 3: a document built from fixture pull requests in each of the seven labels has the items and the six counts, and no sha; REQ-043 AC2.
- Rule 4: a ready pull request without a `Summary:` line gives `unknown`, an unreadable count gives `unknown`, never 0; REQ-043 AC3.
- Rules 2 and 3: the document validates against `kit/pipeline-schema.json` and a document with a sha, a raw verdict line or a project name does not; REQ-043 AC4.
- Rule 4: a write or an upload that fails leaves every label set and fails no routing; REQ-043 AC5.
- Rule 5: the workflow uploads `agk-pipeline` with a retention of 7 days and the router still posts no comment, merges nothing and runs no agent; REQ-043 AC6.
- Rule 6: the text of the conductor's role file; REQ-043 AC7.

## Proof

REQ-043 AC1 and AC7: *every change says in one sentence what it does for a person, and a clearing verdict is not given without it.* Rules 1 and 6. REQ-043 AC2 and AC4: *the document shows what is ready and what waits for approval, and how many are in each state, in plain words and without a sha.* Rules 2 and 3. REQ-043 AC3: *what cannot be read is `unknown`, never 0.* Rule 4. REQ-043 AC5 and AC6: *publishing the document can never break routing, and the router stays the only writer of state.* Rules 4 and 5.

## Residual

- 2026-10-25: nothing checks that a summary is written in words a non-developer understands; the body check bounds its length only, and the judgment is the conductor's and a person's (due 2026-12-31).
- 2026-10-25: the document is published as a workflow artifact, which a reader outside GitHub can download only with a token; whether that is the right channel is a question below (due 2026-12-31).
- 2026-10-25: the counts do not include the seventh label `agk:ci-running`, so they need not add up to the number of open pull requests (due 2026-12-31).

## Open questions

- Q-S0036-1: Rule 1 applies to a body with a `Brief: #<n>` line (a builder pull request, an intake included, not a draft). Is that the scope? A pull request by a person without a `Brief:` line, a release pull request and a docs-only pull request are left out by this reading, so they never have a summary and appear in `ready` as `unknown`. The criteria assume this scope.
- Q-S0036-2: Rule 1 bounds a summary to 120 characters, and what "plain words a non-developer understands" means is left to the conductor. Should the body check also refuse mechanical signs of developer words (a backtick, a hex string of 7 or more characters, a `#<n>` reference, a file path)? The criteria assume the length only, because a mechanical list will refuse some good sentences and miss bad ones.
- Q-S0036-3: Rule 5 publishes a workflow artifact. A reader outside GitHub (the portal) must hold a token to download it, and an artifact expires. Is that the right channel, or should the document be a file on a branch, a release asset or a page? The criteria assume the artifact, as the brief says.
- Q-S0036-4: An `approve` item has one `spec` and one `spec_title`. A pull request whose verdict has several `Approval:` lines (several specs) would need several items. The criteria assume one item for each `Approval:` line, and `counts.approve` counting pull requests.
- Q-S0036-5: The words of an `approve` item are the title of the spec file, which is the developer's title (for example a long title naming rules). Should an `approve` item also carry the `Summary:` line of its pull request, so that the person reads one plain sentence for it too? The criteria assume the spec title only, as the brief says.
- Q-S0036-6: `counts` holds six of the seven router labels; `agk:ci-running` is left out. Should it be a seventh count, so that the counts add up to the open pull requests? The criteria assume the six of the brief.
- Q-S0036-7: The router writes the document "after each routing it does". A routing that sets no label (nothing changed) may still need a fresh `as_of`, and the artifact is overwritten each time. The criteria assume it writes after every routing run, changed or not, so that `as_of` shows the router is alive.
