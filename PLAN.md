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

## Next — question C: fixed width vs SPX growth (plan agreed Aug 16)

Full design and status in the master plan, question C. Feasibility numbers
already established: SPX 3,900 → 6,600 (18.5% CAGR, drift +3.5 pts/day);
the 10-point width shrank from 0.255% to 0.153% of SPX; average daily move
35 points.

- Part 1 (implementable now, deliberately minimal — no new section/figures):
  add a "width as % of SPX" column to the existing yearly table in the
  baseline report plus a one-sentence verdict. Evidence already established:
  win rate by year 28.8% → 26.3% → 23.9% → 18.8% while relative width
  shrank 0.228% → 0.145%; note the confounders (few 2026 trades, vol
  regime) — causal test is Part 2.
- Part 2 (BLOCKED — awaiting new Option Alpha exports): variant backtests
  cloned from the template — width 15, width 20, and center shift $3.00
  above previous close. Without the paid OA tier, exports cover only ~1
  year, so variant-vs-baseline comparisons must use the matching one-year
  window and be labeled accordingly. Loaders are already general; each
  variant is a new raw file + comparison section.

## Then — question D

- Strike-grid rounding (previous close vs selected strike), up- vs
  down-rounding asymmetry.

Optional later: intraday 10:00 SPX for filter-skipped days; daily OHLC for
9:30 open vs overnight gap.

## Later phases

- Phase 3: slippage/fee scenarios, regime comparisons, parameter robustness.
- Phase 4: full automated report covering analysis questions A–F.
