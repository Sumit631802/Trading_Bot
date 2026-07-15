"""Input validation helpers.

All functions raise `bot.exceptions.ValidationError` with a human-readable
message on failure and otherwise return a normalised value. Keeping
validation isolated here (rather than scattered through the CLI) makes it
unit-testable and reusable if a second front-end (e.g. a web UI) is added
later.
"""

from __future__ import annotations

import re

from .exceptions import ValidationError

VALID_SIDES = {"BUY", "SELL"}
VALID_ORDER_TYPES = {"MARKET", "LIMIT", "STOP_LIMIT"}
# Loose Binance Futures symbol pattern, e.g. BTCUSDT, ETHUSDT, 1000PEPEUSDT
_SYMBOL_RE = re.compile(r"^[A-Z0-9]{5,20}$")


def validate_symbol(symbol: str) -> str:
    symbol = (symbol or "").strip().upper()
    if not symbol:
        raise ValidationError("Symbol is required (e.g. BTCUSDT).")
    if not _SYMBOL_RE.match(symbol):
        raise ValidationError(
            f"'{symbol}' does not look like a valid Binance Futures symbol."
        )
    return symbol


def validate_side(side: str) -> str:
    side = (side or "").strip().upper()
    if side not in VALID_SIDES:
        raise ValidationError(f"Side must be one of {sorted(VALID_SIDES)}, got '{side}'.")
    return side


def validate_order_type(order_type: str) -> str:
    order_type = (order_type or "").strip().upper()
    if order_type not in VALID_ORDER_TYPES:
        raise ValidationError(
            f"Order type must be one of {sorted(VALID_ORDER_TYPES)}, got '{order_type}'."
        )
    return order_type


def validate_quantity(quantity) -> float:
    try:
        quantity = float(quantity)
    except (TypeError, ValueError):
        raise ValidationError(f"Quantity must be a number, got '{quantity}'.")
    if quantity <= 0:
        raise ValidationError("Quantity must be greater than 0.")
    return quantity


def validate_price(price, order_type: str):
    """Price is required for LIMIT / STOP_LIMIT orders and forbidden for MARKET."""
    if order_type == "MARKET":
        return None
    if price is None:
        raise ValidationError(f"Price is required for {order_type} orders.")
    try:
        price = float(price)
    except (TypeError, ValueError):
        raise ValidationError(f"Price must be a number, got '{price}'.")
    if price <= 0:
        raise ValidationError("Price must be greater than 0.")
    return price


def validate_stop_price(stop_price, order_type: str):
    if order_type != "STOP_LIMIT":
        return None
    if stop_price is None:
        raise ValidationError("Stop price is required for STOP_LIMIT orders.")
    try:
        stop_price = float(stop_price)
    except (TypeError, ValueError):
        raise ValidationError(f"Stop price must be a number, got '{stop_price}'.")
    if stop_price <= 0:
        raise ValidationError("Stop price must be greater than 0.")
    return stop_price
