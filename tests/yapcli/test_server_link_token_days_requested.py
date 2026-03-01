from __future__ import annotations

from typing import Any, Dict

from yapcli.server import PlaidBackend


class _FakePlaidResponse:
    def __init__(self, payload: Dict[str, Any]) -> None:
        self._payload = payload

    def to_dict(self) -> Dict[str, Any]:
        return self._payload


class _FakePlaidClient:
    def __init__(self) -> None:
        self.requests: list[Dict[str, Any]] = []

    def link_token_create(self, request: Any, **_kwargs: Any) -> _FakePlaidResponse:
        self.requests.append(request.to_dict())
        return _FakePlaidResponse({"link_token": "token"})


def test_create_link_token_sets_default_days_requested_for_transactions() -> None:
    backend = PlaidBackend(
        env={
            "PLAID_CLIENT_ID": "client",
            "PLAID_SECRET": "secret",
            "PLAID_ENV": "sandbox",
            "PLAID_COUNTRY_CODES": "US",
        },
        products=["transactions"],
    )
    fake_client = _FakePlaidClient()
    backend.client = fake_client  # type: ignore[assignment]

    payload = backend.create_link_token()

    assert payload.get("link_token") == "token"
    assert len(fake_client.requests) == 1
    transactions = fake_client.requests[0].get("transactions")
    assert isinstance(transactions, dict)
    assert transactions.get("days_requested") == 365


def test_create_link_token_uses_env_days_requested_override() -> None:
    backend = PlaidBackend(
        env={
            "PLAID_CLIENT_ID": "client",
            "PLAID_SECRET": "secret",
            "PLAID_ENV": "sandbox",
            "PLAID_COUNTRY_CODES": "US",
            "YAPCLI_DAYS_REQUESTED": "90",
        },
        products=["transactions"],
    )
    fake_client = _FakePlaidClient()
    backend.client = fake_client  # type: ignore[assignment]

    backend.create_link_token()

    assert len(fake_client.requests) == 1
    transactions = fake_client.requests[0].get("transactions")
    assert isinstance(transactions, dict)
    assert transactions.get("days_requested") == 90


def test_create_link_token_ignores_env_days_requested_out_of_range(caplog) -> None:
    # values outside the Plaid-specified bounds should be replaced by the default
    from yapcli.server import (
        DEFAULT_LINK_DAYS_REQUESTED,
        MAX_LINK_DAYS_REQUESTED,
    )

    for raw_val in ("0", str(MAX_LINK_DAYS_REQUESTED + 1)):
        caplog.clear()
        caplog.set_level("WARNING")

        backend = PlaidBackend(
            env={
                "PLAID_CLIENT_ID": "client",
                "PLAID_SECRET": "secret",
                "PLAID_ENV": "sandbox",
                "PLAID_COUNTRY_CODES": "US",
                "YAPCLI_DAYS_REQUESTED": raw_val,
            },
            products=["transactions"],
        )
        fake_client = _FakePlaidClient()
        backend.client = fake_client  # type: ignore[assignment]

        backend.create_link_token()

        assert len(fake_client.requests) == 1
        transactions = fake_client.requests[0].get("transactions")
        assert isinstance(transactions, dict)
        assert transactions.get("days_requested") == DEFAULT_LINK_DAYS_REQUESTED

