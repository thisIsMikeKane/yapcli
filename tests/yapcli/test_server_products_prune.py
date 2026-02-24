from __future__ import annotations

from typing import Any, Dict

import pytest

from yapcli.server import PlaidBackend


def test_backend_prunes_products_using_consented_products(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_get_item(
        self: PlaidBackend, *, include_institution: bool = True
    ) -> Dict[str, Any]:
        return {
            "error": None,
            "item": {"consented_products": ["transactions"]},
            "institution": None,
        }

    monkeypatch.setattr(PlaidBackend, "get_item", fake_get_item)

    backend = PlaidBackend(
        env={
            "PLAID_CLIENT_ID": "client",
            "PLAID_SECRET": "secret",
            "PLAID_ENV": "sandbox",
            "PLAID_COUNTRY_CODES": "US",
        },
        access_token="access",
        item_id="item",
        products=["transactions", "investments"],
    )

    assert backend.plaid_products == ["transactions"]


def test_backend_falls_back_to_consented_when_intersection_empty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_get_item(
        self: PlaidBackend, *, include_institution: bool = True
    ) -> Dict[str, Any]:
        return {
            "error": None,
            "item": {"consented_products": ["investments"]},
            "institution": None,
        }

    monkeypatch.setattr(PlaidBackend, "get_item", fake_get_item)

    backend = PlaidBackend(
        env={
            "PLAID_CLIENT_ID": "client",
            "PLAID_SECRET": "secret",
            "PLAID_ENV": "sandbox",
            "PLAID_COUNTRY_CODES": "US",
        },
        access_token="access",
        item_id="item",
        products=["transactions"],
    )

    assert backend.plaid_products == ["investments"]
