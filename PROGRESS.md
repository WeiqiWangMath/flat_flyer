# Progress Log

Living record of development state. Updated (and committed) at every
milestone so the git history doubles as the dev log. The Coverage section of
the generated report (`make report`) shows the same status automatically.

## Status by phase

Master plan: [docs/Option_Alpha_SPX_Coding_and_Report_Plan.md](docs/Option_Alpha_SPX_Coding_and_Report_Plan.md)

### Phase 1 — Baseline pipeline

- [x] Project scaffold, git repository, raw data under `data/raw/`
- [ ] Loader for `positions.csv` and `filtered_trade.txt`
- [ ] Structure and payoff validation
- [ ] Baseline metrics (question A)
- [ ] Core charts
- [ ] HTML report v1 with Coverage section
- [ ] Unit tests and one-command rebuild (`make report`)

### Phase 2 — Market-data analysis (questions B, C, D)

- [ ] Not started

### Phase 3 — Robustness analysis (questions E, F)

- [ ] Not started

### Phase 4 — Automated full report

- [ ] Not started

## Log

### Aug 1, 2026

- Created project structure (`data/`, `src/flat_flyer/`, `tests/`, `docs/`,
  `reports/`), moved raw exports to `data/raw/`, added README, Makefile,
  requirements, .gitignore. Initialized git.
- Inspected inputs: `positions.csv` has 507 iron butterfly trades
  (Mar 24, 2023 – Mar 2026); `filtered_trade.txt` is the skipped-day log with
  reasons (bid/ask spread filter, pricing issues, max-price filter, early
  close days, one leg error).
