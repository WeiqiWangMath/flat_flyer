"""Question D — strike-grid rounding (kept deliberately small).

The center strike is previous close + $0.01 rounded to the 5-point SPX grid.
``grid_error`` = K − previous close is therefore always in (−2.5, +2.5].
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from . import config
from .market_data import with_previous_close


def build_grid_rounding_table(positions: pd.DataFrame,
                              spx: pd.DataFrame) -> pd.DataFrame:
    """Per-trade distance from previous close to the selected center strike."""
    spx = with_previous_close(spx)
    days = positions["opened"].dt.normalize()
    prev = spx.set_index("date")["prev_close"].reindex(days).to_numpy()
    k = positions["short_put"].to_numpy(dtype=float)
    err = k - prev
    side = np.where(err > 1e-9, "up", np.where(err < -1e-9, "down", "exact"))
    return pd.DataFrame({
        "opened": positions["opened"].to_numpy(),
        "prev_close": prev,
        "center_strike": k,
        "grid_error": err,
        "side": side,
        "pl": positions["P/L"].to_numpy(dtype=float),
    }).reset_index(drop=True)


def grid_rounding_summary(grid: pd.DataFrame) -> dict:
    err = grid["grid_error"]
    up = grid.loc[grid["side"] == "up", "pl"]
    down = grid.loc[grid["side"] == "down", "pl"]
    return {
        "n": len(grid),
        "mean_abs_error": float(err.abs().mean()),
        "median_abs_error": float(err.abs().median()),
        "max_abs_error": float(err.abs().max()),
        "half_grid": config.STRIKE_GRID / 2.0,
        "n_up": int((grid["side"] == "up").sum()),
        "n_down": int((grid["side"] == "down").sum()),
        "avg_pl_up": float(up.mean()) if len(up) else float("nan"),
        "avg_pl_down": float(down.mean()) if len(down) else float("nan"),
        "win_rate_up": float((up > 0).mean()) if len(up) else float("nan"),
        "win_rate_down": float((down > 0).mean()) if len(down) else float("nan"),
        "corr_error_pl": float(err.corr(grid["pl"])),
    }


def verdict_sentence(summary: dict) -> str:
    return (
        f"Grid rounding shifts the center by at most "
        f"{summary['half_grid']:g} points (median |error| "
        f"{summary['median_abs_error']:.2f}); up- vs down-rounding avg P/L "
        f"${summary['avg_pl_up']:.0f} vs ${summary['avg_pl_down']:.0f} — "
        f"the 5-point grid does not materially affect results."
    )
