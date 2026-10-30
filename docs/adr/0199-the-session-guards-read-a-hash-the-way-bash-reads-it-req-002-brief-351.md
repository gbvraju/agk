# ADR-0199: the session guards read a `#` the way bash reads it (REQ-002, brief 351)

- Status: Proposed
- Date: 2026-10-30
- Deciders: maintainers
- Related: none
- Requirements: REQ-002

Protected classes: `.claude/`, `tests/kit/`

## Context

Brief #351 (priority 0, a security fix): the review of #346 found that `tokens_of` in `.claude/hooks/architect_guard.py`,
which the conductor guard and its shadow mode also use, read a command with the lexer's default comment handling. That lexer
starts a comment at a `#` anywhere, while bash starts one only at the start of a word. For `git status#;id` the guard saw the
words `git status` and allowed them, while bash ran `git status#` and then `id`. The builder reproduced the `Measured:` line on
the default branch before changing anything: `tokens_of('git status#;id')` printed `['git', 'status']`, and
`bash -c 'echo hi#;echo PWNED'` printed `hi#` then `PWNED`.

## Decision

1. **The words are the words bash passes (answer 1).** `tokens_of` sets the lexer's comment characters to none, so a `#` stays
   inside its word, and returns None for any command with a `#` outside a quoted string, escaped or not. A quoted `#` (in single
   or double quotes) is one character of its word for bash and for the guard alike. A command the guard cannot read the same way
   as bash is denied, never allowed.
2. **Every guard gets the fix (answer 2).** The architect guard, the conductor guard (its `git` reads, `gh api`, `session.py`
   forms, the bounded run and the comment post) and the shadow mode all read commands through `tokens_of`, so the one change
   covers them. `conductor_guard.py` is not edited. No allowed form is widened: a form is only ever narrower than before.
3. **Tests first (answer 3).** The three guard test files gain the brief's cases (`git status#;id`,
   `gh api repos/x/y#;touch z`, `python3 scripts/agk/session.py queue --role conductor#;id`, a `#` after a word in each allowed
   form and in a bounded run), a quoted `#` in a comment body and in a body file path that stays allowed as bash reads it, and
   the forms allowed today, which stay allowed. All of them were red before the change except the quoted ones.

## Consequences

A session can no longer run a command its guard never saw by hiding it behind a `#` inside a word. A command with an unquoted
`#`, even one bash would read harmlessly (`git log x#y`, or a trailing `# comment`), is now denied: such a command is rewritten
with the `#` in quotes or without it. Projects that installed the kit should upgrade.

## Residual

None.
