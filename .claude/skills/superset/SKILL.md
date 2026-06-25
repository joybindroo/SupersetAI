---
name: superset
description: Manage Apache Superset dashboards, charts, datasets, and databases via its REST API. Use whenever the task involves listing, creating, updating, deleting, or exporting Superset resources, or any operation against a Superset instance.
---

# Superset REST API

This project wraps the Apache Superset REST API. **Always prefer the CLI below**
over hand-writing curl/requests — it handles auth (JWT + CSRF + session cookie +
Referer + token refresh), which is easy to get subtly wrong.

## Setup (once)
- Config comes from `.env` (copy from `.env.example`): `SUPERSET_BASE_URL`,
  `SUPERSET_USERNAME`, `SUPERSET_PASSWORD`, `SUPERSET_PROVIDER` (use `db` — this
  instance uses built-in users created in Settings, **not** LDAP).
- Deps: `pip install -r requirements.txt`.

## Common path — use the CLI
Output is terse by default (`id<TAB>name<TAB>extra` per line). Add `--json` for full payloads.

```bash
python -m superset_cli dashboard list                 # id, title, status
python -m superset_cli dashboard get 12               # full JSON
python -m superset_cli dashboard create --title "X"   # quick create
python -m superset_cli dashboard create --file d.json # full payload
python -m superset_cli dashboard update 12 --file d.json
python -m superset_cli dashboard delete 12
python -m superset_cli dashboard export 12 13 --out dashes.zip

python -m superset_cli chart list                     # id, name, viz_type
python -m superset_cli chart get 5
python -m superset_cli chart create --file chart.json
python -m superset_cli chart update 5 --file chart.json
python -m superset_cli chart delete 5
```

## Long tail — use the `raw` escape hatch
For any endpoint not wrapped above (datasets, databases, queries, RLS, etc.),
call it directly. `path` is relative to `/api/v1`. Query params go in the path
(Superset uses Rison, not JSON, for the `q` param).

```bash
python -m superset_cli raw GET /dataset/
python -m superset_cli raw GET /database/
python -m superset_cli raw POST /chart/ --file chart.json
python -m superset_cli raw DELETE /dataset/7
```

To discover exact payload shapes for an endpoint, check the live Swagger spec at
`<SUPERSET_BASE_URL>/swagger/v1` rather than guessing. Do **not** memorize the
whole API — look up the specific endpoint when needed.

## Gotchas
- A `403` after a successful login means the user's **role** lacks the
  `can read`/`can write` permission on that resource — not an auth-token problem.
- Creating a chart requires valid `datasource_id`, `datasource_type`, `viz_type`,
  and a `params` JSON string; pull an existing chart with `chart get <id> --json`
  as a template before creating a new one.
- List endpoints paginate; use `--page-size` / `--page` or the Rison `q` param.

## When extending
Add common operations as real CLI subcommands in `superset_cli.py` (backed by a
method in `superset_client.py`). Reserve `raw` for genuinely one-off calls.
```
