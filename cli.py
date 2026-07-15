#!/usr/bin/env python3
"""Command-line interface for the simplified Binance Futures Testnet trading bot.

Examples
--------
Market order:
    python cli.py --symbol BTCUSDT --side BUY --type MARKET --quantity 0.01

Limit order:
    python cli.py --symbol BTCUSDT --side SELL --type LIMIT --quantity 0.01 --price 65000

Stop-limit order (bonus order type):
    python cli.py --symbol BTCUSDT --side SELL --type STOP_LIMIT \\
        --quantity 0.01 --price 64000 --stop-price 64500

Credentials are read from the BINANCE_API_KEY / BINANCE_API_SECRET
environment variables (or a local .env file — see README) so they never
need to be typed on the command line or committed to source control.
"""

from __future__ import annotations

import argparse
import os
import sys

from bot.client import DEFAULT_BASE_URL, BinanceFuturesClient
from bot.exceptions import TradingBotError, ValidationError
from bot.logging_config import LOG_FILE, setup_logging
from bot.orders import OrderService

try:  # optional: load a local .env file if python-dotenv is installed
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="trading-bot",
        description="Place MARKET / LIMIT / STOP_LIMIT orders on Binance USDT-M Futures Testnet.",
    )
    parser.add_argument("--symbol", required=True, help="Trading pair, e.g. BTCUSDT")
    parser.add_argument("--side", required=True, choices=["BUY", "SELL", "buy", "sell"])
    parser.add_argument(
        "--type",
        dest="order_type",
        required=True,
        choices=["MARKET", "LIMIT", "STOP_LIMIT", "market", "limit", "stop_limit"],
        help="Order type",
    )
    parser.add_argument("--quantity", required=True, help="Order quantity, e.g. 0.01")
    parser.add_argument(
        "--price", required=False, default=None, help="Required for LIMIT / STOP_LIMIT orders"
    )
    parser.add_argument(
        "--stop-price",
        dest="stop_price",
        required=False,
        default=None,
        help="Required for STOP_LIMIT orders",
    )
    parser.add_argument(
        "--base-url",
        default=DEFAULT_BASE_URL,
        help=f"API base URL (default: {DEFAULT_BASE_URL})",
    )
    parser.add_argument(
        "--verbose", action="store_true", help="Echo INFO-level logs to the console too"
    )
    return parser


def print_summary(symbol, side, order_type, quantity, price, stop_price) -> None:
    print("=" * 50)
    print("ORDER REQUEST SUMMARY")
    print("=" * 50)
    print(f"  Symbol      : {symbol}")
    print(f"  Side        : {side}")
    print(f"  Type        : {order_type}")
    print(f"  Quantity    : {quantity}")
    if price is not None:
        print(f"  Price       : {price}")
    if stop_price is not None:
        print(f"  Stop Price  : {stop_price}")
    print("=" * 50)


def print_result(result) -> None:
    print("\nORDER RESPONSE")
    print("-" * 50)
    if result.success:
        print(f"  Status       : SUCCESS")
        print(f"  Order ID     : {result.order_id}")
        print(f"  Order Status : {result.status}")
        print(f"  Executed Qty : {result.executed_qty}")
        print(f"  Avg Price    : {result.avg_price}")
    else:
        print(f"  Status       : FAILED")
        print(f"  Error        : {result.error_message}")
    print("-" * 50)
    print(f"(Full request/response details logged to: {LOG_FILE})")


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    logger = setup_logging(verbose=args.verbose)

    api_key = os.environ.get("BINANCE_API_KEY")
    api_secret = os.environ.get("BINANCE_API_SECRET")

    side = args.side.upper()
    order_type = args.order_type.upper()

    print_summary(args.symbol, side, order_type, args.quantity, args.price, args.stop_price)

    if not api_key or not api_secret:
        print(
            "\nERROR: BINANCE_API_KEY / BINANCE_API_SECRET environment variables are not set.\n"
            "See README.md for setup instructions.",
            file=sys.stderr,
        )
        logger.error("Missing API credentials in environment.")
        return 1

    try:
        client = BinanceFuturesClient(api_key, api_secret, base_url=args.base_url)
        service = OrderService(client)
        result = service.place_order(
            symbol=args.symbol,
            side=side,
            order_type=order_type,
            quantity=args.quantity,
            price=args.price,
            stop_price=args.stop_price,
        )
    except ValidationError as exc:
        print(f"\nERROR: Invalid input — {exc}", file=sys.stderr)
        logger.error("Validation error: %s", exc)
        return 1
    except TradingBotError as exc:
        print(f"\nERROR: {exc}", file=sys.stderr)
        logger.error("Unhandled trading bot error: %s", exc)
        return 1
    except Exception as exc:  # pragma: no cover - last-resort safety net
        print(f"\nUNEXPECTED ERROR: {exc}", file=sys.stderr)
        logger.exception("Unexpected error")
        return 1

    print_result(result)
    return 0 if result.success else 1


if __name__ == "__main__":
    sys.exit(main())
