# SupersetAI

Token-efficient tooling for driving an Apache Superset instance via its REST API —
designed to be used by AI agents (and humans).

## Layout
- **`superset_client.py`** — reusable client. Handles the auth dance (JWT + CSRF +
  session cookie + Referer + token refresh) and dashboard/chart CRUD.
- **`superset_cli.py`** — terse CLI wrapper: `python -m superset_cli <resource> <action>`.
- **`.claude/skills/superset/SKILL.md`** — Claude Code skill: routes agents to the CLI,
  falls back to `raw`/swagger for the long tail.
- **`example.py`** — standalone usage demo.

## Setup
```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env   # then fill in SUPERSET_BASE_URL / USERNAME / PASSWORD
```

## Usage
```bash
.venv/bin/python -m superset_cli dashboard list
.venv/bin/python -m superset_cli chart get 9 --json
.venv/bin/python -m superset_cli raw GET "/database/"
```

Full API reference for an instance lives at `<SUPERSET_BASE_URL>/swagger/v1`.

> Credentials live in `.env`, which is git-ignored. Never commit real credentials.
