# Proposed spec amendments 98 (SPEC-0034, SPEC-0012, SPEC-0013; REQ-039)

Date: 2026-10-30 (from `date -u`). Approved specs change only through a proposal like this one (principle 6). It is applied by
ADR-0183 (brief #263 build (b)), which stays `Proposed` for the maintainers' decision, and it changes
`docs/specs/0034-a-team-sets-how-many-builder-sessions-run-at-once-and-agk-ha.md`, `docs/specs/0012-intake.md` and
`docs/specs/0013-playbook.md`. The number 98 is asked as Q-263-B1 (95 is held for brief #305).

1. **SPEC-0034 rule 9, a sentence added after the first `check_pr_body.py` sentence.** "The router's red-branch issue (SPEC-0032
   rule 7: its title, its `Priority: 0` line and the router's token as its author) is not a brief for this rule, so a repository
   whose only open `agk-brief` issue is that one needs no `Brief:` line; an issue of the same shape written by anyone else is a
   brief. The governance workflow saves up to 100 open briefs, so that the red-branch issue cannot hide another."
2. **SPEC-0012 rule 3, the command replaced.** "`git switch --no-track -c`" for "`git switch -c`", and a sentence added: "The branch
   does not track the default branch, so that a plain push refuses without offering a push to the default branch; `next-steps`
   prints the push command `git push -u origin HEAD`."
3. **SPEC-0013 rule 3, a sentence added.** "`next-steps` shows the vision and the project charter, each with its path and full
   text, before the commit message, and prints the push command `git push -u origin HEAD`. Where `gh auth status` succeeds, it also
   prints one command `gh pr create --base <default branch> --title <commit title> --body-file <body file>`, so that the
   repository's pull request template does not replace the body; the person runs it, the skill does not."
4. **SPEC-0013 rule 4, words added.** "On a new branch `start/<slug>` from `origin/<default branch>`" becomes "On a new branch
   `start/<slug>` from `origin/<default branch>`, created with `--no-track`".
