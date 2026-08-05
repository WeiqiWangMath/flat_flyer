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

## Next — question B: displacement and mean reversion

Full design in the master plan, question B. No new data is required: the
export's Price at Open is the SPX level at the 10:00am entry, Price at Close
is the settlement level, and previous closes come from the verified daily
series. Preliminary look: 57% of trades enter with SPX already beyond the
wings, so the working hypothesis is that this is mostly a mean-reversion bet.

Work order for the implementing agent:

1. New module (e.g. `displacement.py`) computing per-trade variables:
   d = Price at Open − center strike; m = Price at Close − Price at Open;
   final miss |Price at Close − K|; normalized d (% of SPX and multiples of
   the 10-point width); payoff-anchored bucket labels
   (|d| ≤ credit, credit–width, 1–1.5x, 1.5–2.5x, >2.5x width).
   Write the tidy table to `data/processed/`.
2. Analyses: displacement distribution; regression of m on d; toward-vs-away
   share by bucket vs the 50% random-walk benchmark; win rate / avg P/L by
   bucket; credit vs |d| (the 9.65 filter as an implicit displacement filter);
   everything split by sign of d.
3. Four figures + statistics table; new report section; flip question B to
   "done" in the report Coverage list with a one-sentence verdict.
4. Unit tests for the variable construction and bucketing.
5. Optional follow-up (separate task): extend `market_data.py` to daily OHLC
   (Yahoo/Stooq) to add the 9:30 open and split overnight gap vs morning drift.

## Later — rest of Phase 2 (questions C, D)

- C: 10-point width as % of SPX over time; performance by SPX-level regime.
- D: strike-grid rounding displacement (previous close vs selected strike),
  up- vs down-rounding asymmetry.

## Later phases

- Phase 3: slippage/fee scenarios, regime comparisons, parameter robustness.
- Phase 4: full automated report covering analysis questions A–F.
