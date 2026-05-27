import datetime
import statistics

from pydantic import BaseModel

from scholar.evaluation.judge import Score


class ConfigSummary(BaseModel):
    """Aggregated metrics for one scoring run"""

    config_name: str
    n: int
    mean_faithfulness: float
    std_faithfulness: float
    min_faithfulness: int
    max_faithfulness: int
    mean_helpfulness: float
    std_helpfulness: float
    min_helpfulness: int
    max_helpfulness: int


class ComparisonReport(BaseModel):
    """Multi-config evaluation report"""

    generated_at: datetime.datetime
    configs: list[ConfigSummary]
    total_questions: int  # max(n) across all configs, tentative


def compute_summary(scores: list[Score]) -> ConfigSummary:
    """compute one aggregated summary for a specific config"""
    if not scores:
        raise ValueError("Cannot compute summary for empty scores list")

    config_names = {s.config_name for s in scores}

    if len(config_names) != 1:
        raise ValueError(f"Expected scores for one config, got multiple: {config_names}")

    config_name = config_names.pop()
    faithfulness_scores = [f.faithfulness for f in scores]
    helpfulness_scores = [h.helpfulness for h in scores]

    return ConfigSummary(
        config_name=config_name,
        n=len(scores),
        mean_faithfulness=float(statistics.mean(faithfulness_scores)),
        std_faithfulness=float(statistics.stdev(faithfulness_scores))
        if len(faithfulness_scores) > 1
        else 0.0,
        min_faithfulness=int(min(faithfulness_scores)),
        max_faithfulness=int(max(faithfulness_scores)),
        mean_helpfulness=float(statistics.mean(helpfulness_scores)),
        std_helpfulness=float(statistics.stdev(helpfulness_scores))
        if len(helpfulness_scores) > 1
        else 0.0,
        min_helpfulness=int(min(helpfulness_scores)),
        max_helpfulness=int(max(helpfulness_scores)),
    )


def render_markdown(report: ComparisonReport) -> str:
    """formats the comparision report into markdown structured fomrat"""

    lines = [
        "# Scholar Evaluation Report",
        "",
        f"Generated: {report.generated_at.isoformat(timespec='seconds')}",
        f"Total Questions: {report.total_questions}",
        "",
        "## Summary",
        "",
        "| Configuration | n | Faithfulness | Helpfulness |",
        "|---------------|---|--------------|-------------|",
    ]

    for cfg in report.configs:
        faithfulness = f"{cfg.mean_faithfulness:.2f} ± {cfg.std_faithfulness:.2f} ({cfg.min_faithfulness}–{cfg.max_faithfulness})"
        helpfulness = f"{cfg.mean_helpfulness:.2f} ± {cfg.std_helpfulness:.2f} ({cfg.min_helpfulness}–{cfg.max_helpfulness})"
        lines.append(f"| {cfg.config_name} | {cfg.n} | {faithfulness} | {helpfulness} |")

    notes = [
        "",
        "## Notes",
        "",
        "Scores produced by `llama-3.3-70b-versatile` as judge with structured output.",
        "Context passed to judge was the first 200 chars of each retrieved chunk.",
    ]
    lines.extend(notes)

    return "\n".join(lines)
