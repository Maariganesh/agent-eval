"""
Rich terminal reporter: prints structured evaluation tables, verdicts,
deltas, and regression warnings.
"""
from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from harness_eval.models import EvaluationReport, TaskStatus, Verdict


def print_console_report(report: EvaluationReport, console: Console | None = None) -> None:
    """
    Renders a comprehensive terminal report using Rich.
    """
    console = console or Console()

    # 1. Header Banner
    console.print("\n")
    header_text = Text()
    header_text.append("AGENT HARNESS EVALUATION REPORT\n", style="bold cyan")
    header_text.append(f"Baseline: {report.baseline_name}  vs  Candidate: {report.candidate_name}\n", style="dim")
    header_text.append(f"Timestamp: {report.timestamp} | Total Tasks: {report.total_tasks}", style="dim")
    console.print(Panel(header_text, border_style="cyan"))

    # 2. Main Verdict Panel
    verdict_color = (
        "bold green" if report.verdict == Verdict.POSITIVE
        else "bold red" if report.verdict == Verdict.NEGATIVE
        else "bold yellow"
    )
    border_color = (
        "green" if report.verdict == Verdict.POSITIVE
        else "red" if report.verdict == Verdict.NEGATIVE
        else "yellow"
    )
    verdict_badge = f"[{verdict_color}]VERDICT: {report.verdict.value}[/{verdict_color}]"
    
    body = f"{verdict_badge}\n\n[bold]{report.verdict_summary}[/bold]\n"
    if report.verdict_reasons:
        body += "\n[underline]Key Evidence & Reasoning:[/underline]\n"
        for r in report.verdict_reasons:
            prefix = "* "
            if "GUARDRAIL VIOLATED" in r or "REGRESSION" in r:
                body += f"  [bold red]{prefix}{r}[/bold red]\n"
            elif "improved" in r.lower():
                body += f"  [green]{prefix}{r}[/green]\n"
            else:
                body += f"  [yellow]{prefix}{r}[/yellow]\n"

    console.print(Panel(body, title="Executive Summary", border_style=border_color))

    # 3. High-level Metrics Summary Table
    table = Table(title="Dimensional Quality & Efficiency Metrics", header_style="bold blue")
    table.add_column("Evaluation Dimension", style="bold")
    table.add_column(f"Baseline ({report.baseline_name})", justify="center")
    table.add_column(f"Candidate ({report.candidate_name})", justify="center")
    table.add_column("Net Delta (Impact)", justify="center")

    def _delta_str(delta: float, is_pct: bool = True, invert: bool = False) -> str:
        if delta == 0:
            return "[dim]0.0%[/dim]" if is_pct else "[dim]0.0[/dim]"
        positive = (delta < 0) if invert else (delta > 0)
        color = "green" if positive else "red"
        symbol = "+" if delta > 0 else ""
        unit = "%" if is_pct else ""
        return f"[{color}]{symbol}{delta*100:.1f}{unit}[/{color}]" if is_pct else f"[{color}]{symbol}{delta:.3f}[/{color}]"

    table.add_row(
        "1. Functional Correctness (Tests)",
        f"{report.baseline_avg_functional*100:.1f}%",
        f"{report.candidate_avg_functional*100:.1f}%",
        _delta_str(report.net_functional_delta),
    )
    table.add_row(
        "2. Team Convention Compliance",
        f"{report.baseline_avg_convention*100:.1f}%",
        f"{report.candidate_avg_convention*100:.1f}%",
        _delta_str(report.net_convention_delta),
    )
    table.add_row(
        "3. Business Spec Fulfillment",
        f"{report.baseline_avg_fulfillment*100:.1f}%",
        f"{report.candidate_avg_fulfillment*100:.1f}%",
        _delta_str(report.net_fulfillment_delta),
    )
    table.add_row(
        "Net Quality Impact Score",
        "-",
        "-",
        f"[{'bold green' if report.net_quality_delta > 0 else 'bold red'}]{report.net_quality_delta:+.1f} pts[/{'bold green' if report.net_quality_delta > 0 else 'bold red'}]",
    )
    table.add_row(
        "4. Token Usage & Cost",
        f"{report.baseline_total_tokens:,} toks (${report.baseline_total_cost_usd:.4f})",
        f"{report.candidate_total_tokens:,} toks (${report.candidate_total_cost_usd:.4f})",
        f"[{'green' if report.net_cost_pct_change <= 0 else 'yellow'}]{report.net_cost_pct_change:+.1f}% toks[/{'green' if report.net_cost_pct_change <= 0 else 'yellow'}]",
    )
    console.print(table)

    # 4. Task Breakdown Table
    task_table = Table(title="Task-by-Task Comparison Matrix", header_style="bold magenta")
    task_table.add_column("Task ID", style="cyan")
    task_table.add_column("Status", justify="center")
    task_table.add_column("Func Delta", justify="center")
    task_table.add_column("Conv Delta", justify="center")
    task_table.add_column("Spec Delta", justify="center")
    task_table.add_column("Tokens Delta", justify="center")
    task_table.add_column("Summary")

    for cmp in report.task_comparisons:
        status_style = (
            "[bold green]IMPROVED[/bold green]" if cmp.status == TaskStatus.IMPROVED
            else "[bold red]REGRESSED[/bold red]" if cmp.status == TaskStatus.REGRESSED
            else "[bold yellow]MIXED[/bold yellow]" if cmp.status == TaskStatus.MIXED
            else "[dim]UNCHANGED[/dim]"
        )
        task_table.add_row(
            cmp.task_id,
            status_style,
            _delta_str(cmp.delta_functional),
            _delta_str(cmp.delta_convention),
            _delta_str(cmp.delta_fulfillment),
            f"{cmp.delta_total_tokens:+,}",
            cmp.change_summary,
        )
    console.print(task_table)

    # 5. Recommendations Panel
    if report.recommendations:
        recs_text = "\n".join(f"  [cyan]->[/cyan] {rec}" for rec in report.recommendations)
        console.print(Panel(recs_text, title="Actionable Harness Recommendations", border_style="blue"))
    console.print("\n")
