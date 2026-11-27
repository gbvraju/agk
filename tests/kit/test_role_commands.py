"""A role's words match its guard and its start prompt (brief #2053, ADR-0851; REQ-071).

Answer 1: every command a role's files tell it to run is judged by that role's own guard
(`decide` of the hook its agent file's front matter names), or, for a role with no hook, by the
`deny` and `ask` entries of `.claude/settings.json`. Answer 2: every start of a builder that a
supervisor makes carries the short-job line of `launch.FIX_JOB`. Answer 3: no role's files both
ban and order one form. Answer 4: the known mismatches are strict expected failures by name, so the
pull request that fixes one removes its entry. Files only (and the fixture `git`); no network, no
model, no subprocess per form.
"""

from __future__ import annotations

import ast
import fnmatch
import importlib
import itertools
import json
import os
import re
import shutil
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

import pytest

KIT = Path(__file__).resolve().parents[2]
HOOKS = KIT / ".claude" / "hooks"
AGENTS = KIT / ".claude" / "agents"
RUNTIME = KIT / "kit" / "templates" / "runtime"
SCRIPTS = KIT / "scripts" / "agk"
sys.path.insert(0, str(HOOKS))
sys.path.insert(0, str(SCRIPTS))

# The one guide paragraph addressed to a role, by its opening words (answer 1).
ROLE_PARAGRAPHS = {"conductor": [("docs/guides/getting-started.md", "3. **Start the conductor.**")]}
SHA = "0123456789abcdef0123456789abcdef01234567"
WHEN = "2026-11-27T10:00:00Z"
# Placeholder class -> its filled value; {file} and {dir} sit under a temp `agk-conductor-<name>`.
FILL = {
    "number": ("7", ("<n>", "<N>", "<number>", "<pr>")),
    "sha": (SHA, ("<sha>", "<head>", "<that sha>", "<full head>")),
    "session": ("s1", ("<session>", "<session name>", "<id>", "<name>", "<a short name>")),
    "time": (WHEN, ("<last line read>", "<the time of your previous Report:>", "<time>")),
    "file": ("{file}", ("<file>", "<that file>", "<body file>", "<the scratch file>", "FILE", "<path>")),
    "dir": ("{dir}", ("<scratch directory>", "<s>", "<scratch>")),
    "text": ("one line", ("<one line>", "<message>")),
    "cap": ("3", ("<used>", "<cap>")),
    "unit": ("hours", ("<unit>",)),
    "adapter": ("{adapter}", ("<launch_adapter>",)),
    "branch": ("claude/brief-7", ("<branch>",)),
    "kind": ("build", ("<kind>",)),
}
# The scratch folder each guard reads as its own, directly in the system temp folder.
SCRATCH = {"architect-review": "agk-review-r{pid}", "architect": "agk-review-r{pid}"}
SPAN = re.compile(r"`([^`]+)`")
FULL = re.compile(r'^python3?\s+(?:-I\s+)?(?:scripts/agk/|<kit>/|"<plugin>/scripts/agk/)(\w+\.py)"?')
SHORT = re.compile(r"^(\w+\.py)\s+[a-z-][^`]*$")
ITEM = re.compile(r"^\s*(?:[-*]|\d+\.)\s")
ELIDED = re.compile(r"\.\.\.|\u2026")
SHORT_AFTER = re.compile(r"\b(?:run|start|with|after)(?: exactly)?\s*$")
NOT_AFTER = re.compile(r"\b(?:never|not|no)\s+(?:run|start)\s*$", re.I)


@dataclass(frozen=True)
class Form:
    role: str
    where: str  # file:line, the place a failure names
    text: str  # as the role file writes it

    @property
    def file(self) -> str:
        return self.where.rsplit(":", 1)[0]


@dataclass
class Role:
    name: str
    guard: str | None  # module name, or None: judged by .claude/settings.json
    flag: str | None
    tools: list[str]
    sources: list[Path] = field(default_factory=list)


def front_matter(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    return text.split("---", 2)[1] if text.startswith("---") else ""


def roles() -> dict[str, Role]:
    """Every agent file's role, its guard from the `PreToolUse` hook and its sources."""
    found = {}
    for agent in sorted(AGENTS.glob("*.md")):
        head = front_matter(agent)
        hook = re.search(r"\.claude/hooks/(\w+)\.py(?:\s+(--[a-z]+))?", head)
        tools = re.search(r"^tools:\s*(.+)$", head, re.M)
        role = Role(
            agent.stem,
            hook.group(1) if hook else None,
            hook.group(2) if hook else None,
            [t.strip() for t in tools.group(1).split(",")] if tools else ["*"],
        )
        role.sources = [agent]
        if (RUNTIME / f"{agent.stem}.txt").is_file():
            role.sources.append(RUNTIME / f"{agent.stem}.txt")
        for skill in sorted(set(re.findall(r"skills/([\w-]+)/SKILL\.md", agent.read_text()))):
            role.sources.append(KIT / "skills" / skill / "SKILL.md")
        found[agent.stem] = role
    return found


def rel(path: Path) -> str:
    return str(path.relative_to(KIT)) if path.is_relative_to(KIT) else path.name


def runs_commands(role: Role) -> bool:
    """A role whose tools hold no shell runs no command, so its files name only inputs."""
    return "*" in role.tools or "Bash" in role.tools


def paragraphs(path: Path) -> list[tuple[int, str]]:
    """(first line, text) of each paragraph, lines joined, and each line of a fenced block alone."""
    out, start, lines, fenced = [], 0, [], False
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if line.strip().startswith("```"):
            fenced = not fenced
            continue
        if fenced:
            out.append((number, f"`{line.strip()}`"))
        elif line.strip():
            if lines and ITEM.match(line):
                out.append((start, " ".join(lines)))
                start, lines = 0, []
            start = start or number
            lines.append(line.strip())
        elif lines:
            out.append((start, " ".join(lines)))
            start, lines = 0, []
    if lines:
        out.append((start, " ".join(lines)))
    return out


def guide_paragraphs(role: str) -> list[tuple[str, int, str]]:
    """The guide paragraph of ROLE_PARAGRAPHS: from its opening words to the next numbered item."""
    out = []
    for name, opening in ROLE_PARAGRAPHS.get(role, []):
        lines = (KIT / name).read_text(encoding="utf-8").splitlines()
        for number, line in enumerate(lines, 1):
            if line.strip().startswith(opening):
                body = itertools.takewhile(
                    lambda x: x.strip() and not re.match(r"\s*\d+\. \*\*", x), lines[number:]
                )
                out.append((name, number, " ".join([line.strip(), *(x.strip() for x in body)])))
    return out


def forms_in(role: str, name: str, items: list[tuple[int, str]]) -> list[Form]:
    out = []
    for number, text in items:
        for match in SPAN.finditer(text):
            span = match.group(1).strip()
            short = SHORT.match(span)
            if FULL.match(span):
                out.append(Form(role, f"{name}:{number}", span))
            elif short and (SCRIPTS / short.group(1)).is_file():
                before = text[: match.start()]
                if SHORT_AFTER.search(before) and not NOT_AFTER.search(before):
                    out.append(Form(role, f"{name}:{number}", f"python3 scripts/agk/{span}"))
    return out


def role_forms(role: Role) -> list[Form]:
    out = []
    for source in role.sources:
        out += forms_in(role.name, rel(source), paragraphs(source))
    for name, number, text in guide_paragraphs(role.name):
        out += forms_in(role.name, name, [(number, text)])
    return out


def alternatives(text: str) -> list[str]:
    """`a|b` alternatives of one word expanded (`python3|python`, `--json|--all`)."""
    words = [w.split("|") if "|" in w and "<" not in w else [w] for w in text.split(" ")]
    return [" ".join(choice) for choice in itertools.product(*words)]


def fill(text: str, scratch: dict[str, str]) -> str:
    """The form with every placeholder of FILL filled; `<kit>` and the plugin's folder written as
    the installed `scripts/agk/`. A placeholder left raises, naming its class only."""
    text = text.replace("<kit>/", "scripts/agk/").replace('"<plugin>/scripts/agk/', "scripts/agk/")
    text = re.sub(r'(scripts/agk/\w+\.py)"', r"\1", text)
    for value, names in FILL.values():
        for name in names:
            text = text.replace(name, value.format(**scratch))
    left = re.search(r"<[^<>]+>", text)
    if left:
        raise LookupError(f"placeholder {left.group(0).split()[0].strip('<>')} has no FILL entry")
    return text


def make_scratch(base: Path) -> dict[str, dict[str, str]]:
    """Per role, the {file}, {dir} and {adapter} of FILL; `base` is the system temp folder."""
    flow = (KIT / "agk.toml").read_text(encoding="utf-8")
    adapter = re.search(r'^launch_adapter = "([^"]+)"', flow, re.M)
    out = {}
    for name in roles():
        pattern = SCRATCH.get(name, "agk-conductor-roles-{pid}")
        folder = base / pattern.format(pid=os.getpid())
        folder.mkdir(exist_ok=True)
        (folder / "plan.md").write_text("Brief: #7 on example.com\n", encoding="utf-8")
        out[name] = {
            "file": str(folder / "plan.md"),
            "dir": str(folder),
            "adapter": f'"{adapter.group(1)}"' if adapter else '"start"',
        }
    return out


def settings_rule(command: str) -> str | None:
    """The `deny` or `ask` entry of `.claude/settings.json` that holds this command, else None."""
    permissions = json.loads((KIT / ".claude" / "settings.json").read_text())["permissions"]
    for kind in ("deny", "ask"):
        for entry in permissions.get(kind, []):
            pattern = re.fullmatch(r"Bash\((.*)\)", entry)
            if pattern and fnmatch.fnmatchcase(command, pattern.group(1).replace(":*", "*")):
                return f"settings {kind}"
    return None


def judge(role: Role, command: str, root: Path = KIT) -> str | None:
    """The role's own decision on one command: None when allowed, else the guard's reason."""
    if role.guard is None:
        return settings_rule(command)
    guard = importlib.import_module(role.guard)
    payload = {"tool_name": "Bash", "tool_input": {"command": command}, "cwd": str(root)}
    if role.flag == "--shadow":
        return guard.decide(payload, shadow=True)
    if role.flag == "--review":
        return guard.decide(payload, review=True)
    return guard.decide(payload)


def rule_of(reason: str) -> str:
    """The guard rule a refusal names (`conductor guard rule 6`), never the command's value."""
    found = re.match(r"([a-z ]+ guard rule \d+[a-z]?|settings (?:deny|ask))", reason)
    return found.group(1) if found else reason.split(":")[0]


@dataclass(frozen=True)
class Expect:
    answer: int  # 1: a form its guard refuses; 2: a start without its kind line; 3: an order beside its ban
    id: str
    role: str
    file: str
    form: str  # a part of the form, the start call or the banned key at that file
    why: str  # a Q- id or a brief


# Answer 4: the known mismatches, each a strict expected failure until P2 or P3 removes it.
EXPECTED = [
    Expect(1, "reprove", "conductor", "docs/guides/getting-started.md", "conductor.py reprove", "Q-1163-1"),
    Expect(1, "check-brief", "conductor", ".claude/agents/conductor.md", "check_brief.py", "Q-P0B-1"),
    Expect(1, "checklist", "conductor", ".claude/agents/conductor.md", "agk/checklist.py", "Q-P0B-1"),
    Expect(1, "save-checklist", "conductor", ".claude/agents/conductor.md", "--save-checklist", "Q-P0B-1"),
    Expect(1, "verdict-status", "conductor", ".claude/agents/conductor.md", "--status --pr", "Q-853-1"),
    Expect(2, "build-job-line", "builder", "scripts/agk/autopilot.py", "launch.prompt_for(name, number)",
           "brief #2053 case 2"),  # fmt: skip
    Expect(2, "launcher-build-line", "builder", "kit/templates/runtime/launcher.txt", "`job: build",
           "brief #2053 case 2"),  # fmt: skip
    Expect(2, "adapter-start-line", "builder", "scripts/agk/launch.py",
           'start_with(opts["--adapter"], found, runs=runs)', "Q-P0B-2"),  # fmt: skip
    Expect(3, "conductor-watch", "conductor", ".claude/agents/conductor.md", "conductor.py watch",
           "brief #2053 case 3"),  # fmt: skip
    Expect(3, "wake-timer", "conductor", ".claude/agents/conductor.md", "wake-up timer", "brief #2053 case 3"),
    Expect(3, "wake-tool", "conductor", ".claude/agents/conductor.md", "ScheduleWakeup", "brief #2053 case 3"),
]
# A form a role file names as another actor's, with that actor; never judged as the role's own.
OTHERS_RUN = {
    ("conductor", "conductor.py watchdog --pass"): "the machine's scheduler",
    ("conductor", "merge_cleared.py --pr <n> --owner"): "the owner",
    ("conductor", "session.py claim"): "each builder the conductor starts",
}
# Labels of one file that are two modes: a ban under one binds only its own lines.
MODE_SPLITS = {"kit/templates/runtime/builder.txt": [("SHORT JOBS", "INTERACTIVE")]}
# Answer 2: every start of a builder, (file, function, call) -> who starts it.
START_PATHS = {
    ("scripts/agk/autopilot.py", "next_command", "prompt_for"): "supervised",
    ("scripts/agk/autopilot.py", "next_command", "resume_for"): "supervised",
    ("scripts/agk/autopilot.py", "next_command", "start_with"): "supervised",
    ("scripts/agk/conductor.py", "watch_builders", "resume_for"): "supervised",
    ("scripts/agk/launch.py", "main", "start_with"): "supervised",  # prompts --adapter (Q-P0B-2)
    ("scripts/agk/launch.py", "main", "prompt_for"): "person",
    ("scripts/agk/launch.py", "resume_main", "resume_for"): "person",
    ("scripts/agk/launch.py", "resume_main", "start_with"): "person",
    ("scripts/agk/launch.py", "start_with", "prompt_for"): "default",  # judged at each caller
}
BUILDER_STEPS = re.compile(r"^\d+\. (`job: (?:build|fix) [^`]*`.*)$", re.M)
BAN = re.compile(r"\b(?:never run|run no|start no|schedule no)\s+(`[^`]+`|\w+)", re.I)
REFUSED = re.compile(r"((?:`[^`]+`[^`.;]*?)+)\bstays? refused", re.I)
WORDS = {
    "watch": ("conductor.py watch", "session.py watch"),
    "loop": ("conductor.py watch", "session.py watch"),
    "wake": ("ScheduleWakeup", "wake-up timer"),
}
LABEL = re.compile(r"^([A-Z][A-Z ]+[A-Z])(?: \([^)]*\))?:")


def expected(answer: int, role: str, file: str, text: str) -> Expect | None:
    wanted = (answer, role, file)
    return next((e for e in EXPECTED if (e.answer, e.role, e.file) == wanted and e.form in text), None)


def others(form: Form) -> str | None:
    return next((who for (r, f), who in OTHERS_RUN.items() if r == form.role and f in form.text), None)


def key_of(text: str) -> str | None:
    """`conductor.py watch` of `python3 scripts/agk/conductor.py watch --since ...`."""
    found = re.search(r"(\w+\.py)(?:\"?\s+([a-z][\w-]*))?", text)
    return " ".join(x for x in found.groups() if x) if found else None


def refusals(role: Role, form: Form, scratch: dict[str, str], root: Path = KIT) -> list[str]:
    """Why the role's guard refuses the form (answer 1), naming file:line and the rule only."""
    out = []
    for choice in alternatives(form.text):
        try:
            command = fill(choice, scratch)
        except LookupError as exc:
            return [f"{role.name} {form.where}: {exc}"]
        reason = judge(role, command, root)
        if reason:
            out.append(f"{role.name} {form.where}: refused by {rule_of(reason)}")
    return out


def judged(role: Role) -> list[Form]:
    """The forms of a role its guard judges: not elided, not another actor's."""
    return [f for f in role_forms(role) if not ELIDED.search(f.text) and not others(f)]


def labelled(role: Role) -> list[tuple[str, int, str, str | None]]:
    """(file, line, text, label) of every paragraph of the role's sources."""
    out = []
    for source in role.sources:
        for number, text in paragraphs(source):
            found = LABEL.match(text)
            out.append((rel(source), number, text, found.group(1) if found else None))
    for name, number, text in guide_paragraphs(role.name):
        out.append((name, number, text, None))
    return out


def bans(role: Role) -> list[tuple[str, str, str | None]]:
    """(banned key, file:line, label) of every ban sentence (answer 3)."""
    out = []
    for name, number, text, label in labelled(role):
        found = [m.group(1).strip("`") for m in BAN.finditer(text)]
        found += [s for m in REFUSED.finditer(text) for s in SPAN.findall(m.group(1))]
        for word in found:
            keys = WORDS.get(word, (key_of(word),) if ".py" in word else ())
            out += [(key, f"{name}:{number}", label) for key in keys]
    return out


def binds(file: str, ban_label: str | None, order_label: str | None) -> bool:
    for pair in MODE_SPLITS.get(file, []):
        if ban_label in pair:
            return order_label == ban_label
    return True


def orders(role: Role) -> list[tuple[str, str, str | None]]:
    """(key, file:line, label) of every order: a judged form, a wake-up timer, a granted tool."""
    out = []
    head = role.sources[0].read_text(encoding="utf-8").splitlines() if role.sources else []
    for number, line in enumerate(head, 1):
        if line.startswith("tools:") and "ScheduleWakeup" in line:
            out.append(("ScheduleWakeup", f"{rel(role.sources[0])}:{number}", None))
    labels = {(n, t): label for n, t, _, label in [(f"{a}:{b}", c, c, d) for a, b, c, d in labelled(role)]}
    for name, number, text, label in labelled(role):
        if "wake-up timer" in text and not BAN.search(text):
            out.append(("wake-up timer", f"{name}:{number}", label))
    for form in judged(role):
        label = next((lab for (w, _), lab in labels.items() if w == form.where), None)
        out.append((key_of(form.text), form.where, label))
    return out


def conflicts(role: Role) -> dict[tuple[str, str], list[str]]:
    """(key, order file) -> the `order <file:line> beside ban <file:line>` pairs (answer 3)."""
    out: dict[tuple[str, str], list[str]] = {}
    for key, where, label in orders(role):
        file = where.rsplit(":", 1)[0]
        for banned, at, ban_label in bans(role):
            same_file = at.rsplit(":", 1)[0] == file
            if banned == key and (not same_file or binds(file, ban_label, label)):
                found = out.setdefault((key, file), [])
                if f"order {where} beside ban {at}" not in found:
                    found.append(f"order {where} beside ban {at}")
    return out


def calls() -> list[tuple[str, str, str, ast.Call, ast.FunctionDef, str]]:
    """Every call of `prompt_for`, `resume_for` and `start_with` in the kit's scripts."""
    out = []
    for path in sorted(SCRIPTS.glob("*.py")):
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        for function in [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]:
            for node in ast.walk(function):
                name = getattr(node, "func", None)
                name = getattr(name, "attr", None) or getattr(name, "id", None)
                if isinstance(node, ast.Call) and name in ("prompt_for", "resume_for", "start_with"):
                    segment = ast.get_source_segment(source, node) or name
                    out.append((rel(path), function.name, name, node, function, segment))
    return out


def carries(call: ast.Call, function: ast.FunctionDef) -> bool:
    """The prompt the call builds has `FIX_JOB` added: in the same sum, or by `+=` on its name."""
    def fix(node: ast.AST) -> bool:
        return any(getattr(n, "attr", getattr(n, "id", None)) == "FIX_JOB" for n in ast.walk(node))

    for node in ast.walk(function):
        if isinstance(node, ast.BinOp) and call in list(ast.walk(node)) and fix(node):
            return True
        if isinstance(node, ast.Assign) and node.value is call:
            names = {getattr(t, "id", None) for t in node.targets}
            for aug in ast.walk(function):
                if isinstance(aug, ast.AugAssign) and getattr(aug.target, "id", 0) in names:
                    if fix(aug.value):
                        return True
    return False


ROLES = roles()
COMMANDING = [r for r in ROLES.values() if runs_commands(r)]
JOB_LINE = __import__("launch").FIX_JOB.split(":")[0]  # "This is one short job (SPEC-0064 rule 4)"
JOB_WORDS = JOB_LINE.removeprefix("This is ").split(" (")[0]


def case(values: tuple, id_: str, entry: Expect | None):
    marks = [pytest.mark.xfail(strict=True, reason=f"{entry.id} ({entry.why})")] if entry else []
    return pytest.param(*values, id=id_, marks=marks)


FORM_CASES = [
    case((r.name, f), f"{r.name}-{f.where}-{key_of(f.text)}", expected(1, r.name, f.file, f.text))
    for r in COMMANDING for f in judged(r)
]  # fmt: skip
START_CASES = [
    case((c,), f"{c[0]}:{c[1]}:{c[2]}:{c[3].lineno}", expected(2, "builder", c[0], c[5])) for c in calls()
]
STEPS = BUILDER_STEPS.findall((RUNTIME / "launcher.txt").read_text(encoding="utf-8"))
STEP_CASES = [
    case((s,), s.split("`")[1], expected(2, "builder", "kit/templates/runtime/launcher.txt", s)) for s in STEPS
]
CONFLICT_CASES = [
    case((r.name, key, file, pairs), f"{r.name}-{key}-{file}", expected(3, r.name, file, key))
    for r in COMMANDING for (key, file), pairs in conflicts(r).items()
]  # fmt: skip


@pytest.fixture(scope="module")
def scratch():
    made = make_scratch(Path(tempfile.gettempdir()))
    yield made
    for folder in {v["dir"] for v in made.values()}:
        shutil.rmtree(folder, ignore_errors=True)


@pytest.fixture(autouse=True)
def kit_project(monkeypatch):
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(KIT))
    monkeypatch.chdir(KIT)


@pytest.mark.parametrize(("name", "form"), FORM_CASES)
def test_every_role_form_is_allowed(name, form, scratch):
    """REQ-071: answer 1, each command a role's files name passes that role's own guard."""
    assert not refusals(ROLES[name], form, scratch[name]), refusals(ROLES[name], form, scratch[name])


@pytest.mark.parametrize("site", START_CASES)
def test_every_supervised_start_says_it_is_one_short_job(site):
    """REQ-071: answer 2, a supervised start carries the short-job line, a person's start none."""
    file, function, callee, call, body, _ = site
    kind = START_PATHS.get((file, function, callee))
    assert kind, f"{file} {function}: a start of a builder that START_PATHS does not name"
    if kind == "default" or (callee == "start_with" and (len(call.args) > 2 or any(
            k.arg == "prompts" for k in call.keywords))):  # fmt: skip
        return  # the prompt is judged where it is built
    said = JOB_LINE in __import__("launch").prompt_for("s1", 7) if callee == "start_with" else carries(call, body)
    assert said == (kind == "supervised"), f"{file} {function}: a {kind} start, short-job line {said}"


@pytest.mark.parametrize("step", STEP_CASES)
def test_every_launcher_builder_step_says_it_is_one_short_job(step):
    """REQ-071: answer 2, each `job: build` and `job: fix` step of the launcher says its kind."""
    assert JOB_WORDS in step, f"kit/templates/runtime/launcher.txt {step.split('`')[1]}: no short-job line"


@pytest.mark.parametrize(("name", "key", "file", "pairs"), CONFLICT_CASES)
def test_no_role_orders_what_it_bans(name, key, file, pairs):
    """REQ-071: answer 3, no role's files order a form they ban."""
    pytest.fail(f"{name} {key}: " + "; ".join(pairs))


def test_every_hook_guard_imports_and_decides():
    """REQ-071: answer 6, a guard that fails to import fails here, naming its hook."""
    for role in COMMANDING:
        if role.guard:
            assert callable(getattr(importlib.import_module(role.guard), "decide", None)), role.guard
    assert {r.guard for r in COMMANDING} >= {"conductor_guard", "steward_guard", "architect_guard", None}


def test_the_hand_lists_are_live():
    """REQ-071: answers 4 and 8, every entry has a reason and still names a case at its file."""
    ids = [p.id for p in FORM_CASES + START_CASES + STEP_CASES + CONFLICT_CASES if p.marks]
    for entry in EXPECTED:
        assert re.search(r"Q-[A-Z0-9]+-\d+|brief #\d+", entry.why), f"{entry.id}: no Q- id or brief"
        assert entry.form in (KIT / entry.file).read_text(encoding="utf-8"), f"{entry.id}: stale"
    assert len(ids) == len(EXPECTED) == len({e.id for e in EXPECTED}), "an entry matches no case or two"
    for (name, form), who in OTHERS_RUN.items():
        text = " ".join(s.read_text(encoding="utf-8") for s in ROLES[name].sources)
        assert form in text and who, f"OTHERS_RUN {name} {form}: stale"
    for file, pairs in MODE_SPLITS.items():
        text = (KIT / file).read_text(encoding="utf-8")
        assert all(f"\n{label}" in text for pair in pairs for label in pair), f"MODE_SPLITS {file}: stale"
    assert all(guide_paragraphs(r) for r in ROLE_PARAGRAPHS), "ROLE_PARAGRAPHS: a paragraph is gone"
    called = {c[:3] for c in calls()}
    assert set(START_PATHS) <= called, f"START_PATHS: stale {sorted(set(START_PATHS) - called)}"
