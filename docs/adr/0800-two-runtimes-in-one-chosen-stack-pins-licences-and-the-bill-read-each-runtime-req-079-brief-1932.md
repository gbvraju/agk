# ADR-0800: Two runtimes in one chosen stack: pins, licences and the bill of materials read each runtime (REQ-079)

- Status: Proposed
- Date: 2026-11-25
- Deciders: maintainers (the owner's word, quoted below)
- Related: brief #1932, v1 acceptance plan 3 (#1771, AD-03 and AD-06), ADR-0672 (pins), ADR-0768 (Python dependency
  files), ADR-0789 (the bill at a commit; decision 1 as amended here, decision 6 below), ADR-0791 (the foundation wait), ADR-0742 (the baseline counts), ADR-0676
  and ADR-0748 (the licences step), ADR-0370 (the bill of materials), SPEC-0072 rule 4, amendment 247, plan #661
- Requirements: REQ-079

Protected classes: `scripts/agk/`, `tests/kit/`

## Context

An adopted project with Node at the root and a Python service in `service/` accepted a stack record whose chosen option
names both runtimes. `gates/pins.py:pick` returns a stack only when the option names exactly one runtime of `STACKS`, so
the project read as `not run: no stack chosen`, and `pins`, `licences` and the bill of materials never ran, before and
after the acceptance. Each reader also took one build file and one lock at the project root. The owner's word
(2026-11-25, the steward chat, quoted as data): "Yes, file draft briefs 1 to 5 and the first slices of SPEC-0073 and
SPEC-0074".

## Decision

1. `gates/pins.py` gains `runtimes(texts, files)`: one `Runtime` per part of the chosen option whose name is a `STACKS`
   key, in the record's order, each with its `STACKS` row, its folder, the build file read there, its own parts (the
   runtime part and the parts after it, up to the next runtime part) and every part of the option. It is None exactly
   where `pick` is None for a reason other than two runtimes. With one runtime it keeps the root and every part, so
   the single-runtime output is unchanged byte for byte. `pick` and `chosen` keep their return and meaning.
2. With two runtimes or more, a runtime's folder is the folder of the tracked files (`git ls-files`; every file under
   the root outside a git work tree; the commit's tree for `sbom.py`) that holds its build file: Node `package.json`;
   Python `pyproject.toml`, else `requirements.txt`, which is then the build file read with its `-r` files. The root
   wins; else the one such folder, a path with a `node_modules` part ignored; with none, the root (the build file is
   missing, as today); with two or more, one finding `a runtime's build file is in more than one folder` (component
   class: build file), held to the first, and that runtime's other checks are not run (`Q-MR-3`).
3. `findings` runs today's reading once per runtime in its folder, each finding held to its path from the project root
   (`service/requirements.txt`), so the baseline counts each file apart. A part is compared with its own runtime's lock
   only. `skipped` gives `no stack chosen` only when `runtimes` is None; `waiting` holds when every runtime waits.
4. `gates/licences.py` reads every runtime's readable lock with its own reader and class against the one `allowed`
   list; a runtime with no lock is skipped (`pins` fails it), and `not run: no lock` holds only when no runtime has one.
   A licence named by a record part is looked up among every part of the option. `sbom.py:chosen_at` gives `runtimes`
   at the commit, `lock_components` adds the packages of every runtime's lock, each `bom-ref` once, and the product's
   name is read from the build file of the runtime at the root, else of the first runtime.
5. SPEC-0072 rule 4 is not edited here: `docs/runs/proposed-spec-amendments-247.md` proposes its words (`Q-MR-1`).
6. This amends ADR-0789 decision 1 (Accepted), which accepts a missing root `pyproject.toml` only when the chosen
   stack is `node`. `sbom.py make` now also accepts it with a declared work type and an Accepted option of two
   runtimes whose first runtime at the root is not Python: the build file of the first runtime at the root (else of
   the first runtime) names the product. A Python runtime that names the product still needs `pyproject.toml`, and
   every other case of a missing `pyproject.toml` is refused as before. The `both-parts` refusal case of
   `test_elsewhere_a_missing_pyproject_is_refused_as_today` is removed with this item.
7. Single-runtime readers: `scripts/agk/basics.py`, `scripts/agk/engines.py`, `scripts/agk/gates/layers.py`,
   `scripts/agk/gates/node_pack.py`, `scripts/agk/gates/python_pack.py`, `scripts/agk/gates/tests_floor.py` and
   `scripts/agk/run_gates.py` (its no-pack row) still read `pins.chosen` or `pins.pick`, one runtime only, and stay
   `not run` with two runtimes (`Q-MR-2`). A test lists every module that reads either and fails on one not named in
   this paragraph.

## Consequences

A two-runtime project gets its pins, licences and bill of materials once its stack is accepted. Messages name the rule
and the component class, never a name, a folder or a version (principle 8). Two tests of `tests/kit/test_product_deps.py`
that held the old reading of an option with both runtimes change with this decision: the `both-parts` case of
`test_elsewhere_a_missing_pyproject_is_refused_as_today` is removed, since `make` now names the product from the root's
`package.json`, and `test_with_both_parts_and_no_pyproject_bom_does_not_run` becomes
`test_with_both_parts_and_no_pyproject_bom_runs`.

## Residual

The packs, `layers`, `tests_floor`, `basics` and `stack-files` per runtime are a follow-up brief (`Q-MR-2`, 2026-11-25).
A record part that names its folder is a later brief (`Q-MR-3`, 2026-11-25).
