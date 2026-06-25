"""
Minimal, reusable client for the Apache Superset REST API.

Handles the auth dance that trips most people up:
  1. POST /api/v1/security/login        -> JWT access token (+ refresh token)
  2. GET  /api/v1/security/csrf_token/  -> CSRF token bound to the session cookie
  3. Mutating calls send BOTH the Bearer token AND the CSRF token, share the
     session cookie, and include a Referer header.

Config is read from environment variables (see .env.example):
  SUPERSET_BASE_URL, SUPERSET_USERNAME, SUPERSET_PASSWORD, SUPERSET_PROVIDER
"""

from __future__ import annotations

import os
from typing import Any, Optional

import requests


class SupersetError(RuntimeError):
    """Raised when the Superset API returns an error response."""


class SupersetClient:
    def __init__(
        self,
        base_url: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        provider: Optional[str] = None,
        verify_ssl: bool = True,
    ):
        self.base_url = (base_url or os.environ["SUPERSET_BASE_URL"]).rstrip("/")
        self.username = username or os.environ["SUPERSET_USERNAME"]
        self.password = password or os.environ["SUPERSET_PASSWORD"]
        # "db" for the built-in user store; "ldap" if your instance uses LDAP.
        self.provider = provider or os.environ.get("SUPERSET_PROVIDER", "db")

        self.api = f"{self.base_url}/api/v1"
        self.session = requests.Session()
        self.session.verify = verify_ssl
        self.access_token: Optional[str] = None
        self.csrf_token: Optional[str] = None

    # ------------------------------------------------------------------ auth
    def login(self) -> "SupersetClient":
        """Authenticate, then fetch a CSRF token. Call once before other methods."""
        resp = self.session.post(
            f"{self.api}/security/login",
            json={
                "username": self.username,
                "password": self.password,
                "provider": self.provider,
                "refresh": True,
            },
            timeout=30,
        )
        self._raise_for_status(resp, "login")
        self.access_token = resp.json()["access_token"]
        self.session.headers["Authorization"] = f"Bearer {self.access_token}"
        self._fetch_csrf()
        return self

    def _fetch_csrf(self) -> None:
        resp = self.session.get(f"{self.api}/security/csrf_token/", timeout=30)
        self._raise_for_status(resp, "csrf_token")
        self.csrf_token = resp.json()["result"]
        self.session.headers["X-CSRFToken"] = self.csrf_token
        # Superset's CSRF protection also checks the Referer header.
        self.session.headers["Referer"] = self.base_url

    # --------------------------------------------------------------- requests
    def request(self, method: str, path: str, **kwargs: Any) -> Any:
        """Generic escape hatch for any endpoint not covered by a helper.

        `path` is relative to /api/v1 (e.g. "/dataset/" or "/database/1").
        Pass a body with json=... and query params already encoded in `path`.
        """
        return self._request(method.upper(), path, **kwargs)

    def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        url = f"{self.api}{path}"
        resp = self.session.request(method, url, timeout=60, **kwargs)
        # A 401 usually means the JWT expired — re-login once and retry.
        if resp.status_code == 401 and self.access_token:
            self.login()
            resp = self.session.request(method, url, timeout=60, **kwargs)
        self._raise_for_status(resp, f"{method} {path}")
        if resp.content:
            ctype = resp.headers.get("Content-Type", "")
            return resp.json() if "application/json" in ctype else resp.content
        return None

    @staticmethod
    def _raise_for_status(resp: requests.Response, what: str) -> None:
        if not resp.ok:
            body = resp.text[:1000]
            raise SupersetError(f"{what} failed [{resp.status_code}]: {body}")

    # ------------------------------------------------------------- dashboards
    def list_dashboards(self, page_size: int = 100, page: int = 0) -> Any:
        # Rison-encoded query param; this simple form works for paging.
        q = f"(page_size:{page_size},page:{page})"
        return self._request("GET", f"/dashboard/?q={q}")

    def get_dashboard(self, dashboard_id: int) -> Any:
        return self._request("GET", f"/dashboard/{dashboard_id}")

    def create_dashboard(self, payload: dict) -> Any:
        return self._request("POST", "/dashboard/", json=payload)

    def update_dashboard(self, dashboard_id: int, payload: dict) -> Any:
        return self._request("PUT", f"/dashboard/{dashboard_id}", json=payload)

    def delete_dashboard(self, dashboard_id: int) -> Any:
        return self._request("DELETE", f"/dashboard/{dashboard_id}")

    def export_dashboards(self, ids: list[int]) -> bytes:
        """Returns a ZIP archive (bytes) of the given dashboards."""
        rison_ids = "!(" + ",".join(str(i) for i in ids) + ")"
        return self._request("GET", f"/dashboard/export/?q={rison_ids}")

    # ----------------------------------------------------------------- charts
    def list_charts(self, page_size: int = 100, page: int = 0) -> Any:
        q = f"(page_size:{page_size},page:{page})"
        return self._request("GET", f"/chart/?q={q}")

    def get_chart(self, chart_id: int) -> Any:
        return self._request("GET", f"/chart/{chart_id}")

    def create_chart(self, payload: dict) -> Any:
        return self._request("POST", "/chart/", json=payload)

    def update_chart(self, chart_id: int, payload: dict) -> Any:
        return self._request("PUT", f"/chart/{chart_id}", json=payload)

    def delete_chart(self, chart_id: int) -> Any:
        return self._request("DELETE", f"/chart/{chart_id}")
