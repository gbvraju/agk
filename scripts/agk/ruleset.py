"""agk ruleset: the plan that applies the kit's branch ruleset and repository settings (SPEC-0013).

Usage:
    python3 ruleset.py plan [--phase 1|2|auto] [--repo O/R] [--api-dir DIR] [--tighten]
                            [--payload-dir DIR] [--root DIR]

Kit-only (never installed). It reads with `gh api --method GET` (the repository, its rulesets and
their detail, the runs of `governance.yml` on the default branch) or from recorded files in
`--api-dir`, and prints the plan. It holds no credential, sends nothing to GitHub and never calls a
write method: the commands it prints (`gh api --method POST|PUT|PATCH ... --input FILE`) are run by
the person's own `gh` after the person agrees. `--payload-dir` is the one place it writes files: the
payload of each command, in a directory the caller names (a temporary one).

The plan is add-only and idempotent: it creates the ruleset when none matches the default branch,
adds a missing rule and sets a missing repository setting; it never removes a rule, a setting or a
bypass actor and never loosens a value. A value looser than the kit's is reported as a finding with
its fix and changes only with `--tighten`. Phase 1 is every element except the required status
check `governance`; phase 2 adds it once `governance.yml` has succeeded on the default branch.
Exit 0: a plan or `nothing to do`; 4: it could not read the repository or the caller is not an
admin (the text of the ruleset and the settings path are printed, nothing else); 2: usage.
On exit 4 the reason names the cause: `plan-limit` when GitHub answers that rulesets need a paid
plan for a private repository, `no-admin` only when `permissions.admin` is not true, `forbidden`
when an admin is refused for another reason; the printed text is the rules of the phase the plan
chose (brief #263 build (a)).
"""

from __future__ import annotations

import copy
import json
import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))  # isolated mode (-I) leaves it off

from doctor import Reads, admin_reason, origin_repo, targets_default

KIT = Path(__file__).resolve().parents[2]
USAGE = (
    "usage: ruleset.py plan [--phase 1|2|auto] [--repo O/R] [--api-dir DIR] [--tighten] "
    "[--payload-dir DIR] [--root DIR]"
)
SIMPLE = ("deletion", "required_linear_history", "non_fast_forward")
SETTINGS_PATH = (
    "Settings > Rules > Rulesets (the ruleset) and Settings > General (allow auto-merge; "
    "automatically delete head branches) (verify)"
)
CONTEXT = "governance"
PHASE2_CLAUSE = f"; required status check `{CONTEXT}`"
WHY = {
    "plan-limit": "rulesets and branch protection on a private repository need a paid plan (GitHub "
    "Pro, Team or Enterprise); upgrade the plan or make the repository public, then run it again. "
    "Until then nothing protects the default branch, and applying it by hand is refused the same "
    "way. The ruleset to apply then:",
    "forbidden": "GitHub refused the read although the account is an admin of the repository; read "
    "GitHub's message with `gh api` on the same path. Apply it by hand:",
}
REPO_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")


class Stop(Exception):
    """Exit with a code and a text."""

    def __init__(self, text: str, code: int) -> None:
        super().__init__(text)
        self.code = code


def desired() -> dict:
    return json.loads((KIT / "kit" / "templates" / "ruleset.json").read_text(encoding="utf-8"))


class Cannot(Exception):
    """The ruleset cannot be applied from here, for a reason class."""

    def __init__(self, reason: str, branch: str | None = None) -> None:
        super().__init__(reason)
        self.reason = reason
        self.branch = branch  # the default branch, when the repository could be read


def cannot(reason: str, branch: str | None = None) -> Cannot:
    return Cannot(reason, branch)


def rules_text(phase: int) -> str:
    """The kit's ruleset text for a phase: phase 1 leaves out the required status check and says
    when it is added; phase 2 is `branch-rules.txt` exactly (brief #263 answer 2)."""
    text = (KIT / "kit" / "templates" / "branch-rules.txt").read_text(encoding="utf-8").strip()
    if phase == 2 or PHASE2_CLAUSE not in text:
        return text
    return (
        text.replace(PHASE2_CLAUSE, "", 1)
        + f"\nPhase 2, once `{CONTEXT}` has succeeded on the default branch: add the required "
        f"status check `{CONTEXT}`."
    )


def cannot_text(reason: str, phase: int, how: str) -> Stop:
    why = WHY.get(reason, "Apply it by hand:")
    return Stop(
        f"cannot apply the ruleset from here ({reason}). {why}\n"
        f"phase {phase} ({how})\n{rules_text(phase)}\nWhere: {SETTINGS_PATH}",
        4,
    )


def clean(rules: list[dict]) -> list[dict]:
    return [{k: v for k, v in r.items() if k in ("type", "parameters")} for r in rules]


class Plan:
    def __init__(self) -> None:
        self.notes: list[str] = []
        self.findings: list[str] = []
        self.actions: list[dict] = []

    def empty(self) -> bool:
        return not self.actions and not self.findings


def tighten_pull_request(rule: dict, want: dict, tighten: bool, plan: Plan, name: str) -> bool:
    """Report (or with --tighten fix) a pull_request rule looser than the kit's; True if changed."""
    params = rule.setdefault("parameters", {})
    changed = False
    if not params.get("dismiss_stale_reviews_on_push"):
        plan.findings.append(
            f"ruleset '{name}': stale approvals are not dismissed on push (fix: --tighten)"
        )
        if tighten:
            params["dismiss_stale_reviews_on_push"] = True
            changed = True
    if params.get("allowed_merge_methods") != ["squash"]:
        plan.findings.append(
            f"ruleset '{name}': merge methods other than squash are allowed (fix: --tighten)"
        )
        if tighten:
            params["allowed_merge_methods"] = ["squash"]
            changed = True
    return changed


def plan_for(
    repo: str, branch: str, repo_data: dict, details: list[dict], phase: int, tighten: bool
) -> Plan:
    want = desired()
    plan = Plan()
    matching = sorted(
        (d for d in details if d.get("target") == "branch" and targets_default(d, branch)),
        key=lambda d: (d.get("enforcement") != "active", d.get("id", 0)),
    )
    active = [d for d in matching if d.get("enforcement") == "active"]
    phase2_rules = want["phase2_rules"] if phase == 2 else []
    if not matching:
        payload = copy.deepcopy(want["ruleset"])
        payload["rules"] += copy.deepcopy(phase2_rules)
        plan.actions.append(
            {
                "why": "create the ruleset (none targets the default branch)",
                "method": "POST",
                "endpoint": f"repos/{repo}/rulesets",
                "payload": payload,
            }
        )
    else:
        first = matching[0]
        for d in matching:
            payload = {
                k: copy.deepcopy(d.get(k))
                for k in ("name", "target", "enforcement", "bypass_actors", "conditions")
            }
            payload["bypass_actors"] = payload["bypass_actors"] or []
            payload["rules"] = clean(copy.deepcopy(d.get("rules") or []))
            reasons: list[str] = []
            name = d.get("name", "")
            if d.get("enforcement") != "active":
                plan.findings.append(
                    f"ruleset '{name}': enforcement is not active (fix: --tighten)"
                )
                if tighten:
                    payload["enforcement"] = "active"
                    reasons.append("set enforcement to active")
            if d.get("bypass_actors"):
                plan.findings.append(f"ruleset '{name}': it has bypass actors (fix: --tighten)")
                if tighten:
                    payload["bypass_actors"] = []
                    reasons.append("remove the bypass actors")
            for rule in payload["rules"]:
                if rule["type"] == "pull_request" and tighten_pull_request(
                    rule, want, tighten, plan, name
                ):
                    reasons.append("tighten the pull request rule")
            if d is first:
                present = {r["type"] for r in payload["rules"]}
                union = {r.get("type") for x in active or [d] for r in x.get("rules") or []}
                for kind in SIMPLE:
                    if kind not in union and kind not in present:
                        payload["rules"].append({"type": kind})
                        reasons.append(f"add the {kind} rule")
                if "pull_request" not in union:
                    pr = [r for r in want["ruleset"]["rules"] if r["type"] == "pull_request"][0]
                    payload["rules"].append(copy.deepcopy(pr))
                    reasons.append("add the pull_request rule")
                if phase2_rules:
                    checks = [
                        r
                        for x in (active or [d])
                        for r in x.get("rules") or []
                        if r.get("type") == "required_status_checks"
                    ]
                    contexts = {
                        c.get("context")
                        for r in checks
                        for c in (r.get("parameters") or {}).get("required_status_checks") or []
                    }
                    if not checks:
                        payload["rules"] += copy.deepcopy(phase2_rules)
                        reasons.append(f"add the required status check {CONTEXT}")
                    elif CONTEXT not in contexts:
                        for rule in payload["rules"]:
                            if rule["type"] == "required_status_checks":
                                rule.setdefault("parameters", {}).setdefault(
                                    "required_status_checks", []
                                ).append({"context": CONTEXT})
                                reasons.append(f"add {CONTEXT} to the required status checks")
                                break
            if reasons:
                plan.actions.append(
                    {
                        "why": f"ruleset '{name}': " + "; ".join(reasons),
                        "method": "PUT",
                        "endpoint": f"repos/{repo}/rulesets/{d.get('id')}",
                        "payload": payload,
                    }
                )
    patch = {k: v for k, v in want["repository_settings"].items() if repo_data.get(k) is not True}
    if patch:
        plan.actions.append(
            {
                "why": "set the repository settings: " + ", ".join(sorted(patch)),
                "method": "PATCH",
                "endpoint": f"repos/{repo}",
                "payload": patch,
            }
        )
    return plan


def read_repo(reads: Reads) -> dict:
    repo_data, reason = reads.get("repo", "")
    if not isinstance(repo_data, dict):
        raise cannot(reason or "bad-response")
    if (repo_data.get("permissions") or {}).get("admin") is not True:
        raise cannot("no-admin", repo_data.get("default_branch") or "main")
    return repo_data


def read_rest(reads: Reads, branch: str, repo_data: dict) -> tuple[list[dict], bool | None]:
    listing, reason = reads.get("rulesets", "/rulesets")
    if not isinstance(listing, list):
        raise cannot(admin_reason(reason or "bad-response", repo_data), branch)
    details = []
    for entry in sorted(listing, key=lambda e: str(e.get("id"))):
        if entry.get("target") != "branch":
            continue
        data, reason = reads.get(f"ruleset-{entry.get('id')}", f"/rulesets/{entry.get('id')}")
        if not isinstance(data, dict):
            raise cannot(admin_reason(reason or "bad-response", repo_data), branch)
        details.append(data)
    return details, governance_ran(reads, branch)


def governance_ran(reads: Reads, branch: str) -> bool | None:
    path = f"/actions/workflows/governance.yml/runs?branch={branch}&status=success&per_page=1"
    runs, _ = reads.get("governance-runs", path)
    return None if not isinstance(runs, dict) else int(runs.get("total_count") or 0) >= 1


def choose_phase(given: str, ran: bool | None) -> tuple[int, str]:
    if given != "auto":
        return int(given), "given"
    if ran:
        return 2, "auto: governance has succeeded on the default branch"
    if ran is False:
        return 1, "auto: governance has not succeeded on the default branch"
    return 1, "auto: the runs of governance could not be read"


def render(
    plan: Plan, repo: str, branch: str, phase: int, how: str, payload_dir: Path | None
) -> str:
    lines = [f"repo: {repo} (default branch {branch}); phase {phase} ({how})"]
    lines += [f"finding: {f}" for f in plan.findings]
    if plan.empty():
        lines.append("nothing to do")
    for n, action in enumerate(plan.actions, 1):
        file = f"payload-{n}.json"
        shown = str(payload_dir / file) if payload_dir else f"<payload-{n}.json>"
        lines.append(f"{n}. {action['why']}")
        lines.append(f"   gh api --method {action['method']} {action['endpoint']} --input {shown}")
        if payload_dir is None:
            lines.append("   payload: " + json.dumps(action["payload"], sort_keys=True))
    if plan.actions:
        lines.append("Nothing was sent. Run the commands only after you agree to the plan.")
    return "\n".join(lines) + "\n"


def parse(args: list[str]) -> dict[str, Any]:
    if not args or args[0] != "plan":
        raise ValueError("command")
    opts: dict[str, Any] = {"phase": "auto", "tighten": False}
    it = iter(args[1:])
    for arg in it:
        if arg == "--tighten":
            opts["tighten"] = True
        elif arg in ("--phase", "--repo", "--api-dir", "--payload-dir", "--root"):
            value = next(it, None)
            if value is None:
                raise ValueError("value")
            opts[arg[2:].replace("-", "_")] = value
        else:
            raise ValueError("option")
    if opts["phase"] not in ("1", "2", "auto"):
        raise ValueError("phase")
    return opts


def main(argv: list[str] | None = None) -> int:
    try:
        opts = parse(list(sys.argv[1:] if argv is None else argv))
    except ValueError:
        print(USAGE, file=sys.stderr)
        return 2
    try:
        root = Path(opts.get("root", "."))
        repo = opts.get("repo") or origin_repo(root)
        if not repo or not REPO_RE.match(repo):
            raise Stop("repository unknown; pass --repo OWNER/REPO (path class: git remote)", 2)
        api_dir = Path(opts["api_dir"]) if opts.get("api_dir") else None
        reads = Reads(repo, api_dir)
        try:
            repo_data = read_repo(reads)
            branch = repo_data.get("default_branch") or "main"
            details, ran = read_rest(reads, branch, repo_data)
        except Cannot as exc:
            # the phase the plan would choose; without a repository read the runs are not read
            auto = opts["phase"] == "auto" and exc.branch
            ran = governance_ran(reads, exc.branch) if auto else None
            raise cannot_text(exc.reason, *choose_phase(opts["phase"], ran)) from None
        phase, how = choose_phase(opts["phase"], ran)
        plan = plan_for(repo, branch, repo_data, details, phase, opts["tighten"])
        payload_dir = Path(opts["payload_dir"]) if opts.get("payload_dir") else None
        if payload_dir is not None:
            payload_dir.mkdir(parents=True, exist_ok=True)
            for n, action in enumerate(plan.actions, 1):
                (payload_dir / f"payload-{n}.json").write_text(
                    json.dumps(action["payload"], indent=2, sort_keys=True) + "\n", encoding="utf-8"
                )
        sys.stdout.write(render(plan, repo, branch, phase, how, payload_dir))
        return 0
    except Stop as exc:
        print(str(exc))
        return exc.code


if __name__ == "__main__":
    sys.exit(main())
