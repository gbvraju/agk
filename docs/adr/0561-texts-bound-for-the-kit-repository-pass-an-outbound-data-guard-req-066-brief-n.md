# ADR-0561: Texts bound for the kit repository pass an outbound data guard

- Status: Proposed
- Date: 2026-11-15
- Deciders: maintainers
- Related: SPEC-0059, SPEC-0042, ADR-0557, brief #1324, brief #1320, plan #661
- Requirements: REQ-066

## Context

SPEC-0059 rule 6 lets the steward file a kit brief, correction or question straight to the kit repository from a
customer project, but only after an outbound data guard passes on every text; rule 11 has the steward's guard deny a
post to the kit repository that the outbound guard matches or cannot check. Rule 17 makes both build (e). On the
default branch no check judges a text posted to another repository: `guard.scan_text` (SPEC-0042 rule 10) judges the
session's own tool calls and `check_neutrality.py` the tracked files. Until this build the steward gives the owner a
draft instead of filing to the kit.

## Decision

1. **The check.** `scripts/agk/steward_outbound.py check (--text TEXT | --file FILE) [--root DIR]` refuses, fail
   closed, a text that holds: a token of the project's `config/neutrality.txt`, or of the kit's list
   `kit/templates/neutrality.txt` where the project holds it (in a project the kit's list is installed as that same
   `config/neutrality.txt`, SPEC-0059 rule 6's two lists reading as one file there); a finding of `guard.scan_text`
   with the `[guard] patterns` (e-mail addresses and phone numbers, and the secret and other personal kinds that
   detector already finds); a URL whose host is a host of the project's git remotes, or such a host named bare, other
   than the kit's own repository on its host; and a repository name other than the kit's, read from a forge or remote
   URL, a `repos/<owner>/<repo>` path, an `<owner>/<repo>#<n>` reference or a literal `<owner>/<repo>` of the
   project's remotes (`Q-S0059-12`: the remotes and `[guard] patterns`, no other list). It holds no detector or token
   list of its own.
2. **Fail closed.** A list that cannot be read, git remotes that cannot be read (`git config --local`), a refused
   `[guard]` table or a file that cannot be read refuse the text. Each refusal is one line per class,
   `outbound guard: SPEC-0059 rule 6 refuses <class> (setting: <setting>); rewrite it with invented names
   (example.com)`, naming the setting and the class, never the value; exit 2. A clean text prints `ok outbound`.
3. **The kit repository.** `KIT_REPO`, the `repository` of `.claude-plugin/plugin.json`, held equal to it by a test,
   since a project does not install the plugin file. A project whose remotes include the kit repository is the kit
   itself, and nothing it posts there leaves a project.
4. **The denial.** `.claude/hooks/steward_guard.py` runs the check on the title and body of a post that targets the
   kit repository (`gh issue create|comment -R|--repo <kit>`, a non-GET `gh api repos/<kit>/...`) and denies it,
   naming rule 11 and each class with its setting, when the check refuses or a body cannot be read. A post to another
   repository or to the project's own (`{owner}/{repo}`) is judged as before.

## Consequences

A steward in a customer project may file to the kit repository a text that passes the check; one that names the
project's people, hosts, repositories or neutrality tokens is denied before it leaves. The check is a deny list
over the detectors the kit has: a value no detector or list knows still depends on the steward's rewriting with
invented names. Protected path classes changed: `scripts/agk/` (`steward_outbound.py`), `.claude/`
(`hooks/steward_guard.py`), `agk.toml` (the `[[testing.map]]` entries), `tests/kit/`
(`test_steward_outbound_guard.py`) and `kit/` (`manifest.json`).

## Residual

- 2026-11-15: a kit repository on a host other than `github.com`, or a fork, needs `KIT_REPO` read from a setting
  (`Q-1324-1`).
