from __future__ import annotations

import datetime as dt
from typing import Any, Dict

from yapcli.server import PlaidBackend


class _FakePlaidResponse:
    def __init__(self, payload: Dict[str, Any]) -> None:
        self._payload = payload

    def to_dict(self) -> Dict[str, Any]:
        return self._payload


class _FakePlaidClient:
    def __init__(self, payload: Dict[str, Any]) -> None:
        self.payload = payload
        self.requests: list[Dict[str, Any]] = []

    def investments_transactions_get(
        self, request: Any, **_kwargs: Any
    ) -> _FakePlaidResponse:
        self.requests.append(request.to_dict())
        return _FakePlaidResponse(self.payload)


def test_get_investments_transactions_passes_start_and_end_dates() -> None:
    backend = PlaidBackend(
        env={
            "PLAID_CLIENT_ID": "client",
            "PLAID_SECRET": "secret",
            "PLAID_ENV": "sandbox",
            "PLAID_PRODUCTS": "investments",
            "PLAID_COUNTRY_CODES": "US",
        }
    )
    backend.access_token = "access"

    fake_client = _FakePlaidClient(payload={"investment_transactions": []})
    backend.client = fake_client  # type: ignore[assignment]

    start_date = dt.date(2026, 1, 1)
    end_date = dt.date(2026, 1, 31)
    payload = backend.get_investments_transactions(
        start_date=start_date,
        end_date=end_date,
    )

    assert payload.get("error") is None
    assert len(fake_client.requests) == 1
    assert fake_client.requests[0].get("start_date") == start_date
    assert fake_client.requests[0].get("end_date") == end_date
