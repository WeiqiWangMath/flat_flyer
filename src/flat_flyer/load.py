"""Load and tidy the raw Option Alpha exports.

Two inputs:

- ``positions.csv``: one row per executed trade with the four legs encoded in
  a single string, e.g.
  ``"long put 3,940 / short put 3,950 / short call 3,950 / long call 3,960"``.
- ``filtered_trade.txt``: a plain-text log of days the strategy skipped.
  Each entry is a date line, a reason line, and (for most reasons) one
  detail line with prices.
"""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

LEG_RE = re.compile(r"(long|short)\s+(put|call)\s+([\d,]+(?:\.\d+)?)")

NUMERIC_COLUMNS = [
    "Quantity", "P/L", "Risk", "ROR", "Premium", "Reward/Risk",
    "Open Price", "Open Bid Price", "Open Ask Price",
    "Close Price", "Close Bid Price", "Close Ask Price",
    "Max Loss", "Max Profit", "Price at Open", "Price at Close",
]


def parse_legs(legs: str) -> dict[str, float]:
    """Parse the leg string into strikes keyed like ``long_put``."""
    strikes: dict[str, float] = {}
    for side, kind, strike in LEG_RE.findall(legs):
        strikes[f"{side}_{kind}"] = float(strike.replace(",", ""))
    return strikes


def load_positions(path: Path) -> pd.DataFrame:
    """Load positions.csv into a tidy DataFrame, one row per trade."""
    df = pd.read_csv(path)

    df["opened"] = pd.to_datetime(df["Opened"], format="%b %d, %Y %I:%M%p")
    df["closed"] = pd.to_datetime(df["Closed"], format="%b %d, %Y %I:%M%p")
    # The export's Exp column is broken ("Invalid date"); DTE is exactly 0,
    # so the expiration date is the open date.
    df["expiration"] = df["opened"].dt.normalize()

    for col in NUMERIC_COLUMNS:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    strikes = df["Legs"].apply(parse_legs).apply(pd.Series)
    df = pd.concat([df, strikes], axis=1)

    df["mid_credit"] = (df["Open Bid Price"] + df["Open Ask Price"]) / 2
    df["open_spread"] = df["Open Ask Price"] - df["Open Bid Price"]

    df = df.sort_values("opened").reset_index(drop=True)
    return df


FILTER_DATE_RE = re.compile(r"^[A-Z][a-z]{2} \d{1,2}, \d{4}$")
BID_RE = re.compile(r"Bid: \$?([\d.]+)")
ASK_RE = re.compile(r"Ask: \$?([\d.]+)")
MID_RE = re.compile(r"Mid price:? \$([\d.]+)")

# Reasons that consist of only the date and reason lines, no detail line.
REASONS_WITHOUT_DETAIL = {"Early close day"}


def load_filtered_log(path: Path) -> pd.DataFrame:
    """Parse filtered_trade.txt into one row per skipped day.

    Columns: date, reason, detail, bid, ask, mid.
    """
    lines = [ln.strip() for ln in path.read_text().splitlines() if ln.strip()]

    records: list[dict] = []
    i = 0
    while i < len(lines):
        if not FILTER_DATE_RE.match(lines[i]):
            raise ValueError(f"Expected a date at line {i + 1}, got: {lines[i]!r}")
        date = pd.to_datetime(lines[i], format="%b %d, %Y")
        reason = lines[i + 1]
        i += 2

        detail = ""
        if reason not in REASONS_WITHOUT_DETAIL and i < len(lines) and not FILTER_DATE_RE.match(lines[i]):
            detail = lines[i]
            i += 1

        def _extract(regex: re.Pattern) -> float | None:
            m = regex.search(detail)
            return float(m.group(1)) if m else None

        bid, ask, mid = _extract(BID_RE), _extract(ASK_RE), _extract(MID_RE)
        if mid is None and bid is not None and ask is not None:
            mid = (bid + ask) / 2

        records.append(
            {"date": date, "reason": reason, "detail": detail,
             "bid": bid, "ask": ask, "mid": mid}
        )

    return pd.DataFrame(records)
