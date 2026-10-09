"""
Interactive standalone HTML report generator for harness evaluation results.
"""
from __future__ import annotations

import json
from harness_eval.models import EvaluationReport, TaskStatus, Verdict


def generate_html_report(report: EvaluationReport) -> str:
    """
    Produces a self-contained, responsive HTML dashboard for the evaluation run.
    """
    verdict_badge_class = (
        "badge-positive" if report.verdict == Verdict.POSITIVE
        else "badge-negative" if report.verdict == Verdict.NEGATIVE
        else "badge-inconclusive"
    )

    reasons_html = "".join(f"<li>{r}</li>" for r in report.verdict_reasons)
    recommendations_html = "".join(f"<li>{rec}</li>" for rec in report.recommendations)

    task_rows_html = []
    task_cards_html = []

    for cmp in report.task_comparisons:
        status_badge = (
            '<span class="badge badge-success">IMPROVED</span>' if cmp.status == TaskStatus.IMPROVED
            else '<span class="badge badge-danger">REGRESSED</span>' if cmp.status == TaskStatus.REGRESSED
            else '<span class="badge badge-warning">MIXED</span>' if cmp.status == TaskStatus.MIXED
            else '<span class="badge badge-neutral">UNCHANGED</span>'
        )

        f_delta_color = "positive" if cmp.delta_functional > 0 else "negative" if cmp.delta_functional < 0 else "neutral"
        c_delta_color = "positive" if cmp.delta_convention > 0 else "negative" if cmp.delta_convention < 0 else "neutral"
        s_delta_color = "positive" if cmp.delta_fulfillment > 0 else "negative" if cmp.delta_fulfillment < 0 else "neutral"

        task_rows_html.append(f"""
        <tr>
            <td style="font-weight: 600;"><code>{cmp.task_id}</code></td>
            <td>{status_badge}</td>
            <td class="{f_delta_color}">{cmp.delta_functional*100:+.1f}%</td>
            <td class="{c_delta_color}">{cmp.delta_convention*100:+.1f}%</td>
            <td class="{s_delta_color}">{cmp.delta_fulfillment*100:+.1f}%</td>
            <td>{cmp.delta_total_tokens:+,}</td>
            <td style="font-size: 0.9rem; color: var(--text-muted);">{cmp.change_summary}</td>
        </tr>
        """)

        # Detailed card for each task
        evidence_items = "".join(f"<li>{note}</li>" for note in cmp.evidence_notes)
        violations_cand = "".join(f"<li><code>{v}</code></li>" for v in cmp.candidate.convention_violations) or "<li>None (Fully compliant)</li>"

        task_cards_html.append(f"""
        <div class="task-card">
            <div class="task-card-header">
                <h3><code>{cmp.task_id}</code>: {cmp.task_title}</h3>
                {status_badge}
            </div>
            <div class="task-card-grid">
                <div class="metric-box">
                    <span class="label">Tests (Pass/Total)</span>
                    <span class="val">Base: {cmp.baseline.tests_passed}/{cmp.baseline.tests_total} &rarr; Cand: {cmp.candidate.tests_passed}/{cmp.candidate.tests_total}</span>
                </div>
                <div class="metric-box">
                    <span class="label">Convention Compliance</span>
                    <span class="val">Base: {cmp.baseline.convention_score*100:.0f}% &rarr; Cand: {cmp.candidate.convention_score*100:.0f}%</span>
                </div>
                <div class="metric-box">
                    <span class="label">Spec Fulfillment</span>
                    <span class="val">Base: {cmp.baseline.fulfillment_score*100:.0f}% &rarr; Cand: {cmp.candidate.fulfillment_score*100:.0f}%</span>
                </div>
                <div class="metric-box">
                    <span class="label">Tokens & Cost</span>
                    <span class="val">{cmp.baseline.total_tokens:,} &rarr; {cmp.candidate.total_tokens:,} (${cmp.candidate.estimated_cost_usd:.4f})</span>
                </div>
            </div>
            <div class="evidence-section">
                <h4>Observed Deltas:</h4>
                <ul>{evidence_items}</ul>
                <h4>Candidate Violations:</h4>
                <ul>{violations_cand}</ul>
            </div>
        </div>
        """)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Agent Harness Evaluation: {report.candidate_name}</title>
    <style>
        :root {{
            --bg: #0f172a;
            --surface: #1e293b;
            --surface-hover: #334155;
            --border: #334155;
            --text: #f8fafc;
            --text-muted: #94a3b8;
            --primary: #38bdf8;
            --success: #10b981;
            --danger: #ef4444;
            --warning: #f59e0b;
        }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            background: var(--bg);
            color: var(--text);
            padding: 2rem;
            line-height: 1.6;
        }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid var(--border);
            padding-bottom: 1.5rem;
            margin-bottom: 2rem;
        }}
        h1 {{ font-size: 1.75rem; font-weight: 700; color: #fff; }}
        .meta {{ color: var(--text-muted); font-size: 0.9rem; margin-top: 0.25rem; }}
        
        .verdict-banner {{
            background: var(--surface);
            border-radius: 12px;
            padding: 1.5rem 2rem;
            margin-bottom: 2rem;
            border-left: 6px solid;
        }}
        .verdict-banner.badge-positive {{ border-left-color: var(--success); }}
        .verdict-banner.badge-negative {{ border-left-color: var(--danger); }}
        .verdict-banner.badge-inconclusive {{ border-left-color: var(--warning); }}

        .verdict-title {{
            display: flex;
            align-items: center;
            gap: 1rem;
            font-size: 1.4rem;
            font-weight: 700;
            margin-bottom: 0.5rem;
        }}
        .verdict-badge {{
            padding: 0.25rem 0.75rem;
            border-radius: 6px;
            font-size: 0.85rem;
            text-transform: uppercase;
            font-weight: 800;
            letter-spacing: 0.05em;
        }}
        .badge-positive .verdict-badge {{ background: var(--success); color: #fff; }}
        .badge-negative .verdict-badge {{ background: var(--danger); color: #fff; }}
        .badge-inconclusive .verdict-badge {{ background: var(--warning); color: #000; }}

        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 1rem;
            margin-bottom: 2rem;
        }}
        .stat-card {{
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 10px;
            padding: 1.25rem;
        }}
        .stat-label {{ color: var(--text-muted); font-size: 0.85rem; text-transform: uppercase; letter-spacing: 0.05em; }}
        .stat-value {{ font-size: 1.8rem; font-weight: 700; margin: 0.25rem 0; }}
        .stat-sub {{ font-size: 0.85rem; color: var(--text-muted); }}

        .positive {{ color: var(--success); font-weight: 600; }}
        .negative {{ color: var(--danger); font-weight: 600; }}
        .neutral {{ color: var(--text-muted); }}

        table {{
            width: 100%;
            border-collapse: collapse;
            background: var(--surface);
            border-radius: 10px;
            overflow: hidden;
            margin-bottom: 2.5rem;
            border: 1px solid var(--border);
        }}
        th, td {{
            padding: 1rem 1.25rem;
            text-align: left;
            border-bottom: 1px solid var(--border);
        }}
        th {{ background: #182234; font-size: 0.85rem; text-transform: uppercase; letter-spacing: 0.05em; color: var(--text-muted); }}
        tr:hover td {{ background: var(--surface-hover); }}

        .badge {{
            display: inline-block;
            padding: 0.2rem 0.5rem;
            border-radius: 4px;
            font-size: 0.75rem;
            font-weight: 700;
        }}
        .badge-success {{ background: rgba(16, 185, 129, 0.2); color: #34d399; border: 1px solid #059669; }}
        .badge-danger {{ background: rgba(239, 68, 68, 0.2); color: #f87171; border: 1px solid #dc2626; }}
        .badge-warning {{ background: rgba(245, 158, 11, 0.2); color: #fbbf24; border: 1px solid #d97706; }}
        .badge-neutral {{ background: rgba(148, 163, 184, 0.2); color: #cbd5e1; border: 1px solid #64748b; }}

        .section-title {{ font-size: 1.3rem; margin-bottom: 1rem; color: var(--primary); }}
        
        .task-card {{
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 10px;
            padding: 1.5rem;
            margin-bottom: 1.25rem;
        }}
        .task-card-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 1rem;
        }}
        .task-card-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 0.75rem;
            background: #151e2e;
            padding: 1rem;
            border-radius: 8px;
            margin-bottom: 1rem;
        }}
        .metric-box .label {{ display: block; font-size: 0.75rem; color: var(--text-muted); }}
        .metric-box .val {{ font-size: 0.95rem; font-weight: 600; }}

        .evidence-section h4 {{ font-size: 0.9rem; color: var(--text-muted); margin-top: 0.75rem; margin-bottom: 0.25rem; }}
        .evidence-section ul {{ padding-left: 1.25rem; font-size: 0.9rem; }}
        .evidence-section li {{ margin-bottom: 0.25rem; }}

        .recs-box {{
            background: #1e1b4b;
            border: 1px solid #4338ca;
            border-radius: 10px;
            padding: 1.5rem;
            margin-bottom: 2rem;
        }}
        .recs-box h3 {{ color: #a5b4fc; margin-bottom: 0.75rem; }}
        .recs-box ul {{ padding-left: 1.5rem; }}
        .recs-box li {{ margin-bottom: 0.4rem; }}
        code {{ background: #0b1120; padding: 0.2rem 0.4rem; border-radius: 4px; font-family: monospace; font-size: 0.9em; }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div>
                <h1>Agent Harness Evaluation Report</h1>
                <div class="meta">Comparing <strong>{report.baseline_name}</strong> &rarr; <strong>{report.candidate_name}</strong> | Evaluated at {report.timestamp}</div>
            </div>
        </header>

        <div class="verdict-banner {verdict_badge_class}">
            <div class="verdict-title">
                <span class="verdict-badge">{report.verdict.value}</span>
                <span>{report.verdict_summary}</span>
            </div>
            <ul style="margin-top: 0.75rem; padding-left: 1.5rem; font-size: 0.95rem;">
                {reasons_html}
            </ul>
        </div>

        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-label">Net Quality Impact</div>
                <div class="stat-value {'positive' if report.net_quality_delta > 0 else 'negative'}">{report.net_quality_delta:+.1f} pts</div>
                <div class="stat-sub">Across {report.total_tasks} benchmark tasks</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Functional Tests</div>
                <div class="stat-value {'positive' if report.net_functional_delta > 0 else 'negative' if report.net_functional_delta < 0 else 'neutral'}">{report.net_functional_delta*100:+.1f}%</div>
                <div class="stat-sub">{report.baseline_avg_functional*100:.1f}% &rarr; {report.candidate_avg_functional*100:.1f}% pass rate</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Team Conventions</div>
                <div class="stat-value {'positive' if report.net_convention_delta > 0 else 'negative' if report.net_convention_delta < 0 else 'neutral'}">{report.net_convention_delta*100:+.1f}%</div>
                <div class="stat-sub">{report.baseline_avg_convention*100:.1f}% &rarr; {report.candidate_avg_convention*100:.1f}% compliance</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Token & Cost Variance</div>
                <div class="stat-value {'positive' if report.net_cost_pct_change <= 0 else 'neutral'}">{report.net_cost_pct_change:+.1f}%</div>
                <div class="stat-sub">${report.baseline_total_cost_usd:.4f} &rarr; ${report.candidate_total_cost_usd:.4f} total</div>
            </div>
        </div>

        <div class="recs-box">
            <h3>Recommendations for Harness Maintainer</h3>
            <ul>{recommendations_html}</ul>
        </div>

        <h2 class="section-title">Comparative Task Matrix</h2>
        <table>
            <thead>
                <tr>
                    <th>Task ID</th>
                    <th>Status</th>
                    <th>Functional &Delta;</th>
                    <th>Convention &Delta;</th>
                    <th>Spec &Delta;</th>
                    <th>Tokens &Delta;</th>
                    <th>Summary</th>
                </tr>
            </thead>
            <tbody>
                {''.join(task_rows_html)}
            </tbody>
        </table>

        <h2 class="section-title">Task Drilldown & Evidence</h2>
        {''.join(task_cards_html)}
    </div>
</body>
</html>
"""
