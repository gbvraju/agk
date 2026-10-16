# Facts engine: live run 1 (SPEC-0009, Proof section)

Date: 2026-10-16 (from `date -u`). The document of `scripts/agk/facts.py` for this repository, built at a clean commit and run twice
in each mode. The document itself is not pasted: it is 200 to 270 kilobytes.

- Commit: `e99bd6e7a6d3160c58849d1f02d6e3c330230b89` (the facts engine commit; `facts.py` is unchanged after it), in a detached checkout with no
  tracked change, so `dirty` is `false` in both documents.
- Command: `python3 scripts/agk/facts.py --today 2026-10-16 .` (`--today` fixed so that the two runs of a day compare; the default
  is the UTC date of `date -u`). The repository name came from `origin` (`gbvraju/agk`).

## Run 1: offline (`gh` not on `PATH`, no `--api-dir`)

| Run | sha256 of the output | Bytes |
| --- | --- | --- |
| 1 | `873758313bc3a07432b00ac61c7fc8fc340c18a6128aa5c30f86c6db10d1cd2f` | 206514 |
| 2 | `873758313bc3a07432b00ac61c7fc8fc340c18a6128aa5c30f86c6db10d1cd2f` | 206514 |

Byte-identical. Exit status 0 both times. Sections that read `"unknown"`, and why:

| Section | Value | Why |
| --- | --- | --- |
| `pull_requests` | `"unknown"` | no GitHub source: `gh` is not on `PATH` (rule 14) |
| `issues` | `"unknown"` | the same (rule 15) |
| `drift.counts.D6` and `drift.total` | `"unknown"` | D6 needs the open audit issues, which are unknown (rule 15); D1 to D5 are counted: all 0 |

Every other section is read: 20 requirements, 753 markers, 13 specs, 23 ADRs, 148 residuals, 237 questions.

## Run 2: with `gh` (GET only, the caller's own login)

| Run | sha256 of the output | Bytes |
| --- | --- | --- |
| 1 | `038fa11c58924e5ea7008b4ed37cedbbfbf396c11a93bd0eb67a76d71b1c76e7` | 269147 |
| 2 | `038fa11c58924e5ea7008b4ed37cedbbfbf396c11a93bd0eb67a76d71b1c76e7` | 269147 |

Byte-identical (the two runs were seconds apart, so the GitHub data had not changed between them). Exit status 0 both times.
The sections that contain `"unknown"`, and why:

| Section | Value | Why |
| --- | --- | --- |
| `pull_requests[].proof` | `"unknown"` on all 55 | no workflow run named `proof` exists yet: SPEC-0010 is not built (rule 14) |

No other value is `"unknown"`: 55 pull requests in the 8-week window (#1 to #56 less #39, which is an issue), each with `files` and `verdicts`
read; 1 issue (the open metrics issue, #39); `drift` all 0. There is no issue labelled `agk-drift-audit`, open or closed, so there is no
drift issue to compare with; the counts for `main` today are D1 to D6 = 0 and total 0, equal to a direct run of `drift_audit.py` on the
same commit.

## What this shows

- Determinism on a real repository, offline and online (rule 4).
- `"unknown"` appears only where a source is missing (rule 5): the offline run shows it for exactly the GitHub sections and the
  D6 count; the online run shows it only for the `proof` field, whose source does not exist yet.
- The document validates against `kit/facts-schema.json` (`tests/kit_dev/test_facts_wiring.py`, rule 23).
