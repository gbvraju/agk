# Requirements

Each requirement is a `### REQ-nnn` section with a `- Status:` line (planned | in-progress | done).
Only the Status line may change without an ADR. `done` requires at least one test marker `REQ-nnn` under `tests/`.

### REQ-001 — Protected paths change only with an ADR in the same PR

- Acceptance: AC1 check fails without ADR; AC2 Status-only change in requirements exempt; AC3 message names the path class
- Status: done

### REQ-002 — Agents never merge or bypass checks

- Acceptance: AC1 branch rules documented and verifiable by agk doctor; AC2 settings deny force-push/reset; AC3 stop hook blocks on red governance
- Status: in-progress

### REQ-003 — Every requirement is traceable to tests

- Acceptance: AC1 matrix generated; AC2 done requires a marker; AC3 matrix never committed; AC4 every acceptance criterion of a `done` requirement has a test marker `REQ-nnn ACn`
- Status: done

### REQ-004 — Accepted decisions are immutable except Status

- Acceptance: AC1 check compares against base; AC2 amendment via new ADR with Amends:
- Status: planned

### REQ-005 — Reviewer groups own path classes

- Acceptance: AC1 reviewers.yaml schema; AC2 CODEOWNERS generated from it; AC3 no personal names in authority
- Status: planned

### REQ-006 — Build-state is appended, never edited by feature PRs

- Acceptance: AC1 check; AC2 row carried in PR body
- Status: planned

### REQ-007 — Product neutrality

- Acceptance: AC1 token list; AC2 check; AC3 kit itself passes with an empty list
- Status: planned

### REQ-008 — Briefs and reports have a fixed shape

- Acceptance: AC1 templates; AC2 PR body check
- Status: planned

### REQ-009 — Install into a new repository (K1)

- Acceptance: AC1 agk init idempotent; AC2 governance green after init
- Status: planned

### REQ-010 — Adopt an existing repository (K2)

- Acceptance: AC1 no product file modified; AC2 idempotent
- Status: planned

### REQ-011 — Drift audit (K2)

- Acceptance: AC1 weekly; AC2 one issue per run; AC3 read-only
- Status: planned

### REQ-012 — Metrics per merged PR (K3)

- Acceptance: AC1 each closed pull request has a derived record of rejections, blocked weakenings, deviations and cost class; AC2 the record also carries hours open to merge, review rounds, protected classes touched, ADRs added, tests before and after, and whether the merged head was cleared; AC3 a weekly issue lists every pull request closed in the week; AC4 cost class is the maintainers' review cost, derived from fix-list rounds and hours open to merge: S, M or L, and unknown when the rounds are unknown
- Status: planned

### REQ-013 — Reviewer agent (K2)

- Acceptance: AC1 the review context of a PR is deterministic and complete; AC2 a report is validated (verdict, findings with a hunk and a rule); AC3 the agent is read-only; AC4 verdicts are measured (rejections per PR)
- Status: planned

### REQ-014 — Install and run agk as a Claude Code plugin (K3)

- Acceptance: AC1 the plugin manifest and the marketplace file are valid and `plugin.json` carries the kit version (`claude plugin validate .`); AC2 the plugin has one skill per command (`/agk:<command>`), no hooks, servers, monitors or `bin/`, user-invoked writers, and no skill runs a forbidden verb; AC3 the repository's own checks, hooks, workflow and reviewer run with no plugin installed; AC4 GitHub issues are intake only: no script or workflow reads an issue for a decision; AC5 `agk upgrade` brings an init or adopt target from kit version X to the current kit, never overwriting an edited file or a user-owned file
- Status: planned

### REQ-015 — Every acceptance criterion is proven by a test

- Acceptance: AC1 the check fails a fixture with a `done` requirement whose second criterion has no test marker `REQ-nnn ACn`; AC2 the check passes on this repository's default branch and on the sandbox; AC3 every `done` requirement of this repository has a test marker for each of its criteria, or its status is set back to `in-progress`
- Status: planned

### REQ-016 — New tests prove behaviour (red-then-green)

- Acceptance: AC1 the check flags a seeded pull request whose new test passes on the base commit, in this repository and in the pilot repository (a different language); AC2 over two consecutive weeks of this repository's real pull requests the check reports no unresolved false flag; AC3 a repository with no `project_tests` reports `unknown`, never `ok`
- Status: planned

### REQ-017 — Decision inbox: every item waiting for a person is listed, none is missed

- Acceptance: AC1 on two weekly hand counts in this repository and two in the pilot repository, the inbox misses zero items (an extra item is a finding, not a failure)
- Status: planned

### REQ-018 — Weekly product report answers the five questions from derived facts

- Acceptance: AC1 for two consecutive ISO weeks the weekly product report is created on schedule in the pilot repository, and for each week the product owner's written answers to the five questions, given from the report alone, are checked by the maintainers against the repository as 5 of 5 correct (an answer the report could not give counts as wrong); AC2 a test shows every number and every status in the report is computed from the facts document, the report names the facts commit, and no field is read from a PR body except the `Behaviour:` and `Verdict:` lines
- Status: planned

### REQ-019 — Plain-language intake: a sentence becomes a Draft requirement with acceptance criteria

- Acceptance: AC1 given one plain-language sentence, `/agk:spec` writes a requirement with Given/When/Then acceptance criteria and a Draft spec as files in a branch; AC2 a draft is treated as a proposal: no derived fact, report or inbox line counts it before it is merged
- Status: planned

### REQ-020 — Playbook: a new repository is started and run from a problem statement to a governed merge using only the kit's own commands, roles and templates

- Acceptance: AC1 the pilot fork, started from nothing, is set up and run using only the playbook, from a written problem statement through `/agk:start`, the architect session, `/agk:init` or `/agk:adopt`, one Approved spec and one brief, to its first governed merged pull request with a `Verdict: cleared` line; AC2 every decision is recorded in the pilot's own repository, and no step is taken from memory or from this repository's chat history; AC3 the record names each step and the file or comment it produced
- Status: planned

### REQ-021 — The weekly product report footer names the kit version

- Acceptance: AC1 Given a repository whose agk.toml names the installed kit version, when the weekly product report is rendered from its facts, then the footer has a line `kit version: <that version>` directly after the `facts:` line; AC2 Given a repository where neither agk.toml nor the legacy pyproject.toml stamp gives a readable version, when the report is rendered, then the footer says `kit version: unknown` and does not guess a version; AC3 Given a repository stamped only in the legacy `[tool.agk]` table of pyproject.toml, when the facts are read, then the version is the one that the upgrade command reads, from one shared reader
- Status: done

### REQ-022 — A busy week's report links the full list of merged pull requests

- Acceptance: AC1 Given a week in which more than ten pull requests merged, when the weekly product report is rendered, then Delivered lists every requirement that is done and, in place of one line per pull request, one line that gives the number of merged pull requests and one link to the full list; AC2 Given the same busy week, when the report is rendered, then Cost shows the week's totals line with its text unchanged and ending with the same link, and shows no line for any single pull request; AC3 Given a busy week, when the link is built, then it is a search of the repository's merged pull requests for the week's UTC dates, the same dates as the opening line of the report, computed from the facts file alone; AC4 Given a week in which ten or fewer pull requests merged, when the report is rendered, then it is byte-identical to the report of the same facts before this change; AC5 Given a busy week, when the report is rendered, then Needs you and At risk are not changed and no pull request they named is left out
- Status: done

### REQ-023 — At risk shows one line per kind of pull request risk

- Acceptance: AC1 Given an At risk section in which two or more pull requests have the same one of four kinds of risk (open too long, sent back, merged with no verdict, merged before its last commit was cleared), when the weekly product report is rendered from its facts, then that kind is one line that names every one of those pull requests by number in ascending order, each number as its own link, and never as a range; AC2 Given a kind with exactly one pull request, when the report is rendered, then its line is exactly the line printed before this change, and when no kind has two or more pull requests the whole At risk section is byte-identical to the report of the same facts before this change; AC3 Given the open-too-long kind or the sent-back kind with two or more pull requests, when the report is rendered, then each number is followed in brackets by that pull request's own value (its days open or its times sent back) and no title is printed; AC4 Given a week in which many pull requests were merged with no verdict, when the report is rendered, then every pull request that At risk named before this change is still named in its line, and no pull request is left out; AC5 Given overdue residuals and the drift audit line, when the report is rendered, then they are printed as before this change and are never grouped; AC6 Given any facts, when the report is rendered, then no file other than the facts file is read and no number in the At risk section is computed from anything but the facts; AC7 Given facts in which the pull requests are marked unknown, when the report is rendered, then At risk prints today's unknown line and does not group; AC8 Given any facts, when the report is rendered, then Delivered, Proven, Needs you, Cost and the footer are byte-identical to the report of the same facts before this change
- Status: done

### REQ-024 — Delivered lists only the requirements that became done in the week

- Acceptance: AC1 Given a requirement whose latest change to `done` is dated inside the report's ISO week in UTC, when the weekly product report is rendered from its facts, then Delivered lists it with its usual line; AC2 Given a requirement that is `done` and whose latest change to `done` is dated outside the report's week, when the report is rendered, then Delivered does not list it; AC3 Given a requirement that became `done`, went back to another status and became `done` again, when the report is rendered, then its latest change to `done` decides whether it is listed; AC4 Given a requirement that is `done` and whose week cannot be read from the facts, when the report is rendered, then it is listed with its usual line followed by `(week it became done: unknown)` and is never dropped; AC5 Given a week in which no requirement became done, when the report is rendered, then Delivered prints no requirement line and its pull request lines are unchanged; AC6 Given the facts document of this change, when it is written, then `schema` is still 1, the per-requirement date is optional and reads `unknown` when it cannot be read, and a facts document without it renders as in AC4; AC7 Given the `product-report` workflow, when its checkout is read, then it fetches the full history, and a test fails if the checkout is shallow; AC8 Given any facts, when the report is rendered, then no file other than the facts file is read, and Proven, Needs you, At risk, Cost and the footer are byte-identical to the report of the same facts before this change
- Status: done

### REQ-025 — Each brief declares a size and expected hours, compared with the actual hours

- Acceptance: AC1 Given the three brief templates, when an item is written from one, then it carries the lines `Size: S|M|L` and `Expected: <low>-<high> hours`; AC2 Given a merged pull request whose body carries `Brief: <path>#<item>`, `Size:` and `Expected:` lines, when the weekly metrics are computed, then the record has `estimated_size` and `estimated_hours` read from the body alone; AC3 Given a merged pull request whose body lacks those lines or carries a malformed one, when the metrics are computed, then both fields read `unknown` and are never guessed or set to zero; AC4 Given a merged pull request, when the metrics are computed, then the record has `actual_hours`, the hours from the earliest author date among the pull request's commits to `merged_at` in one decimal, and `hours_open_to_merge` is unchanged; AC5 Given a week's merged pull requests, when the product report is rendered, then the Cost totals line ends with `estimate: N of M within range`, where M counts the pull requests with a readable estimate and a readable `actual_hours`, N counts those with `low <= actual_hours <= high`, a pull request with an unknown value is in neither, and when M is 0 it ends with `estimate: none declared this week`; AC6 Given pull requests merged before this change, when the metrics and the report are computed, then their estimate reads `unknown`, no past record is rewritten, and the report is otherwise byte-identical; AC7 Given any declared size and hours, when the metrics and the report are computed, then the kit makes no estimate, applies no buffer, uses no model and does not compare the size with `cost_class`; AC8 Given any facts, when the report is rendered, then no file other than the facts file is read
- Status: done

### REQ-026 — The weekly report publishes the facts it was rendered from

- Acceptance: AC1 Given a run of the `product-report` workflow that wrote the week's report, when it finishes, then the run holds one workflow artifact named `agk-facts-<week>` (for example `agk-facts-2026-W42`, the week label of the report) that contains `facts.json`; AC2 Given that artifact, when its file is compared with the facts document the report was rendered from, then they are byte-identical, with nothing filtered out and no field added; AC3 Given the workflow file, when it is read, then the upload step comes after the step that writes the issue, uploads that one file and no other, keeps it for 90 days, errors when the file is missing, and uses an action pinned by a full commit SHA; AC4 Given a missing or empty facts file, when the upload step runs, then it fails the run and the issue already written is left as it is; AC5 Given a re-run of the workflow for the same week, when the upload step runs, then the artifact of the latest run is the one a reader uses and the workflow deletes no other artifact; AC6 Given the workflow file, when it is read, then its permissions are those it had before this change, it commits and pushes nothing, and it has no step that publishes the file anywhere but as a workflow artifact; AC7 Given the repository is private, when the facts are published, then they are readable only by those who can read the repository and there is no anonymous download and no sharing mechanism; AC8 Given any facts, when the report is rendered, then the report, the issue and its label, the inbox output and the metrics workflow are byte-identical to before this change
- Status: done

### REQ-027 — An intake pull request may carry its own approval

- Acceptance: AC1 Given an intake pull request whose spec has no open `Q-S` id and whose opening paragraph records the maintainers' answers, when its final commit changes exactly the spec status `Draft` to `Approved` and the ADR status `Proposed` to `Accepted`, then `intake.py check` in final-commit mode passes; AC2 Given a final commit that changes any other line, touches a third file, sets either status to any other value or touches `docs/requirements.md`, when `intake.py check` runs in final-commit mode, then it refuses and names the rule; AC3 Given a spec with an open `Q-S` id or without the opening paragraph that records the answers, when its final commit sets the spec `Approved`, then the final-commit mode refuses and the rulings pull request of today is the only way; AC4 Given any commit of an intake pull request that is not its final commit, when `intake.py check` runs without the final-commit mode, then it refuses a spec `Approved` or an ADR `Accepted` exactly as before this change and its output for a good draft is unchanged; AC5 Given an intake pull request whose first commit already carries `Approved` or `Accepted`, when the final-commit mode runs, then it refuses, because the final commit must be a separate commit that changes the two status lines only; AC6 Given any repository state, when the final-commit mode runs, then it reads git and files only, uses no network and no model, and never changes the status of the requirement, which stays `planned`
- Status: done

### REQ-028 — A fix list that names only the final commit clears it in advance

- Acceptance: AC1 Given a pull request whose latest verdict by a listed verdict author is `Verdict: fix list <sha>` with one or more `Final: <path> <old> -> <new>` lines and no numbered item, when its head is that sha plus one commit that changes exactly the named status lines and nothing else, then the clearance check passes and the metrics record `merged_head_cleared` `yes` for that head; AC2 Given such a verdict, when the commit after the reviewed sha changes any other line, touches another file or sets a status the Final line does not name, then the clearance check fails naming the rule and `merged_head_cleared` is `no`; AC3 Given a fix list with a numbered item, without a Final line, without a sha or whose sha is not the parent of the head, when the pull request is checked or measured, then it clears no commit and `merged_head_cleared` is decided by a `Verdict: cleared` alone as before; AC4 Given a verdict comment whose author is not a listed verdict author, when the metrics, the facts or the clearance check read the comments, then it is ignored, it clears nothing and counts in no review round and no rejection, and this holds for `Verdict: cleared` too; AC5 Given a `verdict_authors` list in `config/reviewers.yaml`, when the comments are read, then those handles are the listed authors compared without regard to case, and when there is no list the user handle of the maintainers team is the only one while a team handle lists nobody, so verdict fields read `unknown` and `reviewers.py --check` names the setting; AC6 Given a run without a comments file, when `make governance` runs the clearance check, then it prints `skipped` and passes, and in the CI run it reads the file that the workflow wrote from a read-only GET of the pull request's comments; AC7 Given the facts of a pull request whose final commit was cleared by a covered fix list, when the weekly report is rendered, then At risk does not name it as merged before its last commit was cleared, the facts keep `schema` 1 with an optional field, and facts without the field render exactly as before; AC8 Given the governance workflow, when it is read, then its only new permission is read access to pull request comments, the check makes no network call and uses no model, and the workflow writes nothing to the pull request
- Status: planned
