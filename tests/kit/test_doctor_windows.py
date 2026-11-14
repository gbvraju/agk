"""A Windows setup works on the first run (brief #1223, ADR-0522; REQ-014).

Answer 1: on Windows only, the doctor's `windows-tools` check names the fix of each missing tool: a
`python3` that is the Microsoft Store shortcut (under `WindowsApps`), an absent `make` and an absent
`gitleaks`. Answer 2: the account's admin rights come from `permissions.admin` of the repository read
(`gh api repos/{owner}/{repo} --jq .permissions.admin`); when that cannot be read, a refused read is
`cannot check (admin-unknown)`, never `no-admin`. Answer 3: `reviewers.py --codeowners --write`
removes the plain lines outside the agk block that name only the placeholder owner. The platform,
the paths and every GitHub answer are simulated: no Windows and no network are needed.
"""

from __future__ import annotations

import json
from pathlib import Path

import doctor
import reviewers

STORE = r"C:\Users\dev\AppData\Local\Microsoft\WindowsApps\python3.exe"
REAL = r"C:\Program Files\Python312\python3.exe"


def which_of(found: dict[str, str]):
    return lambda name: found.get(name)


ALL_FOUND = {"python3": REAL, "make": r"C:\tools\make.exe", "gitleaks": r"C:\tools\gitleaks.exe"}


# --- answer 1: windows-tools ---------------------------------------------------------------------


def test_answer1_the_check_is_not_reported_off_windows():
    """REQ-014: brief #1223 answer 1 (Windows only)."""
    assert doctor.windows_tools_result("linux", which_of({})) is None
    assert doctor.windows_tools_result("darwin", which_of({})) is None


def test_answer1_all_tools_present_is_ok():
    """REQ-014: brief #1223 answer 1."""
    res = doctor.windows_tools_result("win32", which_of(ALL_FOUND))
    assert res is not None and res.status == "ok"


def test_answer1_the_store_shortcut_names_its_fix():
    """REQ-014: brief #1223 answer 1 (python3 under WindowsApps)."""
    res = doctor.windows_tools_result("win32", which_of({**ALL_FOUND, "python3": STORE}))
    assert res is not None and res.status == "fail"
    assert "python3" in res.message
    assert "App execution aliases" in res.fix and "copy python.exe to python3.exe" in res.fix
    assert "make" not in res.message and "gitleaks" not in res.message


def test_answer1_a_missing_make_names_its_fix():
    """REQ-014: brief #1223 answer 1."""
    found = {k: v for k, v in ALL_FOUND.items() if k != "make"}
    res = doctor.windows_tools_result("win32", which_of(found))
    assert res is not None and res.status == "fail"
    assert "winget install ezwinports.make" in res.fix
    assert "python3" not in res.message and "gitleaks" not in res.message


def test_answer1_a_missing_gitleaks_names_its_fix_with_the_pin():
    """REQ-014: brief #1223 answer 1 (the version the governance workflow pins)."""
    found = {k: v for k, v in ALL_FOUND.items() if k != "gitleaks"}
    res = doctor.windows_tools_result("win32", which_of(found))
    assert res is not None and res.status == "fail"
    assert f"winget install gitleaks.gitleaks --version {doctor.GITLEAKS_PIN}" in res.fix


def test_answer1_every_missing_tool_is_named_at_once():
    """REQ-014: brief #1223 answer 1."""
    res = doctor.windows_tools_result("win32", which_of({"python3": STORE}))
    assert res is not None and res.status == "fail"
    for tool in ("python3", "make", "gitleaks"):
        assert tool in res.message
    for fix in ("App execution aliases", "ezwinports.make", "gitleaks.gitleaks"):
        assert fix in res.fix


def test_answer1_the_report_entry_carries_the_fix_and_prints_it():
    """REQ-014: brief #1223 answer 1 (the printed fix is the tool's own)."""
    res = doctor.windows_tools_result("win32", which_of({"python3": STORE}))
    entry = doctor.windows_tools_entry(res)
    assert entry["id"] == "windows-tools" and entry["status"] == "fail"
    text = doctor.render_text([entry], "0.0.0")
    assert "FAIL windows-tools" in text and "winget install ezwinports.make" in text


# --- answer 2: the admin read ------------------------------------------------------------------


REFUSED = {
    "message": "Not Found",
    "documentation_url": "https://docs.github.com/rest",
    "status": "404",
}
FORBIDDEN = {
    "message": "Forbidden",
    "documentation_url": "https://docs.github.com/rest",
    "status": "403",
}
ADMIN_MESSAGE = {"message": "Must have admin rights to Repository.", "status": "403"}
CONFIG = {"default_branch": "main"}
RULESET_CHECKS = ["ruleset-missing", *doctor.RULESET_IDS]


def repo_json(admin: object = True, keys: bool = True) -> dict:
    data: dict = {"default_branch": "main", "has_issues": True, "full_name": "example-owner/x"}
    if keys:
        data.update(allow_auto_merge=True, delete_branch_on_merge=True)
    if admin is not None:
        data["permissions"] = {"admin": admin, "push": True, "pull": True}
    return data


def remote(tmp_path: Path, repo: dict, rulesets: object) -> dict:
    api = tmp_path / "api"
    api.mkdir(parents=True)
    (api / "repo.json").write_text(json.dumps(repo), encoding="utf-8")
    (api / "rulesets.json").write_text(json.dumps(rulesets), encoding="utf-8")
    reads = doctor.Reads("example-owner/x", api)
    return doctor.remote_results(reads, CONFIG, False, [])


def reasons(results: dict, ids: list[str]) -> set[str]:
    return {results[c].reason for c in ids}


def test_answer2_a_failed_repository_read_is_cannot_check_not_no_admin(tmp_path):
    """REQ-014: brief #1223 answer 2 (the admin read failed)."""
    results = remote(tmp_path, REFUSED, REFUSED)
    assert {results[c].status for c in RULESET_CHECKS} == {"cannot-check"}
    assert reasons(results, RULESET_CHECKS) == {"admin-unknown"}
    assert "no-admin" not in reasons(results, list(results))


def test_answer2_a_refused_ruleset_read_without_permissions_is_admin_unknown(tmp_path):
    """REQ-014: brief #1223 answer 2 (no `permissions` in the repository read)."""
    results = remote(tmp_path, repo_json(admin=None), FORBIDDEN)
    assert reasons(results, RULESET_CHECKS) == {"admin-unknown"}


def test_answer2_an_admin_refused_stays_forbidden(tmp_path):
    """REQ-014: brief #1223 answer 2 (permissions.admin true: not no-admin, brief #263)."""
    results = remote(tmp_path, repo_json(admin=True), FORBIDDEN)
    assert reasons(results, RULESET_CHECKS) == {"forbidden"}


def test_answer2_no_admin_only_when_permissions_admin_is_false(tmp_path):
    """REQ-014: brief #1223 answer 2."""
    results = remote(tmp_path, repo_json(admin=False), FORBIDDEN)
    assert reasons(results, RULESET_CHECKS) == {"no-admin"}


def test_answer2_github_naming_admin_rights_is_no_admin(tmp_path):
    """REQ-014: brief #1223 answer 2 (GitHub's own message says the rights are missing)."""
    results = remote(tmp_path, ADMIN_MESSAGE, ADMIN_MESSAGE)
    assert reasons(results, RULESET_CHECKS) == {"no-admin"}


def test_answer2_missing_merge_keys_are_not_no_admin_for_an_admin(tmp_path):
    """REQ-014: brief #1223 answer 2 (the keys are absent, the account is an admin)."""
    results = remote(tmp_path, repo_json(admin=True, keys=False), [])
    assert results["repo-auto-merge"].reason != "no-admin"
    assert results["repo-delete-branch"].reason != "no-admin"
    results = remote(tmp_path / "b", repo_json(admin=False, keys=False), [])
    assert results["repo-auto-merge"].reason == "no-admin"


def test_answer2_the_hint_names_the_rest_read_of_permissions_admin():
    """REQ-014: brief #1223 answer 2 (REST, no shell quoting of braces)."""
    hint = doctor.HINTS["admin-unknown"]
    assert "gh api repos/OWNER/REPO --jq .permissions.admin" in hint
    assert "{" not in hint
    entry = {"id": "ruleset-missing", "severity": "error", "status": "cannot-check"}
    entry.update(message="cannot check (admin-unknown)", reason="admin-unknown", fix="")
    text = doctor.render_text([entry], "0.0.0")
    assert "?? ruleset-missing error cannot check (admin-unknown)" in text
    assert "admin rights on the repository" not in text


def test_answer2_other_callers_of_the_reads_keep_no_admin(tmp_path):
    """REQ-014: brief #1223 answer 2 (a refused read is still `no-admin` for other readers)."""
    api = tmp_path / "api"
    api.mkdir()
    (api / "rulesets.json").write_text(json.dumps(FORBIDDEN), encoding="utf-8")
    assert doctor.Reads("example-owner/x", api).get("rulesets", "/rulesets") == (None, "no-admin")
    assert doctor.admin_reason("no-admin", repo_json(admin=True)) == "forbidden"
    assert doctor.admin_reason("no-admin", None) == "no-admin"


# --- answer 3: CODEOWNERS placeholder lines --------------------------------------------------------


RENDERED = "# Generated\n/docs/ @example-owner\n"
TEMPLATE_LINES = [
    "# Owners of the project (replace the placeholder)",
    "* @REPLACE-ME",
    "/docs/ @REPLACE-ME",
    "/config/ @replace-me  # the reviewers",
    "/src/ @REPLACE-ME @example-owner",
    "/web/ @example-org/web",
]


def codeowners(tmp_path: Path, text: str) -> Path:
    path = tmp_path / ".github" / "CODEOWNERS"
    path.parent.mkdir(parents=True)
    path.write_text(text, encoding="utf-8")
    return path


def test_answer3_placeholder_lines_are_removed_and_real_owner_lines_kept(tmp_path):
    """REQ-014: brief #1223 answer 3 (outside the marked block)."""
    before = (
        "\n".join(TEMPLATE_LINES) + "\n" + reviewers.BLOCK_BEGIN + "old\n" + reviewers.BLOCK_END
    )
    path = codeowners(tmp_path, before)
    reviewers.write_codeowners(tmp_path, RENDERED, adopt_mode=True)
    lines = path.read_text(encoding="utf-8").splitlines()
    assert "* @REPLACE-ME" not in lines
    assert "/docs/ @REPLACE-ME" not in lines
    assert "/config/ @replace-me  # the reviewers" not in lines
    assert "/src/ @REPLACE-ME @example-owner" in lines  # names a real owner too
    assert "/web/ @example-org/web" in lines
    assert "# Owners of the project (replace the placeholder)" in lines  # a comment, not a rule
    assert reviewers.extract_block(path.read_text(encoding="utf-8")) == RENDERED


def test_answer3_placeholder_lines_are_removed_when_the_block_is_added(tmp_path):
    """REQ-014: brief #1223 answer 3 (the first write appends the block)."""
    path = codeowners(tmp_path, "\n".join(TEMPLATE_LINES) + "\n")
    reviewers.write_codeowners(tmp_path, RENDERED, adopt_mode=True)
    text = path.read_text(encoding="utf-8")
    assert "* @REPLACE-ME\n" not in text and "/docs/ @REPLACE-ME\n" not in text
    assert "/web/ @example-org/web\n" in text and reviewers.extract_block(text) == RENDERED


def test_answer3_a_file_without_placeholder_lines_is_unchanged_outside_the_block(tmp_path):
    """REQ-014: brief #1223 answer 3 (any other line is kept)."""
    outside = "/web/ @example-org/web\n# a note\n\n"
    path = codeowners(tmp_path, outside + reviewers.BLOCK_BEGIN + RENDERED + reviewers.BLOCK_END)
    assert reviewers.write_codeowners(tmp_path, RENDERED, adopt_mode=True).startswith("unchanged")
    assert path.read_text(encoding="utf-8").startswith(outside)
