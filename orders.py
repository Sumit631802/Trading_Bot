"""Order placement logic — sits between the CLI and the raw API client.

Responsible for: validating input, logging the outgoing request summary,
calling the client, and normalising the response into a small `OrderResult`
dataclass that's easy for the CLI (or any future front-end) to print.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Optional

from . import validators
from .client import BinanceFuturesClient
from .exceptions import APIError, NetworkError, ValidationError

logger = logging.getLogger("trading_bot.orders")


@dataclass
class OrderResult:
    success: bool
    order_id: Optional[int] = None
    status: Optional[str] = None
    executed_qty: Optional[str] = None
    avg_price: Optional[str] = None
    raw_response: Optional[dict[str, Any]] = None
    error_message: Optional[str] = None


class OrderService:
    def __init__(self, client: BinanceFuturesClient):
        self.client = client

    def place_order(
        self,
        symbol: str,
        side: str,
        order_type: str,
        quantity,
        price=None,
        stop_price=None,
    ) -> OrderResult:
        # -------------------- validation -------------------- #
        symbol = validators.validate_symbol(symbol)
        side = validators.validate_side(side)
        order_type = validators.validate_order_type(order_type)
        quantity = validators.validate_quantity(quantity)
        price = validators.validate_price(price, order_type)
        stop_price = validators.validate_stop_price(stop_price, order_type)

        logger.info(
            "ORDER REQUEST symbol=%s side=%s type=%s quantity=%s price=%s stop_price=%s",
            symbol, side, order_type, quantity, price, stop_price,
        )

        # -------------------- execution -------------------- #
        try:
            response = self.client.create_order(
                symbol=symbol,
                side=side,
                order_type=order_type,
                quantity=quantity,
                price=price,
                stop_price=stop_price,
            )
        except APIError as exc:
            logger.error("ORDER FAILED (API error): %s", exc)
            return OrderResult(success=False, error_message=str(exc))
        except NetworkError as exc:
            logger.error("ORDER FAILED (network error): %s", exc)
            return OrderResult(success=False, error_message=str(exc))

        logger.info(
            "ORDER RESPONSE orderId=%s status=%s executedQty=%s avgPrice=%s",
            response.get("orderId"),
            response.get("status"),
            response.get("executedQty"),
            response.get("avgPrice"),
        )

        return OrderResult(
            success=True,
            order_id=response.get("orderId"),
            status=response.get("status"),
            executed_qty=response.get("executedQty"),
            avg_price=response.get("avgPrice"),
            raw_response=response,
        )
