"""Paths and strategy/assumption parameters. Change assumptions here only."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]

RAW_DIR = PROJECT_ROOT / "data" / "raw"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
REPORTS_DIR = PROJECT_ROOT / "reports"
FIGURES_DIR = REPORTS_DIR / "figures"

POSITIONS_CSV = RAW_DIR / "positions.csv"
FILTERED_LOG = RAW_DIR / "filtered_trade.txt"

# Strategy definition (Option Alpha "Flat Flyer" template)
WING_WIDTH = 10.0          # points between short and long strikes
STRIKE_GRID = 5.0          # SPX strike grid
MAX_MID_CREDIT = 9.65      # entry filter: maximum mid price
MAX_BID_ASK_SPREAD = 2.0   # entry filter: maximum combined bid/ask spread
CONTRACT_MULTIPLIER = 100  # SPX option multiplier
CAPITAL_ALLOCATION = 100_000.0

# Execution assumptions for later robustness work (Phase 3); the baseline
# report uses the raw Option Alpha numbers with no extra costs.
FEE_PER_CONTRACT_LEG = 0.0
SLIPPAGE_PER_SPREAD = 0.0

# Tolerance (in dollars) when cross-checking reported P/L against the
# theoretical payoff; covers rounding of settlement prices in the export.
PAYOFF_TOLERANCE = 2.0

# Phase 2 Step 2: independent SPX daily closes (FRED → Yahoo → Stooq).
SPX_DAILY_CACHE = PROCESSED_DIR / "spx_daily_closes.csv"
# Points: export "Price at Close" vs independent daily close.
SETTLEMENT_PRICE_TOLERANCE = 0.05
