"""Custom exception hierarchy for the trading bot.

Keeping these separate makes it easy for the CLI layer to catch specific
failure classes and print a clean, user-friendly message instead of a raw
traceback.
"""


class TradingBotError(Exception):
    """Base class for all trading-bot errors."""


class ValidationError(TradingBotError):
    """Raised when user-supplied input fails validation."""


class APIError(TradingBotError):
    """Raised when Binance returns a non-2xx / error response."""

    def __init__(self, message: str, status_code: int | None = None, payload: dict | None = None):
        super().__init__(message)
        self.status_code = status_code
        self.payload = payload or {}


class NetworkError(TradingBotError):
    """Raised when the request could not reach Binance at all
    (timeouts, DNS failures, connection resets, etc.)."""
