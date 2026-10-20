# Brief: {{date}} day

Repository: {{repo}} (default branch `{{default_branch}}`). Branch prefix: `{{branch_prefix}}`.
Next free numbers, read from `origin/{{default_branch}}` when this skeleton was printed: requirement {{next_req}}, ADR {{next_adr}}, spec {{next_spec}}.

## Rules block

- Never merge.
- Never poll CI.
- Check the state of your pull request before every push: `gh api repos/{{repo}}/pulls/{{n}}`.
- Wait for the verdict of the architect session on each pull request before the next one is started.
- You implement; you never decide.

## Items

### Item 1: (title)

- Branch: `{{branch_prefix}}/<slug>`
- Advances: (a requirement id)
- Do: (what to build)
- Done means: (what the reviewer will check)
- Size: S|M|L
- Expected: <low>-<high> hours

## Report format

For each item: the pull request URL, the head commit, the changed lines, the verbatim test counts, and every question raised. The pull request body also carries `Brief: <path>#<item>` and the item's `Size:` and `Expected:` lines, copied unchanged.
