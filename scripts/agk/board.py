"""Make the plan's GitHub Project board and add every brief to it (brief #1190, ADR-0506), copied
from the owner's template board and carrying the business fields (brief #1195, ADR-0507).

    python3 scripts/agk/board.py [--title TEXT] [--owner LOGIN] [--project N] [--yes]
                                 [--template OWNER/NUMBER] [--repo OWNER/REPO]

The owner's command `/agk:board`, run from the repository root with the owner's own `gh` (the
`project` scope), on Windows, macOS or Linux. GitHub Projects are reachable only through GraphQL,
which cloud sessions refuse, so it uses `gh project` subcommands and writes no GraphQL itself; the
open `agk-brief` issues are read with one REST call.

Without `--yes` it prints each step it would take and calls nothing that writes. With `--yes` and
no board (`--project N`, else `[plan] board` of agk.toml) it creates a Project titled
`<repository> plan` under the repository's owner and prints the `board = <n>` line for the person
to commit; it never edits agk.toml. With a template (`--template OWNER/NUMBER`, else
`[plan] board_template`) that first run copies the template Project with `gh project copy`, its
views, fields and columns, instead of creating an empty one; without one it prints the one line
naming the three views to make once in GitHub's screen. Every `--yes` run links the Project to the
repository, adds the fields `Size` (single select S, M, L), `Expected hours` (number), `Persona`,
`Requirement`, `Screens` (text) and `Sign-off` (single select Pending, Signed off, Changes asked)
when missing, and adds each open brief issue not yet on the board with its `Size`, the high end of
its `Expected:` range, its `Persona:`, `Advances:` and `Screens:` lines and `Sign-off` Pending. An
item already on the board is never edited, except that a business field this run added to the board
is filled on it once, and nothing is removed.

Exit 0 when done, after a dry run, in personal mode and when GraphQL is refused (a cloud session);
1 when a `gh` command failed (it is printed); 2 when the `project` scope is missing or for a usage
error.
"""

from __future__ import annotations

import argparse
import json
import re
import shlex
import shutil
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import (  # noqa: E402
    BOARD_TEMPLATE,
    CheckError,
    estimate_parts,
    git,
    personal_table,
    plan_settings,
)

BRIEF_LABEL = "agk-brief"
SIZES = ("S", "M", "L")
SIZE_FIELD = "Size"
HOURS_FIELD = "Expected hours"
PERSONA_FIELD = "Persona"
REQUIREMENT_FIELD = "Requirement"
SCREENS_FIELD = "Screens"
SIGNOFF_FIELD = "Sign-off"
SIGNOFF = ("Pending", "Signed off", "Changes asked")
PENDING = SIGNOFF[0]
TEXT_LINES = {  # brief #1195 answer 2: each text field from the issue's own line
    PERSONA_FIELD: re.compile(r"^Persona: (\S.*?)\s*$", re.MULTILINE),
    REQUIREMENT_FIELD: re.compile(r"^Advances: (\S.*?)\s*$", re.MULTILINE),
    SCREENS_FIELD: re.compile(r"^Screens: (\S.*?)\s*$", re.MULTILINE),
}
BUSINESS = (*TEXT_LINES, SIGNOFF_FIELD)
FIELD_KINDS = {
    SIZE_FIELD: (
        "single select S, M, L",
        ["--data-type", "SINGLE_SELECT", "--single-select-options", ",".join(SIZES)],
    ),
    HOURS_FIELD: ("number", ["--data-type", "NUMBER"]),
    **{name: ("text", ["--data-type", "TEXT"]) for name in TEXT_LINES},
    SIGNOFF_FIELD: (
        "single select " + ", ".join(SIGNOFF),
        ["--data-type", "SINGLE_SELECT", "--single-select-options", ",".join(SIGNOFF)],
    ),
}
VIEWS = (
    "make the three views once in GitHub's screen: Sign-off (a board by Status), Questions"
    " (a table), Roadmap (by Milestone); or copy a template board with --template OWNER/NUMBER"
)
BAD_TEMPLATE = "board: the template is <owner>/<number> of a template board (option: --template)"
LIMIT = "1000"
ORIGIN = re.compile(r"github\.com[:/]([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+?)(?:\.git)?/?$")
SCOPE = re.compile(r"missing required scopes?|auth refresh -s [a-z:,]*project", re.IGNORECASE)
GRAPHQL_REFUSED = re.compile(r"GraphQL is not available|unknown owner type", re.IGNORECASE)
NEEDS_MACHINE = (
    "board: needs a machine with your own gh (cloud sessions cannot reach GitHub Projects)"
)
PERSONAL = "board: needs the GitHub forge (personal mode has no GitHub issues); nothing was done"
REFRESH = "board: the gh token lacks the project scope; run: gh auth refresh -s project"


class GhFailed(Exception):
    """A `gh` command failed; `code` is the exit code the command ends with."""

    def __init__(self, message: str, code: int) -> None:
        super().__init__(message)
        self.code = code


def gh(*args: str) -> Any:
    """Run `gh` with a fixed argument list and return its JSON answer (None when empty)."""
    exe = shutil.which("gh")
    if exe is None:
        raise GhFailed("board: gh is not installed", 1)
    proc = subprocess.run(  # nosec B603 - fixed argument list, no shell
        [exe, *args], capture_output=True, text=True, check=False, encoding="utf-8"
    )
    if proc.returncode != 0:
        said = f"{proc.stderr}\n{proc.stdout}"
        if GRAPHQL_REFUSED.search(said):
            raise GhFailed(NEEDS_MACHINE, 0)
        if SCOPE.search(said):
            raise GhFailed(REFRESH, 2)
        raise GhFailed(f"failed: {shlex.join(['gh', *args])}", 1)
    text = proc.stdout.strip()
    try:
        return json.loads(text) if text else None
    except json.JSONDecodeError:
        raise GhFailed(f"failed: {shlex.join(['gh', *args])} (its answer is not JSON)", 1) from None


def estimate(body: object) -> tuple[str | None, float | None]:
    """(size, high end of the hours) from a brief's own `Size:` and `Expected:` lines."""
    size, expected = estimate_parts(body)
    hours = float(expected.split("-")[1].split()[0]) if expected != "unknown" else None
    return (size if size in SIZES else None), hours


def business(body: object) -> list[tuple[str, str]]:
    """(field, value) for Persona, Requirement and Screens from the issue's own lines, then
    Sign-off Pending (brief #1195 answer 2)."""
    text = body if isinstance(body, str) else ""
    found = [(name, m[1]) for name, line in TEXT_LINES.items() if (m := line.search(text))]
    return [*found, (SIGNOFF_FIELD, PENDING)]


def hours_text(hours: float) -> str:
    return f"{hours:g}"


def repo_name(root: Path, given: str | None) -> str:
    if given:
        return given
    match = ORIGIN.search(git(root, "remote", "get-url", "origin", check=False).strip())
    if not match:
        raise CheckError("board: the remote origin is not a GitHub repository (setting: origin)")
    return match.group(1)


def brief_issues(repo: str) -> list[dict]:
    """The open issues labelled `agk-brief`, oldest first; pull requests left out (REST)."""
    found = gh(
        "api", "--paginate", f"repos/{repo}/issues?state=open&labels={BRIEF_LABEL}&per_page=100"
    )
    issues = [i for i in found or [] if isinstance(i, dict) and "pull_request" not in i]
    return sorted(issues, key=lambda i: int(i["number"]))


def on_board(items: list[dict], repo: str) -> set[int]:
    seen = set()
    for item in items:
        content = item.get("content") or {}
        url = str(content.get("url") or "")
        number = content.get("number")
        if url.startswith(f"https://github.com/{repo}/issues/"):
            seen.add(int(url.rsplit("/", 1)[1]))
        elif isinstance(number, int) and content.get("repository") == repo:
            seen.add(number)
    return seen


def plan_lines(issue: dict) -> tuple[str, list[str]]:
    size, hours = estimate(issue.get("body"))
    parts = [f"Size {size}"] if size else []
    parts += [f"{HOURS_FIELD} {hours_text(hours)}"] if hours is not None else []
    parts += [f"{name} {value}" for name, value in business(issue.get("body"))]
    notes = [] if size else [f"note: #{issue['number']} has no Size line"]
    notes += [] if hours is not None else [f"note: #{issue['number']} has no Expected line"]
    return ", ".join(parts), notes


def split_template(template: str) -> tuple[str, int]:
    owner, number = template.split("/")
    return owner, int(number)


def dry_run(repo: str, owner: str, title: str, project: int | None, template: str | None) -> int:
    present: set[int] = set()
    names: set[str] = set()
    if project is None and template:
        source_owner, number = split_template(template)
        names = {str(f.get("name")) for f in fields_of(number, source_owner)}
        print(f"would copy project {template} as '{title}' under {owner}")
    elif project is None:
        print(f"would create project '{title}' under {owner}")
        print(VIEWS)
    else:
        names = {str(f.get("name")) for f in fields_of(project, owner)}
        items = items_of(project, owner)
        present = on_board(items, repo)
    print(f"would link the project to {repo}")
    missing = [name for name in FIELD_KINDS if name not in names]
    for name in missing:
        print(f"would add field {name} ({FIELD_KINDS[name][0]})")
    issues = brief_issues(repo)
    todo = [i for i in issues if int(i["number"]) not in present]
    for i in todo:
        values, notes = plan_lines(i)
        print(f"would add #{i['number']}" + (f" {values}" if values else ""))
        for note in notes:
            print(note)
    for i in issues if [n for n in missing if n in BUSINESS] else []:
        if int(i["number"]) in present:
            fill = [f"{n} {v}" for n, v in business(i.get("body")) if n in missing]
            print(f"would fill #{i['number']} {', '.join(fill)}")
    print(
        f"ok board: {len(todo)} to add, {len(issues) - len(todo)} already there;"
        " dry run, nothing changed (run again with --yes)"
    )
    return 0


def fields_of(project: int, owner: str) -> list[dict]:
    found = gh(
        "project",
        "field-list",
        str(project),
        "--owner",
        owner,
        "--format",
        "json",
        "--limit",
        "100",
    )
    return list((found or {}).get("fields") or [])


def items_of(project: int, owner: str) -> list[dict]:
    found = gh(
        "project", "item-list", str(project), "--owner", owner, "--format", "json", "--limit", LIMIT
    )
    return list((found or {}).get("items") or [])


def ensure_fields(project: int, owner: str) -> tuple[dict[str, dict], list[str]]:
    """The board's fields by name, each of FIELD_KINDS added when missing, and the names added."""
    fields: dict[str, dict] = {str(f.get("name")): f for f in fields_of(project, owner)}
    added: list[str] = []
    for name, (_, kind) in FIELD_KINDS.items():
        if name not in fields:
            made = gh(
                "project",
                "field-create",
                str(project),
                "--owner",
                owner,
                "--name",
                name,
                *kind,
                "--format",
                "json",
            )
            print(f"added field {name}")
            fields[name] = made or {}
            added.append(name)
    return fields, added


def set_option(edit: list[str], field: dict, name: str, option: str, n: int) -> None:
    found = next((o for o in field.get("options") or [] if o.get("name") == option), None)
    if found is None:
        print(f"note: the {name} field has no option {option}")
        return
    gh(*edit, "--field-id", str(field["id"]), "--single-select-option-id", str(found["id"]))
    print(f"set #{n} {name} {option}")


def set_business(edit: list[str], fields: dict[str, dict], issue: dict, only: set[str]) -> None:
    """Brief #1195 answer 2: Persona, Requirement and Screens as text, Sign-off Pending."""
    n = int(issue["number"])
    for name, value in business(issue.get("body")):
        if name not in only:
            continue
        if name == SIGNOFF_FIELD:
            set_option(edit, fields[name], name, value, n)
        else:
            gh(*edit, "--field-id", str(fields[name]["id"]), "--text", value)
            print(f"set #{n} {name} {value}")


def make_board(owner: str, title: str, template: str | None) -> int:
    """The first run: copy the template board, else create an empty one and name the views."""
    if template:
        source_owner, number = split_template(template)
        made = gh(
            "project",
            "copy",
            str(number),
            "--source-owner",
            source_owner,
            "--target-owner",
            owner,
            "--title",
            title,
            "--format",
            "json",
        )
        project = int((made or {})["number"])
        print(f"copied project {template} as {project} '{title}' under {owner}")
    else:
        made = gh("project", "create", "--owner", owner, "--title", title, "--format", "json")
        project = int((made or {})["number"])
        print(f"created project {project} '{title}' under {owner}")
        print(VIEWS)
    print(f"add to agk.toml under [plan], and commit: board = {project}")
    return project


def apply(repo: str, owner: str, title: str, project: int | None, template: str | None) -> int:
    if project is None:
        project = make_board(owner, title, template)
    view = gh("project", "view", str(project), "--owner", owner, "--format", "json")
    project_id = str((view or {})["id"])
    gh("project", "link", str(project), "--owner", owner, "--repo", repo)
    fields, new_fields = ensure_fields(project, owner)
    items = items_of(project, owner)
    present = on_board(items, repo)
    issues = brief_issues(repo)
    filled = set(new_fields) & set(BUSINESS)
    if filled:  # an older board gained business fields: fill them once on its items
        by_number = {
            int(str((i.get("content") or {}).get("url") or "").rsplit("/", 1)[1]): str(i["id"])
            for i in items
            if str((i.get("content") or {}).get("url") or "").startswith(
                f"https://github.com/{repo}/issues/"
            )
        }
        for i in issues:
            n = int(i["number"])
            if n in by_number:
                edit = ["project", "item-edit", "--id", by_number[n], "--project-id", project_id]
                set_business(edit, fields, i, filled)
    added = 0
    for i in issues:
        n = int(i["number"])
        if n in present:
            continue
        item = gh(
            "project",
            "item-add",
            str(project),
            "--owner",
            owner,
            "--url",
            str(i["html_url"]),
            "--format",
            "json",
        )
        added += 1
        print(f"added #{n}")
        size, hours = estimate(i.get("body"))
        _, notes = plan_lines(i)
        item_id = str((item or {})["id"])
        edit = ["project", "item-edit", "--id", item_id, "--project-id", project_id]
        if size:
            set_option(edit, fields[SIZE_FIELD], SIZE_FIELD, size, n)
        if hours is not None:
            gh(*edit, "--field-id", str(fields[HOURS_FIELD]["id"]), "--number", hours_text(hours))
            print(f"set #{n} {HOURS_FIELD} {hours_text(hours)}")
        set_business(edit, fields, i, set(BUSINESS))
        for note in notes:
            print(note)
    print(f"ok board: {added} added, {len(issues) - added} already there")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--title", help="the Project's title (default: '<repository> plan')")
    parser.add_argument("--owner", help="the Project's owner (default: the repository's owner)")
    parser.add_argument("--project", type=int, help="the Project number (default: [plan] board)")
    parser.add_argument("--yes", action="store_true", help="make the changes; without it a dry run")
    parser.add_argument(
        "--template", help="OWNER/NUMBER of the template board (default: [plan] board_template)"
    )
    parser.add_argument("--repo", help="OWNER/REPO (default: the remote origin)")
    args = parser.parse_args(argv)
    root = Path.cwd()
    try:
        if personal_table(root) is not None:
            print(PERSONAL)
            return 0
        repo = repo_name(root, args.repo)
        settings = plan_settings(root)
        project = args.project if args.project is not None else settings.get("board")
        template = args.template or settings.get("board_template")
    except CheckError as exc:
        print(exc)
        return 2
    if template is not None and not BOARD_TEMPLATE.fullmatch(template):
        print(BAD_TEMPLATE)
        return 2
    if project is not None and project < 1:
        print("board: the project number must be a positive whole number (option: --project)")
        return 2
    owner = args.owner or repo.split("/")[0]
    title = args.title or f"{repo.split('/')[1]} plan"
    try:
        if not args.yes:
            return dry_run(repo, owner, title, project, template)
        return apply(repo, owner, title, project, template)
    except GhFailed as exc:
        print(exc)
        return exc.code
    except (KeyError, TypeError, ValueError):
        print("failed: a gh answer lacked a number or an id it needs; run the command again")
        return 1


if __name__ == "__main__":
    sys.exit(main())
