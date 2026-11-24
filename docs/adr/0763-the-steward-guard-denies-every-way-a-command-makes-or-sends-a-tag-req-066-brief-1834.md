# ADR-0763: The steward guard denies every way a command makes, moves or sends a tag

- Status: Accepted
- Date: 2026-11-23
- Deciders: maintainers
- Related: brief #1834, ADR-0541, ADR-0557, ADR-0561, ADR-0612, ADR-0727, ADR-0732, brief #1763, SPEC-0059 rule 11, session rule 2
- Requirements: REQ-066, REQ-002

Protected classes this decision changes: `.claude/` (`.claude/hooks/steward_guard.py`) and `tests/kit/`
(`tests/kit/test_steward_guard_tags.py`).

## Context

Session rule 2 says a session never tags, and SPEC-0059 rule 11 lists a tag among the steward guard's denials. The guard
judged a push's ref as a tag only by a `refs/tags/` prefix on its destination, so `git push origin v1.0.0` (a local tag
by its short name), `tag v1.0.0`, `HEAD:v1.0.0`, `:v1.0.0`, `--follow-tags`, a push setting, a `git config` or `-c`
that writes one, an alias and `git update-ref refs/tags/...` all passed (CM-04 scored 53 of 54). The architect,
architect-review, conductor and shadow guards allow no push and no `update-ref` at all; the builder has no role guard.

## Decision

1. `git_problem` reads a push as git does: the valued options (`-o`, `--push-option`, `--receive-pack`, `--exec`,
   `--repo`) take their value, the first positional is the remote and the rest are refspecs. A refspec whose source or
   destination is `refs/tags/...`, `tags/...` or the short name of a local tag (`git for-each-ref refs/tags/`), the
   word `tag`, an empty source or a pattern that meets `refs/tags/` denies with `denies a tag (path class: git push)`.
   Today's denials run first and keep their wording; `--follow-tags` joins the force list.
2. Before a push the guard reads `push.followTags`, `remote.<name>.push` and `remote.<name>.mirror` with one
   `git config --get-regexp`; a true `push.followTags`, a push refspec that names a tag or a true mirror denies,
   naming the key (`remote.<name>.…`), never a value. `remote.<name>.tagOpt` changes only a fetch and denies nothing on
   a push.
3. A `git config` that writes `push.followTags`, `remote.*.push`, `remote.*.mirror`, `remote.*.tagOpt` or `alias.*`
   (a value after the key, `--add`, `--unset`, `set`, `-e`, or a section rename into one of them), and any `-c` or
   `--config-env` of those keys, denies `(path class: git config)`; a read of them passes.
4. A subcommand that is not one of the listed git built-ins is looked up as `alias.<name>` and judged as its
   expansion, one level; an alias starting `!`, a nested alias or an alias that cannot be read denies
   `(path class: git alias)`.
5. `git update-ref` naming a tag, or reading `--stdin`, denies `(path class: git update-ref)`; `git fetch` with
   `--tags` or a refspec into `refs/tags/` denies `(path class: git fetch)`; `git fetch origin [<branch>]` passes.
6. It fails closed: when git cannot be run or a read passes its one second, a push denies with `cannot judge a push
   (path class: git push)`. Outside a repository git itself refuses a push, so the guard finds no tag there and judges
   the push as before (the existing tests run outside a repository and stay unchanged). `-C`, `--git-dir` and
   `--work-tree` are passed on to the guard's own reads. `git.exe` is read as `git`.
7. A new test runs one table of every form through every guard `plugin_hooks.ROLE_GUARDS` names, and holds that the
   builder is the one agent with Bash outside that list (Q-1834-1), so a builder guard later turns that row red.

## Consequences

- A steward session can no longer publish a release by a tag's short name, a destination, `--follow-tags`, a push
  setting, an alias or `update-ref`; a work branch push and `refs/notes/agk-evidence` pass as before.
- A steward push costs two local git reads, well inside the hook's four seconds; no network.

## Residual

- The builder can still tag (Q-1834-1); a follow-up brief can give it a push-only guard reusing this reader.
- A tag that exists only on the remote is not seen offline, so `HEAD:<name>` passes when `<name>` is not a local tag
  (Q-1834-2); the remote ruleset is the place for that.
- Config set through the environment (`GIT_CONFIG_COUNT`, `GIT_CONFIG_PARAMETERS`) or an edit of `.git/config` by a
  write tool is not read by this rule.
