"""Thin REST client for the Relm CRM API (https://relmcrm.com).

Errors are NOT raised: Relm returns RFC-9457 problem+json with ``valid_options`` and a
``suggestion`` on any bad input, so the client returns the error body untouched. Passed
straight back to the LLM as tool output, that lets an agent self-correct in one turn
instead of crashing - the whole point of an agent-native CRM.
"""
from __future__ import annotations

import os
from typing import Any, Optional

import requests

DEFAULT_BASE_URL = "https://api.relmcrm.com/v1"


class RelmClient:
    """Minimal authenticated client. Mint a free key at https://app.relmcrm.com/."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: float = 30.0,
    ) -> None:
        self.api_key = api_key or os.environ.get("RELM_API_KEY")
        if not self.api_key:
            raise ValueError(
                "A Relm API key is required. Pass api_key=... or set RELM_API_KEY "
                "(mint a free key, and a free test-mode key, at https://app.relmcrm.com/)."
            )
        self.base_url = (base_url or os.environ.get("RELM_BASE_URL") or DEFAULT_BASE_URL).rstrip("/")
        self.timeout = timeout
        self._session = requests.Session()
        self._session.headers.update(
            {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "User-Agent": "langchain-relm",
            }
        )

    def request(
        self,
        method: str,
        path: str,
        params: Optional[dict] = None,
        json_body: Optional[dict] = None,
    ) -> Any:
        url = f"{self.base_url}/{path.lstrip('/')}"
        resp = self._session.request(method, url, params=params, json=json_body, timeout=self.timeout)
        try:
            data = resp.json()
        except ValueError:
            data = {"detail": resp.text or f"HTTP {resp.status_code}"}
        if resp.status_code >= 400:
            # Preserve Relm's problem+json (valid_options / suggestion) for the agent.
            return {"error": data if isinstance(data, dict) else {"detail": str(data)}}
        return data

    def get(self, path: str, params: Optional[dict] = None) -> Any:
        return self.request("GET", path, params=params)

    def post(self, path: str, json_body: Optional[dict] = None) -> Any:
        return self.request("POST", path, json_body=json_body)

    def patch(self, path: str, json_body: Optional[dict] = None) -> Any:
        return self.request("PATCH", path, json_body=json_body)


def _drop_none(d: dict) -> dict:
    """Omit None values so we never send an explicit null the API didn't ask for."""
    return {k: v for k, v in d.items() if v is not None}
