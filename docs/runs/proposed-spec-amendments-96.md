# Proposed spec amendments 96 (SPEC-0032, SPEC-0006; REQ-039)

Date: 2026-10-29 (from `date -u`). Approved specs change only through a proposal like this one (principle 6). It is applied by
ADR-0178, and it changes `docs/specs/0032-github-events-label-each-pr-people-approve-specs-a-red-branch-stops-work.md` and
`docs/specs/0006-doctor.md`. The conductor confirmed the number 96 in the verdict on 08b173a (Q-302-2);
amendment 95 is held for brief #305.

1. **SPEC-0032 rule 1.** The `pull_request` types become `opened, synchronize, reopened, edited, closed`, and the rule gains:
   "On `closed` the job runs only when the pull request merged. When it merged, `route.py` reads the pull request again with
   GET and, when its body has one line `Finishes: #n` beside the line `Brief: #n` naming the same number, closes issue #n as
   completed with one comment that names the pull request and its merge commit, provided #n is an open issue labelled
   `agk-brief` (brief #302)."
2. **SPEC-0032 rule 8.** "opens or closes only the issue of rule 7" becomes "opens or closes only the issue of rule 7, and
   closes the brief a merged pull request finishes (rule 1)"; "the router posts no comment" gains "but the one comment on the
   brief it closes".
3. **SPEC-0006 rule 5.** A new row after `brief-label`: `brief-finished` | warn | an open issue labelled `agk-brief` has pull
   requests whose body names it with `Brief: #n`, none of them is open, at least one merged, and the latest merge is more than
   a day old (the briefs are listed) | close each brief listed as completed if its work is done; the last pull request of a brief
   carries `Finishes: #n` beside `Brief: #n` (session rule 28).
4. **SPEC-0006 rule 6.** The reads gain `gh api repos/{o}/{r}/issues?state=open&labels=agk-brief&per_page=100` and
   `gh api repos/{o}/{r}/pulls?state=all&per_page=100` (the latest 100 pull requests), both for `brief-finished`; the title of
   the rule counts them (with the label read of `brief-label`, seven reads, and an eighth where the product report is
   installed).
5. **Tests (SPEC-0006 rule 14).** `tests/kit/test_route_finishes.py` (the router and the workflow),
   `tests/kit/test_check_pr_body.py` (the line), `tests/kit/test_doctor_finished_briefs.py` and the doctor case
   `brief-finished-open`, and `tests/kit_dev/test_route_finishes_install.py` (init and upgrade). Their marker is `REQ-039`.
