"""
Token-efficient CLI wrapper around SupersetClient, designed for AI agents.

Usage:
    python -m superset_cli dashboard list
    python -m superset_cli dashboard get 12
    python -m superset_cli dashboard create --title "My Dash"
    python -m superset_cli dashboard create --file payload.json
    python -m superset_cli dashboard update 12 --file payload.json
    python -m superset_cli dashboard delete 12
    python -m superset_cli dashboard export 12 13 --out dashes.zip

    python -m superset_cli chart list
    python -m superset_cli chart get 5
    python -m superset_cli chart create --file chart.json
    python -m superset_cli chart update 5 --file chart.json
    python -m superset_cli chart delete 5

    # Escape hatch for any endpoint (see /swagger/v1):
    python -m superset_cli raw GET /dataset/
    python -m superset_cli raw POST /chart/ --file chart.json

Output is terse by default (id<TAB>name<TAB>extra per line for lists) to save
tokens. Pass --json on any command for the full JSON response.
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from dotenv import load_dotenv

from superset_client import SupersetClient, SupersetError


# --------------------------------------------------------------------- output
def _emit_json(obj: Any) -> None:
    json.dump(obj, sys.stdout, separators=(",", ":"), default=str)
    sys.stdout.write("\n")


def _emit_list(result: dict, name_key: str, extra_key: str) -> None:
    rows = result.get("result", [])
    total = result.get("count", len(rows))
    for r in rows:
        print(f"{r.get('id')}\t{r.get(name_key, '')}\t{r.get(extra_key, '')}")
    print(f"# {len(rows)} of {total}", file=sys.stderr)


def _load_payload(args: argparse.Namespace) -> dict:
    """Build a request body from --file, --data, or --title."""
    if getattr(args, "file", None):
        with open(args.file, encoding="utf-8") as f:
            return json.load(f)
    if getattr(args, "data", None):
        return json.loads(args.data)
    if getattr(args, "title", None):
        return {"dashboard_title": args.title}
    raise SystemExit("error: provide one of --file, --data, or --title")


# --------------------------------------------------------------- subcommands
def cmd_dashboard(client: SupersetClient, args: argparse.Namespace) -> None:
    if args.action == "list":
        res = client.list_dashboards(page_size=args.page_size, page=args.page)
        _emit_json(res) if args.json else _emit_list(res, "dashboard_title", "status")
    elif args.action == "get":
        _emit_json(client.get_dashboard(args.id))
    elif args.action == "create":
        _emit_json(client.create_dashboard(_load_payload(args)))
    elif args.action == "update":
        _emit_json(client.update_dashboard(args.id, _load_payload(args)))
    elif args.action == "delete":
        client.delete_dashboard(args.id)
        print(f"deleted dashboard {args.id}")
    elif args.action == "export":
        data = client.export_dashboards(args.ids)
        with open(args.out, "wb") as f:
            f.write(data)
        print(f"wrote {args.out} ({len(data)} bytes)")


def cmd_chart(client: SupersetClient, args: argparse.Namespace) -> None:
    if args.action == "list":
        res = client.list_charts(page_size=args.page_size, page=args.page)
        _emit_json(res) if args.json else _emit_list(res, "slice_name", "viz_type")
    elif args.action == "get":
        _emit_json(client.get_chart(args.id))
    elif args.action == "create":
        _emit_json(client.create_chart(_load_payload(args)))
    elif args.action == "update":
        _emit_json(client.update_chart(args.id, _load_payload(args)))
    elif args.action == "delete":
        client.delete_chart(args.id)
        print(f"deleted chart {args.id}")


def cmd_raw(client: SupersetClient, args: argparse.Namespace) -> None:
    kwargs: dict = {}
    if args.file or args.data:
        kwargs["json"] = _load_payload(args)
    _emit_json(client.request(args.method, args.path, **kwargs))


# ------------------------------------------------------------------- parser
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="superset_cli", description=__doc__)
    sub = p.add_subparsers(dest="resource", required=True)

    def add_payload_args(sp: argparse.ArgumentParser, with_title: bool = False) -> None:
        sp.add_argument("--file", help="path to a JSON file holding the request body")
        sp.add_argument("--data", help="inline JSON string for the request body")
        if with_title:
            sp.add_argument("--title", help="shortcut: set dashboard_title")

    # dashboard
    d = sub.add_parser("dashboard", help="manage dashboards")
    da = d.add_subparsers(dest="action", required=True)
    dl = da.add_parser("list"); dl.add_argument("--json", action="store_true")
    dl.add_argument("--page-size", type=int, default=100); dl.add_argument("--page", type=int, default=0)
    da.add_parser("get").add_argument("id", type=int)
    add_payload_args(da.add_parser("create"), with_title=True)
    dc = da.add_parser("update"); dc.add_argument("id", type=int); add_payload_args(dc)
    da.add_parser("delete").add_argument("id", type=int)
    de = da.add_parser("export"); de.add_argument("ids", type=int, nargs="+")
    de.add_argument("--out", default="dashboards_export.zip")

    # chart
    c = sub.add_parser("chart", help="manage charts")
    ca = c.add_subparsers(dest="action", required=True)
    cl = ca.add_parser("list"); cl.add_argument("--json", action="store_true")
    cl.add_argument("--page-size", type=int, default=100); cl.add_argument("--page", type=int, default=0)
    ca.add_parser("get").add_argument("id", type=int)
    add_payload_args(ca.add_parser("create"))
    cc = ca.add_parser("update"); cc.add_argument("id", type=int); add_payload_args(cc)
    ca.add_parser("delete").add_argument("id", type=int)

    # raw escape hatch
    r = sub.add_parser("raw", help="call any /api/v1 endpoint directly")
    r.add_argument("method"); r.add_argument("path")
    r.add_argument("--file"); r.add_argument("--data")

    return p


def main(argv: list[str] | None = None) -> int:
    load_dotenv()
    args = build_parser().parse_args(argv)
    try:
        client = SupersetClient().login()
        {"dashboard": cmd_dashboard, "chart": cmd_chart, "raw": cmd_raw}[args.resource](client, args)
    except SupersetError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
