# Upgrade: live proof on the sandbox (for the maintainers; not run by the agent)

Date: 2026-10-16 (from `date -u`). SPEC-0008 rule 23, criterion c of ADR-0015. **Blocked on Q-K3-71** (`docs/runs/proposed-spec-amendments-12.md`,
item 1): the sandbox `gbvraju/agk-sandbox` is a kit 0.1.0 install whose stamp is `[tool.agk]` in `pyproject.toml`; it has no
`agk.toml`, so `upgrade.py` refuses it today. What follows is the procedure once the maintainers have ruled; steps 1 and 2 can be run
now and show the refusal.

## Setup

```
git clone git@github.com:gbvraju/agk-sandbox.git && cd agk-sandbox && git checkout -b upgrade-0.9.0
KIT=/path/to/agk          # a checkout of this kit at the version to upgrade to (the plugin root also works)
```

## Steps

1. `python3 $KIT/scripts/agk/upgrade.py . --dry-run`. Today: `refused: agk.toml is missing (path class agk.toml); ...`, exit 1, nothing written.
2. After Q-K3-71 is ruled and built: the same command prints one line per path (`create`, `replace`, `unchanged`, `conflict`,
   `deleted-locally`, `removed-in-kit`), the `template-*` lines, `dry run: N files would change; ...`, the `Protected classes:` line
   and an ADR skeleton. Record the output. Expected: no `conflict` (the sandbox's vendored files are the kit's 0.1.0 files).
3. `python3 $KIT/scripts/agk/upgrade.py .` (the real run). Record the lines; `git status --short`.
4. Write the ADR of the skeleton (a number, the reason, the decision; `Protected classes:` as printed), run
   `python3 scripts/agk/reviewers.py --codeowners --write` if the output said to, set the `agk.toml` keys the `template-key` lines show.
5. `make governance` and `make test` in the sandbox: green.
6. `git diff --stat origin/main` lists no product file: nothing outside the installed set (`src/`, `tests/` of the project, `README.md`).
7. Open the pull request in the sandbox; `governance` is green.
8. Run step 3 again: `nothing to do`.

## Record

Add `docs/runs/upgrade-live-proof-1.md` with the date, the sandbox commit, the kit version, the lines of steps 2 and 3, the ADR number,
the `git diff --stat` and the `governance` result. Criterion c is met when steps 2 to 8 match. Nothing here touches `gbvraju/colorama` or
`tartley/colorama`.
