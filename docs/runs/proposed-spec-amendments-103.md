# Proposed spec amendments 103 (SPEC-0034; REQ-041)

Date: 2026-10-30 (from `date -u`). Approved specs change only through a proposal like this one (principle 6). Applied by ADR-0190
(brief #331), which stays `Proposed` for the maintainers' decision. The path: `docs/specs/0034-a-team-sets-how-many-builder-sessions-run-at-once-and-agk-ha.md`.
The number 103 was named by the conductor's verdict on 2d53a5d (#364, answer to Q-331-4), as amendment 89 was written for ADR-0154
(decision 5). It needs a person's `Approve: SPEC-0034` on #364 before the pull request can clear; no session posts it.

1. **SPEC-0034 rule 6, the rule that no session starts another**, as amendment 89 worded it ("AGK ships no launcher that runs on its
   own, and no session starts, stops or reviews another, except that a session starts other sessions when a person runs
   `/agk:launch` and confirms its plan"), reads: "AGK ships no launcher that runs on its own, and no session starts, stops or reviews
   another, except that a session starts other sessions when a person runs `/agk:launch` and confirms its plan, and except that, with
   `[flow] auto_start = true` in `agk.toml` (a protected setting, changed only with an ADR in the same pull request) on the default
   branch and in the conductor's checkout, the conductor may, at the end of a review pass, start the sessions that `session.py plan`
   names, within the plan's `capacity.slots` and `[flow] max_builders`, through the one adapter that `[flow] launch_adapter` names,
   and through no other command." With `auto_start` off (the default) the pass only prints the plan and the ready-to-paste prompts.
   The contract of `session.py demand` stays as it is for a team's own launcher.
2. **What the conductor still never does.** It never claims a brief for a started session (each started session posts its own
   `taken:` with `session.py claim`), never starts a session for a taken brief or one the plan does not name, never retries a refused
   adapter in a pass, and never stops or reviews a session it started other than by the review protocol of its pull request.
3. **Tests (rule 14).** The guard allows `session.py plan --json`, `launch.py prompts --plan <scratch file>` and, only when both the
   checkout and the default branch set `auto_start = true` and the same `launch_adapter`, that command with `--adapter` and the
   configured adapter; every other spelling is denied. `launch.py` refuses, with an adapter, a plan without its capacity, a plan
   longer than its slots, and one naming a brief or a session twice, stops at `max_builders`, and reports a refused adapter once.
   The texts of the skill, the role, the template and the guide (`tests/kit/test_conductor_guard_launch.py`,
   `tests/kit/test_launch_auto_start.py`, `tests/kit_dev/test_review_pass_skill.py`).
