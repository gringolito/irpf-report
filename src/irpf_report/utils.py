from collections.abc import Iterable
from datetime import date
import logging
import os
from typing import Any
import httpx


def format_date(date: date) -> str:
    return date.strftime("%d/%m/%Y")


def _get_json_key(key: str, keys: Iterable) -> str | None:
    filtered_keys = list(filter(lambda k: key in k, keys))
    if len(filtered_keys) == 0:
        return None
    return filtered_keys[0]


def search_asset_online(ticker: str) -> dict[str, Any] | None:
    token = os.getenv("IRPF_REPORT_STOCKS_APIKEY")
    if token is None:
        logging.warning("Environment variable IRPF_REPORT_STOCKS_APIKEY is not set. Skipping online ticker search.")
        return None

    url = f"https://www.alphavantage.co/query?function=SYMBOL_SEARCH&keywords={ticker}&apikey={token}"
    response = httpx.get(url)
    if not response.is_success:
        logging.warning("Online ticker search failed: request returned HTTP status code %d.", response.status_code)
        return None

    data = response.json()
    for asset in data["bestMatches"]:
        symbol_key = _get_json_key("symbol", asset.keys())
        if symbol_key is None:
            logging.warning("Online ticker search failed: could not find the 'symbol' field on the returned data.")
            return None

        symbol = asset[symbol_key].split(".")[0]
        if symbol == ticker:
            return asset

    return None


def search_asset_type_online(ticker: str) -> str | None:
    asset = search_asset_online(ticker)
    if asset is None:
        return None

    type_key = _get_json_key("type", asset.keys())
    if type_key is None:
        logging.warning("Online ticker search failed: could not find the 'type' field on the returned data.")
        return None

    asset_type = asset[type_key]
    if asset_type == "Equity":
        return "Stock"
    if asset_type == "ETF":
        return "ETF"
    if asset_type == "Mutual Fund":
        return "Fund"

    return None
