# Proposed spec amendments 139 (SPEC-0039; REQ-046)

Date: 2026-11-08 (from `date -u`). Approved specs change only through a proposal like this one (principle 6). Written for
ADR-0354 (brief #765), which stays `Proposed` for the maintainers' decision. The path:
`docs/specs/0039-the-conductor-merges-a-cleared-pull-request-through-one-guarded-command.md`. The number 139 is the next free
one: 138, reserved for brief #765, was taken on the default branch by brief #751 first. This amendment is not applied to the spec text in this pull request; the owner decides it, and
it needs a person's `Approve: SPEC-0039`; no session posts it.

1. **The GitHub-mode runner (rule 2).** Rule 2 gains: in GitHub mode (`execution` not `local`, `forge` not `files`)
   with `auto_merge = true`, the `merger` job of the governance workflow is the runner of the command, beside the
   conductor. It starts on a `Verdict:` or `Approve:` comment on a pull request, after the green `governance` job of a
   ready pull request and on a green `proof` run of a pull request head, checks out the default branch, and runs exactly `python3 scripts/agk/merge_cleared.py --pr <n>
   --sha <head>`, its one merge call under the secret `AGK_MERGE_TOKEN`, after `merge_cleared.py --event` named that pull request and head (the
   latest verdict clears it; otherwise nothing runs and nothing is posted). Every re-check stays in the command.
2. **After the job's run (rules 6 and 9).** `merge_cleared.py --report` dispatches the default branch's `governance`
   run only after a merge made with the job's own token, which starts no workflow (a merge made with the secret starts
   the push run by itself `(verify)`), and posts one comment `merger: <line>` for a
   hold or a refusal, never the same line twice on a pull request, and nothing for `checks pending`; the next comment
   or green run is the next try, with no loop. A merge GitHub refuses for a ruleset violation holds as `merge refused by the ruleset (rule 6)`, exit 3.
3. **Rule 10.** "The CI path adds no workflow job, no secret and no ruleset change" reads "The CI path adds one
   workflow job (1 above), one optional secret `AGK_MERGE_TOKEN` and no ruleset change: the owner stores a fine-grained
   token for the repository (Contents and Pull requests, read and write) as an Actions secret, so that the merge runs
   under the owner's existing admin bypass. Without it the job posts one line `merge needs AGK_MERGE_TOKEN or the
   owner's tap` and does nothing else."
4. **Rule 8.** "Only the conductor role may merge" reads "Only the conductor role, and in GitHub mode the merger job
   of 1, may merge"; the rest of the rule is unchanged.
5. **Tests.** A cleared head merges, and the default branch's run is dispatched only after a merge by the job's own token; an uncleared head, a held head, a
   local, personal or off project do nothing (a held head gets one comment); a ruleset refusal is said once; a missing
   secret posts its one line and merges nothing.
