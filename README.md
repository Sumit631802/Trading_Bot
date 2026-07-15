# Simplified Trading Bot — Binance Futures Testnet (USDT-M)

A small, structured Python CLI application that places **MARKET**, **LIMIT**,
and **STOP-LIMIT** orders on the [Binance USDT-M Futures Testnet](https://testnet.binancefuture.com),
with input validation, structured logging, and clean error handling.

Built with plain `requests` + manual HMAC-SHA256 request signing (no
`python-binance` dependency), so the authentication flow is fully
transparent and easy to audit.

---

## Project Structure

```
trading_bot/
  bot/
    __init__.py
    client.py          # Low-level signed REST client (Binance Futures API)
    orders.py           # Order placement / business logic (client + validators)
    validators.py       # Input validation
    logging_config.py   # Rotating file + console logging setup
    exceptions.py        # Custom exception hierarchy
  cli.py                 # CLI entry point (argparse)
  logs/
    sample_logs/         # Example log output from real test runs (see below)
  requirements.txt
  .env.example
  README.md
```

**Layering:** `cli.py` (input/output) → `bot/orders.py` (business logic /
validation) → `bot/client.py` (raw signed HTTP calls) → Binance Futures
Testnet API. Each layer only knows about the one below it, which keeps the
code testable and reusable (e.g. a future web UI could reuse `bot/` as-is).

---

## 1. Setup

### 1.1 Get Testnet API credentials

1. Go to https://testnet.binancefuture.com
2. Log in with a GitHub account (this is how the Binance Futures Testnet works).
3. Once logged in, generate an **API Key** and **Secret Key** from the API
   management panel.
4. Note: testnet keys/balances are separate from real Binance accounts and
   reset periodically — this is expected.

### 1.2 Install dependencies

Requires **Python 3.10+**.

```bash
git clone <this-repo-url>
cd trading_bot
python3 -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 1.3 Configure credentials

Copy the example env file and fill in your testnet keys:

```bash
cp .env.example .env
```

```
BINANCE_API_KEY=your_testnet_api_key_here
BINANCE_API_SECRET=your_testnet_api_secret_here
```

Credentials are loaded from environment variables (via `python-dotenv` if a
`.env` file is present) — they are never passed as CLI arguments, so they
won't leak into shell history or log files.

---

## 2. Usage

### Market order

```bash
python cli.py --symbol BTCUSDT --side BUY --type MARKET --quantity 0.01
```

### Limit order

```bash
python cli.py --symbol BTCUSDT --side SELL --type LIMIT --quantity 0.01 --price 65000
```

### Stop-limit order (bonus order type)

```bash
python cli.py --symbol BTCUSDT --side SELL --type STOP_LIMIT \
  --quantity 0.01 --price 64000 --stop-price 64500
```

### All CLI options

| Flag           | Required            | Description                                  |
|----------------|----------------------|-----------------------------------------------|
| `--symbol`     | Yes                  | Trading pair, e.g. `BTCUSDT`                  |
| `--side`       | Yes                  | `BUY` or `SELL`                                |
| `--type`       | Yes                  | `MARKET`, `LIMIT`, or `STOP_LIMIT`             |
| `--quantity`   | Yes                  | Order quantity (base asset)                    |
| `--price`      | For LIMIT/STOP_LIMIT | Limit price                                    |
| `--stop-price` | For STOP_LIMIT       | Trigger price                                  |
| `--base-url`   | No                   | Override API base URL (default: testnet)       |
| `--verbose`    | No                   | Echo INFO-level logs to the console            |

Run `python cli.py --help` for the full list.

### Example output

```
==================================================
ORDER REQUEST SUMMARY
==================================================
  Symbol      : BTCUSDT
  Side        : BUY
  Type        : MARKET
  Quantity    : 0.01
==================================================

ORDER RESPONSE
--------------------------------------------------
  Status       : SUCCESS
  Order ID     : 207996
  Order Status : FILLED
  Executed Qty : 0.01
  Avg Price    : 0
--------------------------------------------------
(Full request/response details logged to: logs/trading_bot.log)
```

---

## 3. Logging

Every request and response is logged to `logs/trading_bot.log` (rotating,
1 MB × 5 backups). File logs include full request parameters (API secret
never included — only the API key header is used, never logged) and full
response bodies at `DEBUG` level, plus concise `INFO`/`ERROR` summaries.
The console only shows warnings/errors by default; pass `--verbose` to also
see INFO logs live.

Example log line:

```
2026-07-15 04:03:27 | INFO  | trading_bot.orders | ORDER REQUEST symbol=BTCUSDT side=BUY type=MARKET quantity=0.01 price=None stop_price=None
2026-07-15 04:03:27 | DEBUG | trading_bot.client | RESPONSE POST /fapi/v1/order status=200 body={...}
2026-07-15 04:03:27 | INFO  | trading_bot.orders | ORDER RESPONSE orderId=207996 status=FILLED executedQty=0.01 avgPrice=0
```

`logs/sample_logs/sample_trading_bot.log` contains a real run against a
local mock of the Binance Futures API showing one **MARKET**, one
**LIMIT**, and one **STOP_LIMIT** order end-to-end (request → response →
result), used here to demonstrate the logging format without committing
live testnet API keys to the repo. **Before submitting, replace this with
a fresh `logs/trading_bot.log` generated by running the commands in
Section 2 against your own real testnet credentials** — that's what the
grader is expecting to see.

---

## 4. Error Handling

| Failure type            | Where it's caught          | Result                                             |
|--------------------------|-----------------------------|-----------------------------------------------------|
| Invalid CLI input         | `bot/validators.py`         | `ValidationError` → clean CLI message, logged, exit code 1 |
| Binance API error (4xx/5xx)| `bot/client.py`            | `APIError` → error message + payload logged, order marked FAILED |
| Network failure/timeout   | `bot/client.py`             | `NetworkError` → logged, order marked FAILED         |
| Missing credentials       | `cli.py`                    | Clear message before any API call is attempted        |
| Anything unexpected       | `cli.py` top-level catch    | Full traceback logged to file, short message on console |

The CLI never crashes with a raw traceback for expected failure modes — it
always prints a short, actionable message and exits with a non-zero status
code, while the full detail is preserved in the log file.

---

## 5. Assumptions

- Only **USDT-M Futures** are supported (not Coin-M).
- `STOP_LIMIT` orders are submitted as Binance's `STOP` order type (limit
  order with a trigger price) — this is the direct Futures API equivalent.
- Quantity/price precision (`stepSize`/`tickSize` per symbol) is **not**
  auto-rounded; the user is expected to supply values that respect the
  symbol's exchange filters (visible via `GET /fapi/v1/exchangeInfo`).
  This was a deliberate scope cut to keep the app simple — see "Possible
  Improvements" below.
- `timeInForce` for LIMIT/STOP_LIMIT orders defaults to `GTC`
  (Good-Til-Cancelled).
- The bot targets the public Testnet only (`https://testnet.binancefuture.com`);
  `--base-url` exists mainly for local testing against a mock server.
- No order-book/position-management features (cancel, modify, list open
  orders) are exposed via the CLI, though `client.py` includes
  `get_order` / `cancel_order` methods that are ready to be wired up.

## 6. Possible Improvements (not implemented — out of scope for this task)

- Auto-fetch and apply `LOT_SIZE` / `PRICE_FILTER` rounding from
  `exchangeInfo` before submitting an order.
- OCO / TWAP / Grid order types.
- Retry with exponential backoff on transient network errors.
- Unit tests with a mocked `requests.Session`.
