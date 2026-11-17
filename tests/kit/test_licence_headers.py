"""Tests of scripts/agk/check_licence_notice.py and the licence grant of doctor.py (brief #1419,
ADR-0596). REQ-014."""

from __future__ import annotations

import datetime

import check_licence_notice as notice
import doctor
import rules

COPYRIGHT = "SPDX-FileCopyrightText: 2026 Balavardhi Raju Gangula"
IDENTIFIER = "SPDX-License-Identifier: LicenseRef-AGK-Proprietary"
NOTICE = (
    "AGK is built and owned by Balavardhi Raju Gangula. Use only in the repository named in the "
    "owner's written grant; no use in any other repository without the owner's permission. "
    "See LICENSE-AGK."
)
MANIFEST = '{"kit_version": "1.0.0", "verbatim": %s, "templates": {}}\n'
REUSE = (
    "version = 1\n\n[[annotations]]\n"
    'path = ["**/*.json", ".github/**"]\n'
    'precedence = "aggregate"\n'
    'SPDX-FileCopyrightText = "2026 Balavardhi Raju Gangula"\n'
    'SPDX-License-Identifier = "LicenseRef-AGK-Proprietary"\n'
)


def kit_repo(repo, files: dict[str, str], reuse: str = REUSE) -> None:
    listed = '["' + '", "'.join(sorted(files)) + '"]'
    repo.commit(
        {
            **files,
            "kit/manifest.json": MANIFEST % listed,
            "REUSE.toml": reuse,
            "LICENSE": "the licence\n",
            "config/protected-paths.txt": "scripts/agk/\n.claude/\nkit/\n",
        }
    )


# --- the comment forms ------------------------------------------------------------------------


def test_hash_form_follows_the_shebang_and_the_encoding_line():
    """REQ-014: a `#!` script keeps its first line, and an encoding line stays second."""
    text = "#!/usr/bin/env python3\n# -*- coding: utf-8 -*-\n\"\"\"Doc.\"\"\"\nx = 1\n"
    out = notice.add_header(text, "hash")
    lines = out.splitlines()
    assert lines[0] == "#!/usr/bin/env python3"
    assert lines[1] == "# -*- coding: utf-8 -*-"
    assert lines[2] == f"# {COPYRIGHT}"
    assert lines[3] == f"# {IDENTIFIER}"
    wrapped = [ln[2:] for ln in lines[4:] if ln.startswith("# ")]
    assert " ".join(wrapped) == NOTICE
    assert all(len(ln) <= 100 for ln in lines)
    assert out.endswith('"""Doc."""\nx = 1\n')
    assert notice.has_header(out, "hash")
    assert not notice.has_header(text, "hash")


def test_hash_form_is_written_once():
    """REQ-014: writing the header twice gives the file of one write."""
    once = notice.add_header("x = 1\n", "hash")
    assert notice.add_header(once, "hash") == once
    assert once.endswith("x = 1\n")


def test_markdown_form_follows_the_front_matter():
    """REQ-014: an agent file keeps its front matter first; the header is one HTML comment."""
    text = "---\nname: a\ndescription: b\n---\n\nBody.\n"
    out = notice.add_header(text, "html")
    assert out.startswith("---\nname: a\ndescription: b\n---\n<!--\n")
    assert f"<!--\n{COPYRIGHT}\n{IDENTIFIER}\n{NOTICE}\n-->\n" in out
    assert out.endswith("\nBody.\n")
    assert notice.has_header(out, "html")


def test_markdown_without_front_matter_starts_with_the_header():
    """REQ-014: a guide without front matter starts with the comment."""
    out = notice.add_header("# Title\n\nText.\n", "html")
    assert out.startswith(f"<!--\n{COPYRIGHT}\n")
    assert out.endswith("-->\n# Title\n\nText.\n")


def test_each_file_type_has_its_comment_form():
    """REQ-014: `#` for Python, shell, PowerShell, YAML, TOML and make; HTML comment for Markdown;
    none for JSON."""
    cases = {
        "scripts/agk/a.py": "hash",
        "scripts/a.sh": "hash",
        "scripts/agk/wsl_setup.ps1": "hash",
        ".github/workflows/a.yml": "hash",
        "config/playbooks/a.toml": "hash",
        "agk.mk": "hash",
        "Makefile": "hash",
        ".gitignore": "hash",
        "config/ci-tools.txt": "hash",
        "CLAUDE.md": "html",
        "kit/manifest.json": None,
        ".claude/settings.json": None,
    }
    for rel, style in cases.items():
        assert notice.style_of(rel) == style, rel


# --- the check --------------------------------------------------------------------------------


def test_every_file_headed_or_annotated_passes(repo):
    """REQ-014: headed files and an annotated JSON file pass."""
    kit_repo(
        repo,
        {
            "scripts/agk/a.py": notice.add_header("#!/usr/bin/env python3\nx = 1\n", "hash"),
            ".claude/agents/a.md": notice.add_header("---\nname: a\n---\nBody.\n", "html"),
            "scripts/agk/rules.json": "{}\n",
            ".github/workflows/a.yml": "on: push\n",
        },
    )
    proc = repo.run("check_licence_notice.py")
    assert proc.returncode == 0, proc.stdout
    assert "ok licence-notice" in proc.stdout


def test_a_missing_header_fails_naming_the_path_class(repo):
    """REQ-014: a kit script without the header fails; the line names the path class."""
    kit_repo(repo, {"scripts/agk/a.py": "x = 1\n", "scripts/agk/b.py": "y = 2\n"})
    proc = repo.run("check_licence_notice.py")
    assert proc.returncode == 1
    assert "scripts/agk/a.py" in proc.stdout
    assert "path class scripts/agk/" in proc.stdout


def test_a_json_file_without_the_annotation_fails(repo):
    """REQ-014: a file that cannot hold a comment needs the REUSE.toml annotation."""
    reuse = REUSE.replace('"**/*.json", ', "")
    kit_repo(repo, {"scripts/agk/rules.json": "{}\n"}, reuse=reuse)
    proc = repo.run("check_licence_notice.py")
    assert proc.returncode == 1
    assert "scripts/agk/rules.json" in proc.stdout
    assert "REUSE.toml" in proc.stdout


def test_an_annotation_naming_another_licence_does_not_count(repo):
    """REQ-014: only an annotation with the owner and the AGK identifier covers a file."""
    reuse = REUSE.replace("LicenseRef-AGK-Proprietary", "MIT")
    kit_repo(repo, {"scripts/agk/rules.json": "{}\n"}, reuse=reuse)
    assert repo.run("check_licence_notice.py").returncode == 1


def test_write_adds_the_headers_and_then_the_check_passes(repo):
    """REQ-014: `--write` heads every kit file that can hold a comment."""
    kit_repo(
        repo,
        {
            "scripts/agk/a.py": "#!/usr/bin/env python3\nx = 1\n",
            ".claude/agents/a.md": "---\nname: a\n---\nBody.\n",
            "kit/agk-kit.mk": "x:\n\techo x\n",
        },
    )
    assert repo.run("check_licence_notice.py", "--write").returncode == 0
    text = (repo.root / "scripts/agk/a.py").read_text(encoding="utf-8")
    assert text.startswith("#!/usr/bin/env python3\n# SPDX-FileCopyrightText:")
    assert repo.run("check_licence_notice.py").returncode == 0
    assert (repo.root / "LICENSE").read_text(encoding="utf-8") == "the licence\n"


def test_a_plugin_command_file_without_the_header_fails(repo):
    """REQ-014 (Q-1419-2): a plugin command file (`skills/<name>/SKILL.md`) is a kit file; without
    the header after its front matter it fails, naming the path class; with it, it passes."""
    command = "---\nname: a\ndescription: b\n---\n\n# /agk:a\n"
    kit_repo(repo, {"scripts/agk/a.py": notice.add_header("x = 1\n", "hash")})
    repo.commit({"skills/a/SKILL.md": command})
    proc = repo.run("check_licence_notice.py")
    assert proc.returncode == 1
    assert "skills/a/SKILL.md" in proc.stdout
    assert "path class skills/" in proc.stdout
    repo.commit({"skills/a/SKILL.md": notice.add_header(command, "html")})
    assert repo.run("check_licence_notice.py").returncode == 0
    text = (repo.root / "skills/a/SKILL.md").read_text(encoding="utf-8")
    assert text.startswith("---\nname: a\ndescription: b\n---\n<!--\n")


def test_a_headed_workflow_keeps_its_text_below_the_header():
    """REQ-014 (Q-1419-1): a workflow takes the `#` header as its first lines and nothing else
    changes, so taking the header off gives the workflow back."""
    workflow = "# The gate.\nname: governance\non: pull_request\njobs: {}\n"
    out = notice.add_header(workflow, "hash")
    assert out.startswith(f"# {COPYRIGHT}\n# {IDENTIFIER}\n")
    assert out.endswith(workflow)
    assert notice.without_header(out) == workflow


def test_kit_templates_carry_no_header(repo):
    """REQ-014: a template becomes a project's own file and is not checked."""
    kit_repo(repo, {"scripts/agk/a.py": notice.add_header("x = 1\n", "hash")})
    repo.commit({"kit/templates/agk.toml": 'mode = "init"\n'})
    assert repo.run("check_licence_notice.py").returncode == 0


def test_a_project_needs_licence_agk_and_headed_kit_scripts(repo):
    """REQ-014: in a project (no kit manifest) the check reads LICENSE-AGK and scripts/agk/."""
    repo.commit({"scripts/agk/a.py": notice.add_header("x = 1\n", "hash"), "README.md": "# p\n"})
    proc = repo.run("check_licence_notice.py")
    assert proc.returncode == 1
    assert "LICENSE-AGK" in proc.stdout
    repo.commit({"LICENSE-AGK": "the licence\n", "scripts/agk/b.py": "y = 2\n"})
    proc = repo.run("check_licence_notice.py")
    assert proc.returncode == 1
    assert "scripts/agk/b.py" in proc.stdout
    repo.commit({"scripts/agk/b.py": notice.add_header("y = 2\n", "hash")})
    assert repo.run("check_licence_notice.py").returncode == 0


# --- the rule budget --------------------------------------------------------------------------


def test_the_header_is_not_counted_in_the_rule_budget():
    """REQ-014: rules.py counts the same words and rule lines with and without the header."""
    plain = "---\nname: a\n---\n\nRule text here.\n\n1. One rule.\n- Two rule.\n"
    assert rules.counts(notice.add_header(plain, "html")) == rules.counts(plain)
    guide = "# Title\n\n1. A rule.\n"
    assert rules.counts(notice.add_header(guide, "html")) == rules.counts(guide)


# --- the grant in agk.toml (doctor) -----------------------------------------------------------


def grant_repo(repo, table: str, origin: str = "https://github.com/example/app.git"):
    repo.commit({"agk.toml": 'mode = "init"\nversion = "1.0.0"\n' + table})
    repo.git("remote", "add", "origin", origin)


def test_doctor_warns_when_the_grant_is_missing(repo):
    """REQ-014: no `[licence]` table gives one warning naming the setting."""
    grant_repo(repo, "")
    lines = doctor.licence_lines(repo.root)
    assert len(lines) == 1
    assert "[licence]" in lines[0]
    assert lines[0].startswith("warn licence-grant:")


def test_doctor_warns_when_the_repository_differs_from_origin(repo):
    """REQ-014: a grant for another repository warns, naming the setting and not the value."""
    grant_repo(
        repo,
        '[licence]\ngrant = "G-1"\nrepository = "example/other"\nvalid_until = "2099-01-01"\n',
    )
    lines = doctor.licence_lines(repo.root)
    assert len(lines) == 1
    assert "[licence] repository" in lines[0]
    assert "example/other" not in lines[0]


def test_doctor_warns_when_the_origin_remote_cannot_be_read(repo):
    """REQ-014: an unknown origin is not a match: one warning that the granted repository could
    not be compared, naming the setting and not the value."""
    repo.commit(
        {
            "agk.toml": 'mode = "init"\nversion = "1.0.0"\n[licence]\ngrant = "G-1"\n'
            'repository = "example/app"\nvalid_until = "2099-01-01"\n'
        }
    )
    lines = doctor.licence_lines(repo.root, today=datetime.date(2026, 11, 16))
    assert len(lines) == 1
    assert lines[0].startswith("warn licence-grant:")
    assert "could not be compared" in lines[0]
    assert "[licence] repository" in lines[0]
    assert "example/app" not in lines[0]


def test_doctor_warns_after_valid_until_and_names_the_uninstall_step(repo):
    """REQ-014: an ended grant warns and names the uninstall step."""
    grant_repo(
        repo, '[licence]\ngrant = "G-1"\nrepository = "example/app"\nvalid_until = 2026-01-01\n'
    )
    lines = doctor.licence_lines(repo.root, today=datetime.date(2026, 11, 16))
    assert len(lines) == 1
    assert "[licence] valid_until" in lines[0]
    assert "uninstall" in lines[0]


def test_doctor_is_quiet_for_a_current_grant_of_this_repository(repo):
    """REQ-014: a grant naming origin's repository and a later date gives no line."""
    grant_repo(
        repo,
        '[licence]\ngrant = "G-1"\nrepository = "Example/App"\nvalid_until = "2027-01-01"\n',
        origin="git@github.com:example/app.git",
    )
    assert doctor.licence_lines(repo.root, today=datetime.date(2026, 11, 16)) == []


def test_doctor_is_quiet_in_the_kit_repository(repo):
    """REQ-014: the kit's own repository needs no grant."""
    repo.commit({"agk.toml": 'mode = "init"\n', "kit/manifest.json": "{}\n"})
    assert doctor.licence_lines(repo.root) == []
