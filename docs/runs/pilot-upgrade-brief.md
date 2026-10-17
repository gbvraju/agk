# Pilot upgrade brief: kit 0.16.0, the zero-product-file proof, and a dry run of the weekly product report

For the session that works in the pilot repository. The maintainers paste it; it names no repository. Rules that hold
throughout: you implement and never decide; you never merge and never enable auto-merge; no secrets anywhere; dates from
`date -u`; if a step does not give the result written under it, **stop and report** (do not repair).

`KIT` below is a checkout of the kit (or the plugin root) whose `kit/manifest.json` says `"kit_version": "0.16.0"`.
`TARGET` is the root of the pilot repository. If `KIT` is not at 0.16.0, stop and report.

## 1. Before anything is written

1. In `TARGET`, on the default branch, up to date with `origin`: `git status --porcelain` prints nothing, and
   `git symbolic-ref -q refs/remotes/origin/HEAD` prints a ref (if it does not: `git remote set-head origin --auto`).
2. Record `git rev-parse HEAD` and the `version` line of `agk.toml` (the version you upgrade from).
3. Check that no other pull request of yours is open. One at a time.

## 2. The upgrade

1. `python3 KIT/scripts/agk/upgrade.py TARGET --dry-run`. Read the whole report. It must list files to create or replace and
   no conflict. A conflict means a kit file was edited locally: stop and report the path class it names.
2. `git switch -c agk-upgrade-0.16.0`, then `python3 KIT/scripts/agk/upgrade.py TARGET` (no `--dry-run`). It prints what it
   wrote; the last write is the `version = "..."` line of `agk.toml`.
3. The new workflow is `.github/workflows/product-report.yml` (Mondays 07:13 UTC, and by hand). It is one of three
   workflows that write issues with the workflow token; the upgrade prints nothing else about it.

## 3. The zero-product-file proof

Adoption touched no product file on its first day; the upgrade must not either. From `TARGET`:

```sh
python3 - <<'PY'
import json, os, subprocess, sys
kit = json.load(open(os.environ["KIT"] + "/kit/manifest.json"))
owned = set(kit["verbatim"]) | {"agk.toml"}
changed = subprocess.run(["git", "status", "--porcelain", "-z", "--untracked-files=all"],
                         capture_output=True, text=True, check=True).stdout.split("\0")
paths = sorted(entry[3:] for entry in changed if entry)
foreign = [p for p in paths if p not in owned]
print(len(paths), "paths changed;", len(foreign), "are not kit files")
for p in foreign:
    print("NOT A KIT FILE:", p)
sys.exit(1 if foreign else 0)
PY
```

Export `KIT` (the path of the kit checkout) before running it. The result must be `0 are not kit files`. Also run `git diff --stat -- agk.toml`: the only
change in `agk.toml` is the `version` line. Anything else: stop and report the output verbatim.

## 4. The pilot's own checks

1. `make governance` and `make test` in `TARGET`. Both must pass; record the commands and the pass counts verbatim.
2. Open one pull request from `agk-upgrade-0.16.0` to the default branch, with the pilot's pull request template filled in
   (the upgrade advances the kit requirement the template asks for; if it asks for something you cannot name, say so in
   the body as a question). **Do not merge. Stop until the maintainers merge it.**

## 5. After the maintainers merge: a dry run of the report

1. Render locally first (writes nothing to GitHub). From `TARGET` on the default branch, up to date:

   ```sh
   today=$(date -u +%F)
   python3 scripts/agk/facts.py --today "$today" > "$TMPDIR/facts.json"
   python3 scripts/agk/product_report.py --facts "$TMPDIR/facts.json" --today "$today" > "$TMPDIR/report.md"
   grep '^## ' "$TMPDIR/report.md"
   ```

   The five headings must print in this order: `## Delivered`, `## Proven`, `## Needs you`, `## At risk`, `## Cost`.
   If `facts.py` prints `unknown` for a repository field, keep it; the report prints it as `unknown` and that is a result.
2. Then once on GitHub: `gh workflow run product-report.yml --ref <default branch> -f today=<a Monday, YYYY-MM-DD>`, and
   wait for the run with `gh run watch` (this is one run you started yourself; do not poll beyond it). The run creates, or
   updates in place, the one issue `agk product report YYYY-Www` labelled `agk-product-report` for the ISO week before
   that Monday. It writes nothing else.
3. Record: the run URL and its conclusion; the issue number and title; the five headings as they appear in the issue
   (verbatim); the footer lines (`facts: <commit>`, `metrics: ...`, `drift audit: ...`).

## 6. Stop and report

Report to the maintainers, in this order: the version you upgraded from and to; the dry-run report of step 2.1 (counts
only); the zero-product-file result of step 3 (verbatim); the `make governance` and `make test` results; the pull request
URL and head SHA; the local report headings and the run URL, conclusion, issue number and headings of step 5; anything
that surprised you. Then stop. The scheduled run on Monday 2026-11-02 at 07:13 UTC is not yours to watch.

## What this brief does not do

It does not name the pilot repository, does not ask for product-owner answers (those are committed in the pilot by its own
session, through a pull request, later), and does not change any product file. Whether GitHub disables the scheduled
workflow after inactivity is `(verify)`; if the scheduled run does not happen, the maintainers dispatch it by hand.
