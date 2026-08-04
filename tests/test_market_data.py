"""Phase 2 Step 2 — market-data replay and SPX fetch tests."""

from __future__ import annotations

from unittest.mock import patch

import pandas as pd
import pytest

from flat_flyer.market_data import (
    MarketDataError,
    fetch_fred,
    load_spx_daily,
    with_previous_close,
)
from flat_flyer.verify import (
    center_strike,
    check_settlement_replay,
    check_strike_selection,
    verify_against_market_data,
)


def test_center_strike_rounds_prev_plus_penny_to_grid():
    # Ordinary nearest-grid cases.
    assert center_strike(3948.72) == 3950.0
    assert center_strike(3970.99) == 3970.0
    # Exact grid previous close stays on that strike after +$0.01.
    assert center_strike(4330.0) == 4330.0
    # Exact midpoint after +$0.01 (4457.49 + 0.01 = 4457.50) rounds down.
    assert center_strike(4457.49) == 4455.0
    assert center_strike(6737.49) == 6735.0


def _toy_positions() -> pd.DataFrame:
    return pd.DataFrame({
        "opened": pd.to_datetime(["2023-03-24 10:00", "2023-03-27 10:00"]),
        "short_put": [3950.0, 3970.0],
        "Price at Close": [3970.99, 3977.53],
        "Premium": [905.0, 945.0],
        "Quantity": [1, 1],
        "P/L": [-95.0, 192.0],
    })


def _toy_spx() -> pd.DataFrame:
    # Include prior session so Mar 24 has a previous close.
    return pd.DataFrame({
        "date": pd.to_datetime(["2023-03-23", "2023-03-24", "2023-03-27"]),
        "close": [3948.72, 3970.99, 3977.53],
    })


def test_strike_selection_matches_recorded_center():
    check, disc = check_strike_selection(_toy_positions(), _toy_spx())
    assert check.passed
    assert disc == []


def test_strike_selection_flags_mismatch():
    positions = _toy_positions()
    positions.loc[0, "short_put"] = 3960.0
    check, disc = check_strike_selection(positions, _toy_spx())
    assert not check.passed
    assert disc[0].check == "strike_mismatch"
    assert disc[0].magnitude == pytest.approx(-10.0)


def test_settlement_replay_exact_match():
    check, disc, detail = check_settlement_replay(_toy_positions(), _toy_spx())
    assert check.passed
    assert disc == []
    assert len(detail) == 2
    assert (detail["price_diff"].abs() < 1e-9).all()
    assert (detail["pl_diff"].abs() < 1e-6).all()


def test_settlement_replay_flags_price_and_pl():
    positions = _toy_positions()
    positions.loc[0, "Price at Close"] = 3980.0  # far from 3970.99
    # Keep reported P/L as original; replay at true SPX close still matches
    # payoff at 3970.99, but price check fails. Force SPX close off as well
    # for a clean pl mismatch by altering the market series instead.
    spx = _toy_spx()
    check, disc, _ = check_settlement_replay(positions, spx)
    assert not check.passed
    assert any(d.check == "settle_price_mismatch" for d in disc)

    positions = _toy_positions()
    positions.loc[0, "P/L"] = 0.0  # wrong vs payoff at matching close
    check, disc, _ = check_settlement_replay(positions, spx)
    assert any(d.check == "settle_pl_mismatch" for d in disc)


def test_verify_against_market_data_reproducible():
    result = verify_against_market_data(_toy_positions(), _toy_spx(), source="test")
    assert result.verdict == "reproducible"
    assert result.passed
    assert result.source == "test"
    assert result.settle_detail is not None


def test_with_previous_close_shifts_by_session():
    out = with_previous_close(_toy_spx())
    assert pd.isna(out.loc[0, "prev_close"])
    assert out.loc[1, "prev_close"] == pytest.approx(3948.72)
    assert out.loc[2, "prev_close"] == pytest.approx(3970.99)


def test_load_spx_daily_falls_back_across_sources(tmp_path):
    cache = tmp_path / "spx.csv"
    good = pd.DataFrame({
        "date": pd.to_datetime(["2023-03-20", "2023-03-21", "2023-03-22",
                                "2023-03-23", "2023-03-24"]),
        "close": [1.0, 2.0, 3.0, 4.0, 5.0],
    })

    def boom(*_a, **_k):
        raise MarketDataError("nope")

    def yahoo_ok(start, end):
        return good.copy()

    with patch("flat_flyer.market_data.fetch_fred", side_effect=boom), \
         patch("flat_flyer.market_data.fetch_yahoo", side_effect=yahoo_ok), \
         patch("flat_flyer.market_data.fetch_stooq", side_effect=boom):
        df, source = load_spx_daily("2023-03-24", "2023-03-24",
                                    use_cache=False, cache_path=cache)
    assert source == "Yahoo"
    assert len(df) >= 1
    assert cache.exists()

    # Second call uses cache without hitting the network.
    with patch("flat_flyer.market_data.fetch_fred", side_effect=boom), \
         patch("flat_flyer.market_data.fetch_yahoo", side_effect=boom), \
         patch("flat_flyer.market_data.fetch_stooq", side_effect=boom):
        df2, source2 = load_spx_daily("2023-03-24", "2023-03-24",
                                      use_cache=True, cache_path=cache)
    assert source2 == "cache"
    assert len(df2) == len(df)


def test_fetch_fred_parses_csv():
    csv = b"observation_date,SP500\n2023-03-23,3948.72\n2023-03-24,3970.99\n"
    with patch("flat_flyer.market_data._http_get", return_value=csv):
        df = fetch_fred(pd.Timestamp("2023-03-23"), pd.Timestamp("2023-03-24"))
    assert list(df["close"]) == pytest.approx([3948.72, 3970.99])
