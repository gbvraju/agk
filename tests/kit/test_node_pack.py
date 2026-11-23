"""Tests of the Node standards pack (SPEC-0072 rules 6 and 8; REQ-079; briefs #1764 and #1766,
ADR-0739 and ADR-0740).

On a sample TypeScript web app with an Accepted stack record that chose Node, the pack's `floor`,
`node-lint` and `node-format` steps run the product's own `node_modules/.bin/` tools over
`project_lint_paths` (default: the layers' paths): a clean sample passes; a planted lint fault
fails naming the rule and the path class and no value; an unformatted file fails; a configuration
that turns a pinned rule off fails the floor naming the rule; a missing tool names `npm ci`; and
the pack is off without a Node stack or a `package.json`. The `node-type` step (brief #1766) runs
the product's `tsc --noEmit -p tsconfig.json`: a typed sample passes, a planted type fault fails
naming its `TS<n>` code, a weakened compiler setting (through `extends` and `references`) fails
the type floor naming the option, and a JavaScript-only product skips the step and says so. The
tools are stand-in scripts written
here (no network, no real install). Fixtures in `tmp_path` only: invented data (example.com).
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import pytest

KIT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KIT_ROOT / "scripts" / "agk"))

import check_playbooks  # noqa: E402
import run_gates  # noqa: E402
from gates import bom, node_pack, python_pack  # noqa: E402
from test_pins import with_lock  # noqa: E402

PLAYBOOKS = KIT_ROOT / "config" / "playbooks"
VALUES = ("greet.ts", "greeting", "hello", "example.com")
CLEAN = 'export const greeting = (name: string): string => "hello " + name; // example.com\n'
RECORD = """# ADR-0002: stack options

- Status: Accepted

1. **Options**
   - Option A — one web app at example.com. Parts: node 22.11.0 MIT, examplelib 1.2.3 MIT.
3. **Chosen**: Option A
"""
# The stand-in eslint: `--print-config` prints the rules of `eslint-rules.json`; a lint run
# reports `no-debugger` for a line `debugger;` and the "File ignored" warning for a file the
# config's `ignores` names, as ESLint's JSON format does.
ESLINT = """
import json, os, sys
conf = json.load(open("eslint-rules.json"))
args = sys.argv[1:]
if args[0] == "--print-config":
    print(json.dumps({"rules": conf["rules"]}))
    sys.exit(0)
out, bad = [], False
for name in [a for a in args if not a.startswith("-") and a not in ("0", "json")]:
    msgs = []
    if name in conf.get("ignores", []):
        msgs.append({"ruleId": None, "severity": 1, "message": "File ignored because of a pattern"})
    elif "debugger;" in open(name).read():
        msgs.append({"ruleId": "no-debugger", "severity": 2, "message": "Unexpected debugger"})
        bad = True
    out.append({"filePath": os.path.abspath(name), "messages": msgs})
print(json.dumps(out))
sys.exit(1 if bad or any(r["messages"] for r in out) else 0)
"""
# The stand-in prettier: a file holding a tab is not formatted; it records its arguments, and judges
# line ends as prettier does: `endOfLine` is `lf` unless `--end-of-line` says otherwise, and with
# `--config-precedence file-override` a `.prettierrc` or `.editorconfig` line end wins
# (brief #1839).
PRETTIER = """
import json, os, sys
args = sys.argv[1:]
json.dump(args, open("prettier-args.json", "w"))
eol, names, i = "lf", [], 1
while i < len(args):
    if args[i] in ("--end-of-line", "--config-precedence"):
        eol = args[i + 1] if args[i] == "--end-of-line" else eol
        i += 2
        continue
    names.append(args[i])
    i += 1
if "file-override" in args and os.path.isfile(".prettierrc"):
    eol = json.load(open(".prettierrc")).get("endOfLine", eol)
if "file-override" in args and os.path.isfile(".editorconfig"):
    for ln in open(".editorconfig"):
        if ln.replace(" ", "").startswith("end_of_line="):
            eol = ln.split("=", 1)[1].strip()
def bad(name):
    text = open(name, newline="").read()
    crlf = text.count("\\r\\n")
    wrong = {"lf": crlf > 0, "crlf": text.count("\\n") > crlf, "auto": False}[eol]
    return "\\t" in text or wrong
for name in [n for n in names if bad(n)]:
    print("[warn] " + name)
sys.exit(1 if any(bad(n) for n in names) else 0)
"""
# The stand-in tsc: `--noEmit -p <config>` reports TS2322 for each `.ts` file under the config's
# folder that holds `: number = "`, as `tsc --pretty false` prints it, relative to the cwd.
TSC = """
import os, sys
conf = sys.argv[sys.argv.index("-p") + 1]
base, bad = os.path.dirname(conf) or ".", []
for top, dirs, names in os.walk(base):
    dirs[:] = [d for d in dirs if d != "node_modules"]
    for name in sorted(names):
        path = os.path.relpath(os.path.join(top, name))
        if name.endswith(".ts") and ': number = "' in open(path).read():
            bad.append(path)
            print(path + "(1,14): error TS2322: Type 'string' is not assignable to type 'number'.")
sys.exit(2 if bad else 0)
"""
STRICT = (
    '{\n  // the product\'s own compiler settings\n  "compilerOptions": {"strict": true,},\n}\n'
)
SOLUTION = (
    '{"compilerOptions": {"strict": true}, "files": [], "references": [{"path": "frontend"}]}'
)
FAULT = 'export const count: number = "hello"; // example.com\n'


def floor_rules() -> dict[str, str]:
    entry = next(e for e in node_entries("web-app") if e["stack"] == "node")
    return {code: "error" for code in entry["rules"]["codes"]}


def node_entries(work_type: str) -> list[dict]:
    return check_playbooks.standard(PLAYBOOKS / f"{work_type}.toml", KIT_ROOT)[1]


@pytest.fixture(autouse=True)
def _no_bill(monkeypatch: pytest.MonkeyPatch) -> None:
    """Brief #1776: the sample's new lock would start the `bom` step, which these samples never
    ran (they had no lock) and which needs a committed, installed project; it has its own tests."""
    monkeypatch.setattr(bom, "applies", lambda _root: False)


def sample(tmp: Path, code: str = CLEAN, rules: dict | None = None, **kw: object) -> Path:
    shutil.copytree(PLAYBOOKS, tmp / "config" / "playbooks")
    toml = kw.get("toml", "")
    (tmp / "agk.toml").write_text(
        f'mode = "init"\n{toml}\n[delivery]\nwork_type = "{kw.get("work_type", "web-app")}"\n',
        encoding="utf-8",
    )
    if kw.get("package", True):
        (tmp / "package.json").write_text('{"devDependencies": {}}\n', encoding="utf-8")
    (tmp / "docs" / "adr").mkdir(parents=True)
    record = RECORD.replace("node 22", f"{kw.get('runtime', 'node')} 22")
    (tmp / "docs" / "adr" / "0002-stack-options.md").write_text(record, encoding="utf-8")
    conf = {"rules": floor_rules() if rules is None else rules, "ignores": kw.get("ignores", [])}
    (tmp / "eslint-rules.json").write_text(json.dumps(conf), encoding="utf-8")
    bin_dir = tmp / "node_modules" / ".bin"
    bin_dir.mkdir(parents=True)
    if kw.get("tsconfig", STRICT) is not None:
        (tmp / "tsconfig.json").write_text(str(kw.get("tsconfig", STRICT)), encoding="utf-8")
    for name, body in (("eslint", ESLINT), ("prettier", PRETTIER), ("tsc", TSC)):
        if name in kw.get("missing", ()):
            continue
        tool = bin_dir / name
        tool.write_text(f"#!{sys.executable}\n{body}", encoding="utf-8")
        tool.chmod(0o755)
    (tmp / "frontend").mkdir()
    (tmp / "frontend" / str(kw.get("name", "greet.ts"))).write_text(code, encoding="utf-8")
    (tmp / "node_modules" / "dep.js").write_text("debugger;\n", encoding="utf-8")  # never read
    if kw.get("package", True):
        with_lock(tmp, "node")  # brief #1776: the pins step reads the lock
    return tmp


def gates(root: Path, capsys: pytest.CaptureFixture[str]) -> tuple[int, str]:
    code = run_gates.main(["--root", str(root)])
    out = capsys.readouterr()
    return code, out.out + out.err


def no_values(text: str) -> None:
    for word in VALUES:
        assert word not in text, word


@pytest.mark.parametrize("work_type", ["web-app", "mobile"])
def test_each_playbook_carries_the_node_entry(work_type: str) -> None:
    """REQ-079: brief #1764 answer 5 (no version: the product's own pins hold it)."""
    _, packs, problems = check_playbooks.standard(PLAYBOOKS / f"{work_type}.toml", KIT_ROOT)
    assert problems == []
    entry = {e["stack"]: e for e in packs}["node"]
    assert (entry["lint"], entry["format"], entry["type"]) == node_pack.STEP_NAMES
    assert entry["config"] == "package.json"
    assert entry["rules"]["tool"] == "eslint" and "version" not in entry["rules"]
    assert {"no-debugger", "no-unused-vars", "no-undef"} <= set(entry["rules"]["codes"])
    assert "node_pack" in run_gates.PACKS


@pytest.mark.parametrize("work_type", ["web-app", "mobile"])
def test_a_clean_sample_passes(
    work_type: str, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """REQ-079: brief #1764 answers 1 to 4 (the vendored file is never read)."""
    code, out = gates(sample(tmp_path, work_type=work_type), capsys)
    assert code == 0, out
    assert "ok standards node" in out and "no pack for node" not in out
    assert "standards node type" not in out and "TypeScript" not in out


def test_a_planted_lint_fault_fails_naming_the_rule_and_path_class(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """REQ-079: the brief's Measured line."""
    code, out = gates(sample(tmp_path, "debugger;\n" + CLEAN), capsys)
    assert code == 1
    assert "FAIL gates: standards node lint: SPEC-0072 rule 6: lint rule no-debugger" in out
    assert "(path class: frontend/**)" in out
    no_values(out)


def test_an_unformatted_file_fails(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """REQ-079: brief #1764 answer 4."""
    code, out = gates(sample(tmp_path, "\t" + CLEAN), capsys)
    assert code == 1
    assert "standards node format: SPEC-0072 rule 6: the file is not formatted, prettier" in out
    assert "(path class: frontend/**)" in out
    no_values(out)


@pytest.mark.parametrize("severity", ["off", 0, ["off"]])
def test_a_pinned_rule_turned_off_fails_the_floor(
    severity: object, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """REQ-079: brief #1764 answer 3 (each missing rule named by its id; `warn` counts as on)."""
    rules: dict[str, object] = dict(floor_rules(), **{"no-debugger": severity})
    rules["no-undef"] = "warn"
    del rules["no-empty"]
    code, out = gates(sample(tmp_path, rules=rules), capsys)
    assert code == 1
    lines = [ln for ln in out.splitlines() if "standards node floor" in ln]
    assert len(lines) == 2, out
    for rule in ("no-debugger", "no-empty"):
        assert any(f"pack's rule {rule} (setting: standards.config)" in ln for ln in lines)


@pytest.mark.parametrize("tool", ["eslint", "prettier", "tsc"])
def test_a_missing_tool_names_npm_ci(
    tool: str, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """REQ-079: brief #1764 answer 2 (never a download, never a version)."""
    code, out = gates(sample(tmp_path, missing=(tool,)), capsys)
    assert code == 1
    assert f"the pack's tool {tool} is not installed" in out and "install: npm ci" in out


@pytest.mark.parametrize("case", ["python", "no-package"])
def test_the_pack_is_off_without_a_node_stack_or_package_json(case: str, tmp_path: Path) -> None:
    """REQ-079: brief #1764 answers 1 and 7."""
    kw = {"runtime": "python"} if case == "python" else {"package": False}
    root = sample(tmp_path, **kw)
    assert not node_pack.on(root)
    assert not any(
        "standards node" in line
        for _, line in run_gates.pack_results(PLAYBOOKS / "web-app.toml", root)
    )


def test_an_ignored_file_is_not_counted(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """REQ-079: brief #1764 answer 7 (the config's `ignores`)."""
    root = sample(tmp_path, ignores=["frontend/greet.ts"])
    (root / "frontend" / "other.ts").write_text(CLEAN, encoding="utf-8")
    code, out = gates(root, capsys)
    assert code == 0, out


def test_project_lint_paths_chooses_the_files_and_a_bad_form_is_refused(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """REQ-079: brief #1764 answer 6 (the setting is read as for Python)."""
    root = sample(tmp_path, "debugger;\n", toml='project_lint_paths = ["web/**"]')
    (root / "web").mkdir()
    (root / "web" / "main.mjs").write_text(CLEAN, encoding="utf-8")
    assert node_pack.files(root, node_pack.patterns(root)) == [("web/main.mjs", "web/**")]
    assert gates(root, capsys)[0] == 0
    (root / "agk.toml").write_text(
        'project_lint_paths = "web"\n[delivery]\nwork_type = "web-app"\n', encoding="utf-8"
    )
    code, out = gates(root, capsys)
    assert code == 1 and "(setting: project_lint_paths)" in out


def test_a_planted_type_fault_fails_naming_its_code(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """REQ-079: brief #1766 answer 1 and its Measured line."""
    code, out = gates(sample(tmp_path, FAULT), capsys)
    assert code == 1
    assert "FAIL gates: standards node type: SPEC-0072 rule 6: type rule TS2322" in out
    assert "(path class: frontend/**)" in out
    no_values(out)
    assert "count" not in out and "assignable" not in out


def test_the_type_step_fills_the_tally(tmp_path: Path) -> None:
    """REQ-079: brief #1766 answer 3 (per-file counts, as the Python pack's)."""
    root = sample(tmp_path, FAULT)
    entry = next(e for e in node_entries("web-app") if e["stack"] == "node")
    tally: dict[str, dict[str, int]] = {}
    steps = dict(node_pack.run(root, entry, tally))
    assert tally["type"] == {"frontend/greet.ts": 1}
    assert steps["type-floor"] == []


@pytest.mark.parametrize(
    ("options", "named"),
    [
        ('"strict": false', ["strict"]),
        ('"target": "es2022"', ["strict"]),
        ('"strict": true, "noImplicitAny": false', ["noImplicitAny"]),
        (
            '"strict": true, "strictNullChecks": false, "noImplicitAny": false',
            ["noImplicitAny", "strictNullChecks"],
        ),
    ],
)
def test_a_weakened_compiler_setting_fails_the_floor(
    options: str, named: list[str], tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """REQ-079: brief #1766 answer 2 (each option named, never its value)."""
    root = sample(tmp_path, tsconfig='{"compilerOptions": {' + options + "}}")
    code, out = gates(root, capsys)
    assert code == 1
    lines = [ln for ln in out.splitlines() if "standards node type-floor" in ln]
    assert len(lines) == len(named), out
    for opt in named:
        assert any(f"compiler option {opt} (path class: tsconfig.json)" in ln for ln in lines)
    assert "false" not in out and "es2022" not in out


def test_the_extends_chain_is_read_inside_the_product(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """REQ-079: brief #1766 answers 2 and 6 (own base file; a package base when installed)."""
    root = sample(tmp_path, tsconfig='{"extends": "./tsconfig.base.json"}')
    (root / "tsconfig.base.json").write_text(STRICT, encoding="utf-8")
    assert gates(root, capsys)[0] == 0
    (root / "tsconfig.json").write_text(
        '{"extends": ["./tsconfig.base.json", "@example/tsconfig/weak.json"]}', encoding="utf-8"
    )
    assert gates(root, capsys)[0] == 0  # the package is not installed: the product's own files
    pkg = root / "node_modules" / "@example" / "tsconfig"
    pkg.mkdir(parents=True)
    (pkg / "weak.json").write_text('{"compilerOptions": {"strictNullChecks": false}}', "utf-8")
    code, out = gates(root, capsys)
    assert code == 1 and "compiler option strictNullChecks (path class: tsconfig.json)" in out


def test_a_referenced_config_is_checked(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """REQ-079: brief #1766 answer 6 (`references`, each config on its own)."""
    root = sample(tmp_path, tsconfig=SOLUTION)
    (root / "frontend" / "tsconfig.json").write_text(
        '{"compilerOptions": {"strict": false}}', encoding="utf-8"
    )
    code, out = gates(root, capsys)
    assert code == 1
    assert "compiler option strict (path class: tsconfig.json references)" in out
    (root / "frontend" / "tsconfig.json").write_text(STRICT, encoding="utf-8")
    (root / "frontend" / "greet.ts").write_text(FAULT, encoding="utf-8")
    code, out = gates(root, capsys)
    assert code == 1 and "type rule TS2322 (path class: frontend/**)" in out


def test_typescript_files_without_a_tsconfig_fail(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """REQ-079: brief #1766 answer 4."""
    code, out = gates(sample(tmp_path, tsconfig=None), capsys)
    assert code == 1
    assert "node type-floor: SPEC-0072 rule 8: the compiler configuration is missing" in out
    assert "(path class: tsconfig.json)" in out


def test_a_javascript_only_product_skips_the_type_step(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """REQ-079: brief #1766 answer 1 (no tsc and no tsconfig needed, and it says so)."""
    root = sample(tmp_path, name="greet.mjs", tsconfig=None, missing=("tsc",))
    code, out = gates(root, capsys)
    assert code == 0, out
    assert "standards node: the type step is skipped: no TypeScript file" in out
    assert "ok standards node" in out


def test_the_floors_fill_the_tally(tmp_path: Path) -> None:
    """REQ-079: brief #1837 answer 1 (one line per configuration read, counting its floor lines)."""
    rules: dict[str, object] = dict(floor_rules(), **{"no-debugger": "off", "no-empty": 0})
    root = sample(tmp_path, rules=rules, tsconfig=SOLUTION)
    (root / "frontend" / "tsconfig.json").write_text(
        '{"compilerOptions": {"strict": false, "noImplicitAny": false}}', encoding="utf-8"
    )
    entry = next(e for e in node_entries("web-app") if e["stack"] == "node")
    tally: dict[str, dict[str, int]] = {}
    node_pack.run(root, entry, tally)
    assert tally["floor"] == {"package.json": 2}
    assert tally["type-floor"] == {"frontend/tsconfig.json": 2}
    (root / "eslint-rules.json").unlink()
    tally = {}
    node_pack.run(root, entry, tally)
    assert tally["floor"] == {"package.json": 1}  # an unreadable configuration counts 1


def test_no_file_in_scope_is_one_reason(tmp_path: Path) -> None:
    """REQ-079: brief #1837 answer 3 (no step runs)."""
    root = sample(tmp_path, toml='project_lint_paths = ["web/**"]')
    entry = next(e for e in node_entries("web-app") if e["stack"] == "node")
    assert node_pack.run(root, entry, {}) == [(python_pack.NO_FILE, [])]


def crlf(text: str) -> str:
    return text.replace("\n", "\r\n")


def test_the_format_step_judges_content_and_keeps_each_files_line_end(tmp_path: Path) -> None:
    """REQ-079: brief #1839 answers 1 and 7 (the argument list; a CRLF twin passes as with ruff)."""
    root = sample(tmp_path, crlf(CLEAN))
    found = [("frontend/greet.ts", "frontend/**")]
    tally: dict[str, int] = {}
    assert node_pack.format_check(root, found, tally) == [] and tally == {}
    args = json.loads((root / "prettier-args.json").read_text(encoding="utf-8"))
    assert args == [*node_pack.FORMAT_FLAGS, "frontend/greet.ts"]
    assert node_pack.FORMAT_FLAGS == (
        "--check", "--end-of-line", "auto", "--config-precedence", "file-override",
    )  # fmt: skip


@pytest.mark.parametrize(
    ("config", "eol", "fails"),
    [
        (".prettierrc", "lf", True),
        (".prettierrc", "crlf", False),
        (".prettierrc", "auto", False),
        (".prettierrc", None, False),
        (".editorconfig", "lf", True),
        (".editorconfig", "crlf", False),
        (None, None, False),
    ],
)
def test_a_projects_own_line_end_choice_still_wins(
    config: str | None, eol: str | None, fails: bool, tmp_path: Path
) -> None:
    """REQ-079: brief #1839 answers 1 and 5 (a project's own `endOfLine` or `end_of_line`)."""
    root = sample(tmp_path, crlf(CLEAN))
    if config == ".prettierrc":
        body = json.dumps({"endOfLine": eol} if eol else {"semi": True})
        (root / config).write_text(body, encoding="utf-8")
    elif config:
        (root / config).write_text(f"root = true\n[*]\nend_of_line = {eol}\n", encoding="utf-8")
    tally: dict[str, int] = {}
    out = node_pack.format_check(root, [("frontend/greet.ts", "frontend/**")], tally)
    want = ["SPEC-0072 rule 6: the file is not formatted, prettier (path class: frontend/**)"]
    assert out == (want if fails else []) and tally == ({"frontend/greet.ts": 1} if fails else {})


def test_a_crlf_twin_passes_the_whole_pack_with_no_line_end_set(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """REQ-079: brief #1839 answer 1 (the `governance` lines of a Git for Windows checkout)."""
    code, out = gates(sample(tmp_path, crlf(CLEAN)), capsys)
    assert code == 0, out
    assert "not formatted" not in out


REAL = shutil.which("prettier")


@pytest.mark.skipif(REAL is None, reason="prettier is not installed here")
@pytest.mark.parametrize(("rc", "fails"), [(None, False), ('{"endOfLine": "lf"}', True)])
def test_the_real_prettier_keeps_a_crlf_files_line_end(
    rc: str | None, fails: bool, tmp_path: Path
) -> None:
    """REQ-079: brief #1839 answers 1 and 7 (the real tool, where it is installed)."""
    root = sample(tmp_path, crlf('export const greeting = "hello";\n'))
    link = root / "node_modules" / ".bin" / "prettier"
    link.unlink()
    link.symlink_to(str(REAL))
    if rc is not None:
        (root / ".prettierrc").write_text(rc, encoding="utf-8")
    out = node_pack.format_check(root, [("frontend/greet.ts", "frontend/**")])
    assert bool(out) is fails, out
