"""SPEC-0041 build (n): the personal-mode guide names what the code accepts, and nothing else.

Advances REQ-048 (AC8).

Brief #1510, answer 5. The commands, subcommands and options are found by asking the parsers of
`personal.py` and `personal_state.py` which words they accept, so a command added to the code and
left out of the guide fails here, and so does a command the guide names that the code refuses. The
settings are `common.PERSONAL_KEYS`. Answers 2 to 4: the security guide, the existing-codebase
guide and the README say what personal mode changes, and the live walk is recorded. No network.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import personal
import personal_state
from check_licence_notice import without_header
from common import PERSONAL_CHOICES, PERSONAL_KEYS, read_list

ROOT = Path(__file__).resolve().parents[2]
GUIDE = ROOT / "docs" / "guides" / "personal-mode.md"
SECURITY = ROOT / "docs" / "guides" / "security.md"
EXISTING = ROOT / "docs" / "guides" / "existing-codebase.md"
README = ROOT / "README.md"
WALK = ROOT / "docs" / "runs" / "personal-mode-walk.md"
# The tails a command may need before it parses: none, a record id, a required option, a step.
TAILS = ([], ["REQ-001"], ["--check"], ["--target", "t"])
NOT_A_WORD = "zz-not-a-command"


def _literals(module) -> set[str]:
    tree = ast.parse(Path(module.__file__).read_text(encoding="utf-8"))
    return {
        n.value for n in ast.walk(tree) if isinstance(n, ast.Constant) and isinstance(n.value, str)
    }


def _ok(module, args: list[str]) -> bool:
    return module.parse(list(args)) is not None


def accepted(module) -> tuple[set[str], set[str], set[str]]:
    """The commands, the `command step` pairs and the options that `module.parse` accepts."""
    words = {w for w in _literals(module) if re.fullmatch(r"[a-z][a-z-]*", w)}
    flags = {w for w in _literals(module) if re.fullmatch(r"--[a-z][a-z-]*", w)}
    commands, steps, forms = set(), set(), []
    for word in sorted(words):
        positional = _ok(module, [word, NOT_A_WORD])
        for tail in TAILS:
            if _ok(module, [word, *tail]):
                commands.add(word)
                forms.append([word, *tail])
        for step in sorted(words):
            if positional:
                break
            for form in ([word, step], [word, step, "x"]):
                if _ok(module, form):
                    commands.add(word)
                    steps.add(f"{word} {step}")
                    forms.append(form)
    options = {
        flag
        for flag in flags
        for form in forms
        if _ok(module, [*form, flag]) or _ok(module, [*form, flag, "x"])
    }
    return commands, steps, options


def guide() -> str:
    return without_header(GUIDE.read_text(encoding="utf-8"))


def _code(text: str) -> list[str]:
    """The inline code spans and the lines of the fenced code blocks."""
    blocks = re.findall(r"```[a-z]*\n(.*?)```", text, re.S)
    lines = [line for block in blocks for line in block.splitlines()]
    rest = re.sub(r"```[a-z]*\n.*?```", "", text, flags=re.S)
    return lines + re.findall(r"`([^`\n]+)`", rest)


def _named(text: str, script: str) -> list[list[str]]:
    """Each `script <word> [<word>]` the code of the text names, as the words after the name."""
    pattern = rf"{re.escape(script)} ([a-z][a-z-]*(?: [a-z][a-z-]*)?)"
    return [m.group(1).split() for part in _code(text) for m in re.finditer(pattern, part)]


def _code_lines(text: str, script: str) -> list[str]:
    """The lines of the fenced code blocks that run `script`."""
    blocks = re.findall(r"```[a-z]*\n(.*?)```", text, re.S)
    return [line for block in blocks for line in block.splitlines() if f"{script} " in line]


def test_parsers_are_probed() -> None:
    commands, steps, options = accepted(personal)
    assert {"baseline", "gate", "confirm", "export", "change", "hook"} <= commands
    assert {"change start", "change finish", "hook install", "hook remove"} <= steps
    assert {"--approve", "--sidecar", "--with-notes", "--check"} <= options
    assert {"id", "attach", "detach"} == accepted(personal_state)[0]


def test_every_command_and_option_the_code_accepts_is_in_the_guide() -> None:
    text = guide()
    for module, script in ((personal, "personal.py"), (personal_state, "personal_state.py")):
        commands, steps, options = accepted(module)
        named = _named(text, script)
        for command in sorted(commands):
            assert any(words[:1] == [command] for words in named), f"{script} {command}"
        for step in sorted(steps):
            assert any(words[:2] == step.split() for words in named), f"{script} {step}"
        for option in sorted(options):
            assert re.search(rf"(?<![\w-]){re.escape(option)}(?![\w-])", text), option


def test_the_guide_names_no_command_or_option_the_code_refuses() -> None:
    text = guide()
    for module, script in ((personal, "personal.py"), (personal_state, "personal_state.py")):
        commands, steps, options = accepted(module)
        for words in _named(text, script):
            assert words[0] in commands, f"{script} {words[0]} is not a command"
            if words[0] in {s.split()[0] for s in steps} and len(words) > 1:
                pair = " ".join(words[:2])
                assert pair in steps, pair
        for line in _code_lines(text, script):
            for flag in re.findall(r"(?<![\w-])--[a-z][a-z-]*", line):
                assert flag in options, f"{script}: {flag}"


def test_every_setting_is_in_the_guide_and_no_other() -> None:
    text = guide()
    for key in PERSONAL_KEYS:
        assert f"`{key}`" in text, key
    for values in PERSONAL_CHOICES.values():
        for value in values:
            assert f"`{value}`" in text, value
    rows = re.findall(r"^\| `([a-z_]+)` \|", text, re.M)
    assert rows and set(rows) == set(PERSONAL_KEYS)


def test_the_security_guide_says_what_stays_on_the_machine() -> None:
    text = SECURITY.read_text(encoding="utf-8")
    assert "\nNothing outside your repository.\n" not in text
    for part in (
        "AGK_HOME",
        "`0700`",
        "`0600`",
        "`quote_lines`",
        "`sync_remote`",
        "personal-mode.md",
    ):
        assert part in text, part


def test_the_existing_codebase_guide_allows_observed_behaviour_as_proposed() -> None:
    text = EXISTING.read_text(encoding="utf-8")
    assert "observed in code" in text
    paragraph = next(p for p in text.split("\n\n") if "observed in code" in p)
    for part in ("`Proposed`", "cit", "`done`", "test"):
        assert part in paragraph, part


def test_the_readme_states_the_limits_in_two_lines() -> None:
    lines = [
        line for line in README.read_text(encoding="utf-8").splitlines() if "ersonal mode" in line
    ]
    assert 1 <= len(lines) <= 2
    assert any("docs/guides/personal-mode.md" in line for line in lines)


def test_the_live_walk_is_recorded_on_an_invented_project() -> None:
    text = WALK.read_text(encoding="utf-8")
    for step in (
        "attach",
        "survey",
        "render",
        "confirm",
        "tests-first",
        "gate",
        "pr-summary",
        "report",
    ):
        assert step in text, step
    assert "export --check" in text and "detach" in text
    assert "git status --porcelain" in text
    hosts = set(re.findall(r"[a-z0-9.-]+\.(?:com|org|net|io)\b", text))
    assert hosts <= {"example.com"}, hosts


def test_the_new_files_carry_no_neutrality_token() -> None:
    tokens = [t.lower() for t in read_list((ROOT / "config" / "neutrality.txt").read_text("utf-8"))]
    for path in (GUIDE, WALK):
        body = path.read_text(encoding="utf-8").lower()
        assert not [t for t in tokens if t in body], path.name
