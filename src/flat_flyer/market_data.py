"""Independent SPX daily closes for Phase 2 Step 2.

Fetch order (first success wins): FRED → Yahoo Finance → Stooq.
Results are cached under ``data/processed/`` so later rebuilds can run offline
when the cache already covers the requested window.
"""

from __future__ import annotations

import io
import json
import urllib.error
import urllib.request
from datetime import datetime, timezone

import pandas as pd

from . import config

USER_AGENT = "flat-flyer/0.1 (research; SPX backtest verification)"
HTTP_TIMEOUT = 30


class MarketDataError(RuntimeError):
    """Raised when every SPX source fails and no usable cache exists."""


def _http_get(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as resp:
        return resp.read()


def _normalize(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["date"] = pd.to_datetime(out["date"]).dt.normalize()
    out["close"] = pd.to_numeric(out["close"], errors="coerce")
    out = out.dropna(subset=["close"]).drop_duplicates(subset=["date"], keep="last")
    return out.sort_values("date").reset_index(drop=True)


def fetch_fred(start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    """S&P 500 daily close from FRED series SP500."""
    url = (
        "https://fred.stlouisfed.org/graph/fredgraph.csv"
        f"?id=SP500&cosd={start:%Y-%m-%d}&coed={end:%Y-%m-%d}"
    )
    raw = _http_get(url)
    df = pd.read_csv(io.BytesIO(raw))
    if "observation_date" not in df.columns or "SP500" not in df.columns:
        raise MarketDataError(f"Unexpected FRED columns: {list(df.columns)}")
    return _normalize(df.rename(columns={"observation_date": "date", "SP500": "close"}))


def fetch_yahoo(start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    """S&P 500 (^GSPC) daily close via Yahoo chart API."""
    # Yahoo period markers are Unix seconds; pad end by one day so the end
    # session is included.
    p1 = int(pd.Timestamp(start).timestamp())
    p2 = int((pd.Timestamp(end) + pd.Timedelta(days=1)).timestamp())
    url = (
        "https://query2.finance.yahoo.com/v8/finance/chart/%5EGSPC"
        f"?period1={p1}&period2={p2}&interval=1d&events=history"
    )
    payload = json.loads(_http_get(url))
    result = (payload.get("chart") or {}).get("result") or []
    if not result:
        err = (payload.get("chart") or {}).get("error")
        raise MarketDataError(f"Yahoo returned no result: {err}")
    block = result[0]
    timestamps = block.get("timestamp") or []
    closes = ((block.get("indicators") or {}).get("quote") or [{}])[0].get("close") or []
    if not timestamps or not closes:
        raise MarketDataError("Yahoo chart payload missing timestamps/closes")
    # Yahoo stamps are exchange-local epoch seconds; normalize to calendar date
    # in US/Eastern so the session date matches FRED/OA.
    dates = (
        pd.to_datetime(timestamps, unit="s", utc=True)
        .tz_convert("America/New_York")
        .tz_localize(None)
        .normalize()
    )
    return _normalize(pd.DataFrame({"date": dates, "close": closes}))


def fetch_stooq(start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    """S&P 500 daily close from Stooq (^spx)."""
    url = (
        "https://stooq.com/q/d/l/"
        f"?s=%5Espx&d1={start:%Y%m%d}&d2={end:%Y%m%d}&i=d"
    )
    raw = _http_get(url)
    text = raw[:200].decode("utf-8", errors="replace").lstrip().lower()
    if text.startswith("<!doctype") or text.startswith("<html"):
        raise MarketDataError("Stooq returned an HTML challenge page, not CSV")
    df = pd.read_csv(io.BytesIO(raw))
    cols = {c.lower(): c for c in df.columns}
    if "date" not in cols or "close" not in cols:
        raise MarketDataError(f"Unexpected Stooq columns: {list(df.columns)}")
    return _normalize(pd.DataFrame({
        "date": df[cols["date"]],
        "close": df[cols["close"]],
    }))


_FETCHERS = (
    ("FRED", "fetch_fred"),
    ("Yahoo", "fetch_yahoo"),
    ("Stooq", "fetch_stooq"),
)


def _usable_for_window(df: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp) -> bool:
    """True when ``df`` spans ``[start, end]`` and has at least one prior session."""
    if df.empty:
        return False
    start = pd.Timestamp(start).normalize()
    end = pd.Timestamp(end).normalize()
    if df["date"].max() < end or df["date"].min() > start:
        return False
    return bool((df["date"] < start).any())


def _read_cache(path) -> pd.DataFrame | None:
    if not path.exists():
        return None
    df = pd.read_csv(path, parse_dates=["date"])
    if "close" not in df.columns:
        return None
    return _normalize(df[["date", "close"]])


def _write_cache(path, df: pd.DataFrame, source: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    out = df[["date", "close"]].copy()
    out["source"] = source
    out["fetched_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    out.to_csv(path, index=False)


def load_spx_daily(start: pd.Timestamp, end: pd.Timestamp,
                   *, use_cache: bool = True,
                   cache_path=None) -> tuple[pd.DataFrame, str]:
    """Return ``(date, close)`` SPX daily closes covering ``[start, end]``.

    Tries the on-disk cache first (if it covers the window), then FRED, Yahoo,
    and Stooq in order. Returns the frame plus the source label used.
    """
    start = pd.Timestamp(start).normalize()
    end = pd.Timestamp(end).normalize()
    # Need one prior session for strike-selection previous-close lookups.
    fetch_start = start - pd.Timedelta(days=10)
    path = cache_path or config.SPX_DAILY_CACHE

    if use_cache:
        cached = _read_cache(path)
        if cached is not None and _usable_for_window(cached, start, end):
            window = cached[(cached["date"] >= fetch_start) & (cached["date"] <= end)]
            return window.reset_index(drop=True), "cache"

    errors: list[str] = []
    # Resolve fetchers by name so tests can patch the module-level functions.
    import flat_flyer.market_data as md

    for name, attr in _FETCHERS:
        fetcher = getattr(md, attr)
        try:
            df = fetcher(fetch_start, end)
            if df.empty:
                raise MarketDataError(f"{name} returned an empty series")
            if not _usable_for_window(df, start, end):
                raise MarketDataError(
                    f"{name} coverage {df['date'].min().date()}–"
                    f"{df['date'].max().date()} misses {start.date()}–{end.date()} "
                    "(or lacks a prior session)"
                )
            _write_cache(path, df, name)
            window = df[(df["date"] >= fetch_start) & (df["date"] <= end)]
            return window.reset_index(drop=True), name
        except (MarketDataError, urllib.error.URLError, urllib.error.HTTPError,
                TimeoutError, ValueError, KeyError, json.JSONDecodeError,
                OSError) as exc:
            errors.append(f"{name}: {exc}")

    # Last resort: partial cache, even if it does not fully cover the window.
    cached = _read_cache(path) if use_cache else None
    if cached is not None and not cached.empty:
        window = cached[(cached["date"] >= fetch_start) & (cached["date"] <= end)]
        if not window.empty:
            return window.reset_index(drop=True), "cache-partial"

    raise MarketDataError(
        "Could not load SPX daily closes from FRED, Yahoo, or Stooq. "
        + " | ".join(errors)
    )


def with_previous_close(spx: pd.DataFrame) -> pd.DataFrame:
    """Add ``prev_close`` = prior session's close (sorted by date)."""
    out = spx.sort_values("date").copy()
    out["prev_close"] = out["close"].shift(1)
    return out
