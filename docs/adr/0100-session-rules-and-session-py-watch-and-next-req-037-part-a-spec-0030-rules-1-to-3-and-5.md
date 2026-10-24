# ADR-0100: session rules and `session.py` watch and next (REQ-037 part a, SPEC-0030 rules 1 to 3 and 5)

- Status: Accepted
- Date: 2026-10-24
- Deciders: maintainers
- Related: ADR-0098, ADR-0096
- Requirements: REQ-037

Protected classes: `.claude/`, `CLAUDE.md`, `config/`, `kit/`, `scripts/agk/`, `tests/kit/`

## Context

SPEC-0030 (Approved, #167) is lane A of the conductor plan (issue #163); this is its first build, measured at about 580 changed lines of code and tests before it was started. The tests were written first (`tests/kit/test_session.py`, `tests/kit/test_session_rules.py`; on the unchanged tree: 23 failed, 2 passed).

## Decision

1. **Rules file** (rule 1): `config/session-rules.md`, installed verbatim, six numbered rules; `CLAUDE.md` and `.claude/agents/architect.md` each gain one line that points at it.
2. **`session.py watch`** (rule 2): `--pr N` ends on a qualifying verdict (listed author counted as SPEC-0025 rule 4 counts, a prefix of the current head, newer than the newest comment seen at the start), a merge or a close; `--merged N` (amendment 51, the verdict on #167) waits on a merge alone; a failed GET is retried on the next poll; `--timeout` ends with exit 3. It only GETs.
3. **`session.py next`** (rule 3): briefs in order of number, skipped with a reason each (shape, open or unreadable dependence, live take of another session), the one POST `taken: <ID> <YYYY-MM-DD>`, a re-read in which the take must be the oldest live one; a take is live 24 hours and after that while a pull request by the taker, opened after the take, mentions the issue as `#n`.
4. **No network in a check** (rule 5): `session.py` is the only caller of `gh` and holds the one `"POST"`; a test pins both.
5. **Kit files**: the manifest lists `config/session-rules.md` and `scripts/agk/session.py`; `kit/hashes.json` is refreshed; flow mode, so no version bump and one line under `## Unreleased` of `CHANGELOG.md`. Amendment 51 (`docs/runs/proposed-spec-amendments-51.md`) is applied to SPEC-0030 and SPEC-0005.

## Consequences

- A session reads one file for its working rule and finds its verdicts and its next brief with one script; the installed kit gains two files.
- Residuals are those of SPEC-0030 (a stale take whose pull request does not mention the issue; two conductors).

## Residual

None beyond SPEC-0030's.
