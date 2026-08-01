"""Baseline performance metrics (master plan question A)."""

from __future__ import annotations

import pandas as pd

from . import config


def equity_curve(df: pd.DataFrame) -> pd.DataFrame:
    """Cumulative P/L and running drawdown, indexed by trade close time."""
    out = df[["closed", "P/L"]].copy()
    out["cum_pl"] = out["P/L"].cumsum()
    out["peak"] = out["cum_pl"].cummax()
    out["drawdown"] = out["cum_pl"] - out["peak"]
    return out


def baseline_stats(df: pd.DataFrame) -> dict:
    pl = df["P/L"]
    winners = pl[pl > 0]
    losers = pl[pl < 0]
    curve = equity_curve(df)

    gross_profit = winners.sum()
    gross_loss = -losers.sum()

    return {
        "n_trades": len(df),
        "first_trade": df["opened"].min().date(),
        "last_trade": df["opened"].max().date(),
        "total_pl": pl.sum(),
        "avg_pl": pl.mean(),
        "median_pl": pl.median(),
        "win_rate": len(winners) / len(df),
        "n_winners": len(winners),
        "n_losers": len(losers),
        "avg_winner": winners.mean(),
        "avg_loser": losers.mean(),
        "largest_winner": pl.max(),
        "largest_loser": pl.min(),
        "profit_factor": gross_profit / gross_loss if gross_loss else float("inf"),
        "max_drawdown": curve["drawdown"].min(),
        "avg_credit": df["Premium"].mean(),
        "avg_mid_credit": df["mid_credit"].mean(),
        "avg_spread": df["open_spread"].mean(),
        "return_on_capital": pl.sum() / config.CAPITAL_ALLOCATION,
    }


def monthly_table(df: pd.DataFrame) -> pd.DataFrame:
    """P/L by year (rows) and month (columns), in dollars."""
    g = df.groupby([df["opened"].dt.year, df["opened"].dt.month])["P/L"].sum()
    table = g.unstack(fill_value=0.0)
    table.columns = [pd.Timestamp(2000, m, 1).strftime("%b") for m in table.columns]
    table.index.name = "Year"
    table["Total"] = table.sum(axis=1)
    return table


def yearly_table(df: pd.DataFrame) -> pd.DataFrame:
    g = df.groupby(df["opened"].dt.year)
    out = pd.DataFrame(
        {
            "Trades": g.size(),
            "Total P/L": g["P/L"].sum(),
            "Avg P/L": g["P/L"].mean(),
            "Win rate": g["P/L"].apply(lambda s: (s > 0).mean()),
            "Avg credit": g["Premium"].mean(),
        }
    )
    out.index.name = "Year"
    return out


def filtered_summary(filtered: pd.DataFrame) -> pd.DataFrame:
    """Skipped days by reason, with date range."""
    g = filtered.groupby("reason")
    out = pd.DataFrame(
        {
            "Days": g.size(),
            "First": g["date"].min().dt.date,
            "Last": g["date"].max().dt.date,
        }
    ).sort_values("Days", ascending=False)
    out.index.name = "Skip reason"
    return out
