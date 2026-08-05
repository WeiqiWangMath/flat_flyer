"""Question B — entry displacement and mean-reversion unit tests."""

from __future__ import annotations

import pandas as pd
import pytest

from flat_flyer.displacement import (
    BUCKET_ORDER,
    build_displacement_table,
    bucket_table,
    displacement_summary,
    verdict_sentence,
)


@pytest.fixture
def toy_positions():
    # Credits in points; wing width 10.
    return pd.DataFrame({
        "opened": pd.to_datetime([
            "2023-03-24 10:00", "2023-03-27 10:00", "2023-03-30 10:00",
            "2023-03-31 10:00", "2023-04-04 10:00",
        ]),
        "short_put": [4000.0, 4000.0, 4000.0, 4000.0, 4000.0],
        "Price at Open": [4005.0, 4012.0, 3985.0, 4025.0, 4000.0],
        "Price at Close": [4002.0, 4001.0, 3995.0, 4030.0, 3990.0],
        "Open Price": [9.0, 9.2, 8.5, 9.5, 8.0],
        "mid_credit": [9.0, 9.2, 8.5, 9.5, 8.0],
        "Premium": [900.0, 920.0, 850.0, 950.0, 800.0],
        "P/L": [700.0, 820.0, 350.0, -50.0, -200.0],
    })


def test_displacement_variables(toy_positions):
    disp = build_displacement_table(toy_positions)
    assert list(disp["d"]) == pytest.approx([5.0, 12.0, -15.0, 25.0, 0.0])
    assert list(disp["m"]) == pytest.approx([-3.0, -11.0, 10.0, 5.0, -10.0])
    assert list(disp["final_miss"]) == pytest.approx([2.0, 1.0, 5.0, 30.0, 10.0])
    # Finished closer to K than at entry?
    assert list(disp["toward_center"]) == [True, True, True, False, False]


def test_payoff_anchored_buckets_use_per_trade_credit(toy_positions):
    disp = build_displacement_table(toy_positions)
    # |d|=5 ≤ credit 9 → inside credit
    assert disp.loc[0, "bucket"] == "inside credit"
    # |d|=12 → between width(10) and 1.5×width(15)
    assert disp.loc[1, "bucket"] == "1–1.5× width"
    # |d|=15 → exactly 1.5× width → upper edge of 1–1.5× (≤ 1.5w)
    assert disp.loc[2, "bucket"] == "1–1.5× width"
    # |d|=25 → 2.5× width exactly → 1.5–2.5×
    assert disp.loc[3, "bucket"] == "1.5–2.5× width"
    # |d|=0 → inside credit
    assert disp.loc[4, "bucket"] == "inside credit"


def test_bucket_inside_credit_boundary_uses_own_credit():
    # Same |d|=9: trade with credit 9.5 is inside; credit 8.0 is credit–width.
    positions = pd.DataFrame({
        "opened": pd.to_datetime(["2023-01-02 10:00", "2023-01-03 10:00"]),
        "short_put": [4000.0, 4000.0],
        "Price at Open": [4009.0, 4009.0],
        "Price at Close": [4000.0, 4000.0],
        "Open Price": [9.5, 8.0],
        "mid_credit": [9.5, 8.0],
        "Premium": [950.0, 800.0],
        "P/L": [950.0, 800.0],
    })
    disp = build_displacement_table(positions)
    assert disp.loc[0, "bucket"] == "inside credit"
    assert disp.loc[1, "bucket"] == "credit–width"


def test_summary_regression_negative_when_reverting(toy_positions):
    disp = build_displacement_table(toy_positions)
    summary = displacement_summary(disp)
    assert summary["n"] == 5
    # Mostly reverting sample → negative slope.
    assert summary["reg_slope"] < 0
    assert "mean_reverting" in summary
    assert verdict_sentence(summary)


def test_bucket_table_ordered(toy_positions):
    disp = build_displacement_table(toy_positions)
    table = bucket_table(disp)
    labels = list(table.index)
    assert labels == [b for b in BUCKET_ORDER if b in labels]
    assert table["Trades"].sum() == len(disp)
