# Flat Flyer — Working Plan

Brief, actionable plan for the current implementation work. The full analysis
design lives in [docs/Option_Alpha_SPX_Coding_and_Report_Plan.md](docs/Option_Alpha_SPX_Coding_and_Report_Plan.md).

## Strategy under analysis

SPX 0DTE iron butterfly ("Flat Flyer" template on Option Alpha):

- Short put and short call at the same strike, $0.01 above the previous close
  (which lands on the 5-point SPX strike grid).
- Long put 10 points below, long call 10 points above (10-wide wings).
- Entry at 10:00am Mon–Fri, 1 contract, held to 4:00pm expiration.
- Entry filters: mid credit at most 9.65, combined bid/ask spread at most $2.00.

## Inputs

- `data/raw/positions.csv` — executed trades (Opened/Closed timestamps, four
  legs, premium, bid/ask at open, P/L, SPX price at open/close).
- `data/raw/filtered_trade.txt` — skipped-day log. Each entry is a date, a
  reason line, and usually a detail line. Observed reasons: `Bid/ask spread`
  (spread filter), `Pricing issue detected` (spread too wide / mid above
  width), `Max price` (mid above 9.65), `Early close day`, `Leg error detected`.

## Phase 1 scope (current)

1. `load.py` — parse both raw files into tidy DataFrames; derive strikes from
   the leg string; coerce numerics; expiry = open date (0DTE).
2. `validate.py` — structural checks (wing width 10, short strikes equal,
   strike on 5-point grid) and payoff cross-checks (P/L vs premium and SPX
   close, max loss consistency). Discrepancies are collected and reported,
   not fatal.
3. `metrics.py` — baseline performance: total/average P/L, win rate, average
   winner/loser, profit factor, cumulative P/L, max drawdown, monthly and
   yearly tables, outcome distribution, skipped-day summary.
4. `plots.py` — equity curve with drawdown, P/L histogram, monthly P/L
   heatmap, credit vs P/L scatter.
5. `report.py` — self-contained HTML report (jinja2, embedded PNGs) with an
   executive summary, stats, figures, validation results, and a Coverage
   section showing which analyses from the master plan are done vs pending.
6. Tests for leg parsing, filtered-log parsing, and payoff math.

One command rebuilds everything: `make report`.

## Later phases (from the master plan)

- Phase 2: market-data variables (previous close, 10:00am level, displacement,
  mean reversion, strike-grid rounding).
- Phase 3: slippage/fee scenarios, regime comparisons, parameter robustness.
- Phase 4: full automated report covering analysis questions A–F.
