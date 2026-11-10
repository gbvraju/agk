"""The real token figure, the prices table and the cost per kind (SPEC-0045 rules 2, 8 and 9).

REQ-052 AC7, brief #798 build (a) (amendment 145, items 7 to 10 and 13). `usage.py` sums, over the
entries of the running session's own transcript with a distinct message id, the four token counts
of each usage record and prints `Usage: <n> tokens`, or `Usage: not shown`; `--since` keeps the
entries at or after a time. `config.model_prices` reads the optional `[models.prices]` table.
`metrics.py --usage-by-kind` prints one line per merged pull request and, with a prices table, one
cost line per kind. Invented transcripts in `tmp_path`, invented data, no network. The tests were
written first.
"""

from __future__ import annotations

import json
import subprocess  # nosec B404 - fixed argument lists, no shell
import sys
import tomllib
from pathlib import Path

import pytest

import config

KIT = Path(__file__).resolve().parents[2]
SCRIPT = KIT / "scripts" / "agk" / "usage.py"
MARKER = "zebra-marker-7f3"  # transcript text that must never reach the output
SESSION = "0a1b2c3d-0000-4000-8000-00000000abcd"


def entry(mid, at, inp=0, made=0, read=0, out=0, text=MARKER, usage=True) -> dict:
    message = {"id": mid, "role": "assistant", "content": [{"type": "text", "text": text}]}
    if usage:
        message["usage"] = {
            "input_tokens": inp,
            "cache_creation_input_tokens": made,
            "cache_read_input_tokens": read,
            "output_tokens": out,
            "service_tier": "standard",
        }
    return {"type": "assistant", "timestamp": at, "message": message, "cwd": "/home/x"}


ENTRIES = [
    {"type": "user", "timestamp": "2026-11-10T08:00:00.000Z", "message": {"content": MARKER}},
    entry("msg_1", "2026-11-10T08:00:01.000Z", 2, 300, 1000, 40),
    entry("msg_1", "2026-11-10T08:00:01.500Z", 2, 300, 1000, 40),  # the same message again
    entry("msg_2", "2026-11-10T09:00:00.000Z", 1, 0, 2000, 7),
    entry("msg_3", "2026-11-10T10:30:00.000Z", 5, 10, 500, 100),
]


def write(path: Path, entries, tail: str = "") -> Path:
    lines = [json.dumps(e) for e in entries]
    path.write_text("\n".join(lines) + "\n" + tail, encoding="utf-8")
    return path


def usage(*args: str, env: dict | None = None, cwd: Path | None = None):
    full = {"PATH": "/usr/bin:/bin", "HOME": str(cwd or KIT)}
    full.update(env or {})
    return subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, str(SCRIPT), *args],
        capture_output=True,
        text=True,
        env=full,
        cwd=cwd or KIT,
    )


# --- rule 8: the figure ---------------------------------------------------------------------------


def test_ac7_each_message_id_is_summed_once_over_the_four_counts(tmp_path):
    """REQ-052 AC7: rule 8, the sum over distinct message ids."""
    path = write(tmp_path / "t.jsonl", ENTRIES)
    proc = usage("--transcript", str(path))
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert proc.stdout == "Usage: 3965 tokens\n"  # 1342 + 2008 + 615, msg_1 once


def test_ac7_since_drops_the_earlier_entries(tmp_path):
    """REQ-052 AC7: rule 8, `--since` gives the tokens since the previous `Report:`."""
    path = write(tmp_path / "t.jsonl", ENTRIES)
    assert usage("--transcript", str(path), "--since", "2026-11-10T09:00:00Z").stdout == (
        "Usage: 2623 tokens\n"
    )
    assert usage("--transcript", str(path), "--since", "2026-11-10T11:00:00Z").stdout == (
        "Usage: not shown\n"
    )


def test_ac7_a_message_counted_before_since_is_never_counted_again(tmp_path):
    """REQ-052 AC7: rule 8, no token is counted twice across two `Report:` lines."""
    rows = [
        entry("msg_9", "2026-11-10T08:59:59Z", 1, 1, 1, 1),
        entry("msg_9", "2026-11-10T09:00:05Z", 1, 1, 1, 1),
    ]
    path = write(tmp_path / "t.jsonl", rows)
    assert usage("--transcript", str(path), "--since", "2026-11-10T09:00:00Z").stdout == (
        "Usage: not shown\n"
    )


@pytest.mark.parametrize("case", ["missing", "folder", "not-utf8", "no-usage", "broken-lines"])
def test_ac7_no_file_an_unreadable_file_or_no_usage_record_is_not_shown(tmp_path, case):
    """REQ-052 AC7: rule 8, never 0 for a missing figure and never an estimate."""
    path = tmp_path / "t.jsonl"
    if case == "folder":
        path.mkdir()
    elif case == "not-utf8":
        path.write_bytes(b"\xff\xfe\x00{")
    elif case == "no-usage":
        write(path, [entry("msg_1", "2026-11-10T08:00:00Z", usage=False), ENTRIES[0]])
    elif case == "broken-lines":
        path.write_text('{"message": [1]}\nnot json\n[1, 2]\n', encoding="utf-8")
    proc = usage("--transcript", str(path))
    assert proc.returncode == 0 and proc.stdout == "Usage: not shown\n", proc.stdout + proc.stderr


def test_ac7_a_broken_last_line_is_skipped_and_the_rest_is_summed(tmp_path):
    """REQ-052 AC7: rule 8, a line still being written does not hide the figure."""
    path = write(tmp_path / "t.jsonl", ENTRIES[3:4], tail='{"type": "assist')
    assert usage("--transcript", str(path)).stdout == "Usage: 2008 tokens\n"


def test_ac7_the_output_never_holds_the_transcript_text(tmp_path):
    """REQ-052 AC7: rule 8, no text of the transcript is printed."""
    path = write(tmp_path / "t.jsonl", ENTRIES)
    for args in ([], ["--since", "2026-11-10T09:00:00Z"]):
        proc = usage("--transcript", str(path), *args)
        assert MARKER not in proc.stdout + proc.stderr and "/home/x" not in proc.stdout


def test_ac7_the_session_transcript_is_found_by_the_runtime_variable(tmp_path):
    """REQ-052 AC7: rule 8, the runtime's session id under its home folder (verify, Q-798-5)."""
    home = tmp_path / "rt"
    folder = home / "projects" / "-work-x"
    folder.mkdir(parents=True)
    write(folder / f"{SESSION}.jsonl", ENTRIES)
    env = {"CLAUDE_CONFIG_DIR": str(home), "CLAUDE_CODE_SESSION_ID": SESSION}
    assert usage(env=env, cwd=tmp_path).stdout == "Usage: 3965 tokens\n"
    for bad in ("", "../x", "a/b", "0a1b*"):
        assert usage(env=env | {"CLAUDE_CODE_SESSION_ID": bad}, cwd=tmp_path).stdout == (
            "Usage: not shown\n"
        )
    assert usage(env={"CLAUDE_CONFIG_DIR": str(home)}, cwd=tmp_path).stdout == "Usage: not shown\n"


def test_ac7_the_default_home_is_the_runtime_folder_under_home(tmp_path):
    """REQ-052 AC7: rule 8, without the folder variable the home is `~/.claude` (verify, Q-798-5)."""
    folder = tmp_path / ".claude" / "projects" / "-p"
    folder.mkdir(parents=True)
    write(folder / f"{SESSION}.jsonl", ENTRIES[3:])
    env = {"CLAUDE_CODE_SESSION_ID": SESSION, "HOME": str(tmp_path)}
    assert usage(env=env, cwd=tmp_path).stdout == "Usage: 2623 tokens\n"


@pytest.mark.parametrize(
    "args",
    [["--since"], ["--since", "yesterday-9"], ["--transcript"], ["--odd-flag-9"], ["x-9"]],
)
def test_ac7_a_bad_argument_is_refused_naming_the_option_not_the_value(tmp_path, args):
    """REQ-052 AC7: rule 8, refusals name the setting, never the value (principle 8)."""
    proc = usage(*args, cwd=tmp_path)
    assert proc.returncode == 2 and proc.stdout.startswith("usage: usage.py")
    assert "yesterday-9" not in proc.stdout and "odd-flag-9" not in proc.stdout
    assert "x-9" not in proc.stdout


def test_ac7_the_command_runs_with_the_network_blocked(tmp_path):
    """REQ-052 AC7: rule 8, no network call: every socket refuses and the figure still prints."""
    path = write(tmp_path / "t.jsonl", ENTRIES)
    code = (
        "import socket, runpy, sys\n"
        "def no(*a, **k):\n    raise OSError('network blocked')\n"
        "socket.socket = no; socket.create_connection = no; socket.getaddrinfo = no\n"
        f"sys.argv = ['usage.py', '--transcript', {str(path)!r}]\n"
        f"runpy.run_path({str(SCRIPT)!r}, run_name='__main__')\n"
    )
    proc = subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, "-c", code], capture_output=True, text=True, cwd=tmp_path
    )
    assert proc.stdout == "Usage: 3965 tokens\n", proc.stdout + proc.stderr
    text = SCRIPT.read_text(encoding="utf-8")
    assert "urllib" not in text and "socket" not in text and "subprocess" not in text


def test_ac7_the_command_writes_no_file(tmp_path):
    """REQ-052 AC7: rule 8, read-only."""
    path = write(tmp_path / "t.jsonl", ENTRIES)
    before = sorted(p.name for p in tmp_path.iterdir())
    usage("--transcript", str(path), cwd=tmp_path)
    assert sorted(p.name for p in tmp_path.iterdir()) == before


def test_ac7_session_rules_8_and_17_take_the_line_of_usage_py():
    """REQ-052 AC7: rule 8, the `Report:` and `Progress:` lines take the printed line."""
    text = (KIT / "config" / "session-rules.md").read_text(encoding="utf-8")
    rules = {x.split(". ", 1)[0]: x for x in text.splitlines() if x[:3].rstrip(". ").isdigit()}
    for n in ("8", "17"):
        assert "`python3 scripts/agk/usage.py`" in rules[n], n
    assert "`Usage: not shown`" in rules["17"] and "never 0" in rules["17"]


# --- rules 2 and 8: the prices table --------------------------------------------------------------

ODD = "turbo-x"  # an invented value that a refusal must never echo


def project(tmp_path: Path, text: str) -> Path:
    (tmp_path / "agk.toml").write_text(text, encoding="utf-8")
    return tmp_path


def test_ac7_no_prices_table_reads_as_empty(tmp_path):
    """REQ-052 AC7: rule 8, the table is optional."""
    assert config.model_prices(project(tmp_path, "[flow]\n")) == {}
    assert config.model_prices(project(tmp_path, '[models]\nbuild = { tier = "mid", effort = "low" }\n')) == {}


def test_ac7_a_prices_table_reads_and_the_kinds_still_read(tmp_path):
    """REQ-052 AC7: rules 2 and 8, `prices` is a key of `[models]` beside the kinds."""
    root = project(tmp_path, "[models.prices]\nstrongest = 15\nmid = 3.5\nfast = 0\n")
    assert config.model_prices(root) == {"strongest": 15, "mid": 3.5, "fast": 0}
    assert config.model_settings(root)["build"] == {"tier": "strongest", "effort": "medium"}


@pytest.mark.parametrize(
    ("text", "setting"),
    [
        (f'[models]\nprices = "{ODD}"\n', "models.prices"),
        (f"[models.prices]\n{ODD.replace('-', '_')} = 1\n", "models.prices"),
        (f'[models.prices]\nmid = "{ODD}"\n', "models.prices.mid"),
        ("[models.prices]\nmid = -1\n", "models.prices.mid"),
        ("[models.prices]\nfast = true\n", "models.prices.fast"),
        ("[models.prices]\nstrongest = nan\n", "models.prices.strongest"),
        ("[models.prices]\nstrongest = inf\n", "models.prices.strongest"),
        ("[models.prices]\nstrongest = [1]\n", "models.prices.strongest"),
    ],
)
def test_ac7_a_bad_prices_table_is_refused_naming_the_setting(tmp_path, text, setting):
    """REQ-052 AC7: rule 8, refused naming the setting, never the value."""
    root = project(tmp_path, text)
    for read in (config.model_prices, config.model_settings):
        with pytest.raises(config.ModelSettingError) as caught:
            read(root)
        assert f"(setting: {setting})" in str(caught.value)
        assert ODD not in str(caught.value) and "turbo_x" not in str(caught.value)


def test_ac7_the_kit_ships_no_prices_table():
    """REQ-052 AC7: rule 8, the kit's agk.toml and templates carry no `[models.prices]`."""
    paths = [KIT / "agk.toml", *sorted((KIT / "kit" / "templates").rglob("*.toml"))]
    assert len(paths) > 1
    for path in paths:
        assert "[models.prices]" not in path.read_text(encoding="utf-8"), path
    models = tomllib.loads((KIT / "agk.toml").read_text(encoding="utf-8")).get("models", {})
    assert "prices" not in models


# --- rule 9: one line per pull request and the cost per kind --------------------------------------

PROTECTED = "constitution/\nconfig/\n.claude/\n.github/\ndocs/requirements.md\nscripts/agk/\ntests/kit/\n"


def brief(size: str, touches: str) -> dict:
    return {"number": 0, "body": f'Sentence: "A widget shows its price."\n\nSize: {size}\nTouches: {touches}\n'}


BRIEFS = {11: brief("S", "tests/kit/**"), 12: brief("M", "src/**")}  # small, build


def pull(number, brief_n, used, state="merged") -> dict:
    return {
        "number": number,
        "state": state,
        "created_at": "2026-10-20T08:00:00Z",
        "merged_at": "2026-10-20T10:00:00Z" if state == "merged" else None,
        "usage": used,
        "brief": brief_n,
        "verdicts": [],
    }


PULLS = [
    pull(21, 11, 2_000_000),  # small at mid
    pull(22, 11, "not-reported"),
    pull(23, 11, 1_000_000),  # small, but it escalated: priced at strongest
    pull(24, 12, 500_000),  # build at strongest
    pull(25, 12, 9_999_999, state="closed"),
]
REPORTS = {
    21: ["Report: abc1234 ready for review; Usage: 2000000 tokens"],
    23: [
        "Report: abc1234 escalate the same check failed twice; Usage: 600000 tokens",
        "Report: def5678 ready for review; Usage: 400000 tokens",
    ],
    24: ["Report: abc1234 ready for review\nRoute: build strongest via strongest; Usage: 1 tokens"],
}


@pytest.fixture
def setup(repo, tmp_path_factory):
    data = tmp_path_factory.mktemp("data")
    repo.write("config/protected-paths.txt", PROTECTED)
    repo.write("config/reviewers.yaml", "version: 1\nverdict_authors: [reviewer]\n")
    api = data / "api"
    api.mkdir()
    for n, item in BRIEFS.items():
        (api / f"issue-{n}.json").write_text(json.dumps(item | {"number": n}), encoding="utf-8")
    for n in (21, 22, 23, 24):
        bodies = REPORTS.get(n, [])
        rows = [{"id": i, "body": b, "user": {"login": "builder"}} for i, b in enumerate(bodies)]
        (api / f"comments-{n}.json").write_text(json.dumps(rows), encoding="utf-8")
    facts = data / "facts.json"
    facts.write_text(json.dumps({"schema": 1, "pull_requests": PULLS}), encoding="utf-8")
    return repo, api, facts


def section(text: str, kind: str) -> list[str]:
    lines = text.splitlines()
    start = next(i for i, x in enumerate(lines) if x.startswith(f"{kind}: "))
    out = []
    for x in lines[start + 1 :]:
        if not x.startswith("  "):
            break
        out.append(x.strip())
    return out


def test_ac7_each_merged_pull_request_has_its_own_line(setup):
    """REQ-052 AC7: rule 9, `#<n> <tokens or not reported>` under each kind's line."""
    repo, api, facts = setup
    proc = repo.run("metrics.py", "--usage-by-kind", str(facts), "--api-dir", str(api))
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert section(proc.stdout, "small") == ["#21 2000000", "#22 not reported", "#23 1000000"]
    assert section(proc.stdout, "build") == ["#24 500000"]
    assert "cost" not in proc.stdout and "#25" not in proc.stdout  # no table: tokens only


def test_ac7_a_prices_table_adds_one_cost_line_per_kind(setup):
    """REQ-052 AC7: rule 9, priced at the kind's tier, or at strongest after an escalation or a
    `Route:` line (Q-798-9); `not reported` adds no cost and is counted."""
    repo, api, facts = setup
    repo.write("agk.toml", "[models.prices]\nstrongest = 15\nmid = 3\n")
    proc = repo.run("metrics.py", "--usage-by-kind", str(facts), "--api-dir", str(api))
    assert proc.returncode == 0, proc.stdout + proc.stderr
    small = section(proc.stdout, "small")
    assert small[-1] == "cost 21.00 at the prices table (1 not reported)"  # 2*3 + 1*15
    assert section(proc.stdout, "build")[-1] == "cost 7.50 at the prices table (0 not reported)"
    assert section(proc.stdout, "design") == []  # no merged pull request, no cost line


def test_ac7_a_tier_with_no_price_makes_the_cost_unknown(setup):
    """REQ-052 AC7: rule 9, a missing price is never 0."""
    repo, api, facts = setup
    repo.write("agk.toml", "[models.prices]\nstrongest = 15\n")
    proc = repo.run("metrics.py", "--usage-by-kind", str(facts), "--api-dir", str(api))
    assert section(proc.stdout, "small")[-1] == "cost unknown at the prices table (1 not reported)"
    assert section(proc.stdout, "build")[-1] == "cost 7.50 at the prices table (0 not reported)"


def test_ac7_unreadable_comments_price_the_pull_request_at_strongest(setup):
    """REQ-052 AC7: rule 9, the higher of the two readings when the facts cannot say (Q-798-9)."""
    repo, api, facts = setup
    (api / "comments-21.json").unlink()
    repo.write("agk.toml", "[models.prices]\nstrongest = 15\nmid = 3\n")
    proc = repo.run("metrics.py", "--usage-by-kind", str(facts), "--api-dir", str(api))
    assert section(proc.stdout, "small")[-1] == "cost 45.00 at the prices table (1 not reported)"


def test_ac7_a_refused_prices_table_names_the_setting(setup):
    """REQ-052 AC7: rule 8, the refusal names the setting, never the value."""
    repo, api, facts = setup
    repo.write("agk.toml", f'[models.prices]\nmid = "{ODD}"\n')
    proc = repo.run("metrics.py", "--usage-by-kind", str(facts), "--api-dir", str(api))
    assert proc.returncode != 0 and "setting: models.prices.mid" in proc.stdout
    assert ODD not in proc.stdout
