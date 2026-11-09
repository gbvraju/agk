# The default branch is red

## When this applies

The required checks of the default branch's head fail, and the one issue titled `The default branch is red` is open.

## Who acts

The router opens the issue. A builder takes its brief. A person acts only when no builder is running or the fix needs a decision.

## Steps

1. Read the issue: it names the failing check, the head and the run. Start from that, not from a guess at the cause.
2. Stop other merges. They are already held: [merge_cleared.py](../../scripts/agk/merge_cleared.py) refuses while the head is red, so start none by hand.
3. When `[failures] issues` is on in `agk.toml`, look for a known fix, with the signature and test of the failure:

   ```
   python3 scripts/agk/failures.py seen --signature <sig> --test <id>
   ```

4. Fix it by one pull request that carries its fix record, which [check_pr_body.py](../../scripts/agk/check_pr_body.py) checks.
5. Let the merge of that fix turn the head green.

## Over when

The router has closed the issue, and `session.py next` no longer prints `default branch red`.

## By mode

- GitHub: as above.
- Local: there is no router, so a person holds the merges, and the one run that stands in for CI (SPEC-0046 rule 12), once built, reports the head in place of CI.
- Personal: red is the failed floor run on the clone. There is no issue and no router, and a session pushes nothing.
