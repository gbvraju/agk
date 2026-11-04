# ADR-0265: merge_cleared.py merges a cleared pull request through one guarded command (REQ-046, brief 531)

- Status: Accepted
- Date: 2026-11-04
- Deciders: maintainers
- Related: ADR-0261, ADR-0263, SPEC-0039
- Requirements: REQ-046

Protected classes: `constitution/`, `config/`, `.claude/`, `scripts/agk/`, `tests/kit/`

## Context

SPEC-0039 (Approved on #519, ADR-0261) splits the guarded merge into the builds of its rule 12.
Build (a) (#530, ADR-0263) gave the setting and the verdict reader, merging nothing. This is build
(b): the re-checks of rules 4 and 5, the pinned merge of rule 6 (its first sentence only), the
lock of rule 9 and the one exception of rule 8. Because it changes `constitution/`, the command's
own hold list holds this pull request, and a person merges it (Q-S0039-14). This ADR number was
reserved for brief #531 by the conductor (the field note on #531).

## Decision

1. `scripts/agk/merge_cleared.py` checks, in this order, each named by its rule and never by a
   value: the setting (rule 1); `paused = true` on the default branch (rule 5, before any read);
   the head (`refused: head moved`, exit 3); the verdict (rule 3); the open red-branch issue (an
   open issue titled `The default branch is red`, whoever wrote it, rule 5); the evidence (rule
   4); the rest of the hold list in the order of rule 5 (`release`, `spec approval`,
   `protected class <class>`, `hold label`, `draft`, `depends-on`, `conflict`). Every hold prints
   `held: <reason> (rule n)` and exits 3. The setting, `paused`, `required_checks`,
   `spec_approvers` and `conductor_accounts` are all read from the one default-branch commit; a
   `config/reviewers.yaml` there that cannot be parsed is refused, naming the settings, and is
   never read as empty (an absent file is the one-account default).
2. Evidence. Local mode is `execution = "local"` on the default branch, or an open issue whose
   title starts `Local mode since` (the record issue of `docs/guides/local-mode.md`). There the
   verdict's body needs a line starting `Local evidence: <sha>`, the sha at least 12 characters
   and a prefix of the head, and an `Evidence check: agrees|differs, head <sha12>` naming the
   head. `differs` passes only with a comment whose first line is exactly
   `Maintainer answer: accept <the 40-character head sha>`, by an account in `spec_approvers`,
   posted after the verdict; any other answer holds as `evidence differs` (the fix list on
   cb0a7ef, item 2, which replaces Q-531-2). In CI mode each name of
   `required_checks` needs a latest check run on the head (the router's `latest_runs`) that is
   `completed` with `success`: a red or other conclusion holds as red, a missing one as missing,
   and one not completed as `checks pending`.
3. The hold list reads the pull request's files page by page, and holds as `files not all read`
   unless the number read equals the pull request's `changed_files` (the list-files endpoint
   stops at 3,000 files; rule 2: a partial read is never a pass). `release` is a patch line that adds
   or removes `version =` in `agk.toml` or `"kit_version":` in `kit/manifest.json`, or either file
   with no patch shown. `spec approval` is the label `agk:approve`, or a body line
   `Approval: SPEC-nnnn` with no comment `Approve: <sha> SPEC-nnnn` by a spec approver whose sha
   is a prefix of the head (`reviewers.approval_shas`; the short form `Approve: SPEC-nnnn` is not
   pinned to a head here, so it holds). A protected class is a file, or a renamed file's old
   path, under `constitution/` or `.github/workflows/`, or exactly `config/reviewers.yaml`,
   `kit/templates/ruleset.json` or `scripts/agk/ruleset.py`. `depends-on` reads each
   `Depends-on: #n`: a pull request must be merged, an issue closed as completed. `conflict` is a
   mergeable state of `dirty` or `unknown`, or none at all; any other state that GitHub will not
   merge is refused by the merge call itself (decision 4).
4. The merge is the one call `gh api --method PUT repos/{repo}/pulls/<n>/merge -f sha=<sha> -f
   merge_method=squash`, made once and never retried. Its answers: a merge sha prints
   `merge-cleared #<n> <sha12>: merged <merge sha12>` (exit 0); HTTP 409 is `refused: head moved`
   (exit 3); HTTP 405 reads the head once more and is `head moved` when it moved, else
   `refused: GitHub did not merge: not mergeable (rule 6)` (exit 3); HTTP 5xx or no answer is
   `refused: GitHub cannot be reached for the merge` (exit 3); any other refusal, or an answer
   without `merged: true` and a 40-character sha, is exit 1. Nothing runs after the merge in this
   build: the governance run, the red-branch stop and the record line are build (c).
5. After the setting passes, the command holds the named lock `merge-cleared` of `lock.py` (one
   slot, whatever `lock_slots` says) for the rest of its run; a second run waits, with lock.py's
   wait lines on standard error so that standard output keeps its one line. It has no loop on a
   timer and no second pass.
6. `.claude/hooks/conductor_guard.py` allows exactly `python3|python <the project's own regular
   scripts/agk/merge_cleared.py> --pr <n> --sha <40 lower-case hex>`, without `--shadow`, and only
   when `merge_cleared.auto_merge_setting` reads `on` from the checkout's `agk.toml` and from
   `origin/<default_branch>`'s as last fetched (the way it reads `auto_start`). For that one
   command it prints an explicit `allow` decision, so that the builders' `ask` entries (decision
   7) do not stop the conductor `(verify: a PreToolUse hook's allow lifts a settings ask rule)`;
   if it does not, the conductor is asked, which is the safe side. `gh pr merge`, `gh api` with
   `PUT` on a merge route, another copy, a link, another interpreter form and any extra option
   stay denied. `gh_api_allowed` in `.claude/hooks/architect_guard.py`, which this guard imports,
   reads the method in each form `gh` accepts (`--method V`, `--method=V`, `-X V`, `-XV`,
   `-X=V`) and denies any option it does not recognise.
7. The builders' block (Q-S0039-15, Q-531-1): builder sessions start with
   `.claude/settings.json`, which allows `Bash(python3 scripts/agk/*)`. Its `ask` list gains
   `Bash(python3 scripts/agk/merge_cleared.py*)`, `Bash(python scripts/agk/merge_cleared.py*)` and
   `Bash(*merge_cleared.py*)`, so a builder never runs the command without a person's yes
   `(verify: ask takes precedence over allow)`. No `deny` entry is added, because a project-wide
   deny would bind the conductor too and whether its hook can lift one is `(verify)`.
8. `scripts/agk/session.py review-queue`, with `auto_merge` on at the default branch, lists an
   open pull request whose latest `Verdict:` comment's first line is exactly
   `Verdict: cleared <its full head>` and that would otherwise be skipped as already reviewed, as
   `#<n> <head7> cleared, not merged`. An unreadable setting reads as off.
9. Principle 2 of `constitution/principles.md` and rule 2 of `config/session-rules.md` each gain
   one sentence naming the exception: with `auto_merge = true` on the default branch, the
   conductor alone may merge a pull request it cleared, and only through
   `scripts/agk/merge_cleared.py`. `.claude/agents/conductor.md` says to run the command in the
   same act as posting `Verdict: cleared <sha>`. This repository keeps `auto_merge` off.

## Consequences

With `auto_merge` off, the default, nothing changes for any session. With it on, the conductor
can merge a cleared pull request whose evidence and hold list pass, by one call pinned to the
head it judged; a builder cannot run the command unasked. `kit/manifest.json` and
`kit/hashes.json` are unchanged: no new file is installed.

## Residual

- 2026-11-04: the `ask` entries hold a builder only while the person answering the prompt says no;
  a builder started with every permission skipped is held only by the account boundary and the
  residual of SPEC-0039 (due 2026-12-31).
- 2026-11-04: only the exact first line `Maintainer answer: accept <head>` accepts a `differs`
  check; an acceptance written in other words holds the pull request until the guide of build (e)
  states the form (due 2026-12-31).
