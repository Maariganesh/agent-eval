"""
CLI entry point for the agent harness evaluation tool.
Provides the 'evaluate' command to test baseline vs candidate harnesses.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
import click
from rich.console import Console

from harness_eval.engine import EvaluationEngine
from harness_eval.models import Verdict
from harness_eval.reporting.console import print_console_report
from harness_eval.reporting.html import generate_html_report
from harness_eval.reporting.markdown import generate_markdown_report
from harness_eval.runner import LiveLLMRunner, OfflineFixtureRunner

console = Console()


def _ensure_subcommand() -> None:
    if len(sys.argv) > 1 and sys.argv[1].startswith("-") and sys.argv[1] not in ["--help", "-h"]:
        sys.argv.insert(1, "evaluate")
    elif len(sys.argv) == 1:
        sys.argv.append("evaluate")


@click.group(invoke_without_command=True)
@click.pass_context
def main(ctx: click.Context) -> None:
    """Agent Harness Evaluation CLI: Rigorous quality & cost evaluation for coding agents."""
    _ensure_subcommand()
    if ctx.invoked_subcommand is None:
        ctx.invoke(evaluate)


@main.command(name="evaluate")
@click.option(
    "--baseline",
    "-b",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    default=Path("harnesses/baseline"),
    help="Directory containing baseline harness (AGENTS.md, rules, skills).",
    show_default=True,
)
@click.option(
    "--candidate",
    "-c",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    default=Path("harnesses/candidate_v2"),
    help="Directory containing candidate harness to evaluate.",
    show_default=True,
)
@click.option(
    "--tasks",
    "-t",
    type=click.Path(exists=True, file_okay=True, dir_okay=True, path_type=Path),
    default=Path("benchmarks/tasks.yaml"),
    help="Path to tasks.yaml benchmark file or benchmark folder.",
    show_default=True,
)
@click.option(
    "--fixtures",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    default=Path("fixtures"),
    help="Path to offline deterministic evaluation fixtures.",
    show_default=True,
)
@click.option(
    "--live",
    is_flag=True,
    default=False,
    help="Execute live LLM calls instead of deterministic offline fixtures.",
)
@click.option(
    "--model",
    type=str,
    default="gpt-4o",
    help="Model identifier if running in --live mode.",
    show_default=True,
)
@click.option(
    "--report-html",
    type=click.Path(path_type=Path),
    default=Path("reports/eval_report.html"),
    help="Output file path for interactive HTML dashboard.",
    show_default=True,
)
@click.option(
    "--report-md",
    type=click.Path(path_type=Path),
    default=Path("reports/eval_report.md"),
    help="Output file path for Markdown report.",
    show_default=True,
)
@click.option(
    "--report-json",
    type=click.Path(path_type=Path),
    default=Path("reports/eval_report.json"),
    help="Output file path for machine-readable JSON data.",
    show_default=True,
)
@click.option(
    "--fail-on-regression",
    is_flag=True,
    default=False,
    help="Exit with non-zero status if evaluation verdict is NEGATIVE (for CI/CD gates).",
)
def evaluate(
    baseline: Path,
    candidate: Path,
    tasks: Path,
    fixtures: Path,
    live: bool,
    model: str,
    report_html: Path,
    report_md: Path,
    report_json: Path,
    fail_on_regression: bool,
) -> None:
    """
    Run comparative evaluation between baseline and candidate harnesses.
    Produces evidence-based reports showing whether the harness change is positive or negative.
    """
    console.print(f"[bold cyan]Initiating Harness Evaluation Pipeline...[/bold cyan]")
    console.print(f"* Baseline Harness:  [yellow]{baseline}[/yellow]")
    console.print(f"* Candidate Harness: [yellow]{candidate}[/yellow]")
    console.print(f"* Benchmark Tasks:   [yellow]{tasks}[/yellow]")
    console.print(f"* Execution Mode:    [green]{'Live LLM (' + model + ')' if live else 'Deterministic Offline Replay'}[/green]\n")

    # Select Runner
    if live:
        runner = LiveLLMRunner(model=model)
    else:
        runner = OfflineFixtureRunner(fixtures_dir=fixtures)

    engine = EvaluationEngine(runner=runner, fixtures_dir=fixtures)

    try:
        base_harness = engine.load_harness_from_dir(baseline)
        cand_harness = engine.load_harness_from_dir(candidate)
        eval_tasks = engine.load_tasks_from_dir(tasks)
    except Exception as e:
        console.print(f"[bold red]Configuration error: {e}[/bold red]")
        sys.exit(1)

    if not eval_tasks:
        console.print(f"[bold red]No evaluation tasks found at {tasks}[/bold red]")
        sys.exit(1)

    with console.status("[bold green]Executing tasks and evaluating multidimensional criteria..."):
        report = engine.evaluate(base_harness, cand_harness, eval_tasks)

    # 1. Print Rich Terminal Report
    print_console_report(report, console=console)

    # 2. Write HTML Report
    if report_html:
        report_html.parent.mkdir(parents=True, exist_ok=True)
        html_content = generate_html_report(report)
        report_html.write_text(html_content, encoding="utf-8")
        console.print(f"[dim]Saved HTML dashboard to: [bold]{report_html}[/bold][/dim]")

    # 3. Write Markdown Report
    if report_md:
        report_md.parent.mkdir(parents=True, exist_ok=True)
        md_content = generate_markdown_report(report)
        report_md.write_text(md_content, encoding="utf-8")
        console.print(f"[dim]Saved Markdown report to: [bold]{report_md}[/bold][/dim]")

    # 4. Write JSON Report
    if report_json:
        report_json.parent.mkdir(parents=True, exist_ok=True)
        report_json.write_text(report.model_dump_json(indent=2), encoding="utf-8")
        console.print(f"[dim]Saved JSON data to: [bold]{report_json}[/bold][/dim]\n")

    # CI/CD Gate
    if fail_on_regression and report.verdict == Verdict.NEGATIVE:
        console.print("[bold red]CI Gate Triggered: Harness change rejected due to negative impact.[/bold red]")
        sys.exit(2)


if __name__ == "__main__":
    main()
