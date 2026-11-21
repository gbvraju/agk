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

## Deploy it

The written steps are in `docs/deploy.md`. A deploy is the person's own act.
