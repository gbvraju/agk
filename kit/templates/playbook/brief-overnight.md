# Brief: {{date}} overnight

Repository: {{repo}} (default branch `{{default_branch}}`). Branch prefix: `{{branch_prefix}}`.
Next free numbers, read from `origin/{{default_branch}}` when this skeleton was printed: requirement {{next_req}}, ADR {{next_adr}}, spec {{next_spec}}.
Never type a number from memory: read it again before you write a file.

## Rules block

- Never merge.
- Never poll CI.
- Check the state of your pull request before every push: `gh api repos/{{repo}}/pulls/{{n}}`.
- One pull request per item, branched from `origin/{{default_branch}}`, never stacked, one open at a time.
- You implement; you never decide. Where this brief leaves something open, record a question and take the most conservative reading.
- Push and stop.

## Items

### Item 1: (title)

- Branch: `{{branch_prefix}}/<slug>`
- Advances: (a requirement id)
- Do: (what to build, in testable terms)
- Done means: (what the reviewer will check)
- Size: S|M|L
- Expected: <low>-<high> hours

## Report format

For each item: the pull request URL, the head commit, the changed lines (code, tests, fixtures separately), and every question raised. The pull request body also carries `Brief: <path>#<item>` and the item's `Size:` and `Expected:` lines, copied unchanged.
