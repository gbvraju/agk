# Proposed spec amendments 100 (SPEC-0006, SPEC-0013; REQ-039)

Date: 2026-10-30 (from `date -u`). Approved specs change only through a proposal like this one (principle 6). It is applied by
ADR-0194 (brief #263 build (a)), which stays `Proposed` for the maintainers' decision, and it changes `docs/specs/0006-doctor.md` and
`docs/specs/0013-playbook.md`. The number 100 is the next free one after 99 (Q-263-A2).

1. **SPEC-0006 rule 3, the reason classes.** The list gains `plan-limit` and `forbidden`, and two sentences are added: "`plan-limit`:
   GitHub answered 403 with its plan message (it holds "Upgrade to GitHub Pro" or "make this repository public"); rulesets and branch
   protection on a private repository need a paid plan, and the hint says to upgrade the plan or make the repository public.
   `forbidden`: a read was refused with 403 or 404 although `permissions.admin` in the repository read is true."
2. **SPEC-0006 rule 6, the ruleset read.** "a 403 or 404 on a ruleset read is `cannot-check` (`no-admin`)" reads "a 403 or 404 on a
   ruleset read is `cannot-check`: `plan-limit` when the 403 carries GitHub's plan message; otherwise `forbidden` when
   `permissions.admin` in the repository read is true, and `no-admin` when it is false or the repository could not be read".
3. **SPEC-0006 rule 15, the cases.** The list gains `plan-limit` (403 with the plan message on the ruleset list: `cannot-check`
   `plan-limit`) and `admin-forbidden` (an admin's repository read and a 403 on a ruleset read: `cannot-check` `forbidden`); the case
   `no-admin` records `permissions.admin` false.
4. **SPEC-0013 rule 19, the text printed for applying by hand.** "it prints the exact text of the ruleset (from
   `kit/templates/branch-rules.txt`)" reads "it prints the reason (`plan-limit`, `no-admin`, `forbidden` or the reason of the failed
   read), the phase it chose by rule 21 (`phase N (...)`) and the rules of that phase: in phase 2 the exact text of
   `kit/templates/branch-rules.txt`, in phase 1 the same text without the required status check `governance` and one line saying that
   phase 2 adds it once `governance` has succeeded on the default branch". A sentence is added: "With `plan-limit` it says that
   rulesets and branch protection on a private repository need a paid plan, and that applying it by hand is refused the same way
   until the plan is upgraded or the repository is public."
