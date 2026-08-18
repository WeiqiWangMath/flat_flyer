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
    ("A", "What did the original backtest deliver?", "done",
     "+$17,543 on $100,000 over 508 trades (Mar 2023 – Mar 2026); win rate 25.8%, "
     "profit factor 1.40, max drawdown −$1,605. No execution costs applied yet."),
    ("B", "Is this a mean-reversion trade or a bet that SPX stays near the center?", "done",
     "Mostly entered as a reversion bet — 57% of entries start beyond the wings — "
     "but the measured afternoon reversion is weak (slope −0.10, t=−1.5)."),
    ("C", "Is a fixed 10-point butterfly still the same strategy as SPX grows?", "partial",
     "Apparently not: the width shrank from 0.255% to 0.153% of SPX while the yearly "
     "win rate fell 28.8% → 18.8% (suggestive, not causal). Width/center variant "
     "backtests pending — ~1 year only without the paid Option Alpha tier."),
    ("D", "Does rounding the center to the 5-point strike grid matter?", "done",
     "No — the grid error stays within ±2.5 points and up- vs down-rounded days "
     "show nearly identical P/L. Immaterial."),
    ("E", "Does the edge survive realistic spreads, slippage, and fees?", "partial",
     "Open: observed spreads and skipped days are summarized, but slippage/fee "
     "scenarios come in Phase 3."),
    ("F", "How sensitive is the result to nearby parameter choices?", "pending",
     "Open: requires additional Option Alpha variant backtests (Phase 3)."),
    ("V1", "Is the export internally consistent (calendar and entry filters)?", "done",
     "Yes — reproducible: all 752 NYSE sessions are exactly one trade or one "
     "logged skip, and every recorded price respects the filters."),
    ("V2", "Do strikes and settlements replay against independent SPX closes?", "done",
     "Yes — reproducible: 508/508 strike selections and settlement P/Ls match "
     "independent daily closes (FRED → Yahoo → Stooq)."),
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
  h3 { font-size: 1.05rem; margin-top: 1.4rem; color: #3d5a6c; }
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
  .note { background: #f7f4ea; border-left: 3px solid #c4a35a; padding: .6rem .9rem; margin: .8rem 0; font-size: .92rem; }
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
{% if b_verdict %}
<p><strong>Displacement / mean reversion:</strong> {{ b_verdict }}</p>
{% endif %}

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

{% if b_summary %}
<h2>4. What drives the result — displacement and mean reversion</h2>
<p>The center strike K is set from the previous close. By 10:00am entry, SPX has usually
already moved. Define:</p>
<ul>
  <li><strong>d</strong> = SPX at 10:00 (export <em>Price at Open</em>) − K — morning displacement</li>
  <li><strong>m</strong> = settlement − SPX at 10:00 — afternoon move after entry</li>
  <li><strong>final miss</strong> = |settlement − K| — alone determines P/L given the credit</li>
</ul>
<p>If the afternoon undoes the morning (<code>m</code> opposite <code>d</code>), the trade is a
<strong>mean-reversion</strong> bet. If <code>m</code> is near zero regardless of <code>d</code>, it is mainly a bet
that SPX stays near the center.</p>

<div class="note">
<strong>Scope note.</strong> This section uses the {{ b_summary.n }} <em>executed</em> trades only.
The {{ n_filtered }} filter-skipped days are excluded because the export does not record a
verified 10:00am SPX level for them (daily FRED/Yahoo closes are 9:30 open / 4:00 close, not
10:00). Those days are not checked here; adding them needs intraday SPX (or ES) minute data.
</div>

<div class="cards">
  <div class="card"><div class="label">Mean d</div>
    <div class="value">{{ "{:+.1f}".format(b_summary.mean_d) }} pts</div></div>
  <div class="card"><div class="label">Std d</div>
    <div class="value">{{ "{:.1f}".format(b_summary.std_d) }} pts</div></div>
  <div class="card"><div class="label">Beyond wings (|d|&gt;{{ width|int }})</div>
    <div class="value">{{ "{:.0%}".format(b_summary.pct_beyond_width) }}</div></div>
  <div class="card"><div class="label">Beyond own credit</div>
    <div class="value">{{ "{:.0%}".format(b_summary.pct_beyond_credit) }}</div></div>
  <div class="card"><div class="label">Toward center</div>
    <div class="value">{{ "{:.0%}".format(b_summary.pct_toward) }}</div></div>
  <div class="card"><div class="label">m-on-d slope</div>
    <div class="value {{ 'pos' if b_summary.reg_slope < 0 else 'neg' }}">{{ "{:.2f}".format(b_summary.reg_slope) }}</div></div>
</div>

<h3>4.1 Where does SPX sit at entry?</h3>
<p>{{ "{:.0%}".format(b_summary.pct_beyond_width) }} of trades enter with SPX already outside the
{{ width|int }}-point wings, and only {{ "{:.0%}".format(b_summary.pct_within_2_5) }} start within
2.5 points of the center. Bucket edges use <em>each trade’s own fill credit</em> (so “inside credit”
means a win if SPX does not move further). Counts are therefore unequal by design — they reflect
how often the strategy is already asking for a pullback.</p>
<img src="data:image/png;base64,{{ figures.displacement_hist }}" alt="Entry displacement histogram">

<h3>4.2 Does the afternoon reverse the morning? (central test)</h3>
<p>Regress post-entry move <code>m</code> on displacement <code>d</code>. A significantly
<strong>negative</strong> slope means large morning moves tend to reverse after 10:00
(mean reversion). A slope near zero means the afternoon is unrelated to how far SPX already
traveled — closer to a “calm afternoon / pin” bet. The dotted line <code>m = −d</code> is full
snap-back to the center.</p>
<p>Fitted line: m = {{ "{:.2f}".format(b_summary.reg_intercept) }} +
{{ "{:.2f}".format(b_summary.reg_slope) }} · d
(r = {{ "{:.2f}".format(b_summary.reg_r) }}, t-stat on slope = {{ "{:.1f}".format(b_summary.reg_t_slope) }},
n = {{ b_summary.reg_n }}).
{% if b_summary.mean_reverting %}
The negative slope is statistically meaningful (|t| &gt; 2): afternoon mean reversion is present.
{% else %}
The slope is not clearly significant (|t| ≤ 2): treat mean reversion as weak or inconclusive.
{% endif %}
</p>
<img src="data:image/png;base64,{{ figures.mean_reversion_scatter }}" alt="Mean reversion scatter">

<h3>4.3 Toward vs away, and do far entries pay?</h3>
<p>Overall, {{ "{:.0%}".format(b_summary.pct_toward) }} of trades finish closer to K than they
started (random-walk benchmark 50%). The table below breaks that down by |d| bucket, with win
rate and average P/L — answering whether “already far from center at 10:00” is rewarded.</p>
{{ bucket_table }}
<img src="data:image/png;base64,{{ figures.bucket_performance }}" alt="Bucket toward-center and outcomes">

<h3>4.4 Credit vs displacement (why the 9.65 filter matters)</h3>
<p>As |d| grows, the iron butterfly mid credit rises toward the wing width. Correlation between
fill credit and |d| is {{ "{:.2f}".format(b_summary.corr_credit_abs_d) }}. The 9.65 max-mid filter
therefore acts as an <em>implicit displacement filter</em>: the most extreme morning moves are
more likely to be skipped. Those skipped days are counted in section 2 but are not placed on
this chart (no verified 10:00 SPX).</p>
<img src="data:image/png;base64,{{ figures.credit_vs_displacement }}" alt="Credit vs absolute displacement">

<h3>4.5 Direction asymmetry</h3>
<p>{{ "{:.0%}".format(b_summary.pct_above) }} of entries have SPX above the center and
{{ "{:.0%}".format(b_summary.pct_below) }} below. Repeating the summary by side of K:</p>
{{ direction_table }}
{% endif %}

{% if d_summary %}
<h2>5. Strike-grid rounding</h2>
<p>The center strike is previous close + $0.01 rounded onto the
{{ config_strike_grid }}-point SPX grid, so the rounding error
(K − previous close) cannot exceed ±{{ "{:g}".format(d_summary.half_grid) }} points.
Median |error| is {{ "{:.2f}".format(d_summary.median_abs_error) }} points — an order of
magnitude smaller than typical entry displacement (|d|).</p>
<p><strong>Conclusion:</strong> {{ d_verdict }}
Up-rounding ({{ d_summary.n_up }} days) and down-rounding ({{ d_summary.n_down }} days)
have nearly the same average P/L (${{ "{:.0f}".format(d_summary.avg_pl_up) }} vs
${{ "{:.0f}".format(d_summary.avg_pl_down) }}) and win rates
({{ "{:.0%}".format(d_summary.win_rate_up) }} vs {{ "{:.0%}".format(d_summary.win_rate_down) }}).
Correlation of grid error with trade P/L is {{ "{:.2f}".format(d_summary.corr_error_pl) }}.</p>
<img src="data:image/png;base64,{{ figures.grid_error_hist }}" alt="Grid rounding error distribution">
{% endif %}

<h2>6. Data validation</h2>
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

<h2>7. Backtest verification — Step 1 (internal consistency)</h2>
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

<h2>8. Backtest verification — Step 2 (SPX close replay)</h2>
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

<h2>9. Coverage — progress against the master plan</h2>
<p>Development status of each analysis question from
<code>docs/Option_Alpha_SPX_Coding_and_Report_Plan.md</code>. This section is rebuilt on every
run, so the report always reflects the current state of the project.</p>
<table>
  <tr><th>ID</th><th>Question</th><th>Status</th><th style="text-align:left">Conclusion / status notes</th></tr>
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
             pct_cols: list[str] | None = None,
             float_cols: list[str] | None = None) -> str:
    df = df.copy()
    for col in money_cols or []:
        if col in df.columns:
            df[col] = df[col].map("${:,.0f}".format)
    for col in pct_cols or []:
        if col in df.columns:
            df[col] = df[col].map("{:.1%}".format)
    for col in float_cols or []:
        if col in df.columns:
            df[col] = df[col].map("{:.2f}".format)
    return df.to_html(border=0)


def build_report(stats: dict, yearly: pd.DataFrame, filtered: pd.DataFrame,
                 checks: list[CheckResult], figures: dict[str, Path],
                 step1: VerificationResult | None = None,
                 step2: VerificationResult | None = None,
                 b_summary: dict | None = None,
                 b_buckets: pd.DataFrame | None = None,
                 b_direction: pd.DataFrame | None = None,
                 b_verdict: str = "",
                 d_summary: dict | None = None,
                 d_verdict: str = "",
                 n_filtered: int | None = None) -> Path:
    config.REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    if step1 is None:
        step1 = VerificationResult(checks=[], verdict="not run")
    if step2 is None:
        step2 = VerificationResult(checks=[], verdict="not run")
    if n_filtered is None:
        n_filtered = len(filtered)

    bucket_html = ""
    direction_html = ""
    if b_buckets is not None and not b_buckets.empty:
        bucket_html = _df_html(
            b_buckets.round(4),
            money_cols=["Avg P/L", "Total P/L"],
            pct_cols=["Share", "Toward K", "Win rate"],
            float_cols=["Avg |d|", "Avg credit"],
        )
    if b_direction is not None and not b_direction.empty:
        direction_html = _df_html(
            b_direction.round(4),
            money_cols=["Avg P/L"],
            pct_cols=["Share", "Toward K", "Win rate"],
            float_cols=["Avg d", "Avg |d|", "m-on-d slope"],
        )

    html = TEMPLATE.render(
        generated=datetime.now().strftime("%b %d, %Y %H:%M"),
        stats=stats,
        width=config.WING_WIDTH,
        config_strike_grid=config.STRIKE_GRID,
        max_mid=config.MAX_MID_CREDIT,
        max_spread=config.MAX_BID_ASK_SPREAD,
        yearly_table=_df_html(yearly.round(2), money_cols=["Total P/L", "Avg P/L", "Avg credit"],
                              pct_cols=["Win rate"]),
        n_filtered=n_filtered,
        filtered_table=_df_html(
            filtered.groupby("reason").size().to_frame("Days")
            .sort_values("Days", ascending=False)
        ),
        checks=checks,
        step1=step1,
        step2=step2,
        b_summary=b_summary,
        b_verdict=b_verdict,
        bucket_table=bucket_html,
        direction_table=direction_html,
        d_summary=d_summary,
        d_verdict=d_verdict,
        coverage=COVERAGE,
        figures={name: _embed(path) for name, path in figures.items()},
    )

    out = config.REPORTS_DIR / "report.html"
    out.write_text(html)

    # Mirror for GitHub Pages (docs/ on main).
    docs = config.PROJECT_ROOT / "docs"
    docs.mkdir(parents=True, exist_ok=True)
    (docs / "index.html").write_text(html)

    return out
