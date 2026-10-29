"""agk pr_body: the pull request body that a kit command prints, checked before it is printed.

Kit-only (never installed). Brief #273: every command whose work ends in a pull request
(`playbook.py next-steps`, `intake.py next-steps`, `engines.py stack-next-steps` and
`design-next-steps`, `upgrade.py TARGET --next-steps`) builds its body here. The body is written to
a file in the repository's git directory (never a tracked file) and checked with the repository's
own `scripts/agk/check_pr_body.py` (the kit's when the repository has none), in the repository's
state as the command was given it: `--brief N` (the brief the work answers), `--brief none` (the
person says the repository has no open brief) or `--issues FILE` (a saved copy of its open briefs,
as the governance workflow saves it). A change of `docs/design/`, or of `docs/specs/` and
`docs/requirements.md`, with at most an ADR, the amendments file and the decisions log beside it,
carries `Brief: none (design)` or `Brief: none (spec)` (`check_pr_body.NONE_FORMS`), which passes
in either state. Without any of these the state is not known and the body is checked as if a brief
were open. The `Summary:` line is cut to fit at a word boundary. A body that still fails is never
printed: the command refuses with the check's own lines, which name the rule and never a value. No
network.
"""

from __future__ import annotations

import json
import os
import re
import subprocess  # nosec B404 - a fixed argument list, no shell
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # isolated mode (-I) leaves it off

from check_pr_body import NONE_FORMS, SUMMARY_MAX, has_brief, none_form_fits
from common import CheckError, git

KIT_CHECK = Path(__file__).resolve().parent / "check_pr_body.py"
REPO_CHECK = "scripts/agk/check_pr_body.py"
BRIEF_ARG = re.compile(r"^(?:#?(\d+)|none)$")
UNKNOWN = [{"number": 0, "labels": [{"name": "agk-brief"}]}]  # the state assumed when not given


def fit_summary(text: str, limit: int = SUMMARY_MAX) -> str:
    """The sentence, cut at the last word boundary that fits in `limit` characters."""
    text = " ".join(text.split())
    if len(text) <= limit:
        return text
    cut = text[: limit + 1].rfind(" ")
    short = text[:cut] if cut > 0 else text[:limit]
    return short.rstrip(" ,;:-—")


def brief_option(value: str | None) -> str | None:
    """`--brief N` as `#N`, `--brief none` as `none`, absent as None; anything else refuses."""
    if value is None:
        return None
    match = BRIEF_ARG.match(value.strip())
    if not match:
        raise CheckError("the brief is a number or `none` (option --brief)")
    return f"#{match.group(1)}" if match.group(1) else "none"


def open_briefs(path: str | None) -> bool | None:
    """Whether the saved copy lists an open brief; None when no copy was given."""
    if path is None:
        return None
    try:
        json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        raise CheckError(
            "the saved copy of the open briefs cannot be read (option --issues)"
        ) from None
    return has_brief(path)


def brief_line(brief: str | None, issues: str | None, changed: dict[str, str] | None) -> str | None:
    """The `Brief:` value of the body, or None for no line; refuses when it cannot be known."""
    if brief and brief.startswith("#"):
        return brief
    form = next((f for f in NONE_FORMS if changed is not None and none_form_fits(f, changed)), None)
    if form:
        return form
    if brief == "none" or open_briefs(issues) is False:
        return None
    raise CheckError(
        "rule 9: the repository has an open brief, or whether it has one is not known; pass the "
        "brief the work answers, or `none` when it has no open brief (option --brief)"
    )


def body_dir(root: Path) -> Path:
    dot_git = root / ".git"
    if dot_git.is_dir():
        return dot_git / "agk"
    return Path(git(root, "rev-parse", "--absolute-git-dir").strip()) / "agk"


def check_body(root: Path, path: Path, issues: str | None, base: str | None) -> tuple[bool, str]:
    """Run the repository's own body check (the kit's when it has none) on the file."""
    repo_check = root / REPO_CHECK
    script = repo_check if repo_check.is_file() else KIT_CHECK
    if issues is None:
        unknown = path.with_name("briefs-unknown.json")
        unknown.write_text(json.dumps(UNKNOWN), encoding="utf-8")
        issues = str(unknown)
    env = {k: v for k, v in os.environ.items() if k not in ("GITHUB_BASE_REF", "AGK_BASE", "CI")}
    if base:
        env["AGK_BASE"] = base
    proc = subprocess.run(  # nosec B603 - a fixed argument list, no shell
        [sys.executable, "-I", str(script), "--issues", str(Path(issues).resolve()), str(path)],
        cwd=root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=env,
    )
    return proc.returncode == 0, proc.stdout


def prepare(
    root: Path,
    fields: list[tuple[str, str]],
    *,
    brief: str | None,
    issues: str | None,
    changed: dict[str, str] | None,
    base: str | None = None,
) -> tuple[Path, str]:
    """Build, write and check the body; raise CheckError when it does not pass."""
    root = root.resolve()
    lines = []
    value = brief_line(brief, issues, changed)
    if value:
        lines.append(f"Brief: {value}")
    for label, text in fields:
        lines.append(f"{label}: {fit_summary(text) if label == 'Summary' else text}")
    text = "\n".join(lines) + "\n"
    folder = body_dir(root)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / "pr-body.md"
    path.write_text(text, encoding="utf-8")
    if issues is None and brief == "none":  # the person's word: the repository has no open brief
        stated = folder / "briefs-none.json"
        stated.write_text("[]", encoding="utf-8")
        issues = str(stated)
    ok, out = check_body(root, path, issues, base)
    if not ok:
        failures = [ln for ln in out.splitlines() if ln.startswith("FAIL ")]
        raise CheckError(
            "the pull request body does not pass the repository's body check; no body is "
            "printed:\n" + "\n".join(failures or ["(the check printed no FAIL line)"])
        )
    return path, text


def print_body(path: Path, text: str) -> None:
    print(f"Pull request body file: {path}\n")
    print("Pull request body:\n")
    print(text)
