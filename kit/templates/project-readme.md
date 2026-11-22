# {{project}}

{{what}}

## Run it

Copy `.env.example` to `.env` (`cp .env.example .env`, or `Copy-Item .env.example .env` in PowerShell) and fill in
each value; for a run on this machine: {{local}}. Then one command:

Run it: `{{run}}`
Run it (PowerShell): `{{run_windows}}`
{{check}}
## Test it

Test it: `python3 -m pytest -q`
Test it (PowerShell): `py -m pytest -q`

The kit's standards check needs its pinned tools once in this Python: `python3 -m pip install -r config/ci-tools.txt`,
or in a project that uses the kit as a plugin
`python3 -m pip install -r "${CLAUDE_PLUGIN_ROOT}/config/ci-tools.txt"`.

## Deploy it

The written steps are in `docs/deploy.md`. A deploy is the person's own act.
