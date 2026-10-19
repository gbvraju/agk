# agk — Agentic Governance Kit

AGK is a set of files and checks you install into a GitHub repository that you build with Claude Code.

- **Decisions are recorded.** A change to a protected path needs an ADR in the same pull request.
- **Checks are enforced.** `make governance` and the `governance` workflow fail a pull request that breaks a rule.
- **Delivery is proven.** The `proof` check reports whether the new tests of a pull request fail without its change.
- **Drift is measured.** A weekly audit lists what slipped past the rules.
- **A Monday report.** One GitHub issue a week says what was delivered, what waits for you and what is at risk.

## Who it is for, and what it needs

It is for one developer, or a small team, who builds with Claude Code and wants the decisions and the proof to live in the
repository, not in a chat. You need:

- [Claude Code](https://claude.com/claude-code), logged in.
- A GitHub repository that you administer (the ruleset step needs admin), with Issues and Actions turned on.
- The GitHub CLI (`gh`), logged in with your own account.
- Python 3.11 or newer, `git` and `make`; `pytest` for `make test`.

## The 10-minute path

Steps 1 to 4 take about ten minutes (not yet timed by anyone outside the project `(verify)`). The whole path to the first
governed merge takes longer. Each step has its command and the output to expect in
[the getting-started guide](docs/guides/getting-started.md).

1. Make an empty repository on GitHub, clone it and make the first commit on `main`.
2. Install the plugin: `claude plugin marketplace add gbvraju/agk`, then `claude plugin install agk@agk`.
3. In Claude Code, in the repository: `/agk:init`. Put your GitHub handle in `config/reviewers.yaml`, then commit and push.
4. `/agk:ruleset` to protect `main`. It picks phase 1, or phase 2 when `governance` has already run on `main`.
5. `/agk:start "<your problem statement>"`; review the vision and the project charter it drafts, and merge.
6. `/agk:spec "<one sentence>"`; review the requirement and the Draft spec it drafts, and merge.
7. Run the architect session (`claude --agent architect`), then an implementation session, then merge the pull request the
   architect has cleared.
8. `/agk:ruleset` again, if it picked phase 1, once `governance` has run on `main`.

## What you get each week

| When (UTC) | What | Where |
| --- | --- | --- |
| Monday 06:43 | One record per pull request closed in the week before | an issue labelled `agk-metrics` |
| Monday 07:13 | The product report: delivered, proven, needs you, at risk, cost | an issue labelled `agk-product-report` |
| Saturday 06:17 | The drift audit, only when it finds something | an issue labelled `agk-drift-audit` |

Expect the Monday issues hours late: on 2026-10-19 the metrics issues came about 7 hours after their slot and the report about
7.5 hours; in India that is usually Monday evening. GitHub can also pause scheduled workflows in a repository with no activity. Each
workflow can also be started by hand from the Actions tab. The schedules are in `.github/workflows/`.

## Honest limits

- **It checks that the process happened, not that the work is good.** A check can see an ADR, a test, a verdict line. It cannot
  see whether the decision is wise, the test is meaningful or the code is right. In the shadow reviews the reviewer agent caught
  0 of 5 human findings (`docs/runs/shadow-review-4.md`); it is experimental and never a gate.
- **No claim is made that AGK catches defects, saves money or beats another tool.** The comparison with other
  spec-driven tools is not written yet (ADR-0025, due 2026-12-31).
- **Claude Code and GitHub only.** The checks and the workflows assume both.
- **Applying the ruleset from `/agk:ruleset` is not yet proven live.** The plan, which only reads, is. The first write was
  refused by the proxy of the session that tried it (`docs/runs/ruleset-sandbox-proof.md`). If the apply step fails for you,
  the plan also prints the exact settings to set by hand.
- **The architect session is not yet proven live.** Its start flag and its guard hook are marked `(verify)` in
  `.claude/agents/architect.md`.
- **Nobody outside the project has used these guides yet.** Where you get stuck, open an issue with the
  [I got stuck form](.github/ISSUE_TEMPLATE/stuck.md).

## The guides

- [Getting started](docs/guides/getting-started.md): a new repository, from nothing to the first governed merge.
- [The product-owner guide](docs/guides/product-owner.md): what arrives each Monday and what to do about it.
- [Adopting AGK in an existing codebase](docs/guides/existing-codebase.md): install without touching your product, record today's
  behaviour, then change.
- [Security](docs/guides/security.md): what AGK stores, where code and credentials go, what each workflow may write.
- [Reference](docs/guides/reference.md): every command and file of the kit.

What the kit was shown to do is recorded in `docs/runs/`: `k1-live-proof.md` (install), `plugin-live-proof.md` (the plugin),
`doctor-live-proof.md`, `upgrade-live-proof.md`, `drift-audit-live-run-1.md`, `metrics-first-run.md`,
`product-report-live-1.md` and `intake-proof.md`.

Licence: Apache-2.0.
