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
import re
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
# folder that holds `: number = "`, and TS7027 for one that holds `return 1;` then more code when
# the config sets `"allowUnreachableCode": false`, as `tsc --pretty false` prints it, relative to
# the cwd. `--listFilesOnly -p <config>` (brief #1890) prints the absolute path of each `.ts` file
# under the config's folder, or under its `include` folders (none for `"files": []`), and fails
# when `tsc-list-fails` exists.
TSC = """
import os, re, sys
conf = sys.argv[sys.argv.index("-p") + 1]
base, bad = os.path.dirname(conf) or ".", []
text = open(conf).read()
found = re.search(r'"include"\\s*:\\s*\\[([^\\]]*)\\]', text)
none = re.search(r'"files"\\s*:\\s*\\[\\s*\\]', text) is not None
dirs = re.findall(r'"([^"]+)"', found.group(1)) if found else [] if none else ["."]
tops = [os.path.join(base, d) for d in dirs]
listing = "--listFilesOnly" in sys.argv
if listing and os.path.exists("tsc-list-fails"):
    sys.exit(1)
reach = re.search(r'"allowUnreachableCode"\\s*:\\s*false', text) is not None
for root in tops if listing else [base]:
    for top, dirs, names in os.walk(root):
        dirs[:] = [d for d in dirs if d != "node_modules"]
        for name in sorted(names):
            path = os.path.relpath(os.path.join(top, name))
            if not name.endswith(".ts"):
                continue
            if listing:
                print(os.path.abspath(path))
                continue
            body = open(path).read()
            if ': number = "' in body:
                bad.append(path)
                msg = "error TS2322: Type 'string' is not assignable to type 'number'."
                print(path + "(1,14): " + msg)
            if reach and "return 1;\\n  " in body:
                bad.append(path)
                print(path + "(3,3): error TS7027: Unreachable code detected.")
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


# Brief #1890, ADR-0784: a floor rule that typescript-eslint turns off is met by its replacement
# rule, or, for a TypeScript file a strict tsconfig.json checks, by the compiler (`EQUIVALENT`).
# The 18 core rules typescript-eslint 8.46.2's `eslint-recommended` block turns off for `.ts`
# files, and `no-unused-vars`, which its `recommended` set turns off for every file.
TS_OFF = (
    "constructor-super", "getter-return", "no-class-assign", "no-const-assign", "no-dupe-args",
    "no-dupe-class-members", "no-dupe-keys", "no-func-assign", "no-import-assign",
    "no-new-native-nonconstructor", "no-obj-calls", "no-redeclare", "no-setter-return",
    "no-this-before-super", "no-undef", "no-unreachable", "no-unsafe-negation", "no-with",
)  # fmt: skip
TS_RULE = "@typescript-eslint/no-unused-vars"
UNREACHABLE = 'export function total(): number {\n  return 1;\n  console.log("example.com");\n}\n'


def stock(**over: object) -> dict[str, object]:
    """The printed rules of the stock `js.configs.recommended` with typescript-eslint's
    `recommended`, numeric severities as `--print-config` prints them."""
    rules: dict[str, object] = dict(floor_rules(), **{r: [0] for r in TS_OFF})
    rules.update({"no-unused-vars": [0], TS_RULE: [2], "no-var": [2]})
    rules.update(over)
    return rules


def strict_with(extra: str = "") -> str:
    return '{"compilerOptions": {"strict": true' + extra + "}}"


def floor_ids(root: Path, rel: str = "frontend/greet.ts") -> list[str]:
    entry = next(e for e in node_entries("web-app") if e["stack"] == "node")
    lines = node_pack.floor(root, entry, [(rel, "frontend/**")])
    return [ln.split("pack's rule ", 1)[1].split(" ", 1)[0].rstrip(",") for ln in lines]


def test_the_stock_typescript_config_leaves_only_no_unreachable(tmp_path: Path) -> None:
    """REQ-079: brief #1890 answers 1 to 3 and its Measured line (19 lines before, 1 after)."""
    root = sample(tmp_path, rules=stock(), tsconfig=strict_with())
    entry = next(e for e in node_entries("web-app") if e["stack"] == "node")
    lines = node_pack.floor(root, entry, [("frontend/greet.ts", "frontend/**")])
    assert lines == [
        "SPEC-0072 rule 8: the configuration does not enable the pack's rule no-unreachable, or "
        "the compiler with allowUnreachableCode off for a file a strict tsconfig.json checks "
        "(setting: standards.config)"
    ]
    no_values("\n".join(lines))


def test_allow_unreachable_code_false_meets_the_whole_floor(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """REQ-079: brief #1890 answer 2 (only `false` meets `no-unreachable`); the node-type step
    then catches unreachable code as TS7027."""
    for value, want in (("", ["no-unreachable"]), ("true", ["no-unreachable"]), ("false", [])):
        extra = f', "allowUnreachableCode": {value}' if value else ""
        root = sample(tmp_path / (value or "unset"), rules=stock(), tsconfig=strict_with(extra))
        assert floor_ids(root) == want, value
    root = tmp_path / "false"
    assert gates(root, capsys)[0] == 0
    (root / "frontend" / "greet.ts").write_text(UNREACHABLE, encoding="utf-8")
    code, out = gates(root, capsys)
    assert code == 1 and "standards node type: SPEC-0072 rule 6: type rule TS7027" in out


def test_without_the_core_set_the_other_floor_rules_are_still_named(tmp_path: Path) -> None:
    """REQ-079: brief #1890 answer 5 (61 before; 43, and 42 with allowUnreachableCode false)."""
    rules = {k: [0] for k in floor_rules()}
    rules.update({TS_RULE: [2], "no-var": [2]})
    root = sample(tmp_path / "a", rules=rules, tsconfig=strict_with())
    assert len(floor_ids(root)) == 43
    root = sample(
        tmp_path / "b", rules=rules, tsconfig=strict_with(', "allowUnreachableCode": false')
    )
    ids = floor_ids(root)
    assert len(ids) == 42 and not set(ids) & set(TS_OFF) and "no-unused-vars" not in ids


@pytest.mark.parametrize(
    "tsconfig",
    [
        '{"compilerOptions": {"strict": false}}',
        '{"compilerOptions": {"strict": true, "noImplicitAny": false}}',
        '{"compilerOptions": {"strict": true, "strictNullChecks": false}}',
    ],
)
def test_a_weak_compiler_meets_no_rule(tsconfig: str, tmp_path: Path) -> None:
    """REQ-079: brief #1890 answer 2 (all 18 named, beside the type floor's own lines)."""
    root = sample(tmp_path, rules=stock(), tsconfig=tsconfig)
    assert sorted(floor_ids(root)) == sorted(TS_OFF)


def test_a_javascript_file_meets_rules_by_rule_rows_only(tmp_path: Path) -> None:
    """REQ-079: brief #1890 answers 2 and 6 (a `.js` file never meets a rule by the compiler)."""
    rules = dict(floor_rules(), **{"no-unused-vars": [0], TS_RULE: [2]})
    root = sample(tmp_path, rules=rules, name="price.test.js", tsconfig=strict_with())
    assert floor_ids(root, "frontend/price.test.js") == []
    (root / "eslint-rules.json").write_text(
        json.dumps({"rules": dict(rules, **{"no-undef": "off"})}), encoding="utf-8"
    )
    assert floor_ids(root, "frontend/price.test.js") == ["no-undef"]


def test_no_redeclare_needs_no_var_on(tmp_path: Path) -> None:
    """REQ-079: brief #1890 answer 2 (TS2451 covers `let` and `const`, not `var`)."""
    root = sample(tmp_path, rules=stock(**{"no-var": "off"}), tsconfig=strict_with())
    assert floor_ids(root) == ["no-redeclare", "no-unreachable"]
    (root / "eslint-rules.json").write_text(
        json.dumps(
            {"rules": stock(**{"no-var": "off", "@typescript-eslint/no-redeclare": "warn"})}
        ),
        encoding="utf-8",
    )
    assert floor_ids(root) == ["no-unreachable"]  # the replacement rule meets it


def test_a_file_outside_the_program_or_a_failed_listing_meets_no_compiler_row(
    tmp_path: Path,
) -> None:
    """REQ-079: brief #1890 answers 2 and 6 (`include`; a listing that fails: the safe side)."""
    root = sample(
        tmp_path / "a",
        rules=stock(),
        tsconfig='{"compilerOptions": {"strict": true}, "include": ["src"]}',
    )
    assert sorted(floor_ids(root)) == sorted(TS_OFF)
    root = sample(tmp_path / "b", rules=stock(), tsconfig=strict_with())
    (root / "tsc-list-fails").write_text("", encoding="utf-8")
    assert sorted(floor_ids(root)) == sorted(TS_OFF)


def test_a_strict_referenced_config_counts(tmp_path: Path) -> None:
    """REQ-079: brief #1890 answers 2 and 6 (`references`: that config's program and options)."""
    root = sample(tmp_path, rules=stock(), tsconfig=SOLUTION)
    (root / "frontend" / "tsconfig.json").write_text(
        strict_with(', "allowUnreachableCode": false'), encoding="utf-8"
    )
    assert floor_ids(root) == []
    (root / "frontend" / "tsconfig.json").write_text(
        '{"compilerOptions": {"strict": false}}', encoding="utf-8"
    )
    assert sorted(floor_ids(root)) == sorted(TS_OFF)


@pytest.mark.parametrize(("level", "met"), [("warn", True), (1, True), ("off", False), (0, False)])
def test_the_replacement_rule_counts_at_warn_and_not_at_off(
    level: object, met: bool, tmp_path: Path
) -> None:
    """REQ-079: brief #1890 answer 6 (as core rules do)."""
    root = sample(
        tmp_path,
        rules=stock(**{TS_RULE: level}),
        tsconfig=strict_with(', "allowUnreachableCode": false'),
    )
    assert floor_ids(root) == ([] if met else ["no-unused-vars"])


def test_the_table_only_names_floor_codes_and_compiler_codes() -> None:
    """REQ-079: brief #1890 answer 8 (the table can neither add nor drop a floor code)."""
    for work_type in ("web-app", "mobile"):
        entry = next(e for e in node_entries(work_type) if e["stack"] == "node")
        codes = entry["rules"]["codes"]
        assert len(codes) == 61 and set(node_pack.EQUIVALENT) <= set(codes)
    assert set(node_pack.EQUIVALENT) == {*TS_OFF, "no-unused-vars"}
    for code, row in node_pack.EQUIVALENT.items():
        assert set(row) <= {"rule", "compiler", "needs"} and ("rule" in row or "compiler" in row)
        assert row.get("rule", f"@typescript-eslint/{code}") == f"@typescript-eslint/{code}"
        for ts in row.get("compiler", ()):
            assert re.fullmatch(r"TS\d+", ts), (code, ts)
        assert row.get("needs") in (None, "allowUnreachableCode", "no-var")
    assert node_pack.EQUIVALENT["no-unreachable"]["needs"] == "allowUnreachableCode"
    assert node_pack.EQUIVALENT["no-redeclare"]["needs"] == "no-var"
    assert "compiler" not in node_pack.EQUIVALENT["no-unused-vars"]


def test_an_adopted_stock_config_lowers_the_held_floor(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """REQ-079: brief #1890 answer 5 and its Measured line (`package.json 19` falls)."""
    root = sample(tmp_path, rules=stock(), tsconfig=strict_with())
    path = root / "agk.toml"
    path.write_text(path.read_text(encoding="utf-8").replace('"init"', '"adopt"'), "utf-8")
    base = root / "config" / "agk-baseline"
    base.mkdir(parents=True)
    (base / "standards-node-floor.txt").write_text("package.json 19\n", encoding="utf-8")
    code, out = gates(root, capsys)
    assert code == 0, out
    assert "baseline standards node floor: a count fell in 1 file" in out
    (base / "standards-node-floor.txt").write_text("package.json 1\n", encoding="utf-8")
    (root / "eslint-rules.json").write_text(
        json.dumps({"rules": stock(**{TS_RULE: "off"})}), encoding="utf-8"
    )
    code, out = gates(root, capsys)
    assert code == 1, out  # 1 to 2: a held count rose
