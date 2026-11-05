# Proposed spec amendments 120 (SPEC-0039; REQ-046)

Date: 2026-11-05 (from `date -u`). Approved specs change only through a proposal like this one (principle 6). Written for
ADR-0284 (brief #576), which stays `Proposed` for the maintainers' decision. The path:
`docs/specs/0039-the-conductor-merges-a-cleared-pull-request-through-one-guarded-command.md`. The number 120 is the one
the conductor reserved in its fix list on #577 of 2026-11-05, which answers Q-576-1. This amendment is applied to the spec
text in the same pull request. It needs a person's `Approve: SPEC-0039` on the pull request; no session posts it.

1. **The after-merge governance run gets the merged body (rule 6).** Rule 6's command
   `env -i PATH="$PATH" HOME=<scratch>` gains `AGK_PR_BODY=<scratch>/home/pr-body.md`: a file holding the merged pull
   request's body, as the command read it before the merge (an empty file for an empty body), so that a `Covered-by:`
   build is judged as CI judges it. No token and no other variable is passed; the file is removed with the scratch folder
   in every case. Nothing else of rule 6 changes.
