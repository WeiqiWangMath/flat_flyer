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
- Independent SPX daily closes — fetched at report time (FRED → Yahoo → Stooq)
  and cached to `data/processed/spx_daily_closes.csv`.

## Done — Phase 2 verification

- Step 1: trade-calendar completeness + entry-price filter consistency.
- Step 2: strike-selection and settlement P/L replay vs independent closes.
  Both steps: **reproducible** on this export.

## Next — Phase 2 analysis variables (questions B–D)

With verified daily closes in hand:

- Displacement from previous close / center strike; mean-reversion vs stay-near
  center; relative 10-point width over time; strike-grid rounding effects.
- Intraday 9:30 open and 10:00 entry levels still needed for the full
  mean-reversion study (question B); daily closes cover C/D and part of B.

## Later phases

- Phase 3: slippage/fee scenarios, regime comparisons, parameter robustness.
- Phase 4: full automated report covering analysis questions A–F.
