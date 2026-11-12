# Proposed spec amendments 168 (SPEC-0030; REQ-039)

Date: 2026-11-12 (from `date -u`). Approved specs change only through a proposal like this one (principle 6). Written for
ADR-0479 (brief #1121), which stays `Proposed` for the maintainers' decision. The path:
`docs/specs/0030-a-conductor-role-reviews-every-pull-request-posts-the-verdic.md`. The numbers 168 and 0479 are the ones
brief #1121 reserved. The owner decides it with `Approve: <head> SPEC-0030` on the pull request; no session posts that line.

The sentence (brief #1121): "A brief whose Touches line names more code paths than its Size allows is refused when it is
filed, so a build that would exceed about 600 changed lines is split before a builder starts, not found at review."

## What is on the default branch today

Read in the code by this session on `origin/main` (af60737):

- `scripts/agk/session.py` `brief_problems`, used by `check_brief.py`, `session.py next` and `session.py plan` (through
  `brief_shape`), checks that there is exactly one `Size: S`, `Size: M` or `Size: L` line and never weighs it against
  `Touches:`.
- SPEC-0043 rule 27 asks each build for about 600 changed lines of code and tests or fewer; only the conductor's review
  applies it, after the build.
- Measured: brief #1093, `Size: M` with 8 code paths, passes `check_brief.py` (`ok brief`); its pull request #1106 came to
  1,107 changed lines.

## Items

1. **Rule 4, one added paragraph.** "A code path is a `Touches:` entry that does not start with `tests/`, `docs/` or
   `changelog.d/` and is not `kit/hashes.json`; equal entries count once. A brief of `Size: S` names at most 3 code paths
   and one of `Size: M` at most 6, else rule 4 refuses it with `rule 4: Size <s> allows at most <n> code paths, Touches
   names <m>: split the brief or raise Size`. A `Broad: <reason>` line (amendment 141) lifts that limit for a sweep. A
   brief of `Size: L` with a `Wave:` line (a planned build) is refused with `rule 4: Size L is refused for a planned build
   (Wave:): split the brief`; `Broad:` does not lift this refusal."
2. **The setting.** "The limits are `brief_code_paths = { S = <n>, M = <n> }` in the `[flow]` table of `agk.toml`, read
   by `config.brief_code_paths`, 3 and 6 when unset or for a missing key. Another key, or a value that is not a whole
   number of 1 or more, is refused naming `setting: flow.brief_code_paths`, never the value."
3. **Where it applies.** "`check_brief.py` (with `--root DIR` it reads the setting of `DIR/agk.toml`, without it the
   defaults), `session.py next` and `session.py plan` apply the same function. A brief already taken or with an open pull
   request is not judged again."
4. **Tests.** `tests/kit/test_check_brief.py`: S with 3 passes and 4 fails naming both numbers; M with 6 passes and 7
   fails; test, doc, changelog and `kit/hashes.json` entries do not count; `Broad:` lifts the limit; L with `Wave:` fails
   and without it passes; the setting changes the limits and an invalid one is refused naming it.
