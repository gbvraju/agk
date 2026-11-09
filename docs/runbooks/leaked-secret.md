# A secret has leaked

## When this applies

A secret scan reports a finding, in the `Secret scan` step of the governance workflow or the `secret-scan` step of `prepush.py`, or a person sees a credential in a commit.

## Who acts

A person, always. A session that sees a finding stops, reports only that the scan failed and where this page is, and never reads, prints or moves the value. Never paste the value into an issue, comment, chat or session.

## Steps

1. Revoke the credential at its provider first, before anything in the repository: a value in a pushed commit must be treated as read.
2. Issue its replacement and store it where the project keeps secrets, never in the repository.
3. Check the provider's own access record for use since the leak.
4. Remove the value from the working tree by a normal pull request. Rewrite no history and add no entry to any ignore list: a revoked value in history is harmless, and rewriting a shared default branch needs the ruleset changed, a person's own decision outside this page.
5. Write the record, only now: one issue titled `A leaked secret was revoked` with the label `agk-secret-leak` and a body of exactly two lines, `Detected: <UTC time>` and `Revoked: <UTC time>`. Name no value, credential, provider or path. Create the label once if the repository lacks it:

   ```
   gh label create agk-secret-leak
   ```

## Over when

The credential is revoked and replaced, the access record is read, and the record issue is closed. A later green scan says nothing about the old commit, because a scan on a push reads only the pushed range.

## By mode

- GitHub: as above.
- Local: as above; the record issue is still opened, since GitHub itself is reachable.
- Personal: the same steps, with no issue opened, so nothing is measured.
