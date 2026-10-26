"""agk doctor (SPEC-0006): report what is misconfigured in a repository that agk governs.

Standard library only. Read-only: it reads local files and runs `git` only to read, and `gh api`
only with GET on four paths (`gh` holds the credential; this script holds none). It writes nothing.
A check that could not read what it needs is `cannot-check` with a reason class, never `ok`.
Messages name a setting or a path class, never a value. Output is a text report or, with --json,
the same findings as one JSON object; the exit code is 0 only when every check is ok.
"""

from __future__ import annotations

import json
import re
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

USAGE = "usage: doctor.py [--repo OWNER/REPO] [--kit-root PATH] [--api-dir DIR] [--json] [ROOT]"
PLACEHOLDER = "@REPLACE-ME"
DRIFT_WORKFLOW = ".github/workflows/drift-audit.yml"
DRIFT_NAME = "drift-audit.yml"
REPORT_WORKFLOW = ".github/workflows/product-report.yml"
REPORT_NAME = "product-report.yml"
ISSUE_WRITERS = ("metrics.yml", "drift-audit.yml", "product-report.yml")  # `issues: write`
KIT_ONLY = ("kit/",)
KIT_ONLY_FILES = ("scripts/agk/init.py", "scripts/agk/adopt.py")
MARKERS = {
    "hash": ("# >>> agk", "# <<< agk"),
    "html": ("<!-- >>> agk -->", "<!-- <<< agk -->"),
}
ABSENT_AS_BLOCK = {".gitignore", ".gitattributes"}
ENGINE_KEYS = ("vision", "stack", "design", "review")
ENGINE_NAME = re.compile(r"^[a-z][a-z0-9-]*$")
ENGINE_FIX = (
    "install the skill the setting names, or remove the setting so the kit's own template is used "
    "(a change to agk.toml needs an ADR in the same pull request)"
)
LIST_LIMIT = 10

# id -> (severity, text when ok, text when it fails, printed fix); the order is the report order.
CHECKS: dict[str, tuple[str, str, str, str]] = {
    "ruleset-missing": (
        "error",
        "a ruleset targets the default branch",
        "no ruleset targets the default branch",
        "create the ruleset of ADR-0001 decision 3: active; no bypass; target the default branch; "
        "restrict deletions; require linear history; require a pull request (dismiss stale "
        "approvals, no merge commits); block force pushes; required status check `governance`; "
        "classic branch protection is not read; use a ruleset (ADR-0001 decision 3)",
    ),
    "ruleset-enforcement": (
        "error",
        "ruleset enforcement is active",
        "ruleset: enforcement is not active",
        "set the ruleset to Active",
    ),
    "ruleset-bypass": (
        "error",
        "ruleset has no bypass actors",
        "ruleset: bypass_actors is not empty",
        "remove every bypass actor",
    ),
    "ruleset-target": (
        "error",
        "the ruleset targets the default branch",
        "ruleset: no branch ruleset includes the default branch",
        "target the default branch",
    ),
    "ruleset-deletion": (
        "error",
        "ruleset restricts deletions",
        "ruleset: the deletion rule is missing",
        "restrict deletions",
    ),
    "ruleset-linear-history": (
        "error",
        "ruleset requires linear history",
        "ruleset: the required_linear_history rule is missing",
        "require linear history",
    ),
    "ruleset-force-push": (
        "error",
        "ruleset blocks force pushes",
        "ruleset: the non_fast_forward rule is missing",
        "block force pushes",
    ),
    "ruleset-pull-request": (
        "error",
        "ruleset requires a pull request",
        "ruleset: pull_request rule missing, stale approvals not dismissed on push, or merge "
        "commits allowed",
        "require a pull request, dismiss stale approvals on push, and do not allow merge commits "
        "(ADR-0001 decision 3 uses squash only)",
    ),
    "required-check-governance": (
        "error",
        "the status check `governance` is required",
        "ruleset: the required status check `governance` is missing",
        "require the status check `governance`; if the ruleset was applied in phase 1 and "
        "`governance` has not yet run on the default branch, run `/agk:ruleset` after its first "
        "run",
    ),
    "repo-auto-merge": (
        "warn",
        "repository setting allow_auto_merge is on",
        "repository setting allow_auto_merge is off",
        "allow auto-merge",
    ),
    "repo-delete-branch": (
        "warn",
        "repository setting delete_branch_on_merge is on",
        "repository setting delete_branch_on_merge is off",
        "auto-delete head branches",
    ),
    "placeholder-team-reviewers": (
        "error",
        "config/reviewers.yaml has no placeholder team",
        "config/reviewers.yaml still names the placeholder team (maintainers or spec_approvers)",
        "replace the placeholder with a real team or user in maintainers and with your user "
        "handle in spec_approvers, then run "
        "`python3 scripts/agk/reviewers.py --codeowners --write`",
    ),
    "placeholder-team-codeowners": (
        "error",
        ".github/CODEOWNERS has no placeholder team",
        ".github/CODEOWNERS still names the placeholder team",
        "replace the placeholder with a real team or user, then run "
        "`python3 scripts/agk/reviewers.py --codeowners --write`",
    ),
    "origin-head": (
        "warn",
        "refs/remotes/origin/HEAD exists",
        "refs/remotes/origin/HEAD is missing",
        "run `git remote set-head origin <default_branch>` (no network; `-a` asks the remote)",
    ),
    "drift-workflow-file": (
        "error",
        ".github/workflows/drift-audit.yml has a schedule",
        ".github/workflows/drift-audit.yml is absent or has no schedule with a cron",
        "restore the file from the kit",
    ),
    "drift-workflow-state": (
        "error",
        "the drift-audit workflow (and the product-report workflow, where installed) is active",
        "the drift-audit workflow or the product-report workflow is not active on GitHub",
        "enable the workflow (GitHub disables scheduled workflows after inactivity (verify))",
    ),
    "issues-disabled": (
        "error",
        "Issues are enabled, or no workflow that writes issues is installed",
        "repository setting has_issues is off and workflows that write issues are installed",
        "enable Issues in the repository settings (General, Features), or delete the workflow "
        "files that write issues (.github/workflows/metrics.yml, drift-audit.yml, "
        "product-report.yml)",
    ),
    "kit-version": (
        "warn",
        "the kit version equals version in agk.toml",
        "the kit version differs from version in agk.toml",
        "run /agk:upgrade (SPEC-0008)",
    ),
    "vendored-missing": (
        "error",
        "every vendored file is present",
        "vendored files are missing",
        "restore them from the kit",
    ),
    "vendored-differs": (
        "error",
        "every vendored file equals the kit's copy",
        "vendored files differ from the kit's copy",
        "review `git log -p -- <path>`; restore the kit's copy, or record the deliberate edit in "
        "an ADR that names the path class",
    ),
    "default-branch-config": (
        "warn",
        "default_branch in agk.toml equals the repository's default branch",
        "default_branch in agk.toml differs from the repository's default branch",
        "set default_branch in agk.toml",
    ),
    "brief-label": (
        "warn",
        "the repository has the agk-brief label",
        "the repository has no agk-brief label",
        "create the label agk-brief (briefs are the issues that carry it)",
    ),
    "pr-mode": (
        "warn",
        "pr_mode in agk.toml is strict or flow",
        "pr_mode in agk.toml is neither strict nor flow",
        "set pr_mode in agk.toml to strict or flow (a change needs an ADR)",
    ),
    "engines-keys": (
        "warn",
        "[engines] in agk.toml has only the keys vision, stack, design and review",
        "[engines] in agk.toml is not a table of the keys vision, stack, design and review",
        "keep only those four keys, each the name of a skill (a change to agk.toml needs an ADR "
        "in the same pull request)",
    ),
    "engine-vision": (
        "warn",
        "engines.vision is absent or names a skill the session can see",
        "engines.vision is invalid, or names a skill the session cannot find",
        ENGINE_FIX,
    ),
    "engine-stack": (
        "warn",
        "engines.stack is absent or names a skill the session can see",
        "engines.stack is invalid, or names a skill the session cannot find",
        ENGINE_FIX,
    ),
    "engine-design": (
        "warn",
        "engines.design is absent or names a skill the session can see",
        "engines.design is invalid, or names a skill the session cannot find",
        ENGINE_FIX,
    ),
    "engine-review": (
        "warn",
        "engines.review is absent or names a skill the session can see",
        "engines.review is invalid, or names a skill the session cannot find",
        ENGINE_FIX,
    ),
}
RULESET_IDS = [
    "ruleset-enforcement",
    "ruleset-bypass",
    "ruleset-target",
    "ruleset-deletion",
    "ruleset-linear-history",
    "ruleset-force-push",
    "ruleset-pull-request",
    "required-check-governance",
]
HINTS = {
    "gh-missing": "install the GitHub CLI (`gh`)",
    "gh-unauthenticated": "run `gh auth login`",
    "no-admin": "use an account with admin rights on the repository",
    "not-github": "pass --repo OWNER/REPO for a repository on github.com",
    "no-kit-root": "pass --kit-root with the plugin or kit checkout",
    "version-mismatch": "use a kit of the same version as version in agk.toml, or run /agk:upgrade",
    "offline": "check the network connection",
    "bad-response": "the input could not be read",
    "plugin-unreadable": "only the project's and this plugin's skills are read; check it by hand",
    "no-ruleset": "no ruleset targets the default branch; fix ruleset-missing or ruleset-target",
}


@dataclass
class Result:
    status: str  # ok | fail | cannot-check
    reason: str = ""
    message: str = ""


class Refusal(Exception):
    def __init__(self, text: str, code: int = 1) -> None:
        super().__init__(text)
        self.code = code


# --- reads ------------------------------------------------------------------------------------


def http_reason(status: str) -> str:
    return {"401": "gh-unauthenticated", "403": "no-admin", "404": "no-admin"}.get(
        status, "bad-response"
    )


def error_payload(data: Any) -> str | None:
    """The reason class of a GitHub error body ({"message": ..., "status": "403"}), else None."""
    if isinstance(data, dict) and "message" in data and str(data.get("status", "")).isdigit():
        return http_reason(str(data["status"]))
    return None


class Reads:
    """Where the GitHub responses come from: recorded JSON files, or `gh api` with GET."""

    def __init__(self, repo: str | None, api_dir: Path | None) -> None:
        self.repo = repo
        self.api_dir = api_dir

    def get(self, name: str, path: str, not_found: str | None = None) -> tuple[Any, str]:
        """(data, "") or (None, reason class); a 404 is `not_found` when that is given."""
        if self.api_dir is not None:
            file = self.api_dir / f"{name}.json"
            if not file.is_file():
                return None, "bad-response"
            try:
                data = json.loads(file.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                raise Refusal("an --api-dir file is not JSON (path class api-dir)", 3) from None
            reason = error_payload(data)
            if not_found and isinstance(data, dict) and str(data.get("status")) == "404":
                return None, not_found
            return (None, reason) if reason else (data, "")
        if not self.repo:
            return None, "not-github"
        endpoint = f"repos/{self.repo}{path}"
        try:
            proc = subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
                ["gh", "api", "--method", "GET", endpoint], capture_output=True, text=True
            )
        except FileNotFoundError:
            return None, "gh-missing"
        except OSError:
            return None, "bad-response"
        if proc.returncode != 0:
            if not_found and "http 404" in f"{proc.stdout}\n{proc.stderr}".lower():
                return None, not_found
            return None, classify_failure(proc.stdout, proc.stderr)
        try:
            data = json.loads(proc.stdout)
        except ValueError:
            return None, "bad-response"
        reason = error_payload(data)
        return (None, reason) if reason else (data, "")


def classify_failure(stdout: str, stderr: str) -> str:
    text = f"{stdout}\n{stderr}".lower()
    if "gh auth login" in text or "not logged in" in text or "http 401" in text:
        return "gh-unauthenticated"
    if "http 403" in text or "http 404" in text or "admin rights" in text:
        return "no-admin"
    if "could not resolve host" in text or "dial tcp" in text or "timeout" in text:
        return "offline"
    try:
        reason = error_payload(json.loads(stdout))
    except ValueError:
        reason = None
    return reason or "bad-response"


def git_read(root: Path, *args: str) -> tuple[int, str]:
    try:
        proc = subprocess.run(  # nosec B603 B607 - fixed argument list, read-only git, no shell
            ["git", "-C", str(root), *args], capture_output=True, text=True
        )
    except OSError:
        return 127, ""
    return proc.returncode, proc.stdout.strip()


def origin_repo(root: Path) -> str | None:
    code, url = git_read(root, "config", "--get", "remote.origin.url")
    if code != 0:
        return None
    match = re.search(r"github\.com[:/]([^/\s]+/[^/\s]+?)(?:\.git)?/?$", url)
    return match.group(1) if match else None


# --- the checks -------------------------------------------------------------------------------


def targets_default(ruleset: dict, branch: str) -> bool:
    """Includes the default branch (`~DEFAULT_BRANCH`, `~ALL`, its ref) and does not exclude it."""
    ref_name = (ruleset.get("conditions") or {}).get("ref_name") or {}
    include = ref_name.get("include") or []
    exclude = ref_name.get("exclude") or []
    ref = f"refs/heads/{branch}"
    if "~DEFAULT_BRANCH" in exclude or "~ALL" in exclude or ref in exclude:
        return False
    return "~DEFAULT_BRANCH" in include or "~ALL" in include or ref in include


def rule_params(rulesets: list[dict], kind: str) -> list[dict]:
    return [
        r.get("parameters") or {}
        for d in rulesets
        for r in (d.get("rules") or [])
        if r.get("type") == kind
    ]


def has_rule(rulesets: list[dict], kind: str) -> bool:
    return any(r.get("type") == kind for d in rulesets for r in (d.get("rules") or []))


def ruleset_results(reads: Reads, repo_data: Any, branch: str) -> dict[str, Result]:
    out: dict[str, Result] = {}

    def cannot_all(reason: str, ids: list[str]) -> None:
        for check in ids:
            out[check] = Result("cannot-check", reason)

    everything = ["ruleset-missing", *RULESET_IDS]
    listing, reason = reads.get("rulesets", "/rulesets")
    if not isinstance(listing, list):
        cannot_all(reason or "bad-response", everything)
        return out
    branch_rulesets = [r for r in listing if isinstance(r, dict) and r.get("target") == "branch"]
    details = []
    for entry in sorted(branch_rulesets, key=lambda r: str(r.get("id"))):
        data, reason = reads.get(f"ruleset-{entry.get('id')}", f"/rulesets/{entry.get('id')}")
        if not isinstance(data, dict):
            cannot_all(reason or "bad-response", everything)
            return out
        details.append(data)
    permissions = repo_data.get("permissions") if isinstance(repo_data, dict) else None
    if not details:
        if isinstance(permissions, dict) and permissions.get("admin") is False:
            cannot_all("no-admin", everything)  # a non-admin may see an empty list
            return out
        out["ruleset-missing"] = Result("fail")
        cannot_all("no-ruleset", RULESET_IDS)
        return out
    out["ruleset-missing"] = Result("ok")
    candidates = [d for d in details if targets_default(d, branch)]
    if not candidates:
        out["ruleset-target"] = Result("fail")
        cannot_all("no-ruleset", [i for i in RULESET_IDS if i != "ruleset-target"])
        return out
    out["ruleset-target"] = Result("ok")

    def verdict(check: str, good: bool) -> None:
        out[check] = Result("ok" if good else "fail")

    active = [d for d in candidates if d.get("enforcement") == "active"]
    verdict("ruleset-enforcement", bool(active))
    # only an active ruleset protects: every other element reads active rulesets alone
    verdict("ruleset-bypass", bool(active) and not any(d.get("bypass_actors") for d in active))
    verdict("ruleset-deletion", has_rule(active, "deletion"))
    verdict("ruleset-linear-history", has_rule(active, "required_linear_history"))
    verdict("ruleset-force-push", has_rule(active, "non_fast_forward"))
    pulls = rule_params(active, "pull_request")
    methods = [p.get("allowed_merge_methods", ["merge", "squash", "rebase"]) for p in pulls]
    verdict(
        "ruleset-pull-request",
        bool(pulls)
        and any(p.get("dismiss_stale_reviews_on_push") is True for p in pulls)
        and not any("merge" in m for m in methods),
    )
    contexts = [
        c.get("context")
        for p in rule_params(active, "required_status_checks")
        for c in (p.get("required_status_checks") or [])
        if isinstance(c, dict)
    ]
    verdict("required-check-governance", "governance" in contexts)
    return out


def workflow_state_result(reads: Reads, report_installed: bool) -> Result:
    """Every scheduled workflow is active: the drift audit, and the product report where installed.

    A workflow that is not active fails the check even when the other could not be read; a file
    that is absent from the repository is reported by `vendored-missing`, not read here.
    """
    names = [("workflow-drift-audit", DRIFT_NAME)]
    if report_installed:
        names.append(("workflow-product-report", REPORT_NAME))
    states, reasons = [], []
    for fixture, name in names:
        data, why = reads.get(fixture, f"/actions/workflows/{name}")
        if isinstance(data, dict) and "state" in data:
            states.append(data["state"])
        else:
            reasons.append(why or "bad-response")
    if any(s != "active" for s in states):
        return Result("fail")
    return Result("cannot-check", reasons[0]) if reasons else Result("ok")


def issues_result(repo_data: Any, reason: str, writers: list[str]) -> Result:
    """Fails when has_issues is false and an issue-writing workflow is installed (no new read)."""
    if not writers:
        return Result("ok")
    if not isinstance(repo_data, dict):
        return Result("cannot-check", reason or "bad-response")
    enabled = repo_data.get("has_issues")
    if not isinstance(enabled, bool):
        return Result("cannot-check", "bad-response")
    if enabled:
        return Result("ok")
    return Result("fail", message=f" ({', '.join(writers)})")


def remote_results(
    reads: Reads, config: dict, report_installed: bool, writers: list[str]
) -> dict[str, Result]:
    out: dict[str, Result] = {}
    repo_data, reason = reads.get("repo", "")
    out["drift-workflow-state"] = workflow_state_result(reads, report_installed)
    out["issues-disabled"] = issues_result(repo_data, reason, writers)
    if not isinstance(repo_data, dict):
        for check in [
            "ruleset-missing",
            *RULESET_IDS,
            "repo-auto-merge",
            "repo-delete-branch",
            "default-branch-config",
            "brief-label",
        ]:
            out[check] = Result("cannot-check", reason or "bad-response")
        return out
    branch = repo_data.get("default_branch") or config.get("default_branch", "main")
    out.update(ruleset_results(reads, repo_data, branch))
    for check, key in (
        ("repo-auto-merge", "allow_auto_merge"),
        ("repo-delete-branch", "delete_branch_on_merge"),
    ):
        if key not in repo_data:
            out[check] = Result("cannot-check", "no-admin")  # only shown to users with push access
        else:
            out[check] = Result("ok" if repo_data[key] is True else "fail")
    label, why = reads.get("label-agk-brief", "/labels/agk-brief", not_found="missing")
    out["brief-label"] = (
        Result("fail") if why == "missing" else Result("cannot-check", why) if why else Result("ok")
    )
    out["default-branch-config"] = Result(
        "ok" if repo_data.get("default_branch") == config.get("default_branch", "main") else "fail"
    )
    return out


def placeholder_result(path: Path) -> Result:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return Result("cannot-check", "bad-response")
    return Result("fail" if PLACEHOLDER in text else "ok")


def drift_file_result(root: Path) -> Result:
    try:
        text = (root / DRIFT_WORKFLOW).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return Result("fail")
    lines = [ln for ln in text.splitlines() if not ln.lstrip().startswith("#")]
    for i, line in enumerate(lines):
        if re.match(r"^\s*schedule:\s*$", line):
            rest = lines[i + 1 :]
            return Result("ok" if any(re.match(r"^\s*-\s*cron:", ln) for ln in rest) else "fail")
    return Result("fail")


def origin_head_result(root: Path) -> Result:
    code, _ = git_read(root, "symbolic-ref", "-q", "refs/remotes/origin/HEAD")
    if code == 0:
        return Result("ok")
    if code == 1:
        return Result("fail")
    return Result("cannot-check", "bad-response")


def find_block(text: str, style: str) -> tuple[str, str | None]:
    begin, end = MARKERS[style]
    lines = text.splitlines(keepends=True)
    begins = [i for i, ln in enumerate(lines) if ln.rstrip("\r\n") == begin]
    ends = [i for i, ln in enumerate(lines) if ln.rstrip("\r\n") == end]
    if not begins and not ends:
        return "none", None
    if len(begins) != 1 or len(ends) != 1 or ends[0] < begins[0]:
        return "broken", None
    return "ok", "".join(lines[begins[0] + 1 : ends[0]])


def installed_files(
    manifest: dict, mode: str, experimental: bool = False
) -> tuple[list[str], dict[str, str]]:
    """(verbatim paths the installer for `mode` writes, marked blocks compared inside markers)."""
    listed = [
        *manifest.get("verbatim", []),
        *(manifest.get("experimental", []) if experimental else []),
    ]
    verbatim = [p for p in listed if not p.startswith(KIT_ONLY) and p not in KIT_ONLY_FILES]
    if mode == "init":
        return sorted(verbatim), {}
    spec = manifest.get("adopt") or {}
    blocks = dict(spec.get("blocks") or {})
    files = set(verbatim) - set(spec.get("skip") or []) - set(blocks)
    rendered = set(manifest.get("rendered") or [])
    return sorted(files), {p: s for p, s in sorted(blocks.items()) if p not in rendered}


def lf(data: bytes) -> bytes:
    """CRLF line ends as LF, a file with a NUL byte as it is: the rule of `common.lf` (brief #263
    item 7), kept here because the doctor imports no other kit script."""
    return data if b"\0" in data else data.replace(b"\r\n", b"\n")


def compare_tree(
    root: Path,
    kit: Path,
    files: list[str],
    blocks: dict[str, str],
    sources: dict[str, str] | None = None,
) -> tuple[list[str], list[str]]:
    missing: list[str] = []
    differs: list[str] = []
    for rel in files:
        target = root / rel
        if not target.is_file():
            missing.append(rel)
        elif lf(target.read_bytes()) != lf((kit / rel).read_bytes()):  # CRLF on Windows
            differs.append(rel)
    for rel, style in blocks.items():
        target = root / rel
        if not target.is_file():
            missing.append(rel)
            continue
        source = (sources or {}).get(rel, rel)
        whole = (kit / source).read_text(encoding="utf-8").rstrip("\n") + "\n"
        text = target.read_text(encoding="utf-8")
        state, inner = find_block(text, style)
        if state == "ok":
            same = inner == whole
        else:
            same = state == "none" and text == whole and rel not in ABSENT_AS_BLOCK
        if not same:
            differs.append(rel)
    return missing, differs


def kit_results(root: Path, kit_root: Path | None, config: dict) -> tuple[dict[str, Result], str]:
    names = ["kit-version", "vendored-missing", "vendored-differs"]
    if kit_root is None:
        return {n: Result("cannot-check", "no-kit-root") for n in names}, "unknown"
    try:
        manifest = json.loads((kit_root / "kit" / "manifest.json").read_text(encoding="utf-8"))
        kit_version = str(manifest["kit_version"])
    except (OSError, ValueError, KeyError):
        return {n: Result("cannot-check", "bad-response") for n in names}, "unknown"
    installed = config.get("version")
    mode = config.get("mode")
    if not isinstance(installed, str) or mode not in ("init", "adopt"):
        return {n: Result("cannot-check", "bad-response") for n in names}, kit_version
    if installed != kit_version:
        out = {n: Result("cannot-check", "version-mismatch") for n in names}
        out["kit-version"] = Result("fail")
        return out, kit_version
    files, blocks = installed_files(manifest, mode, config.get("experimental_reviewer") is True)
    try:
        sources = (manifest.get("adopt") or {}).get("block_sources") or {}
        missing, differs = compare_tree(root, kit_root, files, blocks, sources)
    except (OSError, UnicodeDecodeError):
        return {n: Result("cannot-check", "bad-response") for n in names}, kit_version
    return {
        "kit-version": Result("ok"),
        "vendored-missing": Result("fail", message=listing(missing)) if missing else Result("ok"),
        "vendored-differs": Result("fail", message=listing(differs)) if differs else Result("ok"),
    }, kit_version


def seen_by_the_user(root: Path, name: str) -> bool:
    """A skill of the project or of the user (`~/.claude/skills`): a file-existence check only."""
    places = [root / ".claude" / "skills"]
    try:
        places.append(Path.home() / ".claude" / "skills")
    except (RuntimeError, KeyError):
        pass
    return any((place / name / "SKILL.md").is_file() for place in places)


def engine_results(root: Path, kit_root: Path | None, config: dict) -> dict[str, Result]:
    """`[engines]` (SPEC-0029 rules 1 and 2): present, absent or missing; names the setting only.

    A skill is seen when its `SKILL.md` exists in the project's `.claude/skills/<name>/`, in the
    user's `~/.claude/skills/<name>/` or in the plugin's `skills/<name>/`; only the existence of
    the file is tested, nothing is read or printed. Other plugins' skills are not read (verify).
    """
    table = config.get("engines", {})
    out: dict[str, Result] = {}
    if not isinstance(table, dict):
        out["engines-keys"] = Result("fail")
        table = {}
    else:
        extra = [k for k in table if k not in ENGINE_KEYS]
        out["engines-keys"] = Result("fail" if extra else "ok")
    for key in ENGINE_KEYS:
        if key not in table:
            out[f"engine-{key}"] = Result("ok", message=" (absent: the kit's own template is used)")
            continue
        name = table[key]
        plugin, _, local = name.rpartition(":") if isinstance(name, str) else ("", "", "")
        if not isinstance(name, str) or not ENGINE_NAME.match(local) or plugin not in ("", "agk"):
            valid = isinstance(name, str) and ENGINE_NAME.match(local) and ":" in name
            out[f"engine-{key}"] = (
                Result("cannot-check", "plugin-unreadable")
                if valid
                else Result("fail", message=" (invalid)")
            )
            continue
        if not plugin and seen_by_the_user(root, local):
            out[f"engine-{key}"] = Result("ok", message=" (present)")
        elif kit_root is None:
            out[f"engine-{key}"] = Result("cannot-check", "no-kit-root")
        elif (kit_root / "skills" / local / "SKILL.md").is_file():
            out[f"engine-{key}"] = Result("ok", message=" (present)")
        else:
            out[f"engine-{key}"] = Result("fail", message=" (missing)")
    return out


def listing(paths: list[str]) -> str:
    shown = ", ".join(paths[:LIST_LIMIT])
    more = f" and {len(paths) - LIST_LIMIT} more" if len(paths) > LIST_LIMIT else ""
    return f" ({shown}{more})"


# --- the report -------------------------------------------------------------------------------


def run_checks(
    root: Path, repo: str | None, kit_root: Path | None, api_dir: Path | None
) -> tuple[list[dict], str]:
    agk_toml = root / "agk.toml"
    if not agk_toml.is_file():
        raise Refusal("agk.toml missing (path class agk.toml); this is not an agk target")
    try:
        config = tomllib.loads(agk_toml.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        raise Refusal("agk.toml is not readable TOML (path class agk.toml)", 3) from None
    results: dict[str, Result] = {}
    writers = [n for n in ISSUE_WRITERS if (root / ".github" / "workflows" / n).is_file()]
    results.update(
        remote_results(
            Reads(repo or origin_repo(root), api_dir),
            config,
            (root / REPORT_WORKFLOW).is_file(),
            writers,
        )
    )
    results["placeholder-team-reviewers"] = placeholder_result(root / "config" / "reviewers.yaml")
    results["placeholder-team-codeowners"] = placeholder_result(root / ".github" / "CODEOWNERS")
    results["origin-head"] = origin_head_result(root)
    results["drift-workflow-file"] = drift_file_result(root)
    mode = config.get("pr_mode", "strict")
    results["pr-mode"] = (
        Result("ok", message=f" (mode: {mode})") if mode in ("strict", "flow") else Result("fail")
    )
    kit, version = kit_results(root, kit_root, config)
    results.update(kit)
    results.update(engine_results(root, kit_root, config))
    report = []
    for check, (severity, ok_text, fail_text, fix) in CHECKS.items():
        res = results[check]
        if res.status == "ok":
            message = ok_text + res.message
        elif res.status == "fail":
            message = fail_text + res.message
        else:
            message = f"cannot check ({res.reason})"
        entry = {"id": check, "severity": severity, "status": res.status, "message": message}
        entry["fix"] = fix
        if res.status == "cannot-check":
            entry["reason"] = res.reason
        report.append(entry)
    return report, version


def summary(report: list[dict]) -> dict[str, int]:
    return {s: sum(1 for c in report if c["status"] == s) for s in ("ok", "fail", "cannot-check")}


def render_text(report: list[dict], version: str) -> str:
    lines = [f"agk doctor {version}"]
    marks = {"ok": "ok", "fail": "FAIL", "cannot-check": "??"}
    for c in report:
        lines.append(f"{marks[c['status']]} {c['id']} {c['severity']} {c['message']}")
        if c["status"] == "fail":
            lines.append(f"  fix: {c['fix']}")
        elif c["status"] == "cannot-check":
            lines.append(f"  to check: {HINTS.get(c['reason'], HINTS['bad-response'])}")
    s = summary(report)
    lines.append(f"summary: {s['ok']} ok, {s['fail']} fail, {s['cannot-check']} cannot-check")
    return "\n".join(lines) + "\n"


def render_json(report: list[dict], version: str) -> str:
    data = {"doctor": version, "checks": report, "summary": summary(report)}
    return json.dumps(data, indent=2, sort_keys=True) + "\n"


def exit_code(report: list[dict]) -> int:
    if any(c["status"] == "fail" and c["severity"] == "error" for c in report):
        return 1
    if any(c["status"] != "ok" for c in report):
        return 4
    return 0


def parse_args(args: list[str]) -> dict | None:
    options: dict = {"repo": None, "kit": None, "api": None, "json": False, "root": None}
    i = 0
    while i < len(args):
        arg = args[i]
        if arg == "--json":
            options["json"] = True
            i += 1
        elif arg in ("--repo", "--kit-root", "--api-dir") and i + 1 < len(args):
            key = {"--repo": "repo", "--kit-root": "kit", "--api-dir": "api"}[arg]
            options[key] = args[i + 1]
            i += 2
        elif not arg.startswith("-") and options["root"] is None:
            options["root"] = arg
            i += 1
        else:
            return None
    return options


def main(argv: list[str] | None = None) -> int:
    options = parse_args(list(sys.argv[1:] if argv is None else argv))
    if options is None:
        print(USAGE, file=sys.stderr)
        return 2
    try:
        root = Path(options["root"] or ".")
        if not root.is_dir():
            raise Refusal("ROOT is not a directory (path class: the target root)")
        report, version = run_checks(
            root.resolve(),
            options["repo"],
            Path(options["kit"]) if options["kit"] else None,
            Path(options["api"]) if options["api"] else None,
        )
    except Refusal as exc:
        print(f"refused: {exc}")
        return exc.code
    except OSError:
        print("error: cannot read the target (path class: the target root)")
        return 3
    sys.stdout.write(
        render_json(report, version) if options["json"] else render_text(report, version)
    )
    return exit_code(report)


if __name__ == "__main__":
    sys.exit(main())
