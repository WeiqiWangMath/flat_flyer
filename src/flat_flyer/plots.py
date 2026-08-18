"""Core charts for the baseline report. Figures are saved as PNGs under
``reports/figures/`` and embedded into the HTML report."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from . import config, metrics

plt.rcParams.update(
    {
        "figure.dpi": 130,
        "figure.figsize": (9, 4.5),
        "axes.grid": True,
        "grid.alpha": 0.3,
        "axes.spines.top": False,
        "axes.spines.right": False,
    }
)

GAIN = "#2a9d8f"
LOSS = "#e76f51"
LINE = "#264653"


def _save(fig: plt.Figure, name: str) -> Path:
    config.FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    path = config.FIGURES_DIR / f"{name}.png"
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    return path


def equity_curve(df: pd.DataFrame) -> Path:
    curve = metrics.equity_curve(df)
    fig, (ax1, ax2) = plt.subplots(
        2, 1, sharex=True, figsize=(9, 6), height_ratios=[3, 1]
    )
    ax1.plot(curve["closed"], curve["cum_pl"], color=LINE, lw=1.2)
    ax1.set_ylabel("Cumulative P/L ($)")
    ax1.set_title("Equity curve")
    ax2.fill_between(curve["closed"], curve["drawdown"], 0, color=LOSS, alpha=0.6)
    ax2.set_ylabel("Drawdown ($)")
    fig.autofmt_xdate()
    return _save(fig, "equity_curve")


def pl_histogram(df: pd.DataFrame) -> Path:
    fig, ax = plt.subplots()
    bins = np.arange(-1000, 1050, 50)
    pl = df["P/L"]
    ax.hist(pl[pl > 0], bins=bins, color=GAIN, label="Winners")
    ax.hist(pl[pl <= 0], bins=bins, color=LOSS, label="Losers")
    ax.set_xlabel("Trade P/L ($)")
    ax.set_ylabel("Trades")
    ax.set_title("Distribution of trade outcomes")
    ax.legend()
    return _save(fig, "pl_histogram")


def monthly_heatmap(df: pd.DataFrame) -> Path:
    table = metrics.monthly_table(df).drop(columns="Total")
    fig, ax = plt.subplots(figsize=(9, 0.6 * len(table) + 1.2))
    vmax = np.nanmax(np.abs(table.values)) or 1.0
    im = ax.imshow(table.values, cmap="RdYlGn", vmin=-vmax, vmax=vmax, aspect="auto")
    ax.set_xticks(range(len(table.columns)), table.columns)
    ax.set_yticks(range(len(table.index)), table.index)
    for (i, j), val in np.ndenumerate(table.values):
        ax.text(j, i, f"{val:,.0f}", ha="center", va="center", fontsize=7)
    ax.set_title("Monthly P/L ($)")
    ax.grid(False)
    fig.colorbar(im, ax=ax, shrink=0.8)
    return _save(fig, "monthly_heatmap")


def credit_vs_pl(df: pd.DataFrame) -> Path:
    fig, ax = plt.subplots()
    colors = np.where(df["P/L"] > 0, GAIN, LOSS)
    ax.scatter(df["Premium"], df["P/L"], s=12, c=colors, alpha=0.6)
    ax.set_xlabel("Opening credit ($ per contract)")
    ax.set_ylabel("Trade P/L ($)")
    ax.set_title("Opening credit vs final P/L")
    return _save(fig, "credit_vs_pl")


def displacement_hist(disp: pd.DataFrame) -> Path:
    fig, ax = plt.subplots()
    ax.hist(disp["d"], bins=40, color=LINE, alpha=0.85)
    ax.axvline(0, color="black", lw=1)
    ax.axvline(config.WING_WIDTH, color=LOSS, ls="--", lw=1, label=f"+/−{config.WING_WIDTH:g} width")
    ax.axvline(-config.WING_WIDTH, color=LOSS, ls="--", lw=1)
    ax.set_xlabel("Entry displacement d = SPX@10:00 − center strike (points)")
    ax.set_ylabel("Trades")
    ax.set_title("Distribution of entry displacement")
    ax.legend()
    return _save(fig, "displacement_hist")


def mean_reversion_scatter(disp: pd.DataFrame, summary: dict) -> Path:
    """Central question-B chart: post-entry move m vs entry displacement d."""
    fig, ax = plt.subplots(figsize=(9, 5))
    colors = np.where(disp["pl"] > 0, GAIN, LOSS)
    ax.scatter(disp["d"], disp["m"], s=14, c=colors, alpha=0.55, label="trades")
    # Regression line across the observed d range.
    x = disp["d"].to_numpy()
    xs = np.linspace(np.nanmin(x), np.nanmax(x), 100)
    ax.plot(xs, summary["reg_intercept"] + summary["reg_slope"] * xs, color=LINE, lw=2,
            label=(f"m = {summary['reg_intercept']:.2f} + {summary['reg_slope']:.2f}·d"
                   f"  (r={summary['reg_r']:.2f})"))
    ax.axhline(0, color="black", lw=0.8)
    ax.axvline(0, color="black", lw=0.8)
    # Pure mean-reversion reference: m = −d (full snap-back to K).
    ax.plot(xs, -xs, color="#9a6b00", ls=":", lw=1.2, label="full reversion m = −d")
    ax.set_xlabel("Entry displacement d (points)")
    ax.set_ylabel("Post-entry move m = settle − entry (points)")
    ax.set_title("Mean reversion: does the afternoon undo the morning move?")
    ax.legend(loc="best", fontsize=8)
    return _save(fig, "mean_reversion_scatter")


def bucket_performance(disp: pd.DataFrame, buckets: pd.DataFrame) -> Path:
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4.5))
    labels = list(buckets.index)
    x = np.arange(len(labels))

    toward = buckets["Toward K"].to_numpy()
    ax1.bar(x, toward, color=LINE, alpha=0.85)
    ax1.axhline(0.5, color=LOSS, ls="--", lw=1, label="50% random-walk")
    ax1.set_xticks(x, labels, rotation=25, ha="right")
    ax1.set_ylim(0, 1)
    ax1.set_ylabel("Share finishing closer to K")
    ax1.set_title("Toward-center frequency by |d| bucket")
    ax1.legend(fontsize=8)

    ax2.bar(x - 0.2, buckets["Win rate"], width=0.4, color=GAIN, label="Win rate")
    ax2b = ax2.twinx()
    ax2b.bar(x + 0.2, buckets["Avg P/L"], width=0.4, color=LINE, alpha=0.7, label="Avg P/L")
    ax2.set_xticks(x, labels, rotation=25, ha="right")
    ax2.set_ylabel("Win rate")
    ax2b.set_ylabel("Avg P/L ($)")
    ax2.set_title("Outcome by |d| bucket")
    h1, l1 = ax2.get_legend_handles_labels()
    h2, l2 = ax2b.get_legend_handles_labels()
    ax2.legend(h1 + h2, l1 + l2, fontsize=8, loc="best")
    fig.tight_layout()
    return _save(fig, "bucket_performance")


def credit_vs_displacement(disp: pd.DataFrame) -> Path:
    fig, ax = plt.subplots()
    ax.scatter(disp["abs_d"], disp["credit_pts"], s=12, c=LINE, alpha=0.5)
    ax.axhline(config.MAX_MID_CREDIT, color=LOSS, ls="--", lw=1,
               label=f"max mid filter {config.MAX_MID_CREDIT}")
    ax.axvline(config.WING_WIDTH, color="#9a6b00", ls=":", lw=1, label="wing width")
    ax.set_xlabel("|d| at entry (points)")
    ax.set_ylabel("Fill credit (points)")
    ax.set_title("Credit rises with morning displacement")
    ax.legend(fontsize=8)
    return _save(fig, "credit_vs_displacement")


def all_figures(df: pd.DataFrame) -> dict[str, Path]:
    return {
        "equity_curve": equity_curve(df),
        "pl_histogram": pl_histogram(df),
        "monthly_heatmap": monthly_heatmap(df),
        "credit_vs_pl": credit_vs_pl(df),
    }


def question_b_figures(disp: pd.DataFrame, summary: dict,
                       buckets: pd.DataFrame) -> dict[str, Path]:
    return {
        "displacement_hist": displacement_hist(disp),
        "mean_reversion_scatter": mean_reversion_scatter(disp, summary),
        "bucket_performance": bucket_performance(disp, buckets),
        "credit_vs_displacement": credit_vs_displacement(disp),
    }


def grid_error_hist(grid: pd.DataFrame) -> Path:
    """Frequency distribution of K − previous close (bounded by ± half grid)."""
    fig, ax = plt.subplots()
    half = config.STRIKE_GRID / 2.0
    bins = np.arange(-half, half + 0.25, 0.25)
    ax.hist(grid["grid_error"].dropna(), bins=bins, color=LINE, alpha=0.85,
            edgecolor="white")
    ax.axvline(0, color="black", lw=1)
    ax.axvline(half, color=LOSS, ls="--", lw=1, label=f"±{half:g} (half grid)")
    ax.axvline(-half, color=LOSS, ls="--", lw=1)
    ax.set_xlabel("Grid error = center strike − previous close (points)")
    ax.set_ylabel("Trades")
    ax.set_title("Strike-grid rounding error")
    ax.legend(fontsize=8)
    return _save(fig, "grid_error_hist")
