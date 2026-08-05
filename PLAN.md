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

- `data/raw/positions.csv` — executed trades.
- `data/raw/filtered_trade.txt` — skipped-day log.
- Independent SPX daily closes — FRED → Yahoo → Stooq, cached under
  `data/processed/spx_daily_closes.csv`.

## Done

- Phase 1 baseline (question A).
- Phase 2 verification Steps 1–2 (**reproducible**).
- Question B — displacement / mean reversion on executed trades; skipped days
  excluded with a report note (no verified 10:00 SPX). Finding: weak afternoon
  mean reversion (slope −0.10, t=−1.5) even though 57% of entries start beyond
  the wings.

## Next — questions C and D

- C: 10-point width as % of SPX over time; performance by SPX-level regime.
- D: strike-grid rounding (previous close vs selected strike), up- vs
  down-rounding asymmetry.

Optional later: intraday 10:00 SPX for filter-skipped days; daily OHLC for
9:30 open vs overnight gap.

## Later phases

- Phase 3: slippage/fee scenarios, regime comparisons, parameter robustness.
- Phase 4: full automated report covering analysis questions A–F.
