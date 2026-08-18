"""Question D — strike-grid rounding tests."""

from __future__ import annotations

import pandas as pd
import pytest

from flat_flyer.grid_rounding import (
    build_grid_rounding_table,
    grid_rounding_summary,
    verdict_sentence,
)


def test_grid_error_bounded_by_half_grid():
    positions = pd.DataFrame({
        "opened": pd.to_datetime(["2023-03-24 10:00", "2023-03-27 10:00",
                                  "2023-03-28 10:00"]),
        "short_put": [3950.0, 3970.0, 3980.0],
        "P/L": [100.0, -50.0, 20.0],
    })
    spx = pd.DataFrame({
        "date": pd.to_datetime(["2023-03-23", "2023-03-24", "2023-03-27"]),
        "close": [3948.72, 3970.99, 3977.53],
    })
    # prev for Mar 24 = 3948.72 → err = 3950 - 3948.72 = 1.28
    # prev for Mar 27 = 3970.99 → err = 3970 - 3970.99 = -0.99
    # Mar 28 missing prev → NaN row still produced
    grid = build_grid_rounding_table(positions, spx)
    assert grid.loc[0, "grid_error"] == pytest.approx(1.28)
    assert grid.loc[1, "grid_error"] == pytest.approx(-0.99)
    finite = grid["grid_error"].dropna()
    assert (finite.abs() <= 2.5 + 1e-9).all()


def test_summary_and_verdict():
    grid = pd.DataFrame({
        "opened": pd.to_datetime(["2023-01-02", "2023-01-03", "2023-01-04"]),
        "prev_close": [4001.2, 3998.5, 4000.0],
        "center_strike": [4000.0, 4000.0, 4000.0],
        "grid_error": [-1.2, 1.5, 0.0],
        "side": ["down", "up", "exact"],
        "pl": [10.0, 20.0, -5.0],
    })
    summary = grid_rounding_summary(grid)
    assert summary["n"] == 3
    assert summary["max_abs_error"] == pytest.approx(1.5)
    assert summary["n_up"] == 1 and summary["n_down"] == 1
    assert "does not materially affect" in verdict_sentence(summary)
