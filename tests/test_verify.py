"""Phase 2 Step 1 — internal consistency verification tests."""

from __future__ import annotations

import pandas as pd
import pytest

from flat_flyer.holidays import NYSE_FULL_DAY_CLOSURES, nyse_sessions
from flat_flyer.verify import (
    check_executed_entry_prices,
    check_skipped_entry_prices,
    check_trade_calendar,
    verify_internal_consistency,
)


def _positions(rows: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(rows)
    df["opened"] = pd.to_datetime(df["opened"])
    df["mid_credit"] = (df["Open Bid Price"] + df["Open Ask Price"]) / 2
    df["open_spread"] = df["Open Ask Price"] - df["Open Bid Price"]
    return df


def _filtered(rows: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df["date"])
    return df


def test_nyse_sessions_exclude_holidays_and_weekends():
    sessions = nyse_sessions("2023-04-03", "2023-04-10")
    # Mon 3, Tue 4, Wed 5, Thu 6, Fri 7=Good Friday, Mon 10
    assert [d.strftime("%Y-%m-%d") for d in sessions] == [
        "2023-04-03", "2023-04-04", "2023-04-05", "2023-04-06", "2023-04-10",
    ]
    assert pd.Timestamp("2025-01-09") in NYSE_FULL_DAY_CLOSURES


def test_calendar_complete_when_trade_or_skip_covers_every_session():
    positions = _positions([
        {"opened": "2023-03-24 10:00", "Open Price": 9.0,
         "Open Bid Price": 8.5, "Open Ask Price": 9.5},
        {"opened": "2023-03-27 10:00", "Open Price": 9.1,
         "Open Bid Price": 8.6, "Open Ask Price": 9.6},
    ])
    # Mar 24 Fri trade; Mar 27 Mon trade; Mar 28 Tue skip. Mar 25-26 weekend.
    filtered = _filtered([
        {"date": "2023-03-28", "reason": "Bid/ask spread",
         "bid": 7.5, "ask": 10.0, "mid": 8.75},
    ])
    check, disc = check_trade_calendar(positions, filtered)
    assert check.passed
    assert disc == []


def test_calendar_reports_gap_and_overlap():
    positions = _positions([
        {"opened": "2023-03-24 10:00", "Open Price": 9.0,
         "Open Bid Price": 8.5, "Open Ask Price": 9.5},
        {"opened": "2023-03-28 10:00", "Open Price": 9.0,
         "Open Bid Price": 8.5, "Open Ask Price": 9.5},
    ])
    filtered = _filtered([
        {"date": "2023-03-28", "reason": "Bid/ask spread",
         "bid": 7.5, "ask": 10.0, "mid": 8.75},
    ])
    # Window Mar 24–28: missing Mon 27; overlap on Tue 28.
    check, disc = check_trade_calendar(positions, filtered)
    assert not check.passed
    kinds = {d.check for d in disc}
    assert "calendar_gap" in kinds
    assert "calendar_overlap" in kinds
    assert any(d.date == "2023-03-27" for d in disc)
    assert any(d.date == "2023-03-28" for d in disc)


def test_executed_open_must_lie_inside_bid_ask():
    positions = _positions([
        {"opened": "2023-03-24 10:00", "Open Price": 9.05,
         "Open Bid Price": 8.5, "Open Ask Price": 9.6},
        {"opened": "2023-03-27 10:00", "Open Price": 10.5,  # outside ask
         "Open Bid Price": 8.8, "Open Ask Price": 10.1},
    ])
    check, disc = check_executed_entry_prices(positions)
    assert not check.passed
    assert check.violations == 1
    assert disc[0].check == "open_outside_bid_ask"
    assert disc[0].date == "2023-03-27"


def test_executed_filters_must_pass():
    positions = _positions([
        {"opened": "2023-03-24 10:00", "Open Price": 9.7,
         "Open Bid Price": 9.5, "Open Ask Price": 9.9},  # mid 9.7 > 9.65
    ])
    check, disc = check_executed_entry_prices(positions)
    assert not check.passed
    assert any(d.check == "executed_mid_above_filter" for d in disc)


def test_skipped_bid_ask_requires_spread_above_filter():
    ok = _filtered([
        {"date": "2023-03-28", "reason": "Bid/ask spread",
         "bid": 7.5, "ask": 10.0, "mid": 8.75},  # spread 2.5
    ])
    check, disc = check_skipped_entry_prices(ok)
    assert check.passed and disc == []

    bad = _filtered([
        {"date": "2023-03-28", "reason": "Bid/ask spread",
         "bid": 8.5, "ask": 10.0, "mid": 9.25},  # spread 1.5
    ])
    check, disc = check_skipped_entry_prices(bad)
    assert not check.passed
    assert disc[0].check == "skip_spread_not_violating"


def test_skipped_max_price_requires_mid_above_filter():
    ok = _filtered([
        {"date": "2023-05-05", "reason": "Max price",
         "bid": None, "ask": None, "mid": 9.77},
    ])
    assert check_skipped_entry_prices(ok)[0].passed

    bad = _filtered([
        {"date": "2023-05-05", "reason": "Max price",
         "bid": None, "ask": None, "mid": 9.50},
    ])
    check, disc = check_skipped_entry_prices(bad)
    assert not check.passed
    assert disc[0].check == "skip_mid_not_violating"


def test_pricing_issue_accepts_wide_spread_or_mid_above_width():
    wide = _filtered([
        {"date": "2023-03-29", "reason": "Pricing issue detected",
         "bid": 6.6, "ask": 12.8, "mid": 9.7},
    ])
    assert check_skipped_entry_prices(wide)[0].passed

    above_width = _filtered([
        {"date": "2025-05-12", "reason": "Pricing issue detected",
         "bid": 9.15, "ask": 12.5, "mid": 10.83},
    ])
    assert check_skipped_entry_prices(above_width)[0].passed

    unexplained = _filtered([
        {"date": "2023-03-29", "reason": "Pricing issue detected",
         "bid": 8.5, "ask": 9.5, "mid": 9.0},
    ])
    check, disc = check_skipped_entry_prices(unexplained)
    assert not check.passed
    assert disc[0].check == "skip_pricing_unexplained"


def test_early_close_and_leg_error_need_no_quotes():
    filtered = _filtered([
        {"date": "2023-07-03", "reason": "Early close day",
         "bid": None, "ask": None, "mid": None},
        {"date": "2025-10-22", "reason": "Leg error detected",
         "bid": None, "ask": None, "mid": None},
    ])
    check, disc = check_skipped_entry_prices(filtered)
    assert check.passed
    assert check.total == 0  # nothing price-checked
    assert disc == []


def test_full_verify_verdict_reproducible_on_toy_window():
    positions = _positions([
        {"opened": "2023-03-24 10:00", "Open Price": 9.05,
         "Open Bid Price": 8.5, "Open Ask Price": 9.6},
        {"opened": "2023-03-27 10:00", "Open Price": 9.45,
         "Open Bid Price": 8.8, "Open Ask Price": 10.1},
    ])
    filtered = _filtered([
        {"date": "2023-03-28", "reason": "Bid/ask spread",
         "bid": 7.5, "ask": 10.0, "mid": 8.75},
        {"date": "2023-03-29", "reason": "Pricing issue detected",
         "bid": 6.6, "ask": 12.8, "mid": 9.7},
        {"date": "2023-03-30", "reason": "Max price",
         "bid": None, "ask": None, "mid": 9.77},
        {"date": "2023-03-31", "reason": "Early close day",
         "bid": None, "ask": None, "mid": None},
    ])
    result = verify_internal_consistency(positions, filtered)
    assert result.passed
    assert result.verdict == "reproducible"
    assert result.n_sessions == 6  # Mar 24, 27, 28, 29, 30, 31
    assert result.discrepancies == []


def test_real_export_step1_is_reproducible():
    """Live check against data/raw/; skipped if raw files are absent."""
    from flat_flyer import config, load

    if not config.POSITIONS_CSV.exists() or not config.FILTERED_LOG.exists():
        pytest.skip("raw export not present")
    positions = load.load_positions(config.POSITIONS_CSV)
    filtered = load.load_filtered_log(config.FILTERED_LOG)
    result = verify_internal_consistency(positions, filtered)
    assert result.verdict == "reproducible"
    assert result.passed
    assert result.n_trades + result.n_skipped == result.n_sessions
    assert result.discrepancies == []
