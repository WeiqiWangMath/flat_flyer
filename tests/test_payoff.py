import pandas as pd
import pytest

from flat_flyer.metrics import baseline_stats, equity_curve
from flat_flyer.validate import butterfly_payoff


def test_settle_exactly_at_center_keeps_full_credit():
    assert butterfly_payoff(premium=905, short_strike=3950, settle=3950) == 905


def test_settle_inside_wings_loses_intrinsic():
    # SPX settles 4.38 above the body: lose 438, keep the rest of the credit.
    assert butterfly_payoff(premium=905, short_strike=3950, settle=3954.38) == pytest.approx(467)


def test_settle_beyond_wings_caps_loss_at_width():
    assert butterfly_payoff(premium=905, short_strike=3950, settle=3900) == pytest.approx(-95)
    assert butterfly_payoff(premium=905, short_strike=3950, settle=4100) == pytest.approx(-95)


def test_loss_symmetric_up_and_down():
    down = butterfly_payoff(premium=800, short_strike=4000, settle=3995)
    up = butterfly_payoff(premium=800, short_strike=4000, settle=4005)
    assert down == up == pytest.approx(300)


@pytest.fixture
def toy_trades():
    return pd.DataFrame(
        {
            "opened": pd.to_datetime(["2023-01-02 10:00", "2023-01-03 10:00",
                                      "2023-02-01 10:00", "2023-02-02 10:00"]),
            "closed": pd.to_datetime(["2023-01-02 16:00", "2023-01-03 16:00",
                                      "2023-02-01 16:00", "2023-02-02 16:00"]),
            "P/L": [100.0, -50.0, 200.0, -150.0],
            "Premium": [900.0, 880.0, 910.0, 890.0],
            "mid_credit": [9.0, 8.8, 9.1, 8.9],
            "open_spread": [1.0, 1.2, 0.9, 1.1],
        }
    )


def test_baseline_stats(toy_trades):
    stats = baseline_stats(toy_trades)
    assert stats["n_trades"] == 4
    assert stats["total_pl"] == 100.0
    assert stats["win_rate"] == 0.5
    assert stats["avg_winner"] == 150.0
    assert stats["avg_loser"] == -100.0
    assert stats["profit_factor"] == pytest.approx(300 / 200)


def test_equity_curve_drawdown(toy_trades):
    curve = equity_curve(toy_trades)
    assert curve["cum_pl"].tolist() == [100.0, 50.0, 250.0, 100.0]
    assert curve["drawdown"].min() == -150.0
