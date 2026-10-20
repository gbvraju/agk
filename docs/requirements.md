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
- Status: planned
