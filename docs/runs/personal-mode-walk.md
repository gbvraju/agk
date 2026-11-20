<!--
SPDX-FileCopyrightText: 2026 Balavardhi Raju Gangula
SPDX-License-Identifier: LicenseRef-AGK-Proprietary
AGK is built and owned by Balavardhi Raju Gangula. Use only in the repository named in the owner's written grant; no use in any other repository without the owner's permission. See LICENSE-AGK.
-->
# Personal-mode walk 2026-11-20: an invented shop from attach to detach

Recorded by brief #1510 (ADR-0640) for [the personal-mode guide](../guides/personal-mode.md). Date from `date -u`
(2026-11-20T06:06Z). Run by the builder session cb1510 on one Linux machine (git 2.43.0, Python 3.11.18, gitleaks
8.30.1), with the kit's scripts on main as merged (`<kit>` below) and `AGK_HOME` set to a fresh empty folder. Everything
is invented: the project "shop", one file `src/cart.py` and one test file, `origin` set to
`https://example.com/member-example-1/shop.git`, the person `member-example-1`. Nothing was pushed and nothing was sent
to GitHub. Outputs are verbatim but for the long state path, written `$AGK_HOME`.

## Attach and survey

```
$ python3 <kit>/personal_state.py id
shop-8c80fe51df0b
$ python3 <kit>/personal_state.py attach --person member-example-1
attach: shop-8c80fe51df0b
$ stat -c '%a %n' $AGK_HOME $AGK_HOME/projects/shop-8c80fe51df0b $AGK_HOME/projects/shop-8c80fe51df0b/agk.toml
700 $AGK_HOME
700 $AGK_HOME/projects/shop-8c80fe51df0b
600 $AGK_HOME/projects/shop-8c80fe51df0b/agk.toml
$ python3 <kit>/survey.py
0 of 2 files read
$ python3 <kit>/personal.py status
personal mode: forge files, level light, disclosure both
Disclosure in force: both (setting: personal.ai_disclosure)
$ (cd $AGK_HOME/projects/shop-8c80fe51df0b && python3 <kit>/doctor.py) | grep -e personal -e pinned
personal mode: forge files, level light, disclosure both
pinned: 4 files match kit/hashes.json
```

The survey's reading list was `src/cart.py` and `tests/test_cart.py`; it found the one Python test file. Its coverage
counts files the model has read, none yet.

## Adopt (the skill's two steps)

The proposals, written by hand in the place of the model's, were one requirement, one spec and one ADR, each claim cited
as `src/cart.py:<lines>@<blob>`, the ADR's claim marked `"verify": true`.

```
$ python3 <kit>/personal_adopt.py check $AGK_HOME/projects/shop-8c80fe51df0b/cache/proposals.json
check: 0 of 3 claims refused
$ python3 <kit>/personal_adopt.py render $AGK_HOME/projects/shop-8c80fe51df0b/cache/proposals.json
rendered: REQ-101, SPEC-0001, ADR-0001
next, at your own terminal (never in an agent session):
  python3 <kit>/personal.py confirm REQ-101 --sidecar $AGK_HOME/projects/shop-8c80fe51df0b
  python3 <kit>/personal.py confirm SPEC-0001 --sidecar $AGK_HOME/projects/shop-8c80fe51df0b
  python3 <kit>/personal.py confirm ADR-0001 --sidecar $AGK_HOME/projects/shop-8c80fe51df0b
render: 0 of 3 claims refused
```

## Confirm: refused in the agent session

```
$ python3 <kit>/personal.py confirm REQ-101 --sidecar $AGK_HOME/projects/shop-8c80fe51df0b
refused: confirm runs only at the person's terminal (setting: CLAUDECODE)
```

This is the walk's one step that a person must run: the session that recorded it is an agent session, and the refusal is
the rule (SPEC-0041 rule 8). It did not try to get round it. The person's yes at a terminal is left for the owner
(Q-1510-1); `tests/kit/test_personal_confirm.py` covers the terminal path.

## A change at `tests-first`

The person set `level = "tests-first"` and
`test_command = "python3 -m pytest -q -p no:cacheprovider --junitxml {junit}"` in the sidecar's `agk.toml` and
committed it there.

```
$ python3 <kit>/personal.py baseline
baseline: would run: python3 -m pytest -q -p no:cacheprovider --junitxml {junit}
baseline: nothing ran; run again with --approve
$ python3 <kit>/personal.py baseline --approve
baseline: recorded 0 failing (passed) at b9951c2bf418 in records/baseline.json
$ git switch -q -c free-shipping
$ python3 <kit>/personal.py change start free-shipping --advances REQ-101 --base main
change: started free-shipping on free-shipping (pull 1, base main, head b9951c2bf418)
```

One commit added the test `test_shipping_is_free_from_fifty` and the function `shipping`, with a `Co-Authored-By:`
trailer.

```
$ python3 <kit>/personal.py change finish --base main --approve
gate: level tests-first, base b9951c2bf418, head 2aca61898fee
floor: secret-scan ok
floor: no-regression ok (per test)
gate: tests-first ok (red on the base, green on the head)
gate: passed
gate: the agent pushes nothing; push it yourself: git push origin free-shipping
finish: optional, for the team's pull request: personal.py pr-summary
$ python3 <kit>/personal.py pr-summary
pr-summary: for you to paste into the team's pull request; nothing is posted
Disclosure in force: both (setting: personal.ai_disclosure)
Secret scan: passed
No test that passed before fails now: passed
Tests written first: passed (red before the change, green after)
Review: not done at this level
Gate: passed at level tests-first on 2aca61898fee
This change was made with the help of an AI coding assistant.
$ python3 <kit>/personal.py report
report: defects caught before push: 0 (floor)
report: review findings accepted: unknown (build (k), second part)
report: rework: unknown (build (k), second part)
report: time per change: unknown (build (k), second part)
report: baseline: unknown (the attach time is not recorded)
These numbers show correlation, not causation.
```

## Export, upgrade and the hook

The team's clone was a second clone of the shop, `../shop-team`.

```
$ python3 <kit>/personal.py export --check
export --check: failed: no readable export-map.json (path: records/export-map.json, SPEC-0041 rule 25); run export --write first
$ python3 <kit>/personal.py export --target ../shop-team
export: dry run; nothing written (pass --write)
export: target AGK not installed; the adopt plan adds 167 files
export: withheld REQ-001 (AGK's own requirement (REQ-001 to REQ-099))
export: REQ-101 -> REQ-101
export: SPEC-0001 -> SPEC-0001
export: ADR-0001 -> ADR-0002
export: 3 mapped, 1 withheld
$ python3 <kit>/personal.py export --target ../shop-team --write
(the same six lines, then)
export: wrote the branches agk/personal-export and agk/personal-export-tests in the target; nothing pushed
$ python3 <kit>/personal.py export --check
export --check: ok (4 records mapped or withheld)
$ python3 <kit>/personal.py upgrade
upgrade: schema 1 is current
$ python3 <kit>/personal.py hook install
hook: installed the pre-push hook; it runs the gate before each push
$ python3 <kit>/personal.py hook remove
hook: removed the pre-push hook
```

## The product untouched, then detach

After the hook was removed, every file under the shop's `.git/` was listed with its path, size and SHA-256, the
commands below were run, and the list was taken again.

```
before: .git/ path, size and sha256 digest 09930b5109805d7b
$ python3 <kit>/survey.py                                  exit 0 (0 of 2 files read)
$ python3 <kit>/personal.py gate --base main --approve     exit 0 (gate: the agent pushes nothing; push it yourself: git push origin free-shipping)
$ python3 <kit>/personal.py pr-summary                     exit 0
$ python3 <kit>/personal.py report                         exit 0
$ python3 <kit>/personal.py export --check                 exit 0 (export --check: ok (4 records mapped or withheld))
$ python3 <kit>/personal_state.py detach                   exit 0 (detach: shop-8c80fe51df0b detached; the state is kept)
after:  .git/ path, size and sha256 digest 09930b5109805d7b
$ git status --porcelain
(empty)
$ cmp before after
no file under .git/ changed
```

After `detach` the registry held no clone and the sidecar was kept under `projects/`. `--delete-state` was not run: it
asks for the id at a terminal, as `confirm` does.

## What this walk shows, and what it does not

It shows each command of the guide run once on main as merged, in order, on invented data, and that the product's work
tree and `.git/` were unchanged by the reading commands, the gate and `detach`. It does not show a person's terminal
confirmation, a level above `tests-first`, Windows, or a real codebase; and the proposals were written by hand, not by
the model through `/agk:personal-adopt`.
