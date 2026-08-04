"""Rebuild the full analysis and report: ``make report`` or
``PYTHONPATH=src python -m flat_flyer``."""

from __future__ import annotations

from . import config, load, market_data, metrics, plots, report, validate, verify


def main() -> None:
    print(f"Loading {config.POSITIONS_CSV.name} ...")
    df = load.load_positions(config.POSITIONS_CSV)
    filtered = load.load_filtered_log(config.FILTERED_LOG)
    print(f"  {len(df)} trades, {len(filtered)} skipped days")

    checks = validate.validate_positions(df)
    failed = [c for c in checks if not c.passed]
    print(f"Validation: {len(checks) - len(failed)}/{len(checks)} checks passed")
    for c in failed:
        print(f"  FAIL {c.name}: {c.violations}/{c.total} rows, e.g. {c.examples}")

    step1 = verify.verify_internal_consistency(df, filtered)
    print(f"Phase 2 Step 1 ({step1.verdict}): "
          f"{sum(c.passed for c in step1.checks)}/{len(step1.checks)} checks passed "
          f"over {step1.n_sessions} NYSE sessions "
          f"({step1.n_trades} trades + {step1.n_skipped} skips)")
    for c in step1.checks:
        if not c.passed:
            print(f"  FAIL {c.name}: {c.violations}/{c.total}, e.g. {c.examples}")
    if step1.discrepancies:
        print(f"  {len(step1.discrepancies)} discrepancies recorded")

    start = df["opened"].min()
    end = df["opened"].max()
    print("Loading independent SPX daily closes (FRED → Yahoo → Stooq) ...")
    spx, spx_source = market_data.load_spx_daily(start, end)
    print(f"  {len(spx)} sessions from {spx_source} "
          f"({spx['date'].min().date()} – {spx['date'].max().date()})")
    step2 = verify.verify_against_market_data(df, spx, source=spx_source)
    print(f"Phase 2 Step 2 ({step2.verdict}, source={spx_source}): "
          f"{sum(c.passed for c in step2.checks)}/{len(step2.checks)} checks passed")
    for c in step2.checks:
        status = "OK" if c.passed else "FAIL"
        print(f"  {status} {c.name}: {c.violations}/{c.total}"
              + (f", e.g. {c.examples}" if c.examples else ""))
    if step2.discrepancies:
        print(f"  {len(step2.discrepancies)} discrepancies recorded")

    config.PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(config.PROCESSED_DIR / "trades_clean.csv", index=False)
    filtered.to_csv(config.PROCESSED_DIR / "filtered_days.csv", index=False)
    verify.discrepancies_frame(step1).to_csv(
        config.PROCESSED_DIR / "verify_step1_discrepancies.csv", index=False
    )
    verify.discrepancies_frame(step2).to_csv(
        config.PROCESSED_DIR / "verify_step2_discrepancies.csv", index=False
    )
    if step2.settle_detail is not None:
        step2.settle_detail.to_csv(
            config.PROCESSED_DIR / "verify_step2_settlement.csv", index=False
        )

    stats = metrics.baseline_stats(df)
    figures = plots.all_figures(df)
    out = report.build_report(
        stats, metrics.yearly_table(df), filtered, checks, figures,
        step1=step1, step2=step2,
    )

    print(f"Total P/L ${stats['total_pl']:,.0f} over {stats['n_trades']} trades, "
          f"win rate {stats['win_rate']:.1%}, profit factor {stats['profit_factor']:.2f}")
    print(f"Report written to {out}")


if __name__ == "__main__":
    main()
