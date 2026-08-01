"""Structural and payoff validation of the loaded trades.

Checks are collected into a list of results and reported in the HTML report;
a failing check never aborts the pipeline.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from . import config


@dataclass
class CheckResult:
    name: str
    description: str
    violations: int
    total: int
    examples: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return self.violations == 0


def butterfly_payoff(premium: float, short_strike: float, settle: float,
                     width: float = config.WING_WIDTH,
                     multiplier: float = config.CONTRACT_MULTIPLIER) -> float:
    """Expiration P/L in dollars for one short iron butterfly.

    ``premium`` is the dollar credit received (already multiplied), and the
    position loses the intrinsic value of the body at settlement, capped at
    the wing width.
    """
    intrinsic = min(abs(settle - short_strike), width)
    return premium - intrinsic * multiplier


def _examples(df: pd.DataFrame, mask: pd.Series, n: int = 5) -> list[str]:
    return [d.strftime("%Y-%m-%d") for d in df.loc[mask, "opened"].head(n)]


def validate_positions(df: pd.DataFrame) -> list[CheckResult]:
    checks: list[CheckResult] = []
    total = len(df)

    def add(name: str, description: str, mask: pd.Series) -> None:
        checks.append(CheckResult(name, description, int(mask.sum()), total, _examples(df, mask)))

    add(
        "Four legs present",
        "Every trade parses into long put, short put, short call, long call strikes.",
        df[["long_put", "short_put", "short_call", "long_call"]].isna().any(axis=1),
    )
    add(
        "Short strikes equal",
        "Short put strike equals short call strike (iron butterfly body).",
        df["short_put"] != df["short_call"],
    )
    add(
        f"Wings exactly {config.WING_WIDTH:g} wide",
        "Long put is width below the body and long call is width above.",
        (df["short_put"] - df["long_put"] != config.WING_WIDTH)
        | (df["long_call"] - df["short_call"] != config.WING_WIDTH),
    )
    add(
        f"Body on {config.STRIKE_GRID:g}-point grid",
        "Center strike falls on the SPX strike grid.",
        df["short_put"] % config.STRIKE_GRID != 0,
    )
    add(
        "0DTE",
        "Trade opens and closes on the same calendar day.",
        df["opened"].dt.date != df["closed"].dt.date,
    )
    add(
        f"Mid credit <= {config.MAX_MID_CREDIT}",
        "Open mid price respects the entry filter.",
        df["mid_credit"].round(3) > config.MAX_MID_CREDIT,
    )
    add(
        f"Open spread <= ${config.MAX_BID_ASK_SPREAD:.2f}",
        "Open bid/ask spread respects the entry filter.",
        df["open_spread"].round(3) > config.MAX_BID_ASK_SPREAD,
    )
    add(
        "Premium = open price x 100",
        "Reported premium equals the open price times the contract multiplier.",
        (df["Premium"] - df["Open Price"] * config.CONTRACT_MULTIPLIER).abs() > 0.51,
    )
    add(
        "Max profit + max loss = width x 100",
        "Reported max profit and max loss are consistent with the wing width.",
        (df["Max Profit"] + df["Max Loss"]
         - config.WING_WIDTH * config.CONTRACT_MULTIPLIER).abs() > 1.0,
    )

    expected = df.apply(
        lambda r: butterfly_payoff(r["Premium"], r["short_put"], r["Price at Close"])
        * r["Quantity"],
        axis=1,
    )
    add(
        "P/L matches payoff",
        "Reported P/L equals credit minus settlement intrinsic (capped at width), "
        f"within ${config.PAYOFF_TOLERANCE:.2f}.",
        (df["P/L"] - expected).abs() > config.PAYOFF_TOLERANCE,
    )
    df["expected_pl"] = expected
    df["pl_deviation"] = df["P/L"] - expected

    non_expired = df["Status"].str.lower() != "expired"
    add(
        "All trades expired",
        "Every position was held to expiration (no early exits in this template).",
        non_expired,
    )

    return checks


def deviation_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Trades whose reported P/L deviates most from the theoretical payoff."""
    cols = ["opened", "short_put", "Premium", "Price at Close", "P/L",
            "expected_pl", "pl_deviation"]
    out = df.loc[df["pl_deviation"].abs() > config.PAYOFF_TOLERANCE, cols]
    return out.reindex(out["pl_deviation"].abs().sort_values(ascending=False).index)
