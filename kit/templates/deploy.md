# Deploy

Where it runs: {{hosting}}.

The kit writes these steps and changes no workflow and no hosting setting: a deploy is the person's own act
(brief #1594, ADR-0674). Until a hosting option is chosen in the stack record, the product runs on this machine
only, as the README says.

## Steps

1. Choose where it runs: the stack record's hosting option is the next step to decide, with the steward.
2. Put each setting of `.env.example` in that place's own settings store, never in a tracked file.
3. Run the tests (`python3 -m pytest -q`) and `make governance` on the commit to deploy; both pass.
4. Start it there with `{{run}}`{{health}}.
5. Write the date, the commit and the result in the pull request or the release notes.
