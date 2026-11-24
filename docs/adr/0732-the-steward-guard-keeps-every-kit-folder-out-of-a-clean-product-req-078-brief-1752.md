# ADR-0732: The steward's guard keeps every kit folder out of a clean product (REQ-078)

- Status: Accepted
- Date: 2026-11-22
- Deciders: maintainers
- Related: brief #1752, ADR-0616, SPEC-0071 rules 2 and 7, brief #1748
- Requirements: REQ-078

Protected classes: `.claude/`, `tests/kit/`

## Context

ADR-0616 decision 3 has `steward_guard.py` deny, in a clean project (`[kit] layout = "plugin"`), a write of one exact
path of the plugin's manifest (`verbatim`, `experimental`) or a file under `kit_tests`. The steward test report of
2026-11-22 (a clean, local, solo sample) found 10 of 14 ways to put kit code into the product allowed: a folder copy
(`cp -r`, `rsync`), an archive unpacked into it (`tar -x`), a copy into a kit folder and a new file in a kit folder such as
`scripts/agk/x.py`, which the manifest lists nowhere, so `doctor.py`'s `kit-in-repository` warning never sees it either.
With a manifest it cannot read, the guard checked no Bash command for this rule.

## Decision

1. **Kit-only folders.** The guard reads the manifest's `snapshot` list. A kit-only folder is a `snapshot` entry that
   ends in `/` and under which no `templates` path, `rendered` path or rule 2 kept path lies. It is derived each run,
   never a fixed list; on the kit's own manifest of this date it is `.claude-plugin/`, `.claude/agents/`,
   `.claude/hooks/`, `kit/`, `scripts/agk/`, `skills/` and `tests/kit/`.
2. **A write under a kit-only folder.** The write tools, and every word of a Bash command that is not a reader (as
   ADR-0616), are denied when the path is a kit-only folder or lies under one, whether or not the manifest lists the
   file. A back slash reads as a forward slash first (brief #1748). The denial names `SPEC-0071 rule 7` and the folder
   as the path class.
3. **A folder copy or an unpacked archive.** For `cp`, `mv`, `install`, `ln`, `rsync`, `scp` and `ditto` the
   destination is the last operand, or the value of `-t` or `--target-directory`. For `tar` with `-x` (or `x` in its
   first word, or `--extract`), `unzip`, `cpio -i` and `7z x` it is the value of `-C` or `--directory` (`tar`), `-d`
   (`unzip`), `-D` or `--directory` (`cpio`) or `-o` (`7z`), else the command's folder. A recursive copy (`-r`, `-R`,
   `-a`, `--recursive`, `--archive`; `rsync`, `ditto` and every unpack count as recursive) is denied when its
   destination is a kit-only folder, lies under one or holds one, naming the kit-only folders concerned. A copy that is
   not recursive is judged by decision 2 on the path it makes: the destination folder plus each source's name.
4. **Git and gh into a kit folder (Q-A-1, conservative reading).** `git checkout <ref> -- <paths>`, the paths of
   `git restore --source` and the `-D`/`--dir` and `-O`/`--output` values of `gh release download` are judged by
   decision 2; git and gh stay readers for everything else.
5. **Fail closed.** A manifest that cannot be read, or that has no `snapshot` list, denies the write tools as ADR-0616
   (`a write it cannot check`, path class `kit/manifest.json`), and now also a recursive copy or an unpack into the
   project.
6. Reads, the steward's own scripts run from `${CLAUDE_PLUGIN_ROOT}`, a single file copied to `docs/` or the project
   root, a recursive copy between the project's own folders and every write outside the kit-only folders pass, as
   today. An installed project, the kit's own repository and personal mode have no `[kit] layout = "plugin"` and are
   unchanged.

## Consequences

This changes ADR-0616 decision 3 only by widening what is denied in a clean project; its other decisions stand. A
non-read command whose word names a kit-only folder, such as `mkdir skills`, is denied too, as ADR-0616 accepted for a
listed path. No workflow, ruleset or required check changes, and nothing reads the network.

## Residual

- 2026-11-22: the guard reads words, not the shell's meaning: a destination held in a variable, a `cd` in an earlier
  segment of the same command and an interpreter's own code are not followed (ADR-0616's residual). A `PowerShell` tool
  call is not seen by the plugin hook at all (brief #1752 Q-A-2, a separate kit brief). To review with SPEC-0071 build
  (g)'s rehearsal (due 2027-01-31).
