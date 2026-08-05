# Progress Log

Living record of development state. Updated (and committed) at every
milestone so the git history doubles as the dev log. The Coverage section of
the generated report (`make report`) shows the same status automatically.

## Status by phase

Master plan: [docs/Option_Alpha_SPX_Coding_and_Report_Plan.md](docs/Option_Alpha_SPX_Coding_and_Report_Plan.md)

### Phase 1 — Baseline pipeline (COMPLETE)

- [x] Project scaffold, git repository, raw data under `data/raw/`
- [x] Loader for `positions.csv` and `filtered_trade.txt`
- [x] Structure and payoff validation (11 checks, all passing on the export)
- [x] Baseline metrics (question A)
- [x] Core charts (equity/drawdown, P/L histogram, monthly heatmap, credit vs P/L)
- [x] HTML report v1 with Coverage section (`reports/report.html`)
- [x] Unit tests and one-command rebuild (`make report`)

### Phase 2 — Market-data analysis (questions B, C, D)

- [x] Step 1 — internal consistency (exports only). Verdict: **reproducible**.
- [x] Step 2 — SPX daily-close replay (FRED → Yahoo → Stooq). Verdict:
      **reproducible**.
- [x] Question B — displacement and mean reversion (executed trades only;
      skipped days noted as unchecked for 10:00 SPX). Verdict sentence in
      report: afternoon mean reversion is weak (slope −0.10, t=−1.5) despite
      57% of entries starting beyond the wings.
- [ ] Question C — relative width over time (daily closes already available).
- [ ] Question D — strike-grid rounding (previous closes already available).

### Phase 3 — Robustness analysis (questions E, F)

- [ ] Not started. Slippage/fee scenarios, regime comparisons, and nearby
      Option Alpha backtests for parameter variants.

### Phase 4 — Automated full report

- [ ] Not started. Extend report v1 to cover questions A–F end to end.

## Log

### Aug 5, 2026 — Question B implemented

- Added `displacement.py`: per-trade d, m, final miss, payoff-anchored buckets
  (each trade’s own fill credit), m-on-d OLS, toward/away, direction split.
- Four figures + explained report section 4; skipped filter days excluded with
  an explicit note that 10:00 SPX is not verified for them.
- Finding: mean d = +2.8 pts; 57% beyond wings; m-on-d slope −0.10 (t=−1.5) —
  lean mean-reverting but not statistically strong. `make test`: 40 passed.

### Aug 5, 2026 — Question B designed; preliminary displacement finding

- Agreed the design for question B; full spec in the master plan.
- Key realization: no intraday data needed for core B — Price at Open is the
  10:00am SPX level on executed trades.
- Preliminary: 57% of trades enter beyond the wings; working hypothesis was
  mean reversion (later measured as weak — see above).

### Aug 4, 2026 — Phase 2 Step 2 complete

- Added `market_data.py`: SPX daily closes via FRED → Yahoo → Stooq.
- Strike and settlement replay: 508/508 match FRED. Verdict: reproducible.

### Aug 4, 2026 — Phase 2 Step 1 complete

- Trade-calendar completeness + entry-price filter consistency.
- Verdict: reproducible (752 sessions = 508 trades + 244 skips).

### Aug 1, 2026 — Phase 1 complete

- Baseline: 508 trades, total P/L $17,543, win rate 25.8%, profit factor 1.40,
  max drawdown −$1,605. All 11 validation checks pass.

### Aug 1, 2026 — Setup

- Project scaffold, raw exports under `data/raw/`, docs and git initialized.
