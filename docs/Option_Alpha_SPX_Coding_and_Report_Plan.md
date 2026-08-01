# Option Alpha SPX — High-Level Coding and Report Plan

**Owner:** Weiqi Wang  
**Updated:** August 1, 2026  
**Status:** Planning

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

Study how the strategy depends on SPX's location and movement:

- distance from the previous close to the 10:00 a.m. entry price;
- distance from the center strike at entry;
- movement from 10:00 a.m. to expiration;
- whether SPX moved toward or away from the center strike;
- relationship between these movements, the opening credit, and final P/L.

The main purpose is to determine when the strategy is a mean-reversion trade and when it is mainly a bet that SPX will remain near the center.

### C. Long-term SPX growth and the fixed 10-point width

Examine whether a fixed 10-point butterfly represents the same strategy as the SPX level changes over time:

- track 10 points as a percentage of the SPX level;
- compare performance across years and SPX-level regimes;
- compare the fixed width with percentage- or volatility-scaled alternatives when suitable backtests or data are available.

### D. Strike-grid rounding

Measure the effect of selecting a center strike on the available five-point strike grid:

- calculate the distance between the previous close and the selected center strike;
- test whether upward and downward rounding have different results;
- check whether the grid shift materially changes the entry displacement or P/L.

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

- Add previous close, 9:30 a.m. open, 10:00 a.m. level, and expiration level where available.
- Create the displacement, mean-reversion, scaling, and strike-grid variables.
- Analyze their relationships with credit and P/L.

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

