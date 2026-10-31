---
name: stack
description: Write one Proposed ADR that sets out two or three stacks as options, with trade-offs and the practices each brings, for the architect to accept one. Writes one file; never commits.
disable-model-invocation: true
argument-hint: ""
---

# /agk:stack

`/agk:stack` writes one Proposed ADR, `docs/adr/<adr>-stack-options.md`, in which two or three stacks are options. The architect accepts
one; the ADR then locks it. Run it after the owner approved the vision.

An engine only drafts. If `[engines]` in `agk.toml` has a `stack` key, it names a skill the session can see (`agk doctor` reports it
as present, absent or missing); use that skill to draft the options. If the key is absent, use the kit's template. Either way the text
is written through the kit's template and passes the kit's check. An engine never decides, never approves, and never edits a protected
file by itself; it does not accept an option. The stack ADR is a new file under `docs/adr/`, which is not changed by an engine's draft
anywhere else.

1. Fetch the default branch and make sure the work tree is clean; if it is not, stop and say so. Read the next free ADR number, create
   the branch from the default branch, and write the skeleton:

```
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/agk/engines.py" stack-ids
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/agk/engines.py" stack-write
```

2. Fill the skeleton from the vision and the charter, and from nothing the owner did not give. In the Decision: **Options** has two or
   three bullets `- Option A — <name>. Trade-offs: <text>. External services: <service>, <service>. Practices: <practice>, <practice>.`,
   where `External services:` names, once and before `Practices:`, each service outside the product that the option relies on
   (identity, email, storage, queues or schedulers, payments, and so on), and is left out when the option relies on none;
   **Practices** has one bullet for every practice any option names, `- <practice>: check (step: <the governance step the adopting
   build adds>)` when a check can verify it (pinned actions, least privilege, security headers, a host-boundary test), or
   `- <practice>: judgement` when it is recorded judgement only, and keeps the template's `local profile` bullet; it keeps the
   template's `fast tests` and `test selection` bullets too, and writes in the parenthesis of `test selection`, for each option,
   the `[testing]` profile and the `always_full` paths of `agk.toml` it proposes (`docs/guides/testing.md`); **Chosen** stays
   `none yet`. Never set `Status: Accepted` and never name an option as chosen: that is the
   architect's, in a later change.
3. Check, and correct the file on a failure, at most three rounds, then stop and report:

```
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/agk/engines.py" stack-check
```

   then run `make governance`. Both must pass.
4. Then say what the check cannot check: that the options are the right ones and that the trade-offs are true. Each practice marked
   `check` is added as a governance step by the build that adopts the stack, not by this command. Then say how an option is
   accepted, once this Proposed ADR is merged: by one ordinary commit, in its own pull request, that sets `Status: Accepted` and
   `Chosen: Option <X> — <one-line reason>` together (the line reads `3. **Chosen**: Option <X> — <one-line reason>`), and nothing
   else. It is not a `Final:` commit: a `Final:` commit may change only status lines, and while the ADR is Proposed the check
   refuses any `Chosen` but `none yet`, so only the two lines together pass. `stack-check` accepts the pair, and the expected
   verdict on that pull request is a plain `Verdict: cleared <sha>`. The build which accepts the stack also
   copies the chosen option's `[testing]` values, as the ADR's `test selection` practice gives them, into the `[testing]` table
   of `agk.toml` in the same pull request as the ADR, by a second ordinary commit that changes nothing else, so one ADR sets
   them; the ADR names `agk.toml`, which covers that protected path. Print the text below for the person, with the ADR number and
   the file name filled in:

   The prompt for the accepting change:

```
Accept option <X> of the stack ADR ADR-<n> (docs/adr/<n>-stack-options.md). From a fresh default branch, on a new branch, change
only two lines of that file in one ordinary commit: "- Status: Proposed" becomes "- Status: Accepted", and "3. **Chosen**: none
yet" becomes "3. **Chosen**: Option <X> — <one-line reason>". Then, in a second ordinary commit, copy the [testing] values
that the ADR's test selection practice gives for option <X> into the [testing] table of agk.toml. Run engines.py stack-check
and make governance; both must pass. Then run engines.py stack-next-steps and open one pull request with the body it prints,
unchanged. Neither commit is a Final commit, and they change nothing else.
```

   The body of its pull request is never written by hand: after the accepting commit, the session runs
   `stack-next-steps` again on that branch, and it prints the commit, the push and a body whose `Advances:`, `Build-state row:`
   and `Summary:` lines passed the repository's body check (the Summary cut to 120 characters at a word boundary).

   On that accepting branch `stack-next-steps` prints one extra step after the body: the default local-profile requirement, a
   ready-to-run `/agk:spec "<sentence>"` made from `kit/templates/local-profile.md` and filled in with the accepted option's
   `External services:` (the whole product on one machine with one command, a stand-in for each external service chosen by a
   setting, invented data seeded on start, a startup guard that refuses it outside the local environment). It is an offer:
   nothing is written until a person runs it. A spec approver (`spec_approvers` in `config/reviewers.yaml`) accepts it with the
   `Approve:` line of the intake; or a maintainer declines it with one line in the Residual of the stack ADR,
   `local profile: declined, <reason of at least 20 characters> (YYYY-MM-DD)`. While neither is done, `stack-check` prints the
   information line `local profile: not decided`, never a failure. Pass the extra step on to the person unchanged.

5. Last, print the next steps of this pull request, the Proposed ADR. Add `--brief <n>` when the work answers a brief, or `--brief none`
   when the person says the repository has no open brief. The script prints the body as a file path and its text, only after the
   repository's own `check_pr_body.py` passed it, and refuses rather than print a body that fails. Use the body unchanged.

```
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/agk/engines.py" stack-next-steps --brief <n|none>
```

Do not commit or push, and do not open a pull request: the person or their session does.
