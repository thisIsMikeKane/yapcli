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

from dotenv import load_dotenv
from flask import Flask, request, jsonify
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


app = Flask(__name__)

PLAID_CLIENT_ID = os.getenv("PLAID_CLIENT_ID")
PLAID_SECRET = os.getenv("PLAID_SECRET")
PLAID_ENV = os.getenv("PLAID_ENV", "sandbox")
PLAID_PRODUCTS = os.getenv("PLAID_PRODUCTS", "transactions").split(",")
PLAID_COUNTRY_CODES = os.getenv("PLAID_COUNTRY_CODES", "US").split(",")
SECRETS_DIR = Path(
    os.getenv(
        "PLAID_SECRETS_DIR",
        Path(__file__).resolve().parents[1] / "secrets",
    )
)


def empty_to_none(field):
    value = os.getenv(field)
    if value is None or len(value) == 0:
        return None
    return value


host = plaid.Environment.Sandbox

if PLAID_ENV == "sandbox":
    host = plaid.Environment.Sandbox

if PLAID_ENV == "production":
    host = plaid.Environment.Production

# Parameters used for the OAuth redirect Link flow.
#
# Set PLAID_REDIRECT_URI to 'http://localhost:3000/'
# The OAuth redirect flow requires an endpoint on the developer's website
# that the bank website should redirect to. You will need to configure
# this redirect URI for your client ID through the Plaid developer dashboard
# at https://dashboard.plaid.com/team/api.
PLAID_REDIRECT_URI = empty_to_none("PLAID_REDIRECT_URI")

configuration = plaid.Configuration(
    host=host,
    api_key={
        "clientId": PLAID_CLIENT_ID,
        "secret": PLAID_SECRET,
        "plaidVersion": "2020-09-14",
    },
)

api_client = plaid.ApiClient(configuration)
client = plaid_api.PlaidApi(api_client)

products = []
for product in PLAID_PRODUCTS:
    products.append(Products(product))


# We store the access_token in memory - in production, store it in a secure
# persistent data store.
access_token = None
item_id = None


@app.route("/api/info", methods=["POST"])
def info():
    global access_token
    global item_id
    return jsonify(
        {"item_id": item_id, "access_token": access_token, "products": PLAID_PRODUCTS}
    )


@app.route("/api/create_link_token", methods=["POST"])
def create_link_token():
    try:
        request = LinkTokenCreateRequest(
            products=products,
            client_name="Plaid Quickstart",
            country_codes=list(map(lambda x: CountryCode(x), PLAID_COUNTRY_CODES)),
            language="en",
            user=LinkTokenCreateRequestUser(client_user_id=str(time.time())),
        )

        if PLAID_REDIRECT_URI is not None:
            request["redirect_uri"] = PLAID_REDIRECT_URI

        # create link token
        response = client.link_token_create(request)
        return jsonify(response.to_dict())
    except plaid.ApiException as e:
        print(e)
        return json.loads(e.body)


# Exchange token flow - exchange a Link public_token for
# an API access_token
# https://plaid.com/docs/#exchange-token-flow


@app.route("/api/set_access_token", methods=["POST"])
def get_access_token():
    global access_token
    global item_id
    public_token = request.form["public_token"]
    try:
        exchange_request = ItemPublicTokenExchangeRequest(public_token=public_token)
        exchange_response = client.item_public_token_exchange(exchange_request)
        access_token = exchange_response["access_token"]
        item_id = exchange_response["item_id"]
        institution_id = None
        try:
            item_response = client.item_get(ItemGetRequest(access_token=access_token))
            item_payload = item_response.to_dict()
            institution_id = item_payload.get("item", {}).get("institution_id")
        except plaid.ApiException as item_exc:
            print(item_exc)

        persist_credentials(
            institution_id=institution_id, item_id=item_id, token=access_token
        )

        response_payload = exchange_response.to_dict()
        response_payload["institution_id"] = institution_id
        return jsonify(response_payload)
    except plaid.ApiException as e:
        return json.loads(e.body)


# Retrieve Transactions for an Item
# https://plaid.com/docs/#transactions


@app.route("/api/transactions", methods=["GET"])
def get_transactions():
    # Set cursor to empty to receive all historical updates
    cursor = ""

    # New transaction updates since "cursor"
    added = []
    modified = []
    removed = []  # Removed transaction ids
    has_more = True
    try:
        # Iterate through each page of new transaction updates for item
        while has_more:
            request = TransactionsSyncRequest(
                access_token=access_token,
                cursor=cursor,
            )
            response = client.transactions_sync(request).to_dict()
            cursor = response["next_cursor"]
            # If no transactions are available yet, wait and poll the endpoint.
            # Normally, we would listen for a webhook, but the Quickstart doesn't
            # support webhooks. For a webhook example, see
            # https://github.com/plaid/tutorial-resources or
            # https://github.com/plaid/pattern
            if cursor == "":
                time.sleep(2)
                continue
            # If cursor is not an empty string, we got results,
            # so add this page of results
            added.extend(response["added"])
            modified.extend(response["modified"])
            removed.extend(response["removed"])
            has_more = response["has_more"]
            pretty_print_response(response)

        # Return the 8 most recent transactions
        latest_transactions = sorted(added, key=lambda t: t["date"])[-8:]
        return jsonify({"latest_transactions": latest_transactions})

    except plaid.ApiException as e:
        error_response = format_error(e)
        return jsonify(error_response)


# Retrieve real-time balance data for each of an Item's accounts
# https://plaid.com/docs/#balance


@app.route("/api/balance", methods=["GET"])
def get_balance():
    try:
        balance_request = AccountsBalanceGetRequest(access_token=access_token)
        balance_response = client.accounts_balance_get(balance_request)
        pretty_print_response(balance_response.to_dict())
        return jsonify(balance_response.to_dict())
    except plaid.ApiException as e:
        error_response = format_error(e)
        return jsonify(error_response)


# Retrieve an Item's accounts
# https://plaid.com/docs/#accounts


@app.route("/api/accounts", methods=["GET"])
def get_accounts():
    try:
        request = AccountsGetRequest(access_token=access_token)
        response = client.accounts_get(request)
        pretty_print_response(response.to_dict())
        return jsonify(response.to_dict())
    except plaid.ApiException as e:
        error_response = format_error(e)
        return jsonify(error_response)


# Retrieve investment holdings data for an Item
# https://plaid.com/docs/#investments


@app.route("/api/holdings", methods=["GET"])
def get_holdings():
    try:
        request = InvestmentsHoldingsGetRequest(access_token=access_token)
        response = client.investments_holdings_get(request)
        pretty_print_response(response.to_dict())
        return jsonify({"error": None, "holdings": response.to_dict()})
    except plaid.ApiException as e:
        error_response = format_error(e)
        return jsonify(error_response)


# Retrieve Investment Transactions for an Item
# https://plaid.com/docs/#investments


@app.route("/api/investments_transactions", methods=["GET"])
def get_investments_transactions():
    # Pull transactions for the last 30 days

    start_date = dt.datetime.now() - dt.timedelta(days=(30))
    end_date = dt.datetime.now()
    try:
        options = InvestmentsTransactionsGetRequestOptions()
        request = InvestmentsTransactionsGetRequest(
            access_token=access_token,
            start_date=start_date.date(),
            end_date=end_date.date(),
            options=options,
        )
        response = client.investments_transactions_get(request)
        pretty_print_response(response.to_dict())
        return jsonify({"error": None, "investments_transactions": response.to_dict()})

    except plaid.ApiException as e:
        error_response = format_error(e)
        return jsonify(error_response)


# Retrieve high-level information about an Item
# https://plaid.com/docs/#retrieve-item


@app.route("/api/item", methods=["GET"])
def item():
    try:
        request = ItemGetRequest(access_token=access_token)
        response = client.item_get(request)
        request = InstitutionsGetByIdRequest(
            institution_id=response["item"]["institution_id"],
            country_codes=list(map(lambda x: CountryCode(x), PLAID_COUNTRY_CODES)),
        )
        institution_response = client.institutions_get_by_id(request)
        pretty_print_response(response.to_dict())
        pretty_print_response(institution_response.to_dict())
        return jsonify(
            {
                "error": None,
                "item": response.to_dict()["item"],
                "institution": institution_response.to_dict()["institution"],
            }
        )
    except plaid.ApiException as e:
        error_response = format_error(e)
        return jsonify(error_response)


# Since this quickstart does not support webhooks, this function can be used to poll
# an API that would otherwise be triggered by a webhook.
# For a webhook example, see
# https://github.com/plaid/tutorial-resources or
# https://github.com/plaid/pattern
def poll_with_retries(request_callback, ms=1000, retries_left=20):
    while retries_left > 0:
        try:
            return request_callback()
        except plaid.ApiException as e:
            response = json.loads(e.body)
            if response["error_code"] != "PRODUCT_NOT_READY":
                raise e
            elif retries_left == 0:
                raise Exception("Ran out of retries while polling") from e
            else:
                retries_left -= 1
                time.sleep(ms / 1000)


def pretty_print_response(response):
    print(json.dumps(response, indent=2, sort_keys=True, default=str))


def format_error(e):
    response = json.loads(e.body)
    return {
        "error": {
            "status_code": e.status,
            "display_message": response["error_message"],
            "error_code": response["error_code"],
            "error_type": response["error_type"],
        }
    }


def persist_credentials(*, institution_id, item_id, token):
    identifier = institution_id or item_id
    if identifier is None:
        return

    try:
        SECRETS_DIR.mkdir(parents=True, exist_ok=True)
        (SECRETS_DIR / f"{identifier}_item_id").write_text(item_id or "")
        (SECRETS_DIR / f"{identifier}_access_token").write_text(token or "")
    except OSError as exc:
        print(f"Unable to write tokens to {SECRETS_DIR}: {exc}")


if __name__ == "__main__":
    app.run(port=int(os.getenv("PORT", 8000)))
