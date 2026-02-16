"""
Backend Flask server providing endpoints which can be called from the frontend.
This server is meant to be run locally, and is not intended for production use.

Code initially copied from [Plaid's Python Quickstart](https://github.com/plaid/quickstart) `python/server.py`.
"""

import os
import datetime as dt
import json
import time
from pathlib import Path
from typing import Any, Callable, Dict, Optional

from dotenv import load_dotenv
from flask import Flask, request, jsonify
from loguru import logger
import plaid
from plaid.model.products import Products
from plaid.model.country_code import CountryCode
from plaid.model.item_public_token_exchange_request import (
    ItemPublicTokenExchangeRequest,
)
from plaid.model.link_token_create_request import LinkTokenCreateRequest
from plaid.model.link_token_create_request_user import LinkTokenCreateRequestUser
from plaid.model.transactions_sync_request import TransactionsSyncRequest
from plaid.model.investments_transactions_get_request_options import (
    InvestmentsTransactionsGetRequestOptions,
)
from plaid.model.investments_transactions_get_request import (
    InvestmentsTransactionsGetRequest,
)
from plaid.model.accounts_balance_get_request import AccountsBalanceGetRequest
from plaid.model.accounts_get_request import AccountsGetRequest
from plaid.model.investments_holdings_get_request import InvestmentsHoldingsGetRequest
from plaid.model.item_get_request import ItemGetRequest
from plaid.model.institutions_get_by_id_request import InstitutionsGetByIdRequest
from plaid.api import plaid_api

load_dotenv()


def _empty_to_none(env: Dict[str, str], field: str) -> Optional[str]:
    value = env.get(field)
    if value is None or len(value) == 0:
        return None
    return value


class PlaidBackend:
    """Encapsulates Plaid client + credential state.

    The instance methods return plain Python dicts so they can be called without
    running a Flask server. Flask route handlers are thin wrappers around these
    methods.
    """

    def __init__(
        self,
        *,
        env: Optional[Dict[str, str]] = None,
        access_token: Optional[str] = None,
        item_id: Optional[str] = None,
    ) -> None:
        self._env: Dict[str, str] = dict(env) if env is not None else dict(os.environ)

        self.plaid_client_id = self._env.get("PLAID_CLIENT_ID")
        self.plaid_secret = self._env.get("PLAID_SECRET")
        self.plaid_env = self._env.get("PLAID_ENV", "sandbox")
        self.plaid_products = self._env.get("PLAID_PRODUCTS", "transactions").split(",")
        self.plaid_country_codes = self._env.get("PLAID_COUNTRY_CODES", "US").split(",")

        self.secrets_dir = Path(
            self._env.get(
                "PLAID_SECRETS_DIR",
                str(Path(__file__).resolve().parents[1] / "secrets"),
            )
        )

        # Parameters used for the OAuth redirect Link flow.
        self.plaid_redirect_uri = _empty_to_none(self._env, "PLAID_REDIRECT_URI")

        host = plaid.Environment.Sandbox
        if self.plaid_env == "sandbox":
            host = plaid.Environment.Sandbox
        if self.plaid_env == "production":
            host = plaid.Environment.Production

        configuration = plaid.Configuration(
            host=host,
            api_key={
                "clientId": self.plaid_client_id,
                "secret": self.plaid_secret,
                "plaidVersion": "2020-09-14",
            },
        )
        api_client = plaid.ApiClient(configuration)
        self.client = plaid_api.PlaidApi(api_client)

        self.products = [Products(product) for product in self.plaid_products]

        # We store the access_token in memory - in production, store it in a secure
        # persistent data store.
        self.access_token: Optional[str] = access_token
        self.item_id: Optional[str] = item_id

        self.app = Flask(__name__)
        self._register_routes(self.app)

    def _register_routes(self, app: Flask) -> None:
        @app.route("/api/info", methods=["POST"])
        def info_route():
            return jsonify(self.info())

        @app.route("/api/create_link_token", methods=["POST"])
        def create_link_token_route():
            return jsonify(self.create_link_token())

        @app.route("/api/set_access_token", methods=["POST"])
        def set_access_token_route():
            public_token = request.form["public_token"]
            return jsonify(self.exchange_public_token(public_token))

        @app.route("/api/transactions", methods=["GET"])
        def transactions_route():
            account_id = request.args.get("account_id")
            return jsonify(self.get_transactions(account_id=account_id))

        @app.route("/api/balance", methods=["GET"])
        def balance_route():
            return jsonify(self.get_balance())

        @app.route("/api/accounts", methods=["GET"])
        def accounts_route():
            return jsonify(self.get_accounts())

        @app.route("/api/holdings", methods=["GET"])
        def holdings_route():
            return jsonify(self.get_holdings())

        @app.route("/api/investments_transactions", methods=["GET"])
        def investments_transactions_route():
            return jsonify(self.get_investments_transactions())

        @app.route("/api/item", methods=["GET"])
        def item_route():
            return jsonify(self.get_item())

    def info(self) -> Dict[str, Any]:
        return {
            "item_id": self.item_id,
            "access_token": self.access_token,
            "products": self.plaid_products,
        }

    def create_link_token(self) -> Dict[str, Any]:
        try:
            link_request = LinkTokenCreateRequest(
                products=self.products,
                client_name="Plaid Quickstart",
                country_codes=list(
                    map(lambda x: CountryCode(x), self.plaid_country_codes)
                ),
                language="en",
                user=LinkTokenCreateRequestUser(client_user_id=str(time.time())),
            )

            if self.plaid_redirect_uri is not None:
                link_request["redirect_uri"] = self.plaid_redirect_uri

            response = self.client.link_token_create(link_request)
            return response.to_dict()
        except plaid.ApiException as exc:
            logger.exception("Plaid link_token_create failed")
            return json.loads(exc.body)

    def exchange_public_token(self, public_token: str) -> Dict[str, Any]:
        try:
            exchange_request = ItemPublicTokenExchangeRequest(public_token=public_token)
            exchange_response = self.client.item_public_token_exchange(exchange_request)

            self.access_token = exchange_response["access_token"]
            self.item_id = exchange_response["item_id"]

            institution_id = None
            try:
                item_response = self.client.item_get(
                    ItemGetRequest(access_token=self.access_token)
                )
                item_payload = item_response.to_dict()
                institution_id = item_payload.get("item", {}).get("institution_id")
            except plaid.ApiException:
                logger.exception("Plaid item_get failed while exchanging public_token")

            self.persist_credentials(
                institution_id=institution_id,
                item_id=self.item_id,
                token=self.access_token,
            )

            response_payload = exchange_response.to_dict()
            response_payload["institution_id"] = institution_id
            return response_payload
        except plaid.ApiException as exc:
            return json.loads(exc.body)

    def get_transactions(self, *, account_id: Optional[str] = None) -> Dict[str, Any]:
        cursor = ""
        added = []
        modified = []
        removed = []
        has_more = True
        try:
            while has_more:
                sync_request = TransactionsSyncRequest(
                    access_token=self.access_token,
                    cursor=cursor,
                )
                response = self.client.transactions_sync(sync_request).to_dict()
                cursor = response["next_cursor"]
                if cursor == "":
                    time.sleep(2)
                    continue
                added.extend(response["added"])
                modified.extend(response["modified"])
                removed.extend(response["removed"])
                has_more = response["has_more"]
                self.pretty_print_response(response)

            filtered = added
            if account_id:
                filtered = [t for t in added if t.get("account_id") == account_id]

            latest_transactions = sorted(filtered, key=lambda t: t["date"])[-8:]
            return {"latest_transactions": latest_transactions}
        except plaid.ApiException as exc:
            return self.format_error(exc)

    def get_balance(self) -> Dict[str, Any]:
        try:
            balance_request = AccountsBalanceGetRequest(access_token=self.access_token)
            balance_response = self.client.accounts_balance_get(balance_request)
            self.pretty_print_response(balance_response.to_dict())
            return balance_response.to_dict()
        except plaid.ApiException as exc:
            return self.format_error(exc)

    def get_accounts(self) -> Dict[str, Any]:
        try:
            accounts_request = AccountsGetRequest(access_token=self.access_token)
            response = self.client.accounts_get(accounts_request)
            self.pretty_print_response(response.to_dict())
            return response.to_dict()
        except plaid.ApiException as exc:
            return self.format_error(exc)

    def get_holdings(self) -> Dict[str, Any]:
        try:
            holdings_request = InvestmentsHoldingsGetRequest(
                access_token=self.access_token
            )
            response = self.client.investments_holdings_get(holdings_request)
            self.pretty_print_response(response.to_dict())
            return {"error": None, "holdings": response.to_dict()}
        except plaid.ApiException as exc:
            return self.format_error(exc)

    def get_investments_transactions(self) -> Dict[str, Any]:
        start_date = dt.datetime.now() - dt.timedelta(days=30)
        end_date = dt.datetime.now()
        try:
            options = InvestmentsTransactionsGetRequestOptions()
            investments_request = InvestmentsTransactionsGetRequest(
                access_token=self.access_token,
                start_date=start_date.date(),
                end_date=end_date.date(),
                options=options,
            )
            response = self.client.investments_transactions_get(investments_request)
            self.pretty_print_response(response.to_dict())
            return {"error": None, "investments_transactions": response.to_dict()}
        except plaid.ApiException as exc:
            return self.format_error(exc)

    def get_item(self) -> Dict[str, Any]:
        try:
            item_request = ItemGetRequest(access_token=self.access_token)
            item_response = self.client.item_get(item_request)

            institution_request = InstitutionsGetByIdRequest(
                institution_id=item_response["item"]["institution_id"],
                country_codes=list(
                    map(lambda x: CountryCode(x), self.plaid_country_codes)
                ),
            )
            institution_response = self.client.institutions_get_by_id(
                institution_request
            )

            self.pretty_print_response(item_response.to_dict())
            self.pretty_print_response(institution_response.to_dict())
            return {
                "error": None,
                "item": item_response.to_dict()["item"],
                "institution": institution_response.to_dict()["institution"],
            }
        except plaid.ApiException as exc:
            return self.format_error(exc)

    @staticmethod
    def poll_with_retries(
        request_callback: Callable[[], Any], *, ms: int = 1000, retries_left: int = 20
    ) -> Any:
        while retries_left > 0:
            try:
                return request_callback()
            except plaid.ApiException as exc:
                response = json.loads(exc.body)
                if response["error_code"] != "PRODUCT_NOT_READY":
                    raise
                if retries_left == 0:
                    raise Exception("Ran out of retries while polling") from exc

                retries_left -= 1
                time.sleep(ms / 1000)

    @staticmethod
    def pretty_print_response(response: Any) -> None:
        logger.debug(json.dumps(response, indent=2, sort_keys=True, default=str))

    @staticmethod
    def format_error(exc: plaid.ApiException) -> Dict[str, Any]:
        response = json.loads(exc.body)
        return {
            "error": {
                "status_code": exc.status,
                "display_message": response["error_message"],
                "error_code": response["error_code"],
                "error_type": response["error_type"],
            }
        }

    def persist_credentials(
        self,
        *,
        institution_id: Optional[str],
        item_id: Optional[str],
        token: Optional[str],
    ) -> None:
        identifier = institution_id or item_id
        if identifier is None:
            return

        try:
            self.secrets_dir.mkdir(parents=True, exist_ok=True)
            (self.secrets_dir / f"{identifier}_item_id").write_text(item_id or "")
            (self.secrets_dir / f"{identifier}_access_token").write_text(token or "")
        except OSError as exc:
            logger.warning("Unable to write tokens to {}: {}", self.secrets_dir, exc)


# Module-level Flask app for compatibility with `flask run` and `python -m yapcli.server`.
backend = PlaidBackend()
app = backend.app


if __name__ == "__main__":
    app.run(port=int(os.getenv("PORT", 8000)))
