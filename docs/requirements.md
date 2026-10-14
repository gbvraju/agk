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

- Acceptance: AC1 rejections, blocked weakenings, deviations, cost class
- Status: planned
