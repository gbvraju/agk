"""Kit-only tests of the default local-profile requirement (brief #267; REQ-036 AC4).

Once a stack ADR is accepted, `engines.py stack-next-steps` (and `playbook.py next-steps` when the
tree holds an accepted stack) prints one extra step: a ready-to-run `/agk:spec` sentence filled in
from the accepted option's external services, which writes nothing. A maintainer declines it with
one Residual line of the stack ADR; `engines.py stack-check` prints one information line while it is
neither accepted nor declined, never a failure. Invented stacks in `tmp_path`; no network, no model.
"""

from __future__ import annotations

import subprocess
import sys

import pytest
from conftest import KIT_ROOT, clean_env, git
from test_engines_stack import GOOD_STACK, OPTION_A, OPTION_B, engines, stack_root
from test_playbook import ADR1, GOOD_CHARTER, GOOD_VISION
from test_playbook import run as playbook_run
from test_playbook import started as playbook_started  # noqa: F401  (the fixture of test_playbook)

sys.path.insert(0, str(KIT_ROOT / "scripts" / "agk"))
from intake import check_sentence  # noqa: E402

TEMPLATE = KIT_ROOT / "kit" / "templates" / "local-profile.md"
STACK_TEMPLATE = KIT_ROOT / "kit" / "templates" / "stack-adr.md"
SKILL = KIT_ROOT / "skills" / "stack" / "SKILL.md"
SERVICES = "sign-in, outgoing mail, file storage and timed jobs"
WITH_SERVICES = OPTION_B.replace(" Practices:", f" External services: {SERVICES}. Practices:")
INFO = "info engines: local profile: not decided\n"
DECLINE = "local profile: declined, the product is a single static page with no services"


@pytest.fixture
def started(request):
    return request.getfixturevalue("playbook_started")


def accepted(text=GOOD_STACK, letter="B", option=WITH_SERVICES):
    return (
        text.replace(OPTION_B, option)
        .replace("- Status: Proposed", "- Status: Accepted")
        .replace("3. **Chosen**: none yet", f"3. **Chosen**: Option {letter} — it fits the host")
    )


def with_residual(text, line):
    return text.replace("## Residual\n\nNone.\n", f"## Residual\n\n- {line}\n")


def steps(root, *args):
    return engines(root, "stack-next-steps", "--base", "main", "--date", "2026-10-29", *args)


def sentence_of(out: str) -> str:
    line = next(ln for ln in out.splitlines() if ln.strip().startswith('/agk:spec "'))
    return line.strip()[len('/agk:spec "') : -1]


def tree(root):
    return {
        p.relative_to(root).as_posix(): p.read_bytes()
        for p in root.rglob("*")
        if p.is_file() and ".git" not in p.parts
    }


# --- answer 1: the offer ----------------------------------------------------------------------


def test_ac4_the_accepting_steps_offer_the_local_profile_sentence_from_the_chosen_option(started):
    """REQ-036 AC4: brief 267 answers 1 and 3 (the sentence names the option's services)."""
    stack_root(started, accepted())
    before = tree(started)
    proc = steps(started, "--brief", "none")
    assert proc.returncode == 0, proc.stdout
    out = proc.stdout
    offer = out[out.index("Pull request body:") :]
    assert "local profile" in offer and "nothing is written" in offer.lower()
    sentence = sentence_of(offer)
    assert f"({SERVICES})" in sentence
    assert check_sentence(sentence) == sentence
    for needle in ("one machine", "one command", "stand-in", "invented data", "startup guard"):
        assert needle in sentence, needle
    assert "local profile: declined, <reason of at least 20 characters> (YYYY-MM-DD)" in offer
    assert "ADR-0002" in offer and "Approve:" in offer and "spec_approvers" in offer
    assert tree(started) == before


def test_ac4_the_offer_uses_only_the_services_of_the_chosen_option(started):
    """REQ-036 AC4: brief 267 answer 3 (the other option's services are not offered)."""
    option_a = OPTION_A.replace(" Practices:", " External services: a paging line. Practices:")
    text = accepted(letter="A").replace(OPTION_A, option_a)
    stack_root(started, text)
    proc = steps(started, "--brief", "none")
    assert proc.returncode == 0, proc.stdout
    sentence = sentence_of(proc.stdout)
    assert "(a paging line)" in sentence and SERVICES not in sentence


def test_ac4_an_option_that_names_no_services_still_gets_the_offer(started):
    """REQ-036 AC4: brief 267 answer 3 (no services named: the sentence says so)."""
    stack_root(started, accepted(option=OPTION_B))
    proc = steps(started, "--brief", "none")
    assert proc.returncode == 0, proc.stdout
    sentence = sentence_of(proc.stdout)
    assert "(none named by the stack yet)" in sentence
    assert check_sentence(sentence) == sentence


def test_ac4_the_options_pull_request_gets_no_offer(started):
    """REQ-036 AC4: brief 267 answer 1 (offered only once an option is accepted)."""
    stack_root(started, GOOD_STACK.replace(OPTION_B, WITH_SERVICES))
    proc = steps(started, "--brief", "none")
    assert proc.returncode == 0, proc.stdout
    assert "/agk:spec" not in proc.stdout and "local profile" not in proc.stdout


@pytest.mark.parametrize("decided", ["declined", "requirement"])
def test_ac4_a_decided_local_profile_is_not_offered_again(started, decided):
    """REQ-036 AC4: brief 267 answer 2 (accepted as a requirement, or declined)."""
    text = accepted()
    if decided == "declined":
        text = with_residual(text, f"{DECLINE} (2026-10-29)")
    else:
        reqs = started / "docs" / "requirements.md"
        reqs.write_text(
            reqs.read_text(encoding="utf-8")
            + "\n### REQ-002 — The product runs in a local profile\n\n- Status: planned\n",
            encoding="utf-8",
        )
    stack_root(started, text)
    proc = steps(started, "--brief", "none")
    assert proc.returncode == 0, proc.stdout
    assert "/agk:spec" not in proc.stdout


def test_ac4_a_long_list_of_services_is_named_as_too_long_for_the_intake(started):
    """REQ-036 AC4: brief 267 answer 1 (a ready-to-run sentence; one that would not run says so)."""
    many = ", ".join(f"service number {n}" for n in range(12))
    stack_root(
        started,
        accepted(option=OPTION_B.replace(" Practices:", f" External services: {many}. Practices:")),
    )
    proc = steps(started, "--brief", "none")
    assert proc.returncode == 0, proc.stdout
    assert "300 characters" in proc.stdout and "shorten" in proc.stdout


# --- answer 2: the decision and the information line -------------------------------------------


def test_ac4_an_accepted_stack_without_a_decision_gets_one_information_line(started):
    """REQ-036 AC4: brief 267 answer 2 (`local profile: not decided`, never a failure)."""
    stack_root(started, accepted())
    proc = engines(started, "stack-check")
    assert (proc.returncode, proc.stdout) == (0, "ok engines-stack\n" + INFO), proc.stdout


def test_ac4_a_proposed_stack_gets_no_information_line(started):
    """REQ-036 AC4: brief 267 answer 2 (nothing is offered before an option is accepted)."""
    stack_root(started, GOOD_STACK.replace(OPTION_B, WITH_SERVICES))
    proc = engines(started, "stack-check")
    assert (proc.returncode, proc.stdout) == (0, "ok engines-stack\n"), proc.stdout


def test_ac4_a_declined_local_profile_is_decided(started):
    """REQ-036 AC4: brief 267 answer 2 (one Residual line with a reason and a date)."""
    stack_root(started, with_residual(accepted(), f"{DECLINE} (2026-10-29)"))
    proc = engines(started, "stack-check")
    assert (proc.returncode, proc.stdout) == (0, "ok engines-stack\n"), proc.stdout


def test_ac4_a_local_profile_requirement_is_decided(started):
    """REQ-036 AC4: brief 267 answer 2 (the requirement went through the intake)."""
    reqs = started / "docs" / "requirements.md"
    reqs.write_text(
        reqs.read_text(encoding="utf-8")
        + "\n### REQ-002 — The product runs in a Local Profile\n\n- Status: planned\n",
        encoding="utf-8",
    )
    stack_root(started, accepted())
    proc = engines(started, "stack-check")
    assert (proc.returncode, proc.stdout) == (0, "ok engines-stack\n"), proc.stdout


@pytest.mark.parametrize(
    "line",
    [
        "local profile: declined, too short (2026-10-29)",
        f"{DECLINE}",
        f"{DECLINE} (29 October)",
        "local profile: declined (2026-10-29)",
    ],
)
def test_ac4_a_decline_without_a_reason_or_a_date_fails_naming_the_rule(started, line):
    """REQ-036 AC4: brief 267 answer 2 (a reason of at least 20 characters and a date)."""
    stack_root(started, with_residual(accepted(), line))
    proc = engines(started, "stack-check")
    assert proc.returncode == 1 and "rule 5" in proc.stdout and "local profile" in proc.stdout
    assert "static page" not in proc.stdout and "too short" not in proc.stdout


@pytest.mark.parametrize(
    "option",
    [
        OPTION_B.replace(" Practices:", " External services: . Practices:"),
        OPTION_B.rstrip("\n").rstrip(".") + ". External services: sign-in.\n",
    ],
)
def test_ac4_external_services_are_one_list_before_the_practices(started, option):
    """REQ-036 AC4: brief 267 answer 3 (the services of an option are read from one place)."""
    stack_root(started, GOOD_STACK.replace(OPTION_B, option))
    proc = engines(started, "stack-check")
    assert proc.returncode == 1 and "rule 5" in proc.stdout and "External services" in proc.stdout
    assert "sign-in" not in proc.stdout


def test_ac4_an_option_with_external_services_before_the_practices_passes(started):
    """REQ-036 AC4: brief 267 answer 3 (the services segment is optional and checked)."""
    stack_root(started, GOOD_STACK.replace(OPTION_B, WITH_SERVICES))
    assert engines(started, "stack-check").stdout == "ok engines-stack\n"


# --- answer 1: the playbook's next steps --------------------------------------------------------


def test_ac4_the_playbook_next_steps_offer_it_when_the_tree_holds_an_accepted_stack(tmp_path):
    """REQ-036 AC4: brief 267 answer 1 (`playbook.py next-steps` prints the same extra step)."""
    from conftest import make_repo
    from test_playbook import PRINCIPLES, VISION_TEMPLATE

    root = make_repo(tmp_path / "proj")
    files = {
        "agk.toml": 'default_branch = "main"\n',
        "constitution/principles.md": PRINCIPLES,
        "constitution/vision.md": VISION_TEMPLATE,
        "docs/adr/0001-adopt-agk.md": ADR1,
        "docs/adr/0002-stack-options.md": accepted(),
        "docs/requirements.md": "### REQ-001 — T\n\n- Status: planned\n",
    }
    for rel, body in files.items():
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_text(body, encoding="utf-8")
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "base")
    git(root, "switch", "-q", "-c", "start/a-reading-list")
    (root / "constitution" / "vision.md").write_text(GOOD_VISION, encoding="utf-8")
    (root / "docs" / "adr" / "0003-project-charter.md").write_text(
        GOOD_CHARTER.replace("ADR-0002", "ADR-0003"), encoding="utf-8"
    )
    proc = playbook_run(
        "next-steps",
        "--base",
        "main",
        "--brief",
        "none",
        "--date",
        "2026-10-29",
        "--root",
        str(root),
    )
    assert proc.returncode == 0, proc.stdout
    assert f"({SERVICES})" in sentence_of(proc.stdout)


def test_ac4_the_playbook_next_steps_offer_nothing_without_an_accepted_stack(started):
    """REQ-036 AC4: brief 267 answer 1 (no stack accepted, no offer)."""
    from test_playbook import good_start

    good_start(started)
    proc = playbook_run(
        "next-steps",
        "--base",
        "main",
        "--brief",
        "none",
        "--date",
        "2026-10-29",
        "--root",
        str(started),
    )
    assert proc.returncode == 0, proc.stdout
    assert "/agk:spec" not in proc.stdout and "local profile" not in proc.stdout


# --- answers 4 and 5: the template, the stack ADR template, the skill ---------------------------


def test_ac4_the_kit_ships_the_sentence_as_a_template_with_one_placeholder():
    """REQ-036 AC4: brief 267 answers 3 and 4 (one shape for every project)."""
    text = TEMPLATE.read_text(encoding="utf-8")
    assert text.count("{{") == 1 and text.count("{{services}}") == 1
    assert text.endswith("\n") and text.count("\n") == 1
    sentence = text.strip().replace("{{services}}", SERVICES)
    assert check_sentence(sentence) == sentence


def test_ac4_the_stack_adr_template_carries_the_local_profile_practice():
    """REQ-036 AC4: brief 267 answer 4 (the Practices bullet of the template)."""
    text = STACK_TEMPLATE.read_text(encoding="utf-8")
    bullet = (
        "   - local profile: check (step: a smoke test that starts the local profile and signs in "
        "with the stand-in identity)\n"
    )
    practices = text[text.index("2. **Practices**") : text.index("3. **Chosen**")]
    assert bullet in practices


def test_ac4_a_stack_drafted_from_the_template_keeps_the_practice_and_passes(started):
    """REQ-036 AC4: brief 267 answer 4 (a practice no option names is still well formed)."""
    text = GOOD_STACK.replace(
        "3. **Chosen**",
        "   - local profile: check (step: a smoke test that starts the local profile and signs "
        "in with the stand-in identity)\n3. **Chosen**",
    )
    stack_root(started, text)
    assert engines(started, "stack-check").stdout == "ok engines-stack\n"


def test_ac4_the_skill_tells_of_the_offer_and_the_decline():
    """REQ-036 AC4: brief 267 answers 1 and 2 (the skill prints the extra step)."""
    text = SKILL.read_text(encoding="utf-8")
    for needle in (
        "External services:",
        "local profile",
        "/agk:spec",
        "local profile: declined, <reason of at least 20 characters> (YYYY-MM-DD)",
        "local profile: not decided",
        "spec_approvers",
    ):
        assert needle in text, needle


def test_ac4_the_engines_script_still_runs_without_the_template_in_isolated_mode(started):
    """REQ-036 AC4: brief 267 (the offer reads the kit's own template; isolated mode works)."""
    stack_root(started, accepted())
    proc = subprocess.run(
        [
            sys.executable,
            "-I",
            str(KIT_ROOT / "scripts" / "agk" / "engines.py"),
            "stack-check",
            "--root",
            str(started),
        ],
        capture_output=True,
        text=True,
        env=clean_env(),
    )
    assert proc.stdout == "ok engines-stack\n" + INFO


# --- the fix list of a576d87 ------------------------------------------------------------------


def test_ac4_a_sentence_refused_for_another_reason_prints_that_reason(started):
    """REQ-036 AC4: brief 267 answer 1 (the intake's own refusal is named, not a guessed one)."""
    option = OPTION_B.replace(" Practices:", " External services: sign-in. Then mail. Practices:")
    stack_root(started, accepted(option=option))
    proc = steps(started, "--brief", "none")
    assert proc.returncode == 0, proc.stdout
    assert "not one sentence" in proc.stdout and "300 characters" not in proc.stdout


def test_ac4_a_double_quote_in_the_services_fails_naming_the_setting(started):
    """REQ-036 AC4: brief 267 answer 3 (the printed command stays one quoted argument)."""
    option = OPTION_B.replace(" Practices:", ' External services: a "sign-in" service. Practices:')
    stack_root(started, accepted(option=option))
    proc = engines(started, "stack-check")
    assert proc.returncode == 1 and "rule 5" in proc.stdout and "External services" in proc.stdout
    assert "double quote" in proc.stdout and "sign-in" not in proc.stdout
    offer = steps(started, "--brief", "none")
    assert offer.returncode == 1 and '/agk:spec "' not in offer.stdout


@pytest.mark.parametrize("day", ["2026-99-99", "2026-02-30", "2026-13-01"])
def test_ac4_a_decline_with_a_date_that_does_not_exist_fails(started, day):
    """REQ-036 AC4: brief 267 answer 2 (the date of a decline is a real date)."""
    stack_root(started, with_residual(accepted(), f"{DECLINE} ({day})"))
    proc = engines(started, "stack-check")
    assert proc.returncode == 1 and "rule 5" in proc.stdout and "local profile" in proc.stdout
    assert day not in proc.stdout
