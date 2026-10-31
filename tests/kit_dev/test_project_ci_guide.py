"""Kit-only tests of section 4 of the project CI guide: a heavy check runs only on changed inputs.

Brief #416, ADR-0226; REQ-039. The snippet is read as a workflow (with a small reader of the
block style it uses, and with PyYAML as well where it is installed) and its shell step is run in
throwaway git repositories, so the skip is tested, not only described. No network.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess

import pytest
from conftest import KIT_ROOT

GUIDE = KIT_ROOT / "docs" / "guides" / "project-ci.md"
TITLE = "4. A heavy check runs only when its inputs change"
# Names of hosts, clouds, runners, scanners and model makers that a guide of the kit could slip
# into; GitHub is the one host the kit is built for (answer 4). Matched as whole words, so a file
# name such as a container build file is not read as a vendor's name (Q-416-1).
VENDORS = (
    "gitlab",
    "bitbucket",
    "azure",
    "aws",
    "amazon",
    "google",
    "gcp",
    "circleci",
    "jenkins",
    "travis",
    "buildkite",
    "docker",
    "kubernetes",
    "podman",
    "gitleaks",
    "anthropic",
    "claude",
    "openai",
    "slack",
    "jira",
    "microsoft",
    "apple",
)


def guide() -> str:
    return GUIDE.read_text(encoding="utf-8")


def flat(text: str) -> str:
    return " ".join(text.split())


def section() -> str:
    found = re.search(rf"(?ms)^## {re.escape(TITLE)}\n(.*?)(?=^## |\Z)", guide())
    assert found, f"the guide has no section '{TITLE}'"
    return found.group(1)


def snippet() -> str:
    blocks = re.findall(r"(?ms)^```yaml\n(.*?)^```", section())
    assert len(blocks) == 1, "section 4 has one copyable yaml snippet"
    return blocks[0]


# --- a reader of the block style of the snippet (mappings, lists, literal blocks, flow lists) ---


def _strip_comment(line: str) -> str:
    out, quote = [], None
    for i, ch in enumerate(line):
        if quote:
            if ch == quote:
                quote = None
        elif ch in "'\"":
            quote = ch
        elif ch == "#" and (i == 0 or line[i - 1] in " \t"):
            break
        out.append(ch)
    return "".join(out).rstrip()


def _scalar(text: str):
    text = text.strip()
    if text.startswith("[") and text.endswith("]"):
        return [_scalar(part) for part in text[1:-1].split(",") if part.strip()]
    if len(text) >= 2 and text[0] == text[-1] and text[0] in "'\"":
        return text[1:-1]
    return text


def read_block_yaml(text: str):
    """Read the subset of YAML the guide's snippets use; raise ValueError on anything else."""
    if "\t" in text:
        raise ValueError("a tab in the indentation")
    lines = text.splitlines()
    pos = 0

    def indent(line: str) -> int:
        return len(line) - len(line.lstrip(" "))

    def skip_blank() -> None:
        nonlocal pos
        while pos < len(lines) and not _strip_comment(lines[pos]).strip():
            pos += 1

    def literal(parent: int) -> str:
        nonlocal pos
        body: list[str] = []
        while pos < len(lines) and (not lines[pos].strip() or indent(lines[pos]) > parent):
            body.append(lines[pos])
            pos += 1
        width = min((indent(b) for b in body if b.strip()), default=0)
        return "\n".join(b[width:] for b in body).rstrip("\n") + "\n"

    def value_after(rest: str, own: int):
        nonlocal pos
        rest = rest.strip()
        if rest == "|":
            return literal(own)
        if rest:
            return _scalar(rest)
        skip_blank()
        if pos < len(lines) and indent(lines[pos]) > own:
            return node(indent(lines[pos]))
        if pos < len(lines) and indent(lines[pos]) == own and lines[pos].lstrip().startswith("- "):
            return node(own)
        return None

    def mapping_entry(target: dict, content: str, own: int) -> None:
        match = re.fullmatch(r"([A-Za-z_][\w-]*):(?:\s+(.*))?", content)
        if not match:
            raise ValueError(f"not a key: {content!r}")
        key = match.group(1)
        if key in target:
            raise ValueError(f"a repeated key: {key}")
        target[key] = value_after(match.group(2) or "", own)

    def node(width: int):
        nonlocal pos
        skip_blank()
        first = lines[pos].lstrip()
        if first.startswith("- "):
            items: list = []
            while True:
                skip_blank()
                if pos >= len(lines) or indent(lines[pos]) != width:
                    break
                content = _strip_comment(lines[pos]).strip()
                if not content.startswith("- "):
                    raise ValueError(f"a list item expected: {content!r}")
                pos += 1
                inner = content[2:]
                if re.match(r"[A-Za-z_][\w-]*:(\s|$)", inner):
                    item: dict = {}
                    mapping_entry(item, inner, width + 2)
                    while True:
                        skip_blank()
                        if pos >= len(lines) or indent(lines[pos]) != width + 2:
                            break
                        line = _strip_comment(lines[pos]).strip()
                        pos += 1
                        mapping_entry(item, line, width + 2)
                    items.append(item)
                else:
                    items.append(_scalar(inner))
            return items
        result: dict = {}
        while True:
            skip_blank()
            if pos >= len(lines) or indent(lines[pos]) < width:
                break
            if indent(lines[pos]) > width:
                raise ValueError(f"unexpected indentation: {lines[pos]!r}")
            line = _strip_comment(lines[pos]).strip()
            pos += 1
            mapping_entry(result, line, width)
        return result

    skip_blank()
    tree = node(indent(lines[pos]))
    skip_blank()
    if pos != len(lines):
        raise ValueError(f"unread line: {lines[pos]!r}")
    return tree


def workflow() -> dict:
    tree = read_block_yaml(snippet())
    yaml = _yaml()
    if yaml is not None:
        assert yaml.safe_load(snippet()) == _with_flow(tree), "both readers read the same workflow"
    return tree


def _yaml():
    try:
        import yaml  # type: ignore[import-untyped]
    except ImportError:
        return None
    return yaml


def _with_flow(tree):
    """PyYAML reads `on:` as True; the reader keeps the text. Align the two."""
    if isinstance(tree, dict):
        return {(True if k == "on" else k): _with_flow(v) for k, v in tree.items()}
    if isinstance(tree, list):
        return [_with_flow(v) for v in tree]
    return tree


def job() -> dict:
    jobs = workflow()["jobs"]
    assert isinstance(jobs, dict) and len(jobs) == 1
    return next(iter(jobs.values()))


def step(step_id: str | None = None, name: str | None = None) -> dict:
    for item in job()["steps"]:
        if (step_id and item.get("id") == step_id) or (name and item.get("name") == name):
            return item
    raise AssertionError(f"no step {step_id or name}")


def inputs_step() -> dict:
    found = [s for s in job()["steps"] if "git diff --name-only" in str(s.get("run", ""))]
    assert len(found) == 1, "one step lists the changed files"
    return found[0]


# --- answer 1: the section, its snippet and its steps ---------------------------------------------


def test_section_4_has_the_title_of_answer_1_and_stays_fourth():
    """REQ-039: brief #416 answer 1."""
    titles = re.findall(r"(?m)^## (\d)\. ", guide())
    assert titles == ["1", "2", "3", "4", "5"]
    assert f"## {TITLE}\n" in guide()
    assert "A documentation-only change skips the heavy steps" not in guide()


def test_the_snippet_reads_as_a_workflow_job_with_steps():
    """REQ-039: brief #416 answers 1 and 4 (the snippet parses as workflow steps)."""
    tree = workflow()
    assert set(tree) >= {"on", "jobs"}
    steps = job()["steps"]
    assert isinstance(steps, list) and len(steps) >= 4
    for item in steps:
        assert isinstance(item, dict)
        assert ("run" in item) != ("uses" in item), item
        assert set(item) <= {"name", "id", "if", "env", "run", "uses", "with", "shell"}, item
    assert steps[0]["uses"].startswith("actions/checkout@")
    assert steps[0]["with"]["fetch-depth"] in ("0", 0)


def test_the_snippet_reads_with_pyyaml_where_it_is_installed():
    """REQ-039: brief #416 answer 4 (a real YAML reader agrees with the small one)."""
    yaml = _yaml()
    if yaml is None:
        pytest.skip("PyYAML is not installed; the small reader above still reads the snippet")
    parsed = yaml.safe_load(snippet())
    assert parsed["jobs"]
    assert _with_flow(read_block_yaml(snippet())) == parsed


def test_the_reader_refuses_what_it_cannot_read():
    """REQ-039: brief #416 answer 4 (the test of the test: a broken snippet does not pass)."""
    for broken in (
        "jobs:\n  suite:\n    steps:\n      - run: a\n     - run: b\n",
        "jobs:\n\tsuite: {}\n",
        "jobs:\n  suite:\n  suite:\n",
        "jobs:\n  not a key here\n",
    ):
        with pytest.raises(ValueError):
            read_block_yaml(broken)
    small = "a:\n  - name: x\n    run: |\n      echo 1\n      echo 2\n  - uses: y@z\n"
    tree = read_block_yaml(small)
    assert tree == {"a": [{"name": "x", "run": "echo 1\necho 2\n"}, {"uses": "y@z"}]}


def test_the_inputs_step_lists_the_changed_files_against_the_base_and_names_its_globs():
    """REQ-039: brief #416 answer 1 (the job's own input globs, the workflow itself among them)."""
    found = inputs_step()
    assert found.get("id"), "the step has an id its outputs are read by"
    globs = str(job().get("env", {}).get("INPUTS", ""))
    assert globs, "the input globs are set once, on the job"
    words = globs.split()
    assert any(w.startswith("src/") for w in words), "application code"
    assert any(w.startswith("tests/") for w in words), "tests"
    assert any("ockerfile" in w or "Containerfile" in w for w in words), "container build files"
    assert any("compose" in w for w in words), "compose files"
    assert any(w.startswith(".github/workflows/") for w in words), "the workflow itself"
    assert "pull_request.base.sha" in str(found.get("env", {}))


def test_a_following_step_writes_the_skip_reason_to_the_step_summary():
    """REQ-039: brief #416 answers 1 and 2 (the reason is always visible)."""
    steps = job()["steps"]
    found = inputs_step()
    out = found["id"]
    index = steps.index(found)
    reason = steps[index + 1]
    assert f"steps.{out}.outputs." in reason["if"] and "'false'" in reason["if"]
    assert "skipped: none of $INPUTS changed" in reason["run"]
    assert "GITHUB_STEP_SUMMARY" in reason["run"]
    heavy = steps[index + 2 :]
    assert heavy, "the heavy steps follow"
    for item in heavy:
        assert f"steps.{out}.outputs." in item["if"] and "!= 'false'" in item["if"], item


# --- the shell step, run: what it decides in each case --------------------------------------------


def git(repo, *args: str) -> str:
    env = {
        **os.environ,
        "GIT_AUTHOR_NAME": "t",
        "GIT_AUTHOR_EMAIL": "t@example.invalid",
        "GIT_COMMITTER_NAME": "t",
        "GIT_COMMITTER_EMAIL": "t@example.invalid",
    }
    return subprocess.run(
        ["git", *args], cwd=repo, env=env, check=True, capture_output=True, text=True
    ).stdout.strip()


def repo_with_change(tmp_path, changed: list[str]) -> tuple[str, str]:
    repo = tmp_path / "repo"
    repo.mkdir(parents=True)
    git(repo, "init", "-q", "-b", "main")
    (repo / "README.md").write_text("start\n", encoding="utf-8")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "base")
    base = git(repo, "rev-parse", "HEAD")
    for name in changed:
        path = repo / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("changed\n", encoding="utf-8")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "--allow-empty", "-m", "change")
    return str(repo), base


def decide(tmp_path, changed: list[str], event="pull_request", action="synchronize", base=None):
    if shutil.which("bash") is None:
        pytest.skip("bash is not installed")
    repo, real_base = repo_with_change(tmp_path, changed)
    found = inputs_step()
    out_file = tmp_path / "out"
    out_file.write_text("", encoding="utf-8")
    env = {
        "PATH": os.environ.get("PATH", ""),
        "INPUTS": str(job()["env"]["INPUTS"]),
        "GITHUB_OUTPUT": str(out_file),
        "GITHUB_SHA": git(repo, "rev-parse", "HEAD"),
    }
    values = {
        "${{ github.event_name }}": event,
        "${{ github.event.action }}": action,
        "${{ github.event.pull_request.base.sha }}": real_base if base is None else base,
    }
    for key, value in found.get("env", {}).items():
        text = str(value)
        for expr, real in values.items():
            text = text.replace(expr, real)
        assert "${{" not in text, f"an expression the test does not know: {value}"
        env[key] = text
    proc = subprocess.run(
        ["bash", "-e", "-c", found["run"]], cwd=repo, env=env, capture_output=True, text=True
    )
    assert proc.returncode == 0, proc.stderr
    outputs = dict(
        line.split("=", 1) for line in out_file.read_text(encoding="utf-8").splitlines() if line
    )
    return outputs[output_name()]


def output_name() -> str:
    """The output the heavy steps read: `steps.<id>.outputs.<name>`."""
    last = job()["steps"][-1]["if"]
    match = re.search(rf"steps\.{re.escape(inputs_step()['id'])}\.outputs\.(\w+)", last)
    assert match, last
    return match.group(1)


def test_the_step_parses_as_bash():
    """REQ-039: brief #416 answer 4."""
    if shutil.which("bash") is None:
        pytest.skip("bash is not installed")
    command = ["bash", "-n", "-c", inputs_step()["run"]]
    proc = subprocess.run(command, capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr


def test_a_change_to_other_files_skips(tmp_path):
    """REQ-039: brief #416 answer 1 (briefs, docs, the kit's own files do not run the suite)."""
    assert decide(tmp_path, ["docs/briefs/0001.md", "scripts/agk/x.py", "agk.toml"]) == "false"


@pytest.mark.parametrize(
    "changed",
    [
        ["src/app/main.py"],
        ["tests/test_main.py"],
        ["Dockerfile"],
        ["compose.yaml"],
        [".github/workflows/suite.yml"],
        ["docs/x.md", "src/a b.py"],
    ],
)
def test_a_change_to_an_input_runs_in_full(tmp_path, changed):
    """REQ-039: brief #416 answer 1."""
    assert decide(tmp_path, changed) == "true"


def test_a_push_to_the_default_branch_always_runs_in_full(tmp_path):
    """REQ-039: brief #416 answer 2."""
    assert decide(tmp_path, ["docs/x.md"], event="push", action="") == "true"


def test_ready_for_review_always_runs_in_full(tmp_path):
    """REQ-039: brief #416 answer 2."""
    assert decide(tmp_path, ["docs/x.md"], action="ready_for_review") == "true"


def test_an_unknown_base_or_a_failed_diff_runs_in_full(tmp_path):
    """REQ-039: brief #416 answer 2 (an error never weakens the check)."""
    assert decide(tmp_path / "a", ["docs/x.md"], base="") == "true"
    assert decide(tmp_path / "b", ["docs/x.md"], base="0" * 40) == "true"


# --- answer 2: the must-nots; answer 3: the doctor; answer 4: GitHub only -------------------------


def test_the_section_states_the_must_nots_of_answer_2():
    """REQ-039: brief #416 answer 2."""
    text = flat(section()).lower()
    assert "never removed or weakened" in text
    assert "push to the default branch" in text and "ready_for_review" in text
    assert "always run in full" in text
    assert "skip reason is always visible" in text
    assert "paths-ignore" in text and "never" in text


def test_the_doctor_checks_of_answer_3_are_unchanged():
    """REQ-039: brief #416 answer 3 (the doctor's two checks still point at defaults 1, 2)."""
    text = guide()
    assert "| `ci-drafts` |" in text and "| default 1 |" in text
    assert "| `ci-concurrency` |" in text and "| default 2 |" in text


def test_the_section_names_no_vendor_beyond_github():
    """REQ-039: brief #416 answer 4."""
    text = section().lower()
    for vendor in VENDORS:
        assert not re.search(rf"\b{vendor}\b", text), vendor
    assert "github" in text
