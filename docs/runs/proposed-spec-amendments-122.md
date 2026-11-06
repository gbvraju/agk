# Proposed spec amendments 122 (SPEC-0039; REQ-046)

Date: 2026-11-06 (from `date -u`). Approved specs change only through a proposal like this one (principle 6). Written for
ADR-0293 (brief #601), which stays `Proposed` for the maintainers' decision. The path:
`docs/specs/0039-the-conductor-merges-a-cleared-pull-request-through-one-guarded-command.md`. The number 122 is the one
the conductor reserved in its fix list on #603 of 2026-11-06 (on 322b838), which answers Q-601-1. This amendment is
applied to the spec text in the same pull request. It needs a person's `Approve: SPEC-0039` on the pull request; no
session posts it.

1. **The after-merge governance run gets the record comments (rule 6).** Before the run the command fetches the Final
   comment of each SPEC-0021 rule 3a record in the merge commit's history (the ids that `check_adrs.py --record-ids`
   prints there), with the same GETs as the governance workflow's `Record comments` step (one
   `GET repos/{owner}/{repo}/issues/comments/<id>` each; a comment that cannot be read is left out, so its record counts
   for nothing), and writes them to `<scratch>/home/record-comments.json`. Rule 6's command
   `env -i PATH="$PATH" HOME=<scratch> AGK_PR_BODY=<scratch>/home/pr-body.md` gains
   `AGK_RECORD_COMMENTS=<scratch>/home/record-comments.json`. `check_protected_changes.py` and `check_release.py` read
   the file that `AGK_RECORD_COMMENTS` names when `--comments` is absent, so that a `Covered-by:` line naming an ADR
   accepted by a rule 3a record is judged after the merge as CI judges it. No token and no other variable is passed; the
   file is removed with the scratch folder in every case. Nothing else of rule 6 changes.
