"""NYSE full-day closures for the Flat Flyer backtest window.

Hard-coded (no calendar package) so the verification is reproducible offline.
Includes regular holidays plus the Jan 9, 2025 national day of mourning
(President Carter) when the NYSE was closed.
"""

from __future__ import annotations

import pandas as pd

# Inclusive coverage for positions.csv / filtered_trade.txt (Mar 2023 – Mar 2026).
NYSE_FULL_DAY_CLOSURES: frozenset[pd.Timestamp] = frozenset(
    pd.Timestamp(d) for d in [
        # 2023
        "2023-01-02",  # New Year's Day observed
        "2023-01-16",  # MLK Day
        "2023-02-20",  # Presidents' Day
        "2023-04-07",  # Good Friday
        "2023-05-29",  # Memorial Day
        "2023-06-19",  # Juneteenth
        "2023-07-04",  # Independence Day
        "2023-09-04",  # Labor Day
        "2023-11-23",  # Thanksgiving
        "2023-12-25",  # Christmas
        # 2024
        "2024-01-01",  # New Year's Day
        "2024-01-15",  # MLK Day
        "2024-02-19",  # Presidents' Day
        "2024-03-29",  # Good Friday
        "2024-05-27",  # Memorial Day
        "2024-06-19",  # Juneteenth
        "2024-07-04",  # Independence Day
        "2024-09-02",  # Labor Day
        "2024-11-28",  # Thanksgiving
        "2024-12-25",  # Christmas
        # 2025
        "2025-01-01",  # New Year's Day
        "2025-01-09",  # National day of mourning (Carter)
        "2025-01-20",  # MLK Day
        "2025-02-17",  # Presidents' Day
        "2025-04-18",  # Good Friday
        "2025-05-26",  # Memorial Day
        "2025-06-19",  # Juneteenth
        "2025-07-04",  # Independence Day
        "2025-09-01",  # Labor Day
        "2025-11-27",  # Thanksgiving
        "2025-12-25",  # Christmas
        # 2026 (through March)
        "2026-01-01",  # New Year's Day
        "2026-01-19",  # MLK Day
        "2026-02-16",  # Presidents' Day
    ]
)


def nyse_sessions(start: pd.Timestamp, end: pd.Timestamp) -> pd.DatetimeIndex:
    """Mon–Fri sessions in [start, end] excluding NYSE full-day closures."""
    start = pd.Timestamp(start).normalize()
    end = pd.Timestamp(end).normalize()
    weekdays = pd.bdate_range(start, end)
    return weekdays[~weekdays.isin(NYSE_FULL_DAY_CLOSURES)]
