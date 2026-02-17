from __future__ import annotations

from typing import Any, Dict, List

import pytest

from yapcli.server import PlaidBackend


class _FakePlaidResponse:
    def __init__(self, payload: Dict[str, Any]) -> None:
        self._payload = payload

    def to_dict(self) -> Dict[str, Any]:
        return self._payload


class _FakePlaidClient:
    def __init__(self, pages: List[Dict[str, Any]]) -> None:
        self._pages = pages
        self.calls = 0

    def transactions_sync(self, *_args: Any, **_kwargs: Any) -> _FakePlaidResponse:
        self.calls += 1
        idx = min(self.calls - 1, len(self._pages) - 1)
        return _FakePlaidResponse(self._pages[idx])


def test_transactions_sync_stops_after_two_empty_next_cursor_retries(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Avoid waiting during retries.
    monkeypatch.setattr("yapcli.server.time.sleep", lambda _seconds: None)

    backend = PlaidBackend(
        env={
            "PLAID_CLIENT_ID": "client",
            "PLAID_SECRET": "secret",
            "PLAID_ENV": "sandbox",
            "PLAID_PRODUCTS": "transactions",
            "PLAID_COUNTRY_CODES": "US",
        }
    )
    backend.access_token = "access"

    pages = [
        {
            "next_cursor": "",
            "has_more": True,
            "added": [],
            "modified": [],
            "removed": [],
        },
        {
            "next_cursor": "",
            "has_more": True,
            "added": [],
            "modified": [],
            "removed": [],
        },
        {
            "next_cursor": "",
            "has_more": True,
            "added": [],
            "modified": [],
            "removed": [],
        },
    ]
    fake_client = _FakePlaidClient(pages)
    backend.client = fake_client  # type: ignore[assignment]

    payload = backend.get_transactions(account_id="acc")

    assert fake_client.calls == 3
    assert isinstance(payload, dict)
    assert "error" in payload
    err = payload["error"]
    assert isinstance(err, dict)
    assert err.get("error_code") == "EMPTY_NEXT_CURSOR"
