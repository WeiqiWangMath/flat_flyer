# Flat Flyer — SPX 0DTE Iron Butterfly Analysis

Reproducible analysis of the Option Alpha "Flat Flyer" strategy backtest:
SPX 0DTE iron butterfly, short strikes set $0.01 above the previous close
(rounded to the strike grid), 10-point wings, 10:00am entry, maximum mid
credit 9.65, held to expiration.

## Quick start

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
make report        # rebuild the full analysis and open reports/report.html
make test          # run unit tests
```

## Layout

| Path | Purpose |
|---|---|
| `data/raw/` | Original Option Alpha exports (`positions.csv`, `filtered_trade.txt`) — never modified |
| `data/processed/` | Cleaned intermediate data (generated, gitignored) |
| `src/flat_flyer/` | Analysis package: loading, validation, market data, metrics, plots, report |
| `reports/` | Generated HTML report and figures (gitignored) |
| `tests/` | Unit tests for parsing, payoff math, and verification |
| `docs/` | Master analysis plan |
| `PLAN.md` | Brief working plan for the current phase |
| `PROGRESS.md` | Living development log, updated at every milestone |

## Inputs

- `data/raw/positions.csv` — 508 executed trades (Mar 2023 – Mar 2026) with legs, open/close prices, bid/ask, and P/L.
- `data/raw/filtered_trade.txt` — Option Alpha log of days the strategy skipped, with the reason (bid/ask spread filter, pricing issue, max-price filter, early close, leg error).
- SPX daily closes — pulled automatically from FRED (fallback: Yahoo, Stooq) when you run `make report`.

## Configuration

Strategy parameters, fee and slippage assumptions, and paths live in
`src/flat_flyer/config.py`.
