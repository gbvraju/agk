# Decisions log

One row per decision made outside an ADR, so a compacted session can be reconstructed from the repository.

| Date | Decision | Reason | Recorded in | By |
| ---- | -------- | ------ | ----------- | -- |
| 2026-10-14 | Session-mandated branch names accepted (Q-K0-1) | cosmetic | this log | reviewer |
| 2026-10-14 | CODEOWNERS is the one exception to rule 5 | GitHub needs it committed; changes rarely | ADR-0003 (planned) | reviewer |
| 2026-10-14 | Maintainers handle is a mapping only; approvers hold team names; replace by K1 exit (Q-K0-4) | neutrality | ADR-0001 residual | reviewer |
| 2026-10-14 | build-state creation exempt only when absent at base (Q-K0-5) | bootstrap | check_build_state.py + tests | reviewer |
| 2026-10-14 | Stop hook allows stop when `stop_hook_active` (Q-K0-7) | no infinite loop | stop_check.py + tests | reviewer |
| 2026-10-14 | Action versions on major tags until K1 exit, then SHA pins (Q-K0-9) | residual | this log | reviewer |
| 2026-10-14 | Branch protection documented in ADR-0001 until `agk doctor` (Q-K0-10) | not verifiable from sandbox | ADR-0001 | reviewer |
| 2026-10-14 | CI blocked by account billing; no merge on local verification alone | checks must run in CI | this log | reviewer |
| 2026-10-14 | Repository public from K0; K4 redefined as launch | no paid CI minutes | ADR-0001, ADR-0002 | maintainers |
| 2026-10-14 | Initial-commit author email accepted as public; force-push rewrite rejected (rules 2, 3) | history rewrite breaks rules | this log | maintainers |
| 2026-10-14 | Protected-path Edit/Write are `ask`, not `deny` | agents may change protected paths with an ADR (day-0 rule 0.3); CI and maintainers are the gate | settings.json, ADR-0001 | reviewer |
| 2026-10-14 | Colon-refspec deny removed; feature-branch deletion uncovered, `main` protected by ruleset | unconfirmed pattern syntax | day-0.md | reviewer |
| 2026-10-14 | `governance` added as required status check before merging PR #1 | merge gated by CI | ADR-0001 | maintainers |
| 2026-10-14 | Docs-only PRs carry their own dated build-state row; check_pr_body unchanged (Q-K1-1) | the check requires a dated row; `none (...)` was rejected | this log, PR #2 body | reviewer |
| 2026-10-14 | The governance workflow re-runs on PR body edits (`edited` type) | a body fix needs no empty commit | ADR-0003, governance.yml | reviewer |
| 2026-10-14 | Edit rules cover Write, and a leading `/` anchors at the project root; `Write(...)` rules removed (Q-K1-2) | Claude Code consults only Edit and Read path rules | ADR-0003, docs/runs/day-1.md | reviewer |
| 2026-10-14 | `permissions.ask` is a documented key; order deny, ask, allow; (verify) removed (Q-K1-3) | confirmed in the permissions and settings-reference pages | docs/runs/day-1.md | reviewer |
| 2026-10-14 | One ADR must name every changed protected class (Q-K1-4) | cover must state its scope | ADR-0003 decision 4 | reviewer |
