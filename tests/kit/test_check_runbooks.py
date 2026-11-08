"""Tests of `check_runbooks.py` (SPEC-0056 rules 4 to 7, build (a); REQ-063 AC2, AC3 and AC4).

A runbook page holds the form of rule 4, every command it gives exists (rule 6) and none can print
a value (rule 7). A refusal names the page and the rule and never the text. Fixtures in `tmp_path`
only: invented data (`example.com`), no network, and no test runs a command a page names.
"""

from __future__ import annotations

import ast
import json
import re
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
import tomllib
from pathlib import Path

import pytest

KIT_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = KIT_ROOT / "scripts" / "agk" / "check_runbooks.py"
PAGE = "docs/runbooks/red-default-branch.md"
OTHERS = ("docs/runbooks/actions-blocked.md", "docs/runbooks/leaked-secret.md")
MARK = "Zanzibar"  # invented text of every section: it must never reach the output

GOOD = f"""# {MARK} page

## When this applies

{MARK} signs at example.com.

## Who acts

A person, {MARK}.

## Steps

1. Read {MARK}.

   ```
   python3 scripts/agk/tool.py serve --port <n> --name=<who>
   make lint
   date -u
   ```

2. Look.

   ```
   git status
   gh issue list
   gitleaks detect --redact
   ```

3. Open [the guide](../guides/guide.md#part), or [the site](https://example.com/x).

## Over when

{MARK} is closed.

## By mode

- GitHub: {MARK}.
- Local: {MARK}.
- Personal: {MARK}.
"""


def write(root: Path, rel: str, text: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def check(root: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, "-I", str(SCRIPT), "--root", str(root)], capture_output=True, text=True
    )


@pytest.fixture
def tree(tmp_path: Path) -> Path:
    """A tree whose three kit pages pass, with one script of each kind, a target and a guide."""
    for rel in (PAGE, *OTHERS):
        write(tmp_path, rel, GOOD)
    # A run of either command would leave `ran`: the check must only read them.
    effect = "open('ran', 'w').close()  # serve --port --name\n"
    write(tmp_path, "scripts/agk/tool.py", effect)
    write(tmp_path, "scripts/agk/kitonly.py", effect)
    write(tmp_path, "Makefile", "X := 1\n.PHONY: ghost\nlint:\n\ttouch ran\n")
    write(tmp_path, "agk.mk", "agk-x agk-y:\n\ttouch ran\n")
    write(tmp_path, "docs/guides/guide.md", "invented\n")
    manifest = {"verbatim": ["scripts/agk/tool.py"], "templates": {"agk.toml": "kit/t"}}
    write(tmp_path, "kit/manifest.json", json.dumps(manifest))
    return tmp_path


def refused(root: Path, text: str, rule: int, leak: str = MARK) -> None:
    """The page is refused under `rule`, one line naming the page, and `leak` is not printed."""
    write(root, PAGE, text)
    proc = check(root)
    assert proc.returncode == 1, proc.stdout
    lines = proc.stdout.splitlines()
    assert lines and all(ln.startswith(f"FAIL runbooks: {PAGE} rule ") for ln in lines), lines
    assert any(ln.startswith(f"FAIL runbooks: {PAGE} rule {rule}") for ln in lines), lines
    assert leak not in proc.stdout and leak not in proc.stderr


def with_command(line: str) -> str:
    return GOOD.replace("   date -u\n", f"   {line}\n")


def test_ac2_a_good_page_passes_and_nothing_is_run(tree: Path) -> None:
    """REQ-063 AC2: rule 5, `ok runbooks`; REQ-063 AC3: rule 6, a command is read and never run."""
    proc = check(tree)
    assert (proc.returncode, proc.stdout) == (0, "ok runbooks\n"), proc.stdout
    assert not (tree / "ran").exists()


def test_ac2_no_folder_is_skipped(tmp_path: Path) -> None:
    """REQ-063 AC2: rule 5, the kit between builds (a) and (b)."""
    proc = check(tmp_path)
    assert (proc.returncode, proc.stdout) == (0, "skipped (no runbooks)\n")


@pytest.mark.parametrize("rel", [PAGE, *OTHERS])
def test_ac2_a_kit_page_absent_fails_naming_it(tree: Path, rel: str) -> None:
    """REQ-063 AC2: rule 5, with the folder a missing kit page fails (Q-S0056-4)."""
    (tree / rel).unlink()
    proc = check(tree)
    assert proc.returncode == 1 and proc.stdout.startswith(f"FAIL runbooks: {rel} rule 5")


def test_ac2_a_projects_own_page_is_read(tree: Path) -> None:
    """REQ-063 AC2: rule 2, the check reads a page a project adds."""
    write(tree, "docs/runbooks/own.md", GOOD.replace("## Who acts", "## Who"))
    assert check(tree).stdout.startswith("FAIL runbooks: docs/runbooks/own.md rule 4")


def test_ac2_each_problem_is_one_line(tree: Path) -> None:
    """REQ-063 AC2: rule 5, one line per problem."""
    write(tree, PAGE, GOOD.replace("## Who acts\n", "").replace("- Local: ", "Local: "))
    assert len(check(tree).stdout.splitlines()) == 2


@pytest.mark.parametrize(
    "old, new",
    [
        ("## Who acts\n\nA person", "A person"),  # a section missing
        ("## Over when", "## Finished"),  # a section not of the form
        ("## Over when", "## Who acts"),  # a section twice
        (f"# {MARK} page\n", f"{MARK}\n"),  # no title
        (f"# {MARK} page\n", f"# {MARK} page\n\n# {MARK} again\n"),  # two titles
        (f"# {MARK} page\n", f"# {MARK} page\n\n{MARK} before the sections.\n"),
        (f"A person, {MARK}.\n", ""),  # an empty section
        ("2. Look.", "- Look."),  # not numbered
        ("1. Read", "2. Read"),  # not from 1
        ("3. Open", "4. Open"),  # not in order
        ("2. Look.", f"{MARK}\n\n2. Look."),  # text between the steps
        ("2. Look.", "   1. Nested.\n\n2. Look."),  # a second numbered list inside
        ("- Local: ", "Local: "),  # a mode bullet missing
        ("- Local: ", "- GitHub: "),  # a mode bullet twice
        ("- Local: ", "- Local: x\n- Remote: "),  # a bullet of no mode
    ],
)
def test_ac2_the_form_is_refused(tree: Path, old: str, new: str) -> None:
    """REQ-063 AC2: rules 4 and 5, naming the page and the rule, with no page text."""
    assert old in GOOD
    refused(tree, GOOD.replace(old, new, 1), 4)


def test_ac2_sections_out_of_order_are_refused(tree: Path) -> None:
    """REQ-063 AC2: rule 4, the order of the sections."""
    swapped = GOOD.replace("## Who acts", "## TEMP").replace("## When this applies", "## Who acts")
    refused(tree, swapped.replace("## TEMP", "## When this applies"), 4)


def test_ac2_the_title_comes_first(tree: Path) -> None:
    """REQ-063 AC2: rule 4, one title, then the sections."""
    moved = GOOD.replace(f"# {MARK} page\n\n", "", 1)
    refused(tree, moved.replace("## Over when", f"# {MARK} page\n\n## Over when", 1), 4)


def test_ac2_the_limits(tree: Path) -> None:
    """REQ-063 AC2: rule 4, at most 60 lines and 500 words, each limit on its own."""
    lines = len(GOOD.splitlines())
    write(tree, PAGE, GOOD + "\n" * (60 - lines))
    assert check(tree).returncode == 0
    refused(tree, GOOD + "\n" * (61 - lines), 4)
    words = len(GOOD.split())
    filler = GOOD.replace("is closed.", "is closed. " + "word " * (500 - words), 1)
    write(tree, PAGE, filler)
    assert check(tree).returncode == 0
    refused(tree, filler.replace("is closed.", "is closed. word", 1), 4)


@pytest.mark.parametrize(
    "line, leak",
    [
        ("python3 scripts/agk/absent.py", "absent"),  # a missing script
        ("python3 scripts/agk/tool.py nosuchverb", "nosuchverb"),  # an unknown subcommand
        ("python3 scripts/agk/tool.py serv", "serv "),  # part of a word is not the word
        ("python3 scripts/agk/tool.py serve --nosuchflag", "nosuchflag"),
        ("python3 scripts/agk/tool.py serve --por", "--por"),
        ("python3 scripts/agk/kitonly.py", "kitonly"),  # not installed in a project
        ("python3 scripts/agk/../agk/tool.py", "../agk"),  # not the form of a script
        ("python3 -c 'print(1)'", "print"),  # no script to check
        ("make nosuchtarget", "nosuchtarget"),
        ("make ghost", "ghost"),  # only named by .PHONY
        ("make X", " X"),  # a variable is not a target
        ("make", " make"),
        ("curl https://example.com/x", "curl"),  # a program off the list
        ("# a comment of Zanzibar", MARK),
        ("gh secret list", "secret"),  # a verb off the list
        ("git status; git show HEAD", "HEAD"),  # a second command on the line
        ("git status && date", "&&"),
        ("date | gh issue list", "|"),
        ("gh issue list > out.txt", "out.txt"),
        ("date $(git show HEAD)", "HEAD"),
    ],
)
def test_ac3_a_command_is_refused(tree: Path, line: str, leak: str) -> None:
    """REQ-063 AC3: rule 6, naming the page and the rule, never the command."""
    refused(tree, with_command(line), 6, leak)
    assert not (tree / "ran").exists()


@pytest.mark.parametrize(
    "line",
    [
        "make agk-y",
        "make lint agk-x",
        "python3 scripts/agk/tool.py <verb> --port <a long value>",
        "gh api 'repos/o/r/pulls?state=open&per_page=1' --jq '.[] | .number'",
        "gh run list",
        "gh workflow list",
        "gh label list",
    ],
)
def test_ac3_a_real_command_passes(tree: Path, line: str) -> None:
    """REQ-063 AC3: rule 6, placeholders are skipped and a quoted operator is no operator."""
    write(tree, PAGE, with_command(line))
    proc = check(tree)
    assert (proc.returncode, proc.stdout) == (0, "ok runbooks\n"), proc.stdout


def test_ac3_without_a_manifest_any_existing_script_passes(tree: Path) -> None:
    """REQ-063 AC3: rule 6, the kit-only refusal holds only when `kit/manifest.json` is present."""
    (tree / "kit" / "manifest.json").unlink()
    write(tree, PAGE, with_command("python3 scripts/agk/kitonly.py"))
    assert check(tree).returncode == 0


@pytest.mark.parametrize("fence", ["~~~", "````"])
def test_ac3_every_fence_is_read(tree: Path, fence: str) -> None:
    """REQ-063 AC3: rule 6, a command in another form of fence is checked as well."""
    refused(tree, GOOD.replace("```", fence).replace("   date -u\n", "   curl x\n"), 6, "curl")


@pytest.mark.parametrize(
    "span",
    ["`git show HEAD`", "`` make lint ``", "`python3 scripts/agk/tool.py`", "`date`", "`gh`"],
)
def test_ac3_a_command_in_an_inline_span_is_refused(tree: Path, span: str) -> None:
    """REQ-063 AC3: rule 6, so that nothing escapes the check."""
    refused(tree, GOOD.replace("signs at", f"signs {span} at", 1), 6, span.strip("` "))


def test_ac3_an_inline_span_of_no_program_passes_and_a_lone_backtick_hides_nothing(
    tree: Path,
) -> None:
    """REQ-063 AC3: rule 6, a span is paired within its own block."""
    write(tree, PAGE, GOOD.replace("signs at", "signs `github-actions` at", 1))
    assert check(tree).returncode == 0
    lone = GOOD.replace("- GitHub: ", "- GitHub: ` ")
    refused(tree, lone.replace("- Local: ", "- Local: `date` "), 6)


@pytest.mark.parametrize(
    "target",
    ["../guides/absent.md", "../../../outside.md", "../guides", "absent.md#part"],
)
def test_ac3_a_broken_link_is_refused(tree: Path, target: str) -> None:
    """REQ-063 AC3: rule 6, a missing file, one outside the tree and a folder."""
    write(tree.parent, "outside.md", "invented\n")
    refused(tree, GOOD.replace("../guides/guide.md#part", target), 6, target)


def test_ac3_a_reference_link_and_an_anchor(tree: Path) -> None:
    """REQ-063 AC3: rule 6, a reference definition is a link, a bare anchor resolves to the page."""
    write(tree, PAGE, GOOD.replace("signs at", "signs [a](#steps) at", 1))
    assert check(tree).returncode == 0
    refused(tree, GOOD + "\n[ref]: ../guides/absent.md\n", 6, "absent")


def test_ac3_a_skill_is_not_named(tree: Path) -> None:
    """REQ-063 AC3: rule 6, the plugin is not in a project's tree."""
    refused(tree, GOOD.replace("signs at", "signs /agk:launch at", 1), 6, "launch")
    refused(tree, with_command("date /agk:launch"), 6, "launch")


@pytest.mark.parametrize(
    "line",
    [
        "git show HEAD",
        "git diff",
        "git grep x",
        "git log",
        "git log -p",
        "git log --oneline -p",
        "git log --oneline --format=%B",
        "git log --oneline --patch",
        "git -C . show HEAD",
        "gitleaks detect",
        "gitleaks detect --redact=0",
    ],
)
def test_ac4_a_command_that_can_print_a_value_is_refused(tree: Path, line: str) -> None:
    """REQ-063 AC4: rule 7, in every page, naming the page and the rule."""
    refused(tree, with_command(line), 7, line)


@pytest.mark.parametrize(
    "line",
    [
        "git fetch origin main",
        "git rev-parse HEAD",
        "git log --oneline -5",
        "git log --oneline -n 3 main",
    ],
)
def test_ac4_the_allowed_git_forms_pass(tree: Path, line: str) -> None:
    """REQ-063 AC4: rule 7, `fetch`, `status`, `rev-parse` and `log --oneline`."""
    write(tree, PAGE, with_command(line))
    assert check(tree).returncode == 0, line


def test_ac4_a_scan_finding_is_refused_and_never_printed(tree: Path) -> None:
    """REQ-063 AC4: rule 7, `guard.scan_text`; the value is built here, so no file holds one."""
    value = "ghp_" + "a1B2c3D4" * 4 + "a1B2"
    refused(tree, GOOD.replace("signs at", f"signs {value} at", 1), 7, value)


def test_the_script_reads_files_only() -> None:
    """REQ-063 AC3: rule 5, standard library, `common.py` and the `guard.py` of rule 7."""
    tree = ast.parse(SCRIPT.read_text(encoding="utf-8"))
    nodes = list(ast.walk(tree))
    names = {a.name.split(".")[0] for n in nodes if isinstance(n, ast.Import) for a in n.names}
    names |= {n.module.split(".")[0] for n in nodes if isinstance(n, ast.ImportFrom) and n.module}
    assert names - set(sys.stdlib_module_names) == {"common", "guard"}
    assert not names & {"subprocess", "socket", "urllib", "http", "ssl", "os"}


@pytest.mark.parametrize("args", [["--nosuch"], ["--root"], ["--root", "/nonexistent/example"]])
def test_a_bad_argument_is_a_usage_error(args: list[str]) -> None:
    """REQ-063 AC2: rule 5, a mistyped root is never a silent skip."""
    proc = subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, "-I", str(SCRIPT), *args], capture_output=True, text=True
    )
    assert proc.returncode == 2 and "usage:" in proc.stderr


def test_the_check_is_wired() -> None:
    """REQ-063 AC2: rule 15 (a), the governance step, the manifest entry and the test map."""
    make = (KIT_ROOT / "agk.mk").read_text(encoding="utf-8")
    assert re.search(r"check_playbooks\.py\n\t\$\(PY\) scripts/agk/check_runbooks\.py\n", make)
    manifest = json.loads((KIT_ROOT / "kit" / "manifest.json").read_text(encoding="utf-8"))
    assert "scripts/agk/check_runbooks.py" in manifest["verbatim"]
    config = tomllib.loads((KIT_ROOT / "agk.toml").read_text(encoding="utf-8"))
    entry = [e for e in config["testing"]["map"] if e["code"] == "scripts/agk/check_runbooks.py"]
    assert entry and "tests/kit/test_check_runbooks.py" in entry[0]["tests"]


def test_the_kit_itself_passes() -> None:
    """REQ-063 AC2: rule 15 (a), `skipped` on the kit until build (b) adds the pages."""
    pages = (KIT_ROOT / "docs" / "runbooks").is_dir()
    expected = "ok runbooks\n" if pages else "skipped (no runbooks)\n"
    proc = check(KIT_ROOT)
    assert (proc.returncode, proc.stdout) == (0, expected), proc.stdout
