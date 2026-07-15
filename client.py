"""Thin wrapper around the Binance USDT-M Futures REST API.

Implemented with plain `requests` + manual HMAC-SHA256 signing rather than
the `python-binance` package so the signing/auth flow is fully transparent
and there is no dependency version lock-in. Every request and response is
logged for auditability.

API docs: https://binance-docs.github.io/apidocs/testnet/en/
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import time
from typing import Any
from urllib.parse import urlencode

import requests

from .exceptions import APIError, NetworkError

logger = logging.getLogger("trading_bot.client")

DEFAULT_BASE_URL = "https://testnet.binancefuture.com"
DEFAULT_TIMEOUT = 10  # seconds


class BinanceFuturesClient:
    """Minimal signed REST client for Binance USDT-M Futures Testnet."""

    def __init__(
        self,
        api_key: str,
        api_secret: str,
        base_url: str = DEFAULT_BASE_URL,
        timeout: int = DEFAULT_TIMEOUT,
    ):
        if not api_key or not api_secret:
            raise ValueError("API key and secret must both be provided.")
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({"X-MBX-APIKEY": self.api_key})

    # ------------------------------------------------------------------ #
    # Low-level signed request helper
    # ------------------------------------------------------------------ #
    def _sign(self, params: dict[str, Any]) -> dict[str, Any]:
        params = dict(params)
        params["timestamp"] = int(time.time() * 1000)
        params.setdefault("recvWindow", 5000)
        query_string = urlencode(params, doseq=True)
        signature = hmac.new(
            self.api_secret.encode("utf-8"),
            query_string.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        params["signature"] = signature
        return params

    def _request(
        self,
        method: str,
        path: str,
        params: dict[str, Any] | None = None,
        signed: bool = False,
    ) -> dict[str, Any]:
        url = f"{self.base_url}{path}"
        params = params or {}
        if signed:
            params = self._sign(params)

        # Redact secrets before logging.
        safe_params = {k: v for k, v in params.items() if k != "signature"}
        logger.debug("REQUEST %s %s params=%s", method, path, safe_params)

        try:
            response = self.session.request(
                method, url, params=params, timeout=self.timeout
            )
        except requests.exceptions.RequestException as exc:
            logger.error("NETWORK ERROR %s %s: %s", method, path, exc)
            raise NetworkError(f"Network error calling {path}: {exc}") from exc

        logger.debug(
            "RESPONSE %s %s status=%s body=%s",
            method,
            path,
            response.status_code,
            response.text,
        )

        try:
            data = response.json()
        except ValueError:
            data = {"raw": response.text}

        if not response.ok:
            message = data.get("msg", str(data)) if isinstance(data, dict) else str(data)
            logger.error(
                "API ERROR %s %s status=%s code=%s msg=%s",
                method,
                path,
                response.status_code,
                data.get("code") if isinstance(data, dict) else None,
                message,
            )
            raise APIError(message, status_code=response.status_code, payload=data)

        return data

    # ------------------------------------------------------------------ #
    # Public endpoints
    # ------------------------------------------------------------------ #
    def ping(self) -> dict[str, Any]:
        """Basic connectivity test (unauthenticated)."""
        return self._request("GET", "/fapi/v1/ping")

    def server_time(self) -> dict[str, Any]:
        return self._request("GET", "/fapi/v1/time")

    def exchange_info(self, symbol: str | None = None) -> dict[str, Any]:
        params = {"symbol": symbol} if symbol else {}
        return self._request("GET", "/fapi/v1/exchangeInfo", params)

    # ------------------------------------------------------------------ #
    # Signed / account endpoints
    # ------------------------------------------------------------------ #
    def account_balance(self) -> dict[str, Any]:
        return self._request("GET", "/fapi/v2/balance", signed=True)

    def create_order(
        self,
        symbol: str,
        side: str,
        order_type: str,
        quantity: float,
        price: float | None = None,
        stop_price: float | None = None,
        time_in_force: str = "GTC",
    ) -> dict[str, Any]:
        """Place an order on Binance USDT-M Futures.

        `order_type` here is the internal bot type (MARKET / LIMIT /
        STOP_LIMIT); it is translated to the Binance API's `type` field.
        """
        params: dict[str, Any] = {
            "symbol": symbol,
            "side": side,
            "quantity": quantity,
        }

        if order_type == "MARKET":
            params["type"] = "MARKET"
        elif order_type == "LIMIT":
            params["type"] = "LIMIT"
            params["price"] = price
            params["timeInForce"] = time_in_force
        elif order_type == "STOP_LIMIT":
            params["type"] = "STOP"
            params["price"] = price
            params["stopPrice"] = stop_price
            params["timeInForce"] = time_in_force
        else:
            raise ValueError(f"Unsupported order type: {order_type}")

        return self._request("POST", "/fapi/v1/order", params, signed=True)

    def get_order(self, symbol: str, order_id: int) -> dict[str, Any]:
        params = {"symbol": symbol, "orderId": order_id}
        return self._request("GET", "/fapi/v1/order", params, signed=True)

    def cancel_order(self, symbol: str, order_id: int) -> dict[str, Any]:
        params = {"symbol": symbol, "orderId": order_id}
        return self._request("DELETE", "/fapi/v1/order", params, signed=True)
