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
   three bullets `- Option A — <name>. Trade-offs: <text>. Practices: <practice>, <practice>.`; **Practices** has one bullet for every
   practice any option names, `- <practice>: check (step: <the governance step the adopting build adds>)` when a check can verify it
   (pinned actions, least privilege, security headers, a host-boundary test), or `- <practice>: judgement` when it is recorded
   judgement only; **Chosen** stays `none yet`. Never set `Status: Accepted` and never name an option as chosen: that is the
   architect's, in a later change.
3. Check, and correct the file on a failure, at most three rounds, then stop and report:

```
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/agk/engines.py" stack-check
```

   then run `make governance`. Both must pass.
4. Last, say what the check cannot check: that the options are the right ones and that the trade-offs are true. Each practice marked
   `check` is added as a governance step by the build that adopts the stack, not by this command. Then say how an option is
   accepted, once this Proposed ADR is merged: by one ordinary commit, in its own pull request, that sets `Status: Accepted` and
   `Chosen: Option <X> — <one-line reason>` together (the line reads `3. **Chosen**: Option <X> — <one-line reason>`), and nothing
   else. It is not a `Final:` commit: a `Final:` commit may change only status lines, and while the ADR is Proposed the check
   refuses any `Chosen` but `none yet`, so only the two lines together pass. `stack-check` accepts the pair, and the expected
   verdict on that pull request is a plain `Verdict: cleared <sha>`. Print both texts below for the person, with the ADR number,
   the file name and the requirement filled in:

   The prompt for the accepting change:

```
Accept option <X> of the stack ADR ADR-<n> (docs/adr/<n>-stack-options.md). From a fresh default branch, on a new branch, change
only two lines of that file in one ordinary commit: "- Status: Proposed" becomes "- Status: Accepted", and "3. **Chosen**: none
yet" becomes "3. **Chosen**: Option <X> — <one-line reason>". Run engines.py stack-check and make governance; both must pass.
Open one pull request with the body below. This is not a Final commit, and it changes nothing else.
```

   The body of its pull request (keep the `Summary:` line at most 120 characters; add `Brief: #<n>` when the repository has an
   open brief):

```
Advances: REQ-<n>
Build-state row: <date -u> REQ-<n> <status> (unchanged), the stack ADR ADR-<n> accepts option <X>
Summary: The project's stack is chosen: option <X>, <its name>.
Decisions taken: ADR-<n> Accepted, option <X> chosen by the person who owns the stack (<one-line reason>).
Questions: none
Verified: engines.py stack-check: ok engines-stack; make governance: all checks ok
```

Do not commit or push, and do not open a pull request: the person or their session does.
