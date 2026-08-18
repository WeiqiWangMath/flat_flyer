# Option Alpha SPX — High-Level Coding and Report Plan

**Owner:** Weiqi Wang  
**Updated:** August 16, 2026  
**Status:** In progress — Phase 1, Phase 2 verification, and question B complete; question C planned (part 1 ready to implement, part 2 awaiting Option Alpha variant backtests)

## 1. Goal

Build a reproducible Python analysis that takes the Option Alpha trade data, combines it with additional SPX market data when available, and automatically generates a clear report on the strategy's behavior, performance, and robustness.

The first version should focus on completing the analysis. The detailed code structure, function design, and report styling can be decided later.

## 2. Main analysis questions

### A. Baseline performance

Describe what happened in the original backtest:

- total profit and average profit per trade;
- win rate, average winner, and average loser;
- profit factor;
- cumulative P/L and drawdown;
- performance by month and year;
- distribution of trade outcomes.

### B. Previous close, entry price, and mean reversion

Study how the strategy depends on SPX's location and movement. The main purpose is to determine when the strategy is a mean-reversion trade and when it is mainly a bet that SPX will remain near the center.

**Data note.** No intraday market data is required for the core of B: the export's Price at Open column is the SPX level at the 10:00 a.m. entry, Price at Close is the settlement level, and the previous close is available from the verified independent daily series (and equals the center strike − $0.01). Only the optional 9:30 a.m. open (to separate the overnight gap from the first 30 minutes of trading) needs a small extension of the market-data fetch to daily OHLC (Yahoo or Stooq; FRED has no open).

**Variables per trade:**

- entry displacement d = (SPX at 10:00 a.m.) − (center strike K): how far SPX has already traveled from yesterday's close by entry time;
- post-entry move m = (settlement) − (SPX at 10:00 a.m.);
- final miss |settlement − K|, which alone determines P/L (win iff the miss is below the credit);
- normalized variants of d (percent of SPX level and multiples of the 10-point width), so results are comparable as SPX grows from ~3,900 to ~6,900 (feeds question C).

**Analyses:**

1. Distribution of the entry displacement d, with payoff-anchored buckets: inside the credit (win if nothing moves), credit-to-width (needs a partial pull-back), and 1–1.5x, 1.5–2.5x, >2.5x the width (needs a real reversal).
2. Regression of the post-entry move m on d: a significantly negative slope means morning moves tend to reverse (mean reversion); a slope near zero means the trade is purely a bet on a calm afternoon. This is the central chart of B.
3. Toward-vs-away frequency: share of trades where SPX finishes closer to K than it started, by displacement bucket, against the 50% random-walk benchmark.
4. Win rate and average P/L by displacement bucket: do far-from-center entries pay?
5. Credit vs displacement: credit rises toward the width as |d| grows, so the 9.65 max-mid filter acts as an implicit displacement filter — quantify which days it removes (links to the skipped-day log and Phase 3 costs).
6. Direction asymmetry: repeat the analyses split by the sign of d (SPX above vs below center).

**Preliminary finding (Aug 5, 2026, from the existing columns):** mean d = +2.8, std = 18.9 points; 57% of trades enter with SPX already beyond the wings (|d| > 10) and 62% beyond the credit; only ~11% start within 2.5 points of the center. On the typical day this is therefore a mean-reversion bet, not a pin-the-close bet; the full analysis quantifies whether the reversion is strong enough to justify those entries.

### C. Long-term SPX growth and the fixed 10-point width

Examine whether a fixed 10-point butterfly represents the same strategy as the SPX level changes over time:

- track 10 points as a percentage of the SPX level;
- compare performance across years and SPX-level regimes;
- compare the fixed width with percentage- or volatility-scaled alternatives when suitable backtests or data are available.

**Status: partial (Aug 16, 2026).** Feasibility settled; findings so far from the existing data:

- Over the backtest window SPX grew from ~3,900 to ~6,600 (18.5% CAGR, average drift +3.5 points/day), so the 10-point width shrank from 0.255% to 0.153% of the SPX level — the butterfly is effectively ~40% narrower in 2026 than in 2023. The average close-to-close move (35 points) dwarfs both the width and the drift.

**Part 1 — Analysis** The evidence already shows in one table: win rate fell monotonically by year (28.8% → 26.3% → 23.9% → 18.8%, 2023–2026) as the width shrank relative to SPX (0.228% → 0.145% of the average level at entry). Implementation is limited to adding one column ("width as % of SPX") to the existing yearly table in the baseline report plus a one-sentence verdict with the caveat that the trend is suggestive, not causal — 2026 has few trades and volatility regime is a confounder. The causal test is Part 2.

**Part 2 — variant comparison (needs new Option Alpha backtests).** The export contains only the traded strikes with combo-level quotes, so wider wings or a shifted center cannot be priced from our data. True variants come from cloning the Flat Flyer template on Option Alpha:

- width 15 and width 20 (long legs $15/$20 from the shorts), everything else unchanged;
- center shift: short strikes $3.00 above the previous close, matching the measured daily drift (note: because of the 5-point grid, +$3.00 selects the same strike as +$0.01 on ~39% of days, so the expected effect is modest).

**Data constraint:** without the paid Option Alpha subscription tier, new backtests cover only about one year. Variant comparisons must therefore be run against the baseline restricted to the same one-year window, clearly labeled as such; the full three-year variant comparison stays open until subscription data (or longer exports) become available. Modeled credits (estimating variant credits from the question B credit-vs-displacement relation) remain a fallback, but must be labeled as estimates, never as backtest results.

### D. Strike-grid rounding

Measure the effect of selecting a center strike on the available five-point strike grid:

- calculate the distance between the previous close and the selected center strike;
- test whether upward and downward rounding have different results;
- check whether the grid shift materially changes the entry displacement or P/L.

**Status: done (Aug 18, 2026).** Grid error = K − previous close is bounded by ±2.5 points (median |error| 1.20). Up- vs down-rounding average P/L are essentially identical (~$35 / ~$35). Conclusion: the 5-point grid does not materially affect results — one histogram and a short report section.

### E. Bid-ask spread, slippage, and costs

Test whether the reported result remains attractive under more realistic execution assumptions:

- summarize the combined bid-ask spread;
- recalculate results under several slippage assumptions;
- add fees separately;
- identify the total cost per trade that would eliminate the historical profit.

### F. Parameter robustness

Compare the baseline with a small number of nearby alternatives:

- different maximum midpoint-credit filters around 9.65;
- different butterfly widths;
- possibly different entry times;
- fixed-width versus scaled-width versions.

Use new Option Alpha backtests for true strategy variants. Do not present a filtered subset of the original trades as a complete counterfactual backtest unless that interpretation is valid.

## 3. Coding phases

### Phase 1 — Baseline pipeline

- Load and clean the Option Alpha trade export.
- Validate the four-leg structure and key payoff calculations.
- Calculate the baseline performance metrics.
- Produce the core charts and tables.

### Phase 2 — Market-data analysis

- Add previous close, 9:30 a.m. open, 10:00 a.m. level, and expiration level where available. (Status: previous close via independent daily series, 10:00 a.m. and settlement levels from the export — all verified. The 9:30 a.m. open remains optional.)
- Create the displacement, mean-reversion, scaling, and strike-grid variables.
- Analyze their relationships with credit and P/L.

**Question B implementation (next up):** build the per-trade variables and the six analyses listed under question B above into the pipeline — a displacement module writing tidy variables to `data/processed/`, four figures (displacement histogram with payoff-anchored buckets, move-vs-displacement regression scatter, win rate and average P/L by bucket, credit vs displacement), a statistics table (regression slope, toward-vs-away shares, bucket table), and a new report section that flips question B to done in the Coverage table with a one-sentence verdict: mean-reversion trade, calm-afternoon bet, or a mixture depending on displacement.

**Backtest verification — can the saved trades be reproduced exactly? (COMPLETE — both steps verdict: reproducible)**

Two verification steps are in scope.

Step 1 — internal consistency (uses only the existing exports):

- Trade-calendar completeness: every Mon–Fri trading day (excluding market holidays) must appear either as an executed trade in `positions.csv` or as a skipped day in `filtered_trade.txt`, with no gaps or overlaps.
- Entry-price plausibility: check that each open price lies inside its recorded bid/ask, and that recorded mids and spreads are consistent with the 9.65 and $2.00 filters on both executed and skipped days.

Step 2 — replay against independent SPX daily closes:

- Strike-selection replay: recompute "previous close + $0.01 rounded to the 5-point grid" for every trade day and confirm it matches the recorded center strike.
- Settlement replay: compare the export's Price at Close with the actual SPX closing level, recompute each trade's expiration P/L from that level, and confirm it matches the reported P/L. Note that SPX 0DTE options settle on the 4:00 p.m. close; small persistent differences may reflect the settlement-price definition rather than a backtest error.

For both steps, record every discrepancy with its date and magnitude, and classify the backtest as reproducible, reproducible-with-noted-exceptions, or not reproducible.

Out of scope: quote-level verification of the 10:00 a.m. bid/ask on the four legs, since it requires paid intraday SPX option quote data.

### Phase 3 — Robustness analysis

- Apply slippage and fee scenarios.
- Compare time periods and market regimes.
- Incorporate nearby strategy backtests when available.
- Summarize which findings are stable and which are sensitive to assumptions.

### Phase 4 — Automated report

- Connect every reported number, table, and chart directly to the analysis code.
- Generate the complete report automatically in HTML, with PDF as an optional output.
- Record missing optional data and skipped analyses without stopping the rest of the build.

## 4. Report outline

The generated report should contain:

1. **Executive summary** — the main result and the most important limitation.
2. **Strategy and data** — a concise description of the strategy, datasets, and assumptions.
3. **Baseline performance** — major statistics, equity curve, drawdown, and outcome distribution.
4. **What drives the result** — entry displacement, mean reversion, strike-grid effect, and changing relative width.
5. **Execution and robustness** — bid-ask spread, slippage, fees, and nearby parameter variants.
6. **Conclusion and limitations** — what the evidence supports, what remains uncertain, and what additional data would improve the analysis.

## 5. Minimum completion criteria

The project is complete when:

- one command rebuilds the analysis and report from the input data;
- the raw source data remains unchanged;
- key calculations are checked against the strategy payoff;
- assumptions such as fees and slippage can be changed easily;
- charts and tables are generated by code rather than copied manually;
- missing optional data does not prevent the baseline report from running;
- the report clearly separates observed results from hypothetical strategy variants.

## 6. Details intentionally deferred

The following will be designed when implementation begins:

- exact folder and module structure;
- function and class names;
- detailed input schemas and column mappings;
- package selection;
- chart styling and report template;
- unit-test organization;
- exact parameter grids and statistical methods.

