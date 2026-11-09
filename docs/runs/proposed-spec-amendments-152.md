# Proposed spec amendments 152 (SPEC-0032; REQ-063)

Date: 2026-11-09 (from `date -u`). Approved specs change only through a proposal like this one (principle 6). SPEC-0056
rule 13 calls for it and brief #865 builds it; it changes `docs/specs/0032-github-events-label-each-pr-people-approve-specs-a-red-branch-stops-work.md` once the owner's `Approve:` line approves it, and no Approved spec is edited in this pull request.

1. **SPEC-0032 rule 7, the words on the shape of the issue.** "`Answers:` with the failing check's name, the sha and the run's
   link, and `Size: S`; it names no cause." becomes "`Answers:` with the failing check's name, the sha and the run's link,
   one line `Runbook: docs/runbooks/red-default-branch.md` (SPEC-0056 rule 13: a path and never a value), and `Size: S`; it
   names no cause."
