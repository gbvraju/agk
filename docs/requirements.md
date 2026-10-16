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

- Acceptance: AC1 matrix generated; AC2 done requires a marker; AC3 matrix never committed
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
