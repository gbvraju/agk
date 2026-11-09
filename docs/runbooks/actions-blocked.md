# GitHub Actions is blocked

## When this applies

The checks of a new head never start, or every job fails at once before any step runs: minutes exhausted, billing blocked or an outage. A job that starts, runs its steps and fails is a red check of a change, and this page does not apply.

## Who acts

A person with admin on the repository. A builder only says so in its `Report:`, as [the local-mode guide](../guides/local-mode.md) sets out.

## Steps

1. Read the minutes level and the run-out day:

   ```
   python3 scripts/agk/minutes.py --line
   ```

2. Confirm by [the refusal message](../guides/local-mode.md#when-to-use-it) that a job never started, and that this is not a red check of a change.
3. Choose one: raise the limit or pay the bill; wait for the allowance or the outage to end; or [enter local mode](../guides/local-mode.md#enter-local-mode).

## Over when

Local mode was never entered and new heads get runs again, or `local_mode.py leave` reports a green catch-up and the record issue is closed.

## By mode

- GitHub: as above.
- Local: this is the state the guide's [leave section](../guides/local-mode.md#leave-local-mode) ends.
- Personal: there are no Actions, so this page does not apply.
