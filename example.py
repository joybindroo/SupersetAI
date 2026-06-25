"""
Example usage of SupersetClient.

Run:
    pip install -r requirements.txt
    cp .env.example .env   # then edit .env
    python example.py
"""

import os

from dotenv import load_dotenv

from superset_client import SupersetClient

load_dotenv()  # load credentials from .env into the environment


def main() -> None:
    client = SupersetClient().login()
    print("Authenticated.\n")

    # --- List dashboards ---------------------------------------------------
    dashboards = client.list_dashboards(page_size=10)
    print(f"Dashboards (showing {len(dashboards['result'])} of {dashboards['count']}):")
    for d in dashboards["result"]:
        print(f"  [{d['id']}] {d['dashboard_title']}  status={d['status']}")

    # --- List charts -------------------------------------------------------
    charts = client.list_charts(page_size=10)
    print(f"\nCharts (showing {len(charts['result'])} of {charts['count']}):")
    for c in charts["result"]:
        print(f"  [{c['id']}] {c['slice_name']}  type={c['viz_type']}")

    # --- Create a dashboard (uncomment to try) -----------------------------
    # new = client.create_dashboard({
    #     "dashboard_title": "Created via API",
    #     "published": False,
    # })
    # print("\nCreated dashboard id:", new["id"])
    # client.update_dashboard(new["id"], {"published": True})
    # client.delete_dashboard(new["id"])

    # --- Export dashboards to a ZIP (uncomment to try) ---------------------
    # ids = [d["id"] for d in dashboards["result"][:1]]
    # if ids:
    #     zip_bytes = client.export_dashboards(ids)
    #     with open("dashboards_export.zip", "wb") as f:
    #         f.write(zip_bytes)
    #     print("\nWrote dashboards_export.zip")


if __name__ == "__main__":
    main()
