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


def all_figures(df: pd.DataFrame) -> dict[str, Path]:
    return {
        "equity_curve": equity_curve(df),
        "pl_histogram": pl_histogram(df),
        "monthly_heatmap": monthly_heatmap(df),
        "credit_vs_pl": credit_vs_pl(df),
    }
