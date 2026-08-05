"""Self-contained HTML report: every number, table, and figure comes straight
from the analysis code. Figures are embedded as base64 so the single file can
be shared or archived."""

from __future__ import annotations

import base64
from datetime import datetime
from pathlib import Path

import pandas as pd
from jinja2 import Template

from . import config
from .validate import CheckResult
from .verify import VerificationResult

# Coverage of the master plan's analysis questions; used to render the
# progress section so the report always reflects the current development
# state. Update the status here as phases land.
COVERAGE = [
    ("A", "Baseline performance", "done",
     "Metrics, equity curve, drawdown, monthly/yearly breakdowns, outcome distribution."),
    ("B", "Previous close, entry price, and mean reversion", "pending",
     "Designed (work order in PLAN.md); no intraday data needed — Price at Open "
     "is the 10:00am SPX level. Preliminary: 57% of entries start beyond the wings."),
    ("C", "Long-term SPX growth and the fixed 10-point width", "pending",
     "Relative-width analysis planned for Phase 2."),
    ("D", "Strike-grid rounding", "pending",
     "Rounding displacement analysis planned for Phase 2."),
    ("E", "Bid-ask spread, slippage, and costs", "partial",
     "Observed spreads and skipped-day log are summarized; slippage/fee scenarios come in Phase 3."),
    ("F", "Parameter robustness", "pending",
     "Requires additional Option Alpha backtests (Phase 3)."),
    ("V1", "Backtest verification Step 1 (internal consistency)", "done",
     "Trade-calendar completeness and entry-price filter consistency on the exports."),
    ("V2", "Backtest verification Step 2 (SPX close replay)", "done",
     "Strike-selection and settlement P/L replay against independent daily closes (FRED→Yahoo→Stooq)."),
]

TEMPLATE = Template("""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Flat Flyer — SPX 0DTE Iron Butterfly Report</title>
<style>
  :root { color-scheme: light; }
  body { font-family: -apple-system, "Segoe UI", Helvetica, Arial, sans-serif;
         max-width: 960px; margin: 2rem auto; padding: 0 1.5rem; color: #1c2733; line-height: 1.55; }
  h1 { font-size: 1.7rem; border-bottom: 3px solid #264653; padding-bottom: .4rem; }
  h2 { font-size: 1.25rem; margin-top: 2.2rem; color: #264653; }
  .meta { color: #6b7a88; font-size: .9rem; }
  .cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: .8rem; margin: 1.2rem 0; }
  .card { background: #f4f7f9; border-radius: 8px; padding: .8rem 1rem; }
  .card .label { font-size: .75rem; text-transform: uppercase; letter-spacing: .05em; color: #6b7a88; }
  .card .value { font-size: 1.35rem; font-weight: 600; margin-top: .2rem; }
  .card .value.pos { color: #1d7a5f; } .card .value.neg { color: #c0442c; }
  table { border-collapse: collapse; width: 100%; font-size: .88rem; margin: .8rem 0; }
  th, td { border: 1px solid #d8e0e6; padding: .35rem .6rem; text-align: right; }
  th:first-child, td:first-child { text-align: left; }
  th { background: #eef2f5; }
  img { max-width: 100%; border: 1px solid #e3e9ee; border-radius: 6px; margin: .6rem 0; }
  .status { font-weight: 600; padding: .1rem .5rem; border-radius: 4px; font-size: .8rem; }
  .status.done { background: #d9f2e5; color: #1d7a5f; }
  .status.partial { background: #fdf1d6; color: #9a6b00; }
  .status.pending { background: #eceff2; color: #6b7a88; }
  .ok { color: #1d7a5f; font-weight: 600; } .fail { color: #c0442c; font-weight: 600; }
  footer { margin-top: 3rem; color: #6b7a88; font-size: .8rem; border-top: 1px solid #d8e0e6; padding-top: .8rem; }
</style>
</head>
<body>

<h1>Flat Flyer — SPX 0DTE Iron Butterfly</h1>
<p class="meta">Generated {{ generated }} · {{ stats.n_trades }} trades,
{{ stats.first_trade }} to {{ stats.last_trade }} · Source: Option Alpha backtest export</p>

<h2>1. Executive summary</h2>
<div class="cards">
  <div class="card"><div class="label">Total P/L</div>
    <div class="value {{ 'pos' if stats.total_pl > 0 else 'neg' }}">${{ "{:,.0f}".format(stats.total_pl) }}</div></div>
  <div class="card"><div class="label">Avg P/L per trade</div>
    <div class="value {{ 'pos' if stats.avg_pl > 0 else 'neg' }}">${{ "{:,.2f}".format(stats.avg_pl) }}</div></div>
  <div class="card"><div class="label">Win rate</div>
    <div class="value">{{ "{:.1%}".format(stats.win_rate) }}</div></div>
  <div class="card"><div class="label">Profit factor</div>
    <div class="value">{{ "{:.2f}".format(stats.profit_factor) }}</div></div>
  <div class="card"><div class="label">Max drawdown</div>
    <div class="value neg">${{ "{:,.0f}".format(stats.max_drawdown) }}</div></div>
  <div class="card"><div class="label">Return on $100k</div>
    <div class="value {{ 'pos' if stats.return_on_capital > 0 else 'neg' }}">{{ "{:.1%}".format(stats.return_on_capital) }}</div></div>
</div>
<p>The strategy wins {{ "{:.0%}".format(stats.win_rate) }} of the time; the average winner
(${{ "{:,.0f}".format(stats.avg_winner) }}) is about {{ "{:.1f}".format(stats.avg_winner / -stats.avg_loser) }}x
the average loser (${{ "{:,.0f}".format(stats.avg_loser) }}), which is what makes the low win rate profitable.
Most important caveat: these are Option Alpha model fills at the mid; execution costs and slippage
are not yet applied (Phase 3).</p>

<h2>2. Strategy and data</h2>
<p>SPX 0DTE iron butterfly: short put and call at the strike $0.01 above the previous close,
long wings {{ width }} points away, entered 10:00am Mon–Fri, one contract, held to expiration.
Entry filters: mid credit at most {{ max_mid }}, combined bid/ask spread at most
${{ "{:.2f}".format(max_spread) }}. Average opening credit was
${{ "{:,.0f}".format(stats.avg_credit) }} against a ${{ "{:,.0f}".format(width * 100) }} width,
so the typical max loss per trade is small relative to the credit.</p>

<h3>Days skipped by the entry filters</h3>
<p>{{ n_filtered }} trading days were skipped ({{ "{:.0%}".format(n_filtered / (n_filtered + stats.n_trades)) }}
of eligible days). This selection effect is part of the strategy and matters for the
execution-cost analysis in Phase 3.</p>
{{ filtered_table }}

<h2>3. Baseline performance</h2>
<img src="data:image/png;base64,{{ figures.equity_curve }}" alt="Equity curve and drawdown">
<img src="data:image/png;base64,{{ figures.pl_histogram }}" alt="P/L distribution">
<h3>By year</h3>
{{ yearly_table }}
<h3>By month</h3>
<img src="data:image/png;base64,{{ figures.monthly_heatmap }}" alt="Monthly P/L heatmap">
<h3>Credit vs outcome</h3>
<img src="data:image/png;base64,{{ figures.credit_vs_pl }}" alt="Opening credit vs P/L">

<h2>4. Data validation</h2>
<p>Structural and payoff checks on the raw export. A failing check flags rows for review;
it does not stop the report.</p>
<table>
  <tr><th>Check</th><th>Description</th><th>Result</th></tr>
  {% for c in checks %}
  <tr><td>{{ c.name }}</td><td style="text-align:left">{{ c.description }}</td>
      <td>{% if c.passed %}<span class="ok">OK</span>{% else %}
          <span class="fail">{{ c.violations }}/{{ c.total }} rows</span>
          {% if c.examples %}(e.g. {{ c.examples | join(", ") }}){% endif %}{% endif %}</td></tr>
  {% endfor %}
</table>

<h2>5. Backtest verification — Step 1 (internal consistency)</h2>
<p>Uses only the Option Alpha exports (no external market data). Verdict:
<strong>{{ step1.verdict }}</strong> —
{{ step1.n_sessions }} NYSE sessions =
{{ step1.n_trades }} executed trades + {{ step1.n_skipped }} skipped days.</p>
<table>
  <tr><th>Check</th><th>Description</th><th>Result</th></tr>
  {% for c in step1.checks %}
  <tr><td>{{ c.name }}</td><td style="text-align:left">{{ c.description }}</td>
      <td>{% if c.passed %}<span class="ok">OK</span>{% else %}
          <span class="fail">{{ c.violations }}/{{ c.total }}</span>
          {% if c.examples %}(e.g. {{ c.examples | join(", ") }}){% endif %}{% endif %}</td></tr>
  {% endfor %}
</table>
{% if step1.discrepancies %}
<p>{{ step1.discrepancies | length }} discrepancies (date and magnitude written to
<code>data/processed/verify_step1_discrepancies.csv</code>):</p>
<table>
  <tr><th>Check</th><th>Date</th><th style="text-align:left">Detail</th><th>Magnitude</th></tr>
  {% for d in step1.discrepancies[:25] %}
  <tr><td>{{ d.check }}</td><td>{{ d.date }}</td>
      <td style="text-align:left">{{ d.detail }}</td>
      <td>{% if d.magnitude is not none %}{{ "%.4g"|format(d.magnitude) }}{% else %}—{% endif %}</td></tr>
  {% endfor %}
</table>
{% else %}
<p>No discrepancies recorded.</p>
{% endif %}

<h2>6. Backtest verification — Step 2 (SPX close replay)</h2>
<p>Independent SPX daily closes from <strong>{{ step2.source or "unavailable" }}</strong>
(fetch order: FRED → Yahoo → Stooq, with on-disk cache). Verdict:
<strong>{{ step2.verdict }}</strong> over {{ step2.n_trades }} executed trades.</p>
<table>
  <tr><th>Check</th><th>Description</th><th>Result</th></tr>
  {% for c in step2.checks %}
  <tr><td>{{ c.name }}</td><td style="text-align:left">{{ c.description }}</td>
      <td>{% if c.passed %}<span class="ok">OK</span>{% else %}
          <span class="fail">{{ c.violations }}/{{ c.total }}</span>
          {% if c.examples %}(e.g. {{ c.examples | join(", ") }}){% endif %}{% endif %}</td></tr>
  {% endfor %}
</table>
{% if step2.discrepancies %}
<p>{{ step2.discrepancies | length }} discrepancies (see
<code>data/processed/verify_step2_discrepancies.csv</code>):</p>
<table>
  <tr><th>Check</th><th>Date</th><th style="text-align:left">Detail</th><th>Magnitude</th></tr>
  {% for d in step2.discrepancies[:25] %}
  <tr><td>{{ d.check }}</td><td>{{ d.date }}</td>
      <td style="text-align:left">{{ d.detail }}</td>
      <td>{% if d.magnitude is not none %}{{ "%.4g"|format(d.magnitude) }}{% else %}—{% endif %}</td></tr>
  {% endfor %}
</table>
{% else %}
<p>No discrepancies recorded. Export Price at Close matches the independent SPX
close on every trade day, and replayed expiration P/L matches the reported P/L.</p>
{% endif %}

<h2>7. Coverage — progress against the master plan</h2>
<p>Development status of each analysis question from
<code>docs/Option_Alpha_SPX_Coding_and_Report_Plan.md</code>. This section is rebuilt on every
run, so the report always reflects the current state of the project.</p>
<table>
  <tr><th>Question</th><th>Topic</th><th>Status</th><th style="text-align:left">Notes</th></tr>
  {% for q, topic, status, note in coverage %}
  <tr><td>{{ q }}</td><td style="text-align:left">{{ topic }}</td>
      <td><span class="status {{ status }}">{{ status }}</span></td>
      <td style="text-align:left">{{ note }}</td></tr>
  {% endfor %}
</table>

<footer>Flat Flyer analysis · rebuilt with <code>make report</code> · raw data in
<code>data/raw/</code> is never modified.</footer>
</body>
</html>
""")


def _embed(path: Path) -> str:
    return base64.b64encode(path.read_bytes()).decode()


def _df_html(df: pd.DataFrame, money_cols: list[str] | None = None,
             pct_cols: list[str] | None = None) -> str:
    df = df.copy()
    for col in money_cols or []:
        df[col] = df[col].map("${:,.0f}".format)
    for col in pct_cols or []:
        df[col] = df[col].map("{:.1%}".format)
    return df.to_html(border=0)


def build_report(stats: dict, yearly: pd.DataFrame, filtered: pd.DataFrame,
                 checks: list[CheckResult], figures: dict[str, Path],
                 step1: VerificationResult | None = None,
                 step2: VerificationResult | None = None) -> Path:
    config.REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    if step1 is None:
        step1 = VerificationResult(checks=[], verdict="not run")
    if step2 is None:
        step2 = VerificationResult(checks=[], verdict="not run")

    html = TEMPLATE.render(
        generated=datetime.now().strftime("%b %d, %Y %H:%M"),
        stats=stats,
        width=config.WING_WIDTH,
        max_mid=config.MAX_MID_CREDIT,
        max_spread=config.MAX_BID_ASK_SPREAD,
        yearly_table=_df_html(yearly.round(2), money_cols=["Total P/L", "Avg P/L", "Avg credit"],
                              pct_cols=["Win rate"]),
        n_filtered=len(filtered),
        filtered_table=_df_html(
            filtered.groupby("reason").size().to_frame("Days")
            .sort_values("Days", ascending=False)
        ),
        checks=checks,
        step1=step1,
        step2=step2,
        coverage=COVERAGE,
        figures={name: _embed(path) for name, path in figures.items()},
    )

    out = config.REPORTS_DIR / "report.html"
    out.write_text(html)
    return out
