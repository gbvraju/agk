"""Tests of `measures.py --trial`: one solo trial table of speed, quality and cost.

Brief #1618, ADR-0687, amendment 213 (SPEC-0007 rule 29). REQ-012 AC1: the measured figures of a
run. Saved API responses, a saved git tree and a stub sidecar in `tmp_path` only; invented data
(example.com, `member-example-1`); no network, no model and no `gh`.
"""

from __future__ import annotations

import json
import shutil

import pytest
from test_measures import (
    BUILDER,
    NAMES,
    OWNER,
    REVIEWER,
    Api,
    at,
    comment,
    feature,
    measures,
    ps,
    report_line,
    row,
    taken,
    verdict,
)

RED = "The default branch is red"


@pytest.fixture
def setup(repo, tmp_path):
    repo.write("config/reviewers.yaml", f"version: 1\nverdict_authors: [{REVIEWER}]\n")
    repo.write("config/protected-paths.txt", "scripts/agk/\n")
    repo.write("agk.toml", 'agent_apps = ["claude"]\n')
    repo.commit({"README.md": "x\n"}, "start")
    return repo, Api(tmp_path)


def add(api: Api, n: int, *extra: dict) -> None:
    """Appends comments to the saved thread of issue or pull request N."""
    saved = json.loads((api.path / f"comments-{n}.json").read_text())
    api.put(f"comments-{n}", saved + list(extra))


def trial(repo, api: Api, *args: str, **kw) -> dict[str, str]:
    proc = measures(repo, api, "--trial", *args, **kw)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    return row(proc.stdout, "trial: ")


def test_req_012_ac1_the_trial_figures_of_one_feature(setup):
    """REQ-012 AC1: brief #1618 answer 1 (speed, quality and cost over the range)."""
    repo, api = setup
    feature(repo, api)
    got = trial(repo, api)
    assert got["merged"] == "3"  # #60, #61 and the follow-up #62
    assert (got["lead_hours_median"], got["lead_hours_p90"]) == ("52.0", "52.0")
    assert got["cleared_to_merge_minutes"] == "1170"  # median of 1140 (#60) and 1200 (#61)
    assert got["fix_rounds_per_merged"] == "0.3"  # one fix list over three merges
    assert got["owner_items"] == "1"
    assert got["owner_wait_minutes"] == "30"  # the question, answered half an hour later
    assert got["park_minutes"] == "0"
    assert got["red_spells"] == got["red_hours"] == "unknown"  # no issue list was saved
    assert got["reverts"] == "0"
    assert got["confirmations"] == "none (team mode)"
    assert got["tokens_per_merged"] == "1267"  # (1500 + 2000 + 300) / 3
    assert got["tokens_per_merged_strongest"] == "1267 (configured)"  # a design brief


def test_req_012_ac1_an_owner_needed_is_counted_in_the_owner_wait(setup):
    """REQ-012 AC1: brief #1618 answers 1 and 5 (an `Owner needed:` by a listed verdict author,
    to its answer or, never answered, to the merge; one by anyone else is not an item)."""
    repo, api = setup
    feature(repo, api)
    add(api, 60, comment(40, REVIEWER, at(1, 18), "Owner needed: accept the plan"),
        comment(41, REVIEWER, at(1, 19), "Approve: plan"))  # fmt: skip
    add(api, 61, comment(42, REVIEWER, at(3, 12), "Owner needed: merge it"),
        comment(43, BUILDER, at(3, 12), "Owner needed: not a listed author"))  # fmt: skip
    got = trial(repo, api)
    assert got["owner_items"] == "3"
    assert got["owner_wait_minutes"] == str(30 + 60 + 60)


def test_req_012_ac1_park_time_open_and_closed(setup):
    """REQ-012 AC1: brief #1618 answers 1 and 5 (a park to its unpark; an open one to `--to`)."""
    repo, api = setup
    feature(repo, api)
    add(api, 60, comment(44, REVIEWER, at(1, 13), "Parked-by: wait Q-50-9"),
        comment(45, REVIEWER, at(1, 14, 30), "Unparked-by: answer Q-50-9"))  # fmt: skip
    add(api, 61, comment(46, REVIEWER, at(3, 20), "Parked-by: wait owner-needed"))
    got = trial(repo, api, end="2026-10-03")
    assert got["park_minutes"] == "330 (1 open)"  # 90 closed, 240 open to the end of 10-03


def test_req_012_ac1_red_spells_cut_to_the_range(setup):
    """REQ-012 AC1: brief #1618 answers 1 and 5 (the red issues overlapping the range, one opened
    before `--from` counted from `--from`; another title and a pull request are not spells)."""
    repo, api = setup
    feature(repo, api)
    api.put("issues-red", [
        {"number": 90, "title": RED, "created_at": at(1, 9), "closed_at": at(1, 12)},
        {"number": 91, "title": RED, "created_at": "2026-09-30T21:00:00Z", "closed_at": at(1, 1)},
        {"number": 92, "title": "Widget", "created_at": at(1, 9), "closed_at": at(2, 9)},
        {"number": 93, "title": RED, "created_at": at(1, 9), "closed_at": at(2, 9),
         "pull_request": {}},
        {"number": 94, "title": RED, "created_at": "2026-09-01T00:00:00Z",
         "closed_at": "2026-09-02T00:00:00Z"},
    ])  # fmt: skip
    got = trial(repo, api)
    assert (got["red_spells"], got["red_hours"]) == ("2", "4.0")


def test_req_012_ac1_a_revert_is_counted_by_its_merge_commit(setup):
    """REQ-012 AC1: brief #1618 answers 1 and 5 (a merge commit that starts `Revert "`)."""
    repo, api = setup
    feature(repo, api)
    repo.commit({"c.txt": "c\n"}, 'Revert "Widget frobnicate"\n\nThis reverts an older one.')
    sha = repo.git("rev-parse", "HEAD").strip()
    api.pull(70, None, at(5, 9), at(5, 10), sha, [])
    got = trial(repo, api)
    assert (got["reverts"], got["merged"]) == ("1", "4")
    assert got["tokens_per_merged"] == "1267 (+1 not-reported)"
    assert got["tokens_per_merged_unknown"] == "not-reported"


def test_req_012_ac1_tokens_are_grouped_by_the_configured_tier(setup):
    """REQ-012 AC1: brief #1618 answer 1 and Q-1618-1 (the tier of the brief's kind, `[models]`)."""
    repo, api = setup
    repo.write("agk.toml", 'agent_apps = ["claude"]\n\n[models]\nsmall = { tier = "fast", '
               'effort = "low" }\n')  # fmt: skip
    feature(repo, api)
    api.put("issue-53", {"number": 53, "title": "Widget", "state": "closed", "created_at": at(5),
                         "body": "Widget\nSize: S\nTouches: docs/guide.md\n"})  # fmt: skip
    api.put("comments-53", [taken(50, at(5, 10))])
    api.pull(71, 53, at(5, 11), at(5, 12), "f" * 40, [report_line(51, at(5, 11), 100)], True)
    got = trial(repo, api)
    assert got["tokens_per_merged_fast"] == "100 (configured)"
    assert got["tokens_per_merged_strongest"] == "1267 (configured)"
    assert got["tokens_per_merged"] == "975"  # (3800 + 100) / 4


def test_req_012_ac1_a_bad_models_entry_is_refused_naming_it(setup):
    """REQ-012 AC1: brief #1618 answer 3 (`[models]` read by `model_settings`)."""
    repo, api = setup
    repo.write("agk.toml", 'agent_apps = ["claude"]\n\n[models]\nsmall = { tier = "huge", '
               'effort = "low" }\n')  # fmt: skip
    feature(repo, api)
    proc = measures(repo, api, "--trial")
    assert proc.returncode == 1
    assert "setting: models.small" in proc.stderr
    assert "huge" not in proc.stderr


@pytest.mark.parametrize(
    ("line", "setting"),
    [('review_mode = "duo"', "review_mode"), ('execution = "cloud"', "execution")],
)
def test_req_012_ac1_a_bad_mode_is_refused_naming_the_setting(setup, line, setting):
    """REQ-012 AC1: brief #1618 answer 3 (`review_mode` and `execution`, any other value)."""
    repo, api = setup
    repo.write("agk.toml", f'agent_apps = ["claude"]\n{line}\n')
    feature(repo, api)
    proc = measures(repo, api, "--trial")
    assert proc.returncode != 0
    assert f"setting: {setting}" in proc.stderr
    assert proc.stdout == ""


def test_req_012_ac1_solo_mode_counts_the_persons_confirmations(setup):
    """REQ-012 AC1: brief #1618 answer 3 (`review_mode = "solo"`: the one person's `Confirmed:`)."""
    repo, api = setup
    repo.write("agk.toml", 'agent_apps = ["claude"]\nreview_mode = "solo"\n')
    feature(repo, api)
    add(api, 61, comment(47, REVIEWER, at(2, 18), "Confirmed: Verdict: cleared 0061aaa", app=False),
        comment(48, BUILDER, at(2, 18), "Confirmed: not the person"))  # fmt: skip
    assert trial(repo, api)["confirmations"] == "1"


def test_req_012_ac1_local_mode_still_reads_red_spells_and_reverts(setup):
    """REQ-012 AC1: brief #1618 answers 3 and 4 (`execution = "local"`)."""
    repo, api = setup
    repo.write("agk.toml", 'agent_apps = ["claude"]\nexecution = "local"\n')
    feature(repo, api)
    api.put("issues-red", [{"number": 90, "title": RED, "created_at": at(1, 9),
                            "closed_at": at(1, 12)}])  # fmt: skip
    proc = measures(repo, api, "--trial")
    got = row(proc.stdout, "trial: ")
    assert (got["red_spells"], got["red_hours"], got["reverts"]) == ("1", "3.0", "0")
    assert row(proc.stdout, "totals: ")["billed_minutes"] == "none (local mode)"


def test_req_012_ac1_personal_mode_prints_none(setup, tmp_path):
    """REQ-012 AC1: brief #1618 answers 3 and 4 (the sidecar: owner, park, red figures none)."""
    repo, api = setup
    feature(repo, api)
    sidecar = tmp_path / "sidecar"
    ps.make_sidecar(sidecar, REVIEWER)
    forge = sidecar / "forge"
    for kind, numbers in (("issues", (50,)), ("pulls", (60, 61, 62))):
        (forge / kind).mkdir(parents=True, exist_ok=True)
        for n in numbers:
            src = "issue" if kind == "issues" else "pull"
            data = json.loads((api.path / f"{src}-{n}.json").read_text())
            data.setdefault("state", "closed")
            (forge / kind / f"{n}.json").write_text(json.dumps(data))
    for n in (50, 60, 61, 62):
        shutil.copy(api.path / f"comments-{n}.json", forge / f"comments-{n}.json")
    proc = repo.run("measures.py", "--from", "2026-10-01", "--to", "2026-10-31",
                    "--sidecar", str(sidecar), "--trial")  # fmt: skip
    assert proc.returncode == 0, proc.stdout + proc.stderr
    got = row(proc.stdout, "trial: ")
    for field in ("owner_items", "owner_wait_minutes", "park_minutes", "red_spells", "red_hours",
                  "confirmations"):  # fmt: skip
        assert got[field] == "none (personal mode)", field
    assert got["merged"] == "3"


@pytest.mark.parametrize("args", [("--trial", "--trial"), ("--trial", "yes")])
def test_req_012_ac1_a_bad_trial_option_is_refused_naming_it(setup, args):
    """REQ-012 AC1: brief #1618 answer 3 (`--trial` takes no value and is given once)."""
    repo, api = setup
    proc = measures(repo, api, *args)
    assert proc.returncode == 2
    assert "option: --trial" in proc.stderr
    assert proc.stdout == ""


def test_req_012_ac1_no_merge_gives_unknown_never_zero(setup):
    """REQ-012 AC1: brief #1618 answer 5 (no merged pull request: per-merged figures unknown)."""
    repo, api = setup
    feature(repo, api)
    got = trial(repo, api, start="2026-11-01", end="2026-11-30")
    assert got["merged"] == "0"
    for field in ("tokens_per_merged", "fix_rounds_per_merged", "cleared_to_merge_minutes",
                  "lead_hours_median", "lead_hours_p90"):  # fmt: skip
        assert got[field] == "unknown", field


def test_req_012_ac1_the_trial_is_numbers_only_and_stable(setup):
    """REQ-012 AC1: brief #1618 answers 1 and 5 (no login, title or path; the same bytes; the
    `--json` form holds the same row; without `--trial` the output is unchanged)."""
    repo, api = setup
    feature(repo, api)
    add(api, 61, comment(42, REVIEWER, at(3, 12), "Owner needed: merge it"))
    plain = measures(repo, api).stdout
    text = measures(repo, api, "--trial").stdout
    assert text == measures(repo, api, "--trial").stdout
    assert "trial" not in plain
    assert text.replace(text.splitlines()[-1] + "\n", "") == plain
    data = json.loads(measures(repo, api, "--trial", "--json").stdout)
    assert data["trial"] == row(text, "trial: ")
    assert "trial" not in json.loads(measures(repo, api, "--json").stdout)
    for out in (text, json.dumps(data)):
        for word in (*NAMES, OWNER, "docs/", "scripts/"):
            assert word.lower() not in out.lower(), word
