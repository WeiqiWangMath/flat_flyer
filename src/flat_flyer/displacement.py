"""Question B — entry displacement and mean reversion.

Uses only executed trades. Per-trade variables:

- ``d`` = SPX at 10:00 (Price at Open) − center strike K
- ``m`` = settlement − SPX at 10:00
- final miss = |settlement − K|

Skipped filter days are excluded: they have no verified 10:00 SPX level in the
export (daily FRED/Yahoo closes are not a substitute).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from . import config

# Ordered bucket labels used in tables and charts.
BUCKET_ORDER = [
    "inside credit",
    "credit–width",
    "1–1.5× width",
    "1.5–2.5× width",
    ">2.5× width",
]


def _bucket_label(abs_d: float, credit_pts: float, width: float) -> str:
    """Payoff-anchored |d| bucket using this trade's own credit (points)."""
    if abs_d <= credit_pts:
        return "inside credit"
    if abs_d <= width:
        return "credit–width"
    if abs_d <= 1.5 * width:
        return "1–1.5× width"
    if abs_d <= 2.5 * width:
        return "1.5–2.5× width"
    return ">2.5× width"


def build_displacement_table(positions: pd.DataFrame) -> pd.DataFrame:
    """Tidy per-trade displacement frame for analysis and CSV export."""
    df = positions.copy()
    k = df["short_put"].astype(float)
    entry = df["Price at Open"].astype(float)
    settle = df["Price at Close"].astype(float)
    # Fill credit in SPX points (same units as d); Open Price is the model fill.
    credit_pts = df["Open Price"].astype(float)
    width = float(config.WING_WIDTH)

    d = entry - k
    m = settle - entry
    abs_d = d.abs()
    final_miss = (settle - k).abs()

    out = pd.DataFrame({
        "opened": df["opened"],
        "center_strike": k,
        "spx_entry": entry,
        "spx_settle": settle,
        "credit_pts": credit_pts,
        "mid_credit": df["mid_credit"].astype(float),
        "premium": df["Premium"].astype(float),
        "pl": df["P/L"].astype(float),
        "d": d,
        "abs_d": abs_d,
        "m": m,
        "final_miss": final_miss,
        "d_pct": d / entry * 100.0,
        "d_widths": d / width,
        "toward_center": final_miss < abs_d,
        "sign_d": np.where(d > 0, "above", np.where(d < 0, "below", "at")),
        "win": df["P/L"] > 0,
    })
    out["bucket"] = [
        _bucket_label(a, c, width) for a, c in zip(abs_d, credit_pts, strict=True)
    ]
    out["bucket"] = pd.Categorical(out["bucket"], categories=BUCKET_ORDER, ordered=True)
    return out.reset_index(drop=True)


def _ols(x: np.ndarray, y: np.ndarray) -> dict:
    """Simple OLS of y on x with intercept; no scipy dependency."""
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    mask = np.isfinite(x) & np.isfinite(y)
    x, y = x[mask], y[mask]
    n = len(x)
    if n < 3:
        return {"n": n, "slope": float("nan"), "intercept": float("nan"),
                "r": float("nan"), "r2": float("nan"), "se_slope": float("nan")}
    x_mean, y_mean = x.mean(), y.mean()
    ss_xx = ((x - x_mean) ** 2).sum()
    ss_yy = ((y - y_mean) ** 2).sum()
    ss_xy = ((x - x_mean) * (y - y_mean)).sum()
    slope = ss_xy / ss_xx if ss_xx else float("nan")
    intercept = y_mean - slope * x_mean
    resid = y - (intercept + slope * x)
    r = ss_xy / np.sqrt(ss_xx * ss_yy) if ss_xx and ss_yy else float("nan")
    r2 = r * r if np.isfinite(r) else float("nan")
    dof = n - 2
    mse = (resid @ resid) / dof if dof > 0 else float("nan")
    se_slope = float(np.sqrt(mse / ss_xx)) if ss_xx and np.isfinite(mse) else float("nan")
    return {
        "n": n,
        "slope": float(slope),
        "intercept": float(intercept),
        "r": float(r),
        "r2": float(r2),
        "se_slope": se_slope,
    }


def displacement_summary(disp: pd.DataFrame) -> dict:
    """Headline stats and the central m-on-d regression for question B."""
    d = disp["d"]
    abs_d = disp["abs_d"]
    credit = disp["credit_pts"]
    width = config.WING_WIDTH
    reg = _ols(disp["d"].to_numpy(), disp["m"].to_numpy())
    # Approximate t-stat for slope (large-n); |t| > 2 ≈ significant.
    t_slope = (reg["slope"] / reg["se_slope"]
               if reg["se_slope"] and np.isfinite(reg["se_slope"]) else float("nan"))

    return {
        "n": len(disp),
        "mean_d": float(d.mean()),
        "std_d": float(d.std(ddof=1)),
        "median_abs_d": float(abs_d.median()),
        "pct_beyond_credit": float((abs_d > credit).mean()),
        "pct_beyond_width": float((abs_d > width).mean()),
        "pct_within_2_5": float((abs_d <= 2.5).mean()),
        "pct_toward": float(disp["toward_center"].mean()),
        "pct_above": float((disp["sign_d"] == "above").mean()),
        "pct_below": float((disp["sign_d"] == "below").mean()),
        "corr_credit_abs_d": float(disp["credit_pts"].corr(abs_d)),
        "reg_slope": reg["slope"],
        "reg_intercept": reg["intercept"],
        "reg_r": reg["r"],
        "reg_r2": reg["r2"],
        "reg_se_slope": reg["se_slope"],
        "reg_t_slope": float(t_slope),
        "reg_n": reg["n"],
        "mean_reverting": bool(np.isfinite(t_slope) and t_slope < -2),
    }


def bucket_table(disp: pd.DataFrame) -> pd.DataFrame:
    """Win rate, P/L, and toward-center share by payoff-anchored |d| bucket."""
    rows = []
    for label in BUCKET_ORDER:
        g = disp.loc[disp["bucket"] == label]
        if g.empty:
            continue
        rows.append({
            "Bucket": label,
            "Trades": len(g),
            "Share": len(g) / len(disp),
            "Avg |d|": g["abs_d"].mean(),
            "Toward K": g["toward_center"].mean(),
            "Win rate": g["win"].mean(),
            "Avg P/L": g["pl"].mean(),
            "Total P/L": g["pl"].sum(),
            "Avg credit": g["credit_pts"].mean(),
        })
    out = pd.DataFrame(rows).set_index("Bucket")
    return out


def direction_table(disp: pd.DataFrame) -> pd.DataFrame:
    """Summary split by whether SPX was above or below the center at entry."""
    rows = []
    for label in ("above", "below"):
        g = disp.loc[disp["sign_d"] == label]
        if g.empty:
            continue
        reg = _ols(g["d"].to_numpy(), g["m"].to_numpy())
        rows.append({
            "Side": f"SPX {label} K",
            "Trades": len(g),
            "Share": len(g) / len(disp),
            "Avg d": g["d"].mean(),
            "Avg |d|": g["abs_d"].mean(),
            "Toward K": g["toward_center"].mean(),
            "Win rate": g["win"].mean(),
            "Avg P/L": g["pl"].mean(),
            "m-on-d slope": reg["slope"],
        })
    return pd.DataFrame(rows).set_index("Side")


def verdict_sentence(summary: dict) -> str:
    """One-sentence coverage / executive takeaway for question B."""
    slope = summary["reg_slope"]
    t = summary["reg_t_slope"]
    toward = summary["pct_toward"]
    beyond = summary["pct_beyond_width"]
    if summary["mean_reverting"]:
        tone = (
            f"Afternoon moves mean-revert (m-on-d slope {slope:.2f}, t={t:.1f}): "
            f"{toward:.0%} of trades finish closer to the center than they started, "
            f"and {beyond:.0%} of entries begin already beyond the wings."
        )
    elif np.isfinite(slope) and slope < 0:
        tone = (
            f"Afternoon moves lean mean-reverting (slope {slope:.2f}, t={t:.1f}) "
            f"but the signal is weak; {beyond:.0%} of entries start beyond the wings."
        )
    else:
        tone = (
            f"Little evidence of afternoon mean reversion (slope {slope:.2f}, t={t:.1f}); "
            f"the trade is closer to a calm-afternoon / pin bet despite "
            f"{beyond:.0%} of entries starting beyond the wings."
        )
    return tone
