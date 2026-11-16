# ADR-0563: A GitHub login may hold an underscore

- Status: Accepted
- Date: 2026-11-15
- Deciders: maintainers
- Related: brief #1327, plan #661
- Requirements: REQ-052

## Context

Brief #1327 found that `scripts/agk/launch.py` (the builder resume, `prompts --resume`) and
`scripts/agk/personal_state.py` (`attach --person`) accept a GitHub login only as a letter or digit followed by up to
38 letters, digits or hyphens. A managed-user login is the user's handle, an underscore and the enterprise's short
code (`sam_example`), so `session.py plan` wrote the owner's managed login into every `running` entry and
`launch.py prompts --resume` refused each of them, and `personal_state.py attach` refused that person.

## Decision

1. One login pattern in both files: a login starts with a letter or digit, then letters, digits, hyphens or
   underscores, at most 39 characters in all (`[A-Za-z0-9][A-Za-z0-9_-]{0,38}`, matched whole).
2. A login starting with a hyphen or an underscore, one holding a space, slash, dot or any other character, and one
   longer than 39 characters are still refused, with the same refusal naming the field (`author`) or the option
   (`--person`), never the value.
3. Nothing else changes: the prompt text, the `--author` step and every other check stay as they are.

## Consequences

A project whose people have managed-user logins resumes its builders from an unedited plan and attaches the personal
state. The accepted set grows only by the underscore after the first character. Protected path classes changed:
`scripts/agk/` (`launch.py`, `personal_state.py`) and `tests/kit/` (`test_launch.py`, `test_personal_state.py`).

## Residual

- 2026-11-15 (verify): GitHub's documented form of a managed user's login (handle, underscore, short code) is taken
  from the brief and was not read from GitHub's documentation here.
