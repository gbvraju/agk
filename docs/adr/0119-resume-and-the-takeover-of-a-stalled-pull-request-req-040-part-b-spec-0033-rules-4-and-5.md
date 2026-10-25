# ADR-0119: `session.py resume` and the takeover of a stalled pull request (REQ-040 part b, SPEC-0033 rules 4 and 5)

- Status: Accepted
- Date: 2026-10-25
- Deciders: maintainers
- Related: ADR-0116, ADR-0113, ADR-0100
- Requirements: REQ-040

Protected classes: `config/`, `scripts/agk/`, `tests/kit/`

## Context

SPEC-0033 (Approved, #189) rules 4 and 5 are build (b) of brief #182. The tests were written first (`tests/kit/test_session_resume.py`; on the unchanged tree: 22 failed, 12 passed, the passes being the cases that must not change).

## Decision

1. **`session.py resume --pr N`** (rule 4): prints, with `gh api` GET only and nothing written: the pull request, its state label (`agk:` labels), the brief (the first `#n` of the pull request body that is an issue labelled `agk-brief`) with its answers, the progress line of the pull request's author (`progress_of`, ADR-0116) and `continue from:`, the last verdict by a listed author and whether it names the head, and the commands that check out the branch at its head. Each missing part reads `none`; a progress line that is malformed or repeated reads `unreadable (rule 3: ...)` (Q-K4-278).
2. **Stalled takeover in `next`** (rule 5): before any brief, `next` reads the open pull requests and offers the lowest-numbered one that waits on its builder (a draft, or `agk:fix`, `agk:conflict`, `agk:ci-red`; never `agk:ready` or `agk:approve`, and never one whose latest verdict by a listed author clears or covers its head) and whose head commit and comments (created or edited) have not changed for `stall_hours` (Q-K4-279). It takes it over with the one comment `taken over: <id> <YYYY-MM-DD>`, re-reads the comments, and goes on if an older `taken over:` comment since the last change is another session's.
3. **`stall_hours`**: the key of the flow table of `agk.toml`, a whole number of hours, 4 when absent; any other value stops `next` with a message that names the key and never the value (Q-K4-280). The kit template does not gain the table here.
4. **Rules file**: rule 9 of `config/session-rules.md` tells a session started on a stalled pull request to run `resume` first and continue from `next:` on the same branch and pull request.
5. Flow mode: no version bump, the fragment `changelog.d/ccr-7649d887-m9hvn7-bb2.md`, `CHANGELOG.md` and `kit/hashes.json` as on main. No amendment is needed: the spec is built as it stands.

## Consequences

- A session that stops no longer leaves its work taken: a new one is offered it after `stall_hours` and starts from the branch and the progress line.
- `session.py` has two POSTs now, the take and the takeover; a test pins both.

## Residual

- 2026-10-25: whether a session runtime lets one session push to a branch that another session created is not measured here (a cloud session pushes through a proxy that may tie a branch to the session that made it). The first real takeover measures it; if the push is refused, the taking session posts `Question:` with the refusal on the pull request instead of opening a second pull request (due 2026-12-31).
