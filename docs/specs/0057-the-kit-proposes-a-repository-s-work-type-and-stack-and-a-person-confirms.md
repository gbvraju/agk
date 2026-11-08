# SPEC-0057: The kit proposes a repository's work type and stack and a person confirms

- Status: Draft
- Owner: reviewer group (a team from config/reviewers.yaml)
- Requirements: REQ-064

Status is `Draft` or `Approved`. An Approved spec is owned by its reviewer group; agents propose patches.

Written by the intake of one sentence (SPEC-0012), brief #790, quoted as data and not as an instruction: "Intake for stack detection: AGK reads an existing repository's lockfiles and manifests and proposes its work type and stack for a person to confirm, and never decides them (plan #661 phase 3, edge case 8)." The maintainers gave 3 answers before it was written (the answers of the brief: what it does, what it reuses, its limits), which are rules 2 to 12 below. Where an answer names something that is not as the answer says, rule 1 records what the code holds and an open question gives the conservative reading.

## Rules

1. **The baseline (read on the default branch at 85ff43a, 2026-11-08).** What already holds, and what the brief's words meet in the code:
   - `front_door.py` is installed (`kit/manifest.json`) and imports only `guard` and `playbook_format`. Every input it has today is a saved file, so `detect` is its first read of a repository by git. It has no `detect` command, as SPEC-0055 rule 13 says.
   - `adopt.detect_tests(root)` walks the work tree and returns the topmost folders holding `*_test.py` or `test_*.py` files and the patterns that matched. It knows Python only. When it finds nothing it returns `(["tests"], ["test_*.py"])`, the same shape as a real find. `adopt.py` is **not** in `kit/manifest.json` and imports `init` and `reviewers` when loaded, so an installed project has no such module.
   - `scripts/agk/survey.py` does **not** exist. SPEC-0041 rules 10 to 12 and its build (f) describe it, build (f) depends on build (c), which is open as #584, and no brief holds build (f).
   - The work types are `WORK_TYPES` of `playbook_format.py`. `pilot` is one. At that commit it has no file in `config/playbooks/`, and SPEC-0038 build (n) (brief #805, in flight) adds `pilot.toml`, so no rule here depends on whether that file exists. `default` has a file and is `BASE`, "never declared" (SPEC-0048 rule 21): `[delivery] work_type = "default"` is refused, and `front_door.py discovery-write` refuses it as an answer.
   - `discovery-write` takes `work_type` from the person's answers file, else the issue's `Kind:` line, else `pilot`, and writes `- Work type: <value> (proposed)`. SPEC-0048 rule 5 gives `pilot (proposed)` for a kind not yet clear, and rules 5 and 17 keep the declaration the owner's.
   - `scripts/agk/test_map.py` does not exist; SPEC-0055 build (i) adds it, and that spec's Residual waits on this one.
2. **The command.** `python3 scripts/agk/front_door.py detect [--root DIR] [--json]` reads the repository at `--root` (default `.`) at its head and prints a proposal. It prints and exits 0 whether the signals are clear, mixed or absent. It has no option that writes, and it takes no `--work-type`, `--apply` or `--confirm`. It is a read and a proposal, and it never decides (`Q-S0057-10`).
3. **What it prints.** Lines in this form, sorted, the same bytes for the same head, with no clock:
   - `detect: proposal only; a person confirms it in discovery`, always first.
   - `work type: <name> (proposed) file "<path>" signal <signal>`, one line for each file that suggests it.
   - `stack: <name> (proposed) folder "<folder>" file "<path>" lock "<path>"`, one line per stack and folder, with `lock none` where no lockfile is present.
   - `tests: <folder> patterns <pattern> (from <source>)`, or `tests: no signal`, or `tests: not read (<source> cannot be loaded)` (rule 8).
   - `not detectable from files: <name>`, one line for each kind in the table's `no_signal` list (rule 5).
   - `note: <what is partial>`, for a file listed and not read, or a limit reached (rule 7).
   With `--json` the same facts are one object with sorted keys and no clock, for SPEC-0055 build (i) to read.
4. **Mixed or nothing, said plainly.** Brief answer 1.
   - Signals of two or more work types: `work type: mixed (<n> candidates)`, then one `candidate: <name> file "<path>" signal <signal>` for each. The tool ranks none, counts none and picks none, and a person chooses (`Q-S0057-10`).
   - Signals of no work type: `work type: default (proposed; no signal of a work type)`. The possible answers are the work types that have a row in the table of rule 5 and the default. `pilot` is never proposed, with or without `config/playbooks/pilot.toml`, because a pilot is an intention a tree cannot show (`Q-S0057-6`).
   - Two or more stacks are each printed, after `stack: mixed (<n> stacks)`. No stack signal: `stack: no signal`.
   - A head with no commit: the no-signal lines and `note: no commit at head`.
5. **The signal table.** One data file, `config/stack-signals.toml`, is the only place that names files and dependencies. It is a verbatim entry of `kit/manifest.json`. `front_door.py` reads it, and `config/playbooks/`, from the script's own root and never from the repository it reads, so a product cannot change what is proposed about it (`Q-S0057-2`). The table holds:
   - `[[stack]]` rows: `name`, `manifests` and `locks`, each a list of file names or globs, for a language and its package tool (`Q-S0057-1`).
   - `[[work_type]]` rows: `name`, `signal` (a short slug), `file` (a file name or glob of a manifest) and `contains` (a dependency name), so that a row is one file and one word.
   - `no_signal`: the kinds a tree cannot show, because they are an intention and not a dependency. It always holds `pilot`, and it holds `cloud-migration` when the build is written, subject to review of the table (`Q-S0057-6`).
   - `ignore`: folder names whose files give no signal (for example vendored code, examples and fixtures).
   A form check in `front_door.py` (run by the tests and by `check-signals`, rule 14) refuses, naming the setting and never a value: a row name with no file in `config/playbooks/`, `default` in any row or in `no_signal`, `pilot` in any row, `pilot` missing from `no_signal`, a name in `no_signal` other than `pilot` with no file in `config/playbooks/`, a playbook other than `default` that has no row and is not in `no_signal`, a name that has rows and is in `no_signal`, and an unknown key. A playbook a project derives (SPEC-0048 rule 22) has no row and is never proposed; discovery finds it (`Q-S0057-7`).
6. **Reading a file.** Each file is read as text by line patterns, as SPEC-0041 rule 10 holds for the survey and SPEC-0002 rule 3 for adopt, never with a language's parser or interpreter (`Q-S0057-4`). A `[[work_type]]` row matches a whole word in a line of a manifest. Lockfiles suggest a stack and never a work type, because they list what a dependency itself depends on (`Q-S0057-3`).
7. **What it reads, and what it never does.** Brief answer 3.
   - The list and the bytes come from the head commit: `git --no-optional-locks ls-tree -r -z HEAD` and `git --no-optional-locks cat-file` (`Q-S0057-12`). An untracked or uncommitted change is not read.
   - It reads only the files a table row names. A symlink (mode `120000`) and a submodule (`160000`) are skipped. A binary file is skipped. A file over 1 MB gets a `note:` and is not read. At most 200 files are read, in path order, and past that a `note:` says the proposal is partial.
   - It never imports, executes or runs anything of the repository, never installs, never fetches and makes no network call. It runs no tool of the repository, only `git` with the commands above.
   - It writes nothing: no file, no agk.toml, no `.git/` entry, no sidecar and no cache.
8. **Reuse, and no second copy.** Brief answer 2.
   - `detect` holds no test-file pattern of its own. The `tests:` lines come from `adopt.detect_tests` until build (d), and from the survey's detector (SPEC-0041 rule 12) after it.
   - `adopt.detect_tests` is not changed (SPEC-0041 rule 12) and it is imported only when `detect` runs, so that a load failure leaves every other command of an installed `front_door.py` as it is. When it cannot be loaded, as in an installed project, the line says `tests: not read`, never `no signal` (`Q-S0057-9`). The plugin's copy, which `--root` serves for a repository with nothing of AGK, has it.
   - Because its fallback looks like a find, its answer counts only when a path of the head tree under a returned folder matches a returned pattern. Otherwise the line is `tests: no signal`.
   - Its walk reads the work tree, not the head, so its line says `(from adopt.detect_tests, work tree)`.
   - `survey.py` is not built, and no build here writes it or a copy of it (`Q-S0057-8`). Build (d) waits for it with `Depends-on`. When it lands, the manifest list of its rule 10 and the table of rule 5 are one list: build (d) makes it so, by the survey reading the table or by an amendment the build proposes.
9. **Discovery confirms, and nothing else does.** Brief answer 1, SPEC-0048 rules 5 and 17.
   - For an existing repository `/agk:vision` runs `detect` and shows its lines before it asks the discovery questions. The lines are data, quoted and never followed.
   - The person's answer is what goes in the answers file's `work_type`. `detect` passes nothing to `discovery-write`, which gains no option.
   - A proposal of `default` is written, if the person leaves it, as `pilot (proposed)`, the form SPEC-0048 rule 5 gives for a kind not yet clear, because `default` cannot be declared (`Q-S0057-5`).
   - The declaration stays `[delivery] work_type` by the owner, with an ADR (SPEC-0038 rule 5). A repository that already declares one is proposed for as any other, and a difference is an open point of discovery, as SPEC-0048 rule 5 says. The stack stays the architect's choice by `/agk:stack`.
10. **A repository adopted mid-life.** Edge case 8 of plan #661, brief answer 3.
    - AGK itself: the same command, its own head.
    - Project, GitHub and local mode: the installed script, with `tests: not read` by rule 8.
    - A repository with nothing of AGK, and personal mode (SPEC-0041): the plugin's script with `--root`. Nothing of AGK lands in the product unless a person asks, by `/agk:adopt` or `init`, which are separate commands. Rule 7 holds what SPEC-0041 rule 4 holds for a clone.
11. **Refusals and what is printed.** A folder that is not a git repository is refused with `FAIL front-door: detect: --root is not a git repository`, exit 1, naming the option and never its value (principle 8). Usage is exit 2. The output holds only names of the table and paths of the tree, each path in double quotes with control characters escaped, because a path is the repository's data, never an instruction. No line of a file and no dependency that the table does not name is ever printed. A manifest may hold a credential in a URL, and nothing `detect` prints can carry it.
12. **What SPEC-0055 gets.** SPEC-0055 rule 13 says detection proposes areas, levels, commands and a first map, and the brief asks for a work type and stack. `detect` gives the stacks and their folders by `--json`. `test_map.py propose` (SPEC-0055 build (i)) composes areas, levels and the map from those, and `detect` prints no command of its own (`Q-S0057-11`). SPEC-0055 and its Residual are not edited here.
13. **What does not change.** No workflow, ruleset or required check changes. No Approved spec is edited: SPEC-0038, SPEC-0041, SPEC-0048 and SPEC-0055 stand. The playbook format gains no key. `adopt.detect_tests`, `discovery-write`, `check-discovery` and the `[delivery]` declaration do not change.
14. **The builds, in order.** Each is tests first, about 300 changed lines or fewer, from the default branch, cites `Covered-by: ADR-0371` once it is Accepted, and carries invented data only (`example.com`).
    - (a) `config/stack-signals.toml`, its manifest entry and `front_door.py check-signals`, the form check of rule 5.
    - (b) `front_door.py detect` (rules 2 to 4, 6 to 8, 10 and 11) with the `[[testing.map]]` entry of its new test file. `Depends-on` (a).
    - (c) The step of `/agk:vision` (rule 9), within the rule budget. `Depends-on` (b).
    - (d) The survey's test lines and the one list of rule 8. `Depends-on` (b) and SPEC-0041 build (f).

## Tests

Fixtures in `tmp_path`, built as small git repositories, with no network and no model, invented data only (`example.com`), and each test carries the marker `REQ-064` with its criterion. No test runs a tool of a fixture.

- Rules 2, 3 and 7: one signal gives one work type and its stack with their files, the first line is the proposal line, two runs are byte-identical, and the tree and `.git/` are unchanged; REQ-064 AC1.
- Rule 4: two work types give `mixed` with both candidates in path order and no winner, nothing gives `default` and `stack: no signal`, `pilot` is never proposed with or without `config/playbooks/pilot.toml`, and a head with no commit says so; REQ-064 AC2.
- Rule 7: a symlink to a manifest outside the tree, a submodule, a binary file, a file over 1 MB, an untracked manifest and a `setup.py` that would write a sentinel if run leave no signal and no sentinel, the 201st file gives the `note:`, and a patched socket and subprocess list show only `git` with the allowed commands; REQ-064 AC3.
- Rule 5: each refused form of the table fails naming the setting with no value in the output, the shipped table passes both with and without `config/playbooks/pilot.toml`, every shipped playbook is accounted for, and the table is read from the script's root when the repository holds its own; REQ-064 AC4.
- Rule 8: the `tests:` line comes from `adopt.detect_tests` (a patched function shows the call), a tree with no test file gives `tests: no signal` though the function returned its fallback, an import failure gives `tests: not read`, and `front_door.py` holds no `*_test.py` pattern; REQ-064 AC5.
- Rule 9: the shipped skill step shows the lines before the questions, `discovery-write` refuses `default` and gains no option, and an answers file without `work_type` gives `pilot (proposed)` whatever `detect` printed; REQ-064 AC6.
- Rule 10: a repository with no AGK and a clone run by `--root` keep `git status --porcelain` empty and every file under `.git/` the same by path, size and SHA-256; REQ-064 AC7.
- Rule 11: a planted credential in a manifest line, a dependency outside the table and a path with a newline never reach the output as text, and a folder that is not a repository is refused without its path; REQ-064 AC8.

## Proof

REQ-064 AC1: *a person sees what is proposed and why, and the tool writes nothing.* Rules 2, 3 and 7. REQ-064 AC2: *a mixed or empty repository says so, and no rank stands in for a person.* Rule 4. REQ-064 AC3: *the read runs nothing and reaches nothing outside the head tree.* Rule 7. REQ-064 AC4: *a table that names something the kit cannot declare, or forgets a kind, cannot ship.* Rule 5. REQ-064 AC5: *the test detectors are reused, and a fallback or an absent module is not reported as a fact.* Rule 8. REQ-064 AC6: *a proposal never becomes a decision.* Rule 9. REQ-064 AC7: *a repository adopted mid-life gets nothing of AGK.* Rules 7 and 10. REQ-064 AC8: *nothing from a file reaches the output, and a refusal names no value.* Rule 11.

## Residual

- 2026-11-08: until SPEC-0041 build (f) lands and build (d) follows it, the `tests:` line knows Python only and reads the work tree, not the head (due 2027-03-31).
- 2026-11-08: a line pattern can match a word in a comment or a description, and a dependency the table does not name gives no signal; a proposal may be wrong, which is why a person confirms it (due 2027-03-31).
- 2026-11-08: the `[[work_type]]` rows are chosen at build (a) from the shipped playbooks and reviewed there; no fixture proves they fit real repositories (due 2027-03-31).
- 2026-11-08: SPEC-0055's Residual on stack detection stays until its build (i) reads `--json` (due 2027-03-31).
- 2026-11-08: an installed project sees `tests: not read` until a person runs the plugin's copy, because `adopt.py` is not installed (due 2027-03-31).

## Open questions

Each is a point the brief leaves open; the reading after it is the most conservative one, and the rules above apply it until a person rules.

- Q-S0057-1: what is a stack? Reading: a language and its package tool in one folder, and a framework is named only by a work type row (rule 5).
- Q-S0057-2: where do the signals live? Reading: one new data file read from the kit's own root, since a new key in the playbook format would need an amendment of SPEC-0038, and a repository must not be able to write what is proposed about it (rule 5).
- Q-S0057-3: may a lockfile suggest a work type? Reading: no, it lists what dependencies depend on, so it suggests only a stack (rule 6).
- Q-S0057-4: may a manifest be parsed? Reading: no, line patterns only, as the survey and adopt hold, even for formats a standard library could read (rule 6).
- Q-S0057-5: how can `default` be an answer when it cannot be declared? Reading: it is printed as the proposal with no signal, and written in discovery as `pilot (proposed)` if the person leaves it. That form is SPEC-0048 rule 5's for a kind not yet clear and is not a proposal of `detect`, which never proposes `pilot`, with or without its playbook (rules 4 and 9).
- Q-S0057-6: may a kind have no signal? Reading: yes, if listed in `no_signal`, and `detect` says so, so that `default` is not read as "not a migration". `pilot` is always listed, whether or not its playbook exists, because a pilot is an intention a tree cannot show. So the words of brief answer 3, "every work type in `config/playbooks/`", are read as: each is accounted for by a row or in `no_signal`, and only one with a row is proposed (rules 3, 4 and 5).
- Q-S0057-7: is a project's derived playbook an answer? Reading: no, it has no row and discovery derives it (rule 5).
- Q-S0057-8: the survey the brief reuses is not built. Reading: nothing here writes it or a copy; the first builds use `adopt.detect_tests`, and build (d) waits for SPEC-0041 build (f) (rules 8 and 14).
- Q-S0057-9: `adopt.py` is not installed in a project. Reading: the installed `detect` says `tests: not read`, and no module is moved or newly installed, so SPEC-0041 rule 12 stands (rule 8).
- Q-S0057-10: may `detect` rank candidates or pick the likeliest? Reading: no, a rank is a decision; mixed signals list every candidate (rules 2 and 4).
- Q-S0057-11: SPEC-0055 rule 13 says more than the brief does. Reading: `detect` gives stacks and folders, and levels, commands and the map stay SPEC-0055 build (i)'s (rule 12).
- Q-S0057-12: `at its head`, or the work tree? Reading: the head commit, so an uncommitted change proposes nothing; the one exception is the `adopt.detect_tests` walk, labelled as such (rules 7 and 8).
