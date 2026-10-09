"""
Tests for Click CLI evaluation command.
"""
from click.testing import CliRunner
from harness_eval.cli import main


def test_cli_evaluate_command():
    runner = CliRunner()
    result = runner.invoke(main, ["evaluate", "--baseline", "harnesses/baseline", "--candidate", "harnesses/candidate_v2"])
    assert result.exit_code == 0
    assert "AGENT HARNESS EVALUATION REPORT" in result.output
    assert "VERDICT: POSITIVE" in result.output


def test_cli_evaluate_regressive_fail_flag():
    runner = CliRunner()
    result = runner.invoke(main, [
        "evaluate",
        "--baseline", "harnesses/baseline",
        "--candidate", "harnesses/candidate_regressive",
        "--fail-on-regression",
    ])
    assert result.exit_code == 2
    assert "VERDICT: NEGATIVE" in result.output
    assert "CI Gate Triggered" in result.output
