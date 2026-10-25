# ADR-0140: the Summary line of every pull request body (REQ-043 build a, SPEC-0036 rules 1 and 6)

- Status: Accepted
- Date: 2026-10-25
- Deciders: maintainers
- Related: ADR-0131, ADR-0125, ADR-0138
- Requirements: REQ-043

Protected classes: `.claude/`, `.github/`, `config/`, `scripts/agk/`, `tests/kit/`, `tests/kit_dev/`

## Context

SPEC-0036 (Approved, ADR-0131) rule 9 makes build (a) the `Summary:` line and its check, with the conductor's role file and the session rules; the conductor assigned it on #213 with this ADR number and amendment 76 reserved, and `builder-b` took it on #213. The maintainer's ruling on Q-S0036-1 and Q-S0036-2 is in force: every pull request body that is not a draft needs the line, and the only mechanical test is its length. The tests were written first (`tests/kit/test_pr_summary.py`: 12 failed and 2 passed on the unchanged tree).

## Decision

1. **The check** (`scripts/agk/check_pr_body.py`): a body that is not a draft, with or without a `Brief:` line, fails unless it has exactly one line starting `Summary:` at the start of the line, with 1 to 120 characters after it (whitespace around them is not counted). The message is `SPEC-0036 rule 1: one 'Summary:' line of 1 to 120 characters is required`; it names the rule and never the text. Two `Summary:` lines fail, because the summary is one line (Q-K4-314). A draft is skipped as before.
2. **The conductor** (`.claude/agents/conductor.md`): no clearing verdict while the `Summary:` line is missing or written for developers (a file, a function, a sha, a rule number or the name of a check in place of what changes for a person); it asks for a fix list that rewrites it. The wording is the conductor's judgment, as ruled (Q-S0036-2).
3. **The session rules** (`config/session-rules.md`): rule 27 says every non-draft body has the line, what it says and how long it is. The number follows rule 26 of main; `session.py ids` prints no rule number (Q-K4-313).
4. **The printed bodies** (`intake.py next-steps`, `playbook.py next-steps`) gain a fixed `Summary:` sentence, because each prints a body that must pass `check_pr_body.py` (Q-K4-315).
5. **The template** (`.github/PULL_REQUEST_TEMPLATE.md`, installed verbatim): a line `Summary:` left empty, so that the unchanged template fails the check, with an HTML comment under it that asks for one plain sentence of at most 120 characters (Q-K4-316, the verdict on 5699f52 item 1). The maintainer merges the pull request, because it changes `.github/`. **Not in this build**: `pipeline.json`, its schema and the artifact step are build (b).
6. Flow mode: no version bump, the fragment `changelog.d/ccr-7649d887-m9hvn7-sh.md`, `CHANGELOG.md` and `kit/hashes.json` as on main. Amendment 76 (`docs/runs/proposed-spec-amendments-76.md`) is for SPEC-0012, SPEC-0030 and SPEC-0036.

## Consequences

- A project that upgrades must add a `Summary:` line to its pull request bodies; an open pull request needs only a description edit, which runs the body steps alone (the fragment says so).
- Every open pull request body that is not a draft must gain a `Summary:` line before its governance check passes; the existing tests' fixture bodies gained one.
- A summary is judged by length by the script and by wording by the conductor; the first does not make the second true (a residual of SPEC-0036).

## Residual

- 2026-10-25: nothing checks that a summary is written for a person who is not a developer; the conductor's judgment and a person's are the only test (due 2026-12-31).
