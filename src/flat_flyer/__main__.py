"""Rebuild the full analysis and report: ``make report`` or
``PYTHONPATH=src python -m flat_flyer``."""

from __future__ import annotations

from . import config, load, metrics, plots, report, validate


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

    config.PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(config.PROCESSED_DIR / "trades_clean.csv", index=False)
    filtered.to_csv(config.PROCESSED_DIR / "filtered_days.csv", index=False)

    stats = metrics.baseline_stats(df)
    figures = plots.all_figures(df)
    out = report.build_report(stats, metrics.yearly_table(df), filtered, checks, figures)

    print(f"Total P/L ${stats['total_pl']:,.0f} over {stats['n_trades']} trades, "
          f"win rate {stats['win_rate']:.1%}, profit factor {stats['profit_factor']:.2f}")
    print(f"Report written to {out}")


if __name__ == "__main__":
    main()
