# Upgrade: live proof on the sandbox (for the maintainers; not run by the agent)

Date: 2026-10-16 (from `date -u`). SPEC-0008 rule 23, criterion c of ADR-0015. Q-K3-71 is ruled (option (a), `docs/runs/proposed-spec-amendments-12.md` item 1): the sandbox `gbvraju/agk-sandbox` is a kit 0.1.0 install
stamped only in `[tool.agk]` of `pyproject.toml`; the upgrade reads that stamp, treats it as mode init at 0.1.0 and creates `agk.toml` as its
last write. The agent runs the steps below on a branch of a sandbox clone and opens the pull request (never settings, never `main`); the maintainers
review.

## Setup

```
git clone git@github.com:gbvraju/agk-sandbox.git && cd agk-sandbox && git checkout -b upgrade-0.9.0
KIT=/path/to/agk          # a checkout of this kit at the version to upgrade to (the plugin root also works)
```

## Steps

1. `python3 $KIT/scripts/agk/upgrade.py . --dry-run` prints one line per path (`create`, `replace`, `unchanged`, `conflict`,
   `deleted-locally`, `removed-in-kit`), the `template-*` lines, `dry run: N files would change; ...`, the `Protected classes:` line
   and an ADR skeleton. Record the output. Expected: the `legacy-stamp` line, no `conflict` (the sandbox's vendored files are the kit's 0.1.0 files).
2. `python3 $KIT/scripts/agk/upgrade.py .` (the real run). Record the lines; `git status --short`.
3. Write the ADR of the skeleton (a number, the reason, the decision; `Protected classes:` as printed), run
   `python3 scripts/agk/reviewers.py --codeowners --write` if the output said to, set the `agk.toml` keys the `template-key` lines show.
4. `make governance` and `make test` in the sandbox: green.
5. `git diff --stat origin/main` lists no product file: nothing outside the installed set (`src/`, `tests/` of the project, `README.md`).
6. Open the pull request in the sandbox; `governance` is green.
7. Run step 2 again: `nothing to do`.

## Record

Add `docs/runs/upgrade-live-proof-1.md` with the date, the sandbox commit, the kit version, the lines of steps 1 and 2, the ADR number,
the `git diff --stat` and the `governance` result. Criterion c is met when steps 1 to 7 match. Nothing here touches `gbvraju/colorama` or
`tartley/colorama`.
