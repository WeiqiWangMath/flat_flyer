import pandas as pd
import pytest

from flat_flyer.load import load_filtered_log, parse_legs


def test_parse_legs_iron_butterfly():
    legs = "long put 3,940 / short put 3,950 / short call 3,950 / long call 3,960"
    assert parse_legs(legs) == {
        "long_put": 3940.0,
        "short_put": 3950.0,
        "short_call": 3950.0,
        "long_call": 3960.0,
    }


def test_parse_legs_high_strikes():
    legs = "long put 6,090 / short put 6,100 / short call 6,100 / long call 6,110"
    strikes = parse_legs(legs)
    assert strikes["short_put"] == 6100.0
    assert strikes["long_call"] == 6110.0


@pytest.fixture
def filtered_log(tmp_path):
    content = """Mar 28, 2023
Bid/ask spread
Bid: $7.50 / Ask: $10.00
Mar 29, 2023
Pricing issue detected
Bid/ask spread is too wide for accurate pricing (Bid: $6.60, Ask: $12.80)
May 5, 2023
Max price
Mid price: $9.77
Jul 3, 2023
Early close day
Aug 5, 2024
Pricing issue detected
Bid/ask spread is too wide for accurate pricing (Bid: 0, Ask: $57.00)
Oct 22, 2025
Leg error detected
Long put input: Requested put option not available.
May 12, 2025
Pricing issue detected
Mid price $10.83 is greater than spread width ($10.00). Bid: $9.15, Ask: $12.50
"""
    path = tmp_path / "filtered.txt"
    path.write_text(content)
    return load_filtered_log(path)


def test_filtered_log_row_count(filtered_log):
    assert len(filtered_log) == 7


def test_filtered_log_spread_entry(filtered_log):
    row = filtered_log.iloc[0]
    assert row["date"] == pd.Timestamp("2023-03-28")
    assert row["reason"] == "Bid/ask spread"
    assert row["bid"] == 7.50
    assert row["ask"] == 10.00
    assert row["mid"] == pytest.approx(8.75)


def test_filtered_log_max_price(filtered_log):
    row = filtered_log.iloc[2]
    assert row["reason"] == "Max price"
    assert row["mid"] == 9.77
    assert pd.isna(row["bid"]) or row["bid"] is None


def test_filtered_log_early_close_has_no_detail(filtered_log):
    row = filtered_log.iloc[3]
    assert row["reason"] == "Early close day"
    assert row["detail"] == ""


def test_filtered_log_zero_bid(filtered_log):
    row = filtered_log.iloc[4]
    assert row["bid"] == 0.0
    assert row["ask"] == 57.00


def test_filtered_log_leg_error(filtered_log):
    row = filtered_log.iloc[5]
    assert row["reason"] == "Leg error detected"
    assert "not available" in row["detail"]


def test_filtered_log_mid_above_width(filtered_log):
    row = filtered_log.iloc[6]
    assert row["mid"] == 10.83
    assert row["bid"] == 9.15
