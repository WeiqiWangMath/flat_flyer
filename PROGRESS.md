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

- [x] Step 1 — internal consistency (exports only): trade-calendar completeness
      and entry-price / filter plausibility. Verdict: **reproducible**
      (752 NYSE sessions = 508 trades + 244 skips; 0 discrepancies).
- [x] Step 2 — replay against independent SPX daily closes (FRED → Yahoo →
      Stooq). Verdict: **reproducible** (source FRED): 508/508 strike matches,
      508/508 settlement price and P/L matches.
- [ ] Displacement, mean-reversion, relative-width, and strike-grid variables
      (questions B–D); needs previous close, 9:30am open, 10:00am and settlement
      SPX levels (daily closes now available; intraday still pending).

### Phase 3 — Robustness analysis (questions E, F)

- [ ] Not started. Slippage/fee scenarios, regime comparisons, and nearby
      Option Alpha backtests for parameter variants.

### Phase 4 — Automated full report

- [ ] Not started. Extend report v1 to cover questions A–F end to end.

## Log

### Aug 4, 2026 — Phase 2 Step 2 complete

- Added `market_data.py`: SPX daily closes via FRED → Yahoo → Stooq, cached to
  `data/processed/spx_daily_closes.csv`.
- Strike replay: center = previous close + $0.01 rounded to the 5-point grid
  with half-down on exact midpoints (matches OA on all 508 trades, including
  the two .49 → .50 tie cases).
- Settlement replay: export Price at Close equals FRED SP500 close on every
  trade day; reported P/L matches payoff at that close within $2.
- Report section 6 shows Step 2; `make test` now runs 35 tests.

### Aug 4, 2026 — Phase 2 Step 1 complete

- Added `holidays.py` (NYSE full-day closures for Mar 2023–Mar 2026, including
  Jan 9, 2025 national day of mourning) and `verify.py` (calendar completeness
  + executed/skipped entry-price filter consistency).
- On the saved export: every NYSE session is exactly one trade or one skip;
  every open price is inside its bid/ask; executed mids/spreads respect 9.65 /
  $2.00; skipped days match their stated filter reason. Verdict: reproducible.
- Report section 5 shows Step 1; discrepancies CSV written when any appear.

### Aug 1, 2026 — Phase 1 complete

- Baseline results from the export (no execution costs applied yet):
  508 trades (Mar 24, 2023 – Mar 24, 2026), total P/L $17,543 on $100,000
  (+17.5%), win rate 25.8%, average winner $471 vs average loser -$117,
  profit factor 1.40, max drawdown -$1,605.
- All 11 validation checks pass: four legs parse on every trade, wings are
  exactly 10 wide, body on the 5-point grid, both entry filters respected,
  and reported P/L matches the theoretical payoff (credit minus capped
  intrinsic at settlement) within $2 on every row.
- `filtered_trade.txt` parsed: 244 skipped days — 116 pricing issues,
  63 bid/ask spread filter, 56 max-price filter, 8 early close days,
  1 leg error. That is 32% of eligible days, a meaningful selection effect
  to revisit in Phase 3.
- `make report` rebuilds everything (clean data to `data/processed/`,
  figures, self-contained `reports/report.html`).

### Aug 1, 2026 — Setup

- Created project structure (`data/`, `src/flat_flyer/`, `tests/`, `docs/`,
  `reports/`), moved raw exports to `data/raw/`, added README, Makefile,
  requirements, .gitignore. Initialized git.
- Inspected inputs: `positions.csv` has 508 iron butterfly trades
  (Mar 24, 2023 – Mar 2026); `filtered_trade.txt` is the skipped-day log with
  reasons (bid/ask spread filter, pricing issues, max-price filter, early
  close days, one leg error).
