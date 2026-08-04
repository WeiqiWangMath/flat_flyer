"""Phase 2 backtest verification.

Step 1 — internal consistency of the Option Alpha exports (no external data):
trade-calendar completeness and entry-price / filter plausibility.

Step 2 — replay against independent SPX daily closes:
strike-selection (previous close + $0.01 → 5-point grid) and settlement P/L.

Every discrepancy is recorded with date and magnitude. The overall verdict is
``reproducible``, ``reproducible-with-noted-exceptions``, or
``not reproducible``.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import pandas as pd

from . import config
from .holidays import nyse_sessions
from .validate import CheckResult, butterfly_payoff

# Cent tolerance when comparing open/mid/bid/ask values from the export.
PRICE_TOLERANCE = 0.005


@dataclass
class Discrepancy:
    check: str
    date: str
    detail: str
    magnitude: float | None = None


@dataclass
class VerificationResult:
    """Outcome of a Phase 2 verification step."""

    checks: list[CheckResult]
    discrepancies: list[Discrepancy] = field(default_factory=list)
    n_sessions: int = 0
    n_trades: int = 0
    n_skipped: int = 0
    verdict: str = "not reproducible"
    source: str = ""
    settle_detail: pd.DataFrame | None = None

    @property
    def passed(self) -> bool:
        return all(c.passed for c in self.checks)


def _fmt_date(ts: pd.Timestamp) -> str:
    return pd.Timestamp(ts).strftime("%Y-%m-%d")


def _trade_dates(positions: pd.DataFrame) -> pd.Series:
    return positions["opened"].dt.normalize()


def check_trade_calendar(positions: pd.DataFrame,
                         filtered: pd.DataFrame) -> tuple[CheckResult, list[Discrepancy]]:
    """Every NYSE session is either a trade or a skip; no overlaps or extras."""
    trade_dates = set(_trade_dates(positions))
    skip_dates = set(filtered["date"].dt.normalize())
    covered = trade_dates | skip_dates

    start = min(covered)
    end = max(covered)
    sessions = set(nyse_sessions(start, end))

    gaps = sorted(sessions - covered)
    overlaps = sorted(trade_dates & skip_dates)
    extras = sorted(covered - sessions)
    dup_trades = (
        positions.assign(day=_trade_dates(positions))
        .loc[lambda d: d["day"].duplicated(keep=False), "day"]
        .drop_duplicates()
        .sort_values()
        .tolist()
    )
    dup_skips = (
        filtered.loc[filtered["date"].duplicated(keep=False), "date"]
        .drop_duplicates()
        .sort_values()
        .tolist()
    )

    discrepancies: list[Discrepancy] = []
    for d in gaps:
        discrepancies.append(Discrepancy(
            "calendar_gap", _fmt_date(d),
            "NYSE session missing from both positions and filtered log",
        ))
    for d in overlaps:
        discrepancies.append(Discrepancy(
            "calendar_overlap", _fmt_date(d),
            "Date appears in both positions.csv and filtered_trade.txt",
        ))
    for d in extras:
        discrepancies.append(Discrepancy(
            "calendar_extra", _fmt_date(d),
            "Date is not an NYSE session (weekend/holiday) but appears in the export",
        ))
    for d in dup_trades:
        discrepancies.append(Discrepancy(
            "duplicate_trade", _fmt_date(d),
            "Multiple executed trades on the same session",
        ))
    for d in dup_skips:
        discrepancies.append(Discrepancy(
            "duplicate_skip", _fmt_date(d),
            "Multiple skip entries on the same session",
        ))

    violations = len(gaps) + len(overlaps) + len(extras) + len(dup_trades) + len(dup_skips)
    examples = [_fmt_date(d) for d in (gaps + overlaps + extras)[:5]]
    check = CheckResult(
        name="Trade-calendar completeness",
        description=(
            f"Every NYSE session from {_fmt_date(start)} to {_fmt_date(end)} "
            "appears exactly once as a trade or a skip (no gaps, overlaps, or extras)."
        ),
        violations=violations,
        total=len(sessions),
        examples=examples,
    )
    return check, discrepancies


def check_executed_entry_prices(positions: pd.DataFrame) -> tuple[CheckResult, list[Discrepancy]]:
    """Open price inside bid/ask; mid/spread respect the entry filters."""
    discrepancies: list[Discrepancy] = []
    n = len(positions)

    bid = positions["Open Bid Price"]
    ask = positions["Open Ask Price"]
    open_px = positions["Open Price"]
    mid = positions["mid_credit"]
    spread = positions["open_spread"]
    dates = _trade_dates(positions)

    # Open fill inside [bid, ask].
    outside = (open_px < bid - PRICE_TOLERANCE) | (open_px > ask + PRICE_TOLERANCE)
    for idx in positions.index[outside]:
        discrepancies.append(Discrepancy(
            "open_outside_bid_ask", _fmt_date(dates.loc[idx]),
            (f"Open Price {open_px.loc[idx]:.4g} outside "
             f"[{bid.loc[idx]:.4g}, {ask.loc[idx]:.4g}]"),
            magnitude=float(min(abs(open_px.loc[idx] - bid.loc[idx]),
                                abs(open_px.loc[idx] - ask.loc[idx]))),
        ))

    # Mid equals (bid + ask) / 2.
    expected_mid = (bid + ask) / 2
    mid_mismatch = (mid - expected_mid).abs() > PRICE_TOLERANCE
    for idx in positions.index[mid_mismatch]:
        discrepancies.append(Discrepancy(
            "mid_mismatch", _fmt_date(dates.loc[idx]),
            (f"Recorded mid {mid.loc[idx]:.4g} != (bid+ask)/2 "
             f"{expected_mid.loc[idx]:.4g}"),
            magnitude=float(abs(mid.loc[idx] - expected_mid.loc[idx])),
        ))

    # Executed days must pass both entry filters.
    mid_fail = mid.round(3) > config.MAX_MID_CREDIT
    for idx in positions.index[mid_fail]:
        discrepancies.append(Discrepancy(
            "executed_mid_above_filter", _fmt_date(dates.loc[idx]),
            f"Mid credit {mid.loc[idx]:.4g} exceeds max {config.MAX_MID_CREDIT}",
            magnitude=float(mid.loc[idx] - config.MAX_MID_CREDIT),
        ))

    spread_fail = spread.round(3) > config.MAX_BID_ASK_SPREAD
    for idx in positions.index[spread_fail]:
        discrepancies.append(Discrepancy(
            "executed_spread_above_filter", _fmt_date(dates.loc[idx]),
            f"Open spread {spread.loc[idx]:.4g} exceeds max {config.MAX_BID_ASK_SPREAD}",
            magnitude=float(spread.loc[idx] - config.MAX_BID_ASK_SPREAD),
        ))

    violations = int(outside.sum() + mid_mismatch.sum() + mid_fail.sum() + spread_fail.sum())
    examples = [d.date for d in discrepancies[:5]]
    check = CheckResult(
        name="Executed entry-price plausibility",
        description=(
            "Open price lies inside bid/ask; mid equals (bid+ask)/2; "
            f"mid ≤ {config.MAX_MID_CREDIT} and spread ≤ ${config.MAX_BID_ASK_SPREAD:.2f}."
        ),
        violations=violations,
        total=n,
        examples=examples,
    )
    return check, discrepancies


def check_skipped_entry_prices(filtered: pd.DataFrame) -> tuple[CheckResult, list[Discrepancy]]:
    """Skipped-day mids/spreads are consistent with the stated filter reason."""
    discrepancies: list[Discrepancy] = []
    checked = 0

    for _, row in filtered.iterrows():
        reason = row["reason"]
        date = _fmt_date(row["date"])
        bid, ask, mid = row["bid"], row["ask"], row["mid"]
        spread = (ask - bid) if pd.notna(bid) and pd.notna(ask) else float("nan")

        if reason == "Bid/ask spread":
            checked += 1
            if pd.isna(spread):
                discrepancies.append(Discrepancy(
                    "skip_missing_quotes", date,
                    "Bid/ask spread skip is missing bid and/or ask",
                ))
            elif round(float(spread), 3) <= config.MAX_BID_ASK_SPREAD:
                discrepancies.append(Discrepancy(
                    "skip_spread_not_violating", date,
                    (f"Bid/ask skip has spread {spread:.4g} ≤ "
                     f"${config.MAX_BID_ASK_SPREAD:.2f}"),
                    magnitude=float(config.MAX_BID_ASK_SPREAD - spread),
                ))
            # When both quotes exist, mid should match (bid+ask)/2.
            if pd.notna(bid) and pd.notna(ask) and pd.notna(mid):
                expected = (bid + ask) / 2
                if abs(mid - expected) > PRICE_TOLERANCE:
                    discrepancies.append(Discrepancy(
                        "skip_mid_mismatch", date,
                        f"Skip mid {mid:.4g} != (bid+ask)/2 {expected:.4g}",
                        magnitude=float(abs(mid - expected)),
                    ))

        elif reason == "Max price":
            checked += 1
            if pd.isna(mid):
                discrepancies.append(Discrepancy(
                    "skip_missing_mid", date,
                    "Max price skip is missing mid",
                ))
            elif round(float(mid), 3) <= config.MAX_MID_CREDIT:
                discrepancies.append(Discrepancy(
                    "skip_mid_not_violating", date,
                    f"Max-price skip has mid {mid:.4g} ≤ {config.MAX_MID_CREDIT}",
                    magnitude=float(config.MAX_MID_CREDIT - mid),
                ))

        elif reason == "Pricing issue detected":
            checked += 1
            # Observed forms: spread too wide for accurate pricing, or mid
            # above the wing width. Either condition justifies the skip.
            wide_spread = (
                pd.notna(spread) and round(float(spread), 3) > config.MAX_BID_ASK_SPREAD
            )
            mid_above_width = (
                pd.notna(mid) and round(float(mid), 3) > config.WING_WIDTH
            )
            if not (wide_spread or mid_above_width):
                discrepancies.append(Discrepancy(
                    "skip_pricing_unexplained", date,
                    (f"Pricing issue without spread > {config.MAX_BID_ASK_SPREAD} "
                     f"or mid > {config.WING_WIDTH:g} "
                     f"(bid={bid}, ask={ask}, mid={mid})"),
                ))

        # Early close day / Leg error detected: no price-filter expectation.

    check = CheckResult(
        name="Skipped-day filter consistency",
        description=(
            "Bid/ask skips have spread > "
            f"${config.MAX_BID_ASK_SPREAD:.2f}; max-price skips have mid > "
            f"{config.MAX_MID_CREDIT}; pricing-issue skips show a wide spread "
            f"or mid above the {config.WING_WIDTH:g}-point width."
        ),
        violations=len(discrepancies),
        total=checked,
        examples=[d.date for d in discrepancies[:5]],
    )
    return check, discrepancies


def _classify(checks: list[CheckResult], discrepancies: list[Discrepancy],
              hard: set[str]) -> str:
    if all(c.passed for c in checks):
        return "reproducible"
    if any(d.check in hard for d in discrepancies):
        return "not reproducible"
    return "reproducible-with-noted-exceptions"


_STEP1_HARD = {
    "calendar_gap", "calendar_overlap", "calendar_extra",
    "duplicate_trade", "duplicate_skip",
    "executed_mid_above_filter", "executed_spread_above_filter",
    "skip_spread_not_violating", "skip_mid_not_violating",
    "skip_pricing_unexplained", "open_outside_bid_ask",
}

_STEP2_HARD = {
    "missing_prev_close", "missing_settle_close",
    "strike_mismatch", "settle_price_mismatch", "settle_pl_mismatch",
}


def verify_internal_consistency(positions: pd.DataFrame,
                                filtered: pd.DataFrame) -> VerificationResult:
    """Run Phase 2 Step 1 and return checks, discrepancies, and a verdict."""
    checks: list[CheckResult] = []
    discrepancies: list[Discrepancy] = []

    cal_check, cal_disc = check_trade_calendar(positions, filtered)
    checks.append(cal_check)
    discrepancies.extend(cal_disc)

    exec_check, exec_disc = check_executed_entry_prices(positions)
    checks.append(exec_check)
    discrepancies.extend(exec_disc)

    skip_check, skip_disc = check_skipped_entry_prices(filtered)
    checks.append(skip_check)
    discrepancies.extend(skip_disc)

    covered = set(_trade_dates(positions)) | set(filtered["date"].dt.normalize())
    n_sessions = len(nyse_sessions(min(covered), max(covered))) if covered else 0

    return VerificationResult(
        checks=checks,
        discrepancies=discrepancies,
        n_sessions=n_sessions,
        n_trades=len(positions),
        n_skipped=len(filtered),
        verdict=_classify(checks, discrepancies, _STEP1_HARD),
    )


def center_strike(prev_close: float, grid: float = config.STRIKE_GRID) -> float:
    """Previous close + $0.01, rounded to the SPX strike grid.

    Halfway cases (exactly mid-grid after the +$0.01 nudge) round toward the
    lower strike, which matches the Option Alpha Flat Flyer export.
    """
    if pd.isna(prev_close):
        return float("nan")
    # floor(q + 0.5 - eps) rounds .5 downward for positive SPX levels.
    q = (float(prev_close) + 0.01) / grid
    return math.floor(q + 0.5 - 1e-12) * grid


def check_strike_selection(positions: pd.DataFrame,
                           spx: pd.DataFrame) -> tuple[CheckResult, list[Discrepancy]]:
    """Replay center strike from independent previous closes."""
    from .market_data import with_previous_close

    spx = with_previous_close(spx)
    days = _trade_dates(positions)
    lookup = spx.set_index("date")["prev_close"]
    discrepancies: list[Discrepancy] = []

    for idx, day in days.items():
        prev = lookup.get(day, float("nan"))
        recorded = float(positions.loc[idx, "short_put"])
        if pd.isna(prev):
            discrepancies.append(Discrepancy(
                "missing_prev_close", _fmt_date(day),
                "No previous-session close available for strike replay",
            ))
            continue
        expected = center_strike(prev)
        if expected != recorded:
            discrepancies.append(Discrepancy(
                "strike_mismatch", _fmt_date(day),
                (f"Replay strike {expected:g} != recorded {recorded:g} "
                 f"(prev close {prev:.2f})"),
                magnitude=float(expected - recorded),
            ))

    check = CheckResult(
        name="Strike-selection replay",
        description=(
            "Center strike equals previous close + $0.01 rounded to the "
            f"{config.STRIKE_GRID:g}-point grid (half-down on exact midpoints)."
        ),
        violations=len(discrepancies),
        total=len(positions),
        examples=[d.date for d in discrepancies[:5]],
    )
    return check, discrepancies


def check_settlement_replay(positions: pd.DataFrame,
                            spx: pd.DataFrame) -> tuple[CheckResult, list[Discrepancy], pd.DataFrame]:
    """Compare export settlement price and P/L to independent SPX closes."""
    days = _trade_dates(positions)
    lookup = spx.set_index("date")["close"]
    discrepancies: list[Discrepancy] = []
    rows: list[dict] = []

    price_viol = 0
    pl_viol = 0
    missing = 0

    for idx, day in days.items():
        close = lookup.get(day, float("nan"))
        export_close = float(positions.loc[idx, "Price at Close"])
        premium = float(positions.loc[idx, "Premium"])
        short = float(positions.loc[idx, "short_put"])
        qty = float(positions.loc[idx, "Quantity"])
        reported_pl = float(positions.loc[idx, "P/L"])
        date = _fmt_date(day)

        if pd.isna(close):
            missing += 1
            discrepancies.append(Discrepancy(
                "missing_settle_close", date,
                "No independent SPX close available for settlement replay",
            ))
            continue

        price_diff = export_close - float(close)
        expected_pl = butterfly_payoff(premium, short, float(close)) * qty
        pl_diff = reported_pl - expected_pl

        rows.append({
            "date": date,
            "export_close": export_close,
            "spx_close": float(close),
            "price_diff": price_diff,
            "reported_pl": reported_pl,
            "replay_pl": expected_pl,
            "pl_diff": pl_diff,
        })

        if abs(price_diff) > config.SETTLEMENT_PRICE_TOLERANCE:
            price_viol += 1
            discrepancies.append(Discrepancy(
                "settle_price_mismatch", date,
                (f"Export Price at Close {export_close:.2f} vs SPX close "
                 f"{float(close):.2f}"),
                magnitude=float(price_diff),
            ))

        if abs(pl_diff) > config.PAYOFF_TOLERANCE:
            pl_viol += 1
            discrepancies.append(Discrepancy(
                "settle_pl_mismatch", date,
                (f"Reported P/L {reported_pl:.2f} vs replay {expected_pl:.2f} "
                 f"at SPX close {float(close):.2f}"),
                magnitude=float(pl_diff),
            ))

    violations = missing + price_viol + pl_viol
    check = CheckResult(
        name="Settlement replay",
        description=(
            "Export Price at Close matches the independent SPX close within "
            f"{config.SETTLEMENT_PRICE_TOLERANCE:g} points, and reported P/L "
            f"matches payoff at that close within ${config.PAYOFF_TOLERANCE:.2f}."
        ),
        violations=violations,
        total=len(positions),
        examples=[d.date for d in discrepancies[:5]],
    )
    return check, discrepancies, pd.DataFrame(rows)


def verify_against_market_data(positions: pd.DataFrame,
                               spx: pd.DataFrame,
                               *, source: str = "") -> VerificationResult:
    """Run Phase 2 Step 2 strike and settlement replays."""
    checks: list[CheckResult] = []
    discrepancies: list[Discrepancy] = []

    strike_check, strike_disc = check_strike_selection(positions, spx)
    checks.append(strike_check)
    discrepancies.extend(strike_disc)

    settle_check, settle_disc, settle_detail = check_settlement_replay(positions, spx)
    checks.append(settle_check)
    discrepancies.extend(settle_disc)

    return VerificationResult(
        checks=checks,
        discrepancies=discrepancies,
        n_trades=len(positions),
        verdict=_classify(checks, discrepancies, _STEP2_HARD),
        source=source,
        settle_detail=settle_detail,
    )


def discrepancies_frame(result: VerificationResult) -> pd.DataFrame:
    """Tidy table of discrepancies for CSV / report use."""
    if not result.discrepancies:
        return pd.DataFrame(columns=["check", "date", "detail", "magnitude"])
    return pd.DataFrame([
        {"check": d.check, "date": d.date, "detail": d.detail, "magnitude": d.magnitude}
        for d in result.discrepancies
    ])
