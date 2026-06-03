import datetime
import re
from pathlib import Path

import typer
from dotenv import load_dotenv
from rich import box, print
from rich.console import Console
from rich.rule import Rule
from rich.table import Table

from scholar.corpus.db import Paper, get_engine, init_db
from scholar.corpus.repository import CorpusRepository
from scholar.evaluation.judge import Score, run_judge
from scholar.evaluation.report import ComparisonReport, compute_summary, render_markdown
from scholar.evaluation.runner import load_eval_runs, run_eval
from scholar.evaluation.schema import load_questions
from scholar.graph.graph import create_graph
from scholar.ingestion.arxiv_fetch import download_paper, enrich_chunks, fetch_arxiv_metadata
from scholar.ingestion.loader import load_and_chunk
from scholar.models import get_chat_model
from scholar.retrieval.config import RetrieverConfig
from scholar.retrieval.rag import build_rag_chain
from scholar.retrieval.vectorstore import (
    build_vectorstore,
    get_embeddings,
    load_existing_vectorstore,
)

app = typer.Typer()
load_dotenv()


@app.command()
def ask(
    question: str,
    paper: Path = typer.Option(Path("data/papers/1706.03762.pdf"), "--paper"),
    # paper is not required anymore, only keeping it for backtracking, if needed
) -> None:
    """Ask a question about a paper. Retrieves relevant context and answers with citations."""
    graph = create_graph()
    result = graph.invoke(
        {
            "question": question,
            "question_type": None,
            "retrieved_docs": [],
            "sub_questions": None,
            "sub_questions_docs": None,
            "generated_answer": None,
        }
    )
    print(Rule(f"[bold cyan]{question}[/bold cyan]"))
    print(result["generated_answer"])


@app.command()
def ingest(source: str) -> None:
    """Ingest a paper from a source (currently only arXiv is supported). This will fetch the paper's
    metadata, download the PDF, chunk it, enrich the chunks with metadata, and store the chunks in a
    persistent vectorstore for retrieval."""
    engine = get_engine()
    init_db(engine)  # initializes the db if the paper db does not already exists
    corpus_repository = CorpusRepository(engine)

    arxiv_id = re.sub(r"^arxiv:", "", source, flags=re.IGNORECASE)  # remove arxiv:
    arxiv_id = re.sub(r"v\d+$", "", arxiv_id)  # remove versioning v1..

    if corpus_repository.get(arxiv_id) is not None:
        print(f"[bold yellow]Paper {arxiv_id} already ingested. Skipping ingestion.[/bold yellow]")
        raise typer.Exit()

    paper_metadata = fetch_arxiv_metadata(arxiv_id)
    paper_path = download_paper(paper_metadata)

    chunks = load_and_chunk(paper_path)
    enriched_chunks = enrich_chunks(chunks, paper_metadata)
    persistent_dir = Path("data/chroma") / arxiv_id

    embeddings = get_embeddings()
    build_vectorstore(enriched_chunks, persistent_dir, embeddings)
    paper_record = Paper(
        arxiv_id=arxiv_id,
        title=paper_metadata.title,
        short_citation=paper_metadata.short_citation,
        year=paper_metadata.year,
        abstract=paper_metadata.abstract,
        pdf_path=str(paper_path),
        persist_dir=str(Path("data/chroma") / arxiv_id),
    )

    corpus_repository.add(paper_record)

    print(Rule(f"[bold green]Ingested {paper_metadata.arxiv_id}[/bold green]"))
    print(f"Title: {paper_metadata.title}")
    print(f"Citation: {paper_metadata.short_citation}")
    print(f"Stored at: {persistent_dir}")


@app.command(name="list")
def list_papers() -> None:
    """Show all ingested papers as a table, or a message if none exist."""
    engine = get_engine()
    init_db(engine)
    corpus_repository = CorpusRepository(engine)
    all_papers = corpus_repository.list_all()

    if not all_papers:
        print("[bold green]No paper ingested yet[/bold green]")
        return

    table = Table(title="Corpus")
    table.add_column("arxiv_id", style="cyan")
    table.add_column("title", overflow="ellipsis")
    table.add_column("citation", style="green", overflow="ellipsis")
    table.add_column("year", justify="right")

    for paper in all_papers:
        table.add_row(paper.arxiv_id, paper.title, paper.short_citation, str(paper.year))

    console = Console()
    console.print(table)


PREDEFINED_CONFIGS = {
    "baseline": RetrieverConfig(
        name="baseline",
        kind="semantic",
        k=8,
    ),
    "hybrid": RetrieverConfig(name="hybrid", kind="hybrid", weight=[0.5, 0.5]),
    "reranked": RetrieverConfig(name="reranked", kind="reranked", k=20, top_n=3, rewrite=False),
    "reranked_rewritten": RetrieverConfig(
        name="reranked_rewritten", kind="reranked", k=20, top_n=3, rewrite=True
    ),
}


@app.command(name="eval")
def run_eval_cmd(
    question_path: Path = typer.Option(Path("evaluation/questions.jsonl"), "--questions"),
    config_name: str = typer.Option("baseline", "--config"),
    output_dir: Path = typer.Option(Path("evaluation/runs/"), "--output-dir"),
) -> None:
    """Run all eval questions and save results."""
    if config_name not in PREDEFINED_CONFIGS:
        typer.echo(f"""Error: unknown config '{config_name}'. Valid options:
            {list(PREDEFINED_CONFIGS.keys())}""")
        raise typer.Exit(code=1)

    config = PREDEFINED_CONFIGS[config_name]
    questions_list = load_questions(question_path)
    timestamp = datetime.datetime.now().strftime("%Y%m%dT%H%M%S")
    output_path = output_dir / f"{config.name}_{timestamp}.jsonl"
    evaluation_result = run_eval(questions_list, config, output_path)

    console = Console()
    # summary table
    total_questions = len(questions_list)
    answered = len(evaluation_result)
    skipped = total_questions - answered
    avg_latency = int(sum(r.latency_ms for r in evaluation_result) / answered) if answered else 0
    total_latency_s = sum(r.latency_ms for r in evaluation_result) / 1000

    table = Table(title="Eval Run Summary", show_header=True, header_style="bold cyan")
    table.add_column("Metric", style="bold")
    table.add_column("Value")

    table.add_row("Config", config.name)
    table.add_row("Total questions", str(total_questions))
    table.add_row("Answered", f"[green]{answered}[/green]")
    table.add_row("Skipped (not indexed)", f"[yellow]{skipped}[/yellow]")
    table.add_row("Avg latency", f"{avg_latency} ms")
    table.add_row("Total time", f"{total_latency_s:.1f} s")
    table.add_row("Output", str(output_path))

    console.print(table)


@app.command(name="judge")
def judge(
    run_file: Path = typer.Option(
        Path("evaluation/runs/baseline_2026-05-21 16:52:49.925143.jsonl"), "--run-file"
    ),
    question_path: Path = typer.Option(Path("evaluation/questions.jsonl"), "--question-path"),
) -> None:
    eval_runs = load_eval_runs(run_file)
    model = get_chat_model(pro=False, judge=True)
    questions = load_questions(question_path)
    model_name = getattr(model, "model", "ai chat model")

    scores_dir = Path("evaluation/scores")
    scores_dir.mkdir(parents=True, exist_ok=True)
    scores_path = scores_dir / f"{run_file.stem}-scores.jsonl"

    scores = run_judge(eval_runs, questions, model, scores_path, model_name)

    count = len(scores)
    mean_faith = sum(s.faithfulness for s in scores) / count if count else 0.0
    mean_help = sum(s.helpfulness for s in scores) / count if count else 0.0

    def _score_style(val: float) -> str:
        if val >= 4.0:
            return "bold green"
        elif val >= 3.0:
            return "bold yellow"
        return "bold red"

    console = Console()
    console.print()
    console.print(Rule("[bold magenta] ✦  Judge Results  ✦ [/bold magenta]", style="magenta"))
    console.print()

    table = Table(
        show_header=True,
        header_style="bold cyan",
        box=box.ROUNDED,
        border_style="bright_black",
        padding=(0, 2),
    )
    table.add_column("Metric", style="bold white", min_width=22)
    table.add_column("Value", justify="center", min_width=16)

    table.add_row("Runs scored", f"[bold white]{count}[/bold white]")
    table.add_row(
        "Mean faithfulness",
        f"[{_score_style(mean_faith)}]{mean_faith:.2f} / 5.00[/{_score_style(mean_faith)}]",
    )
    table.add_row(
        "Mean helpfulness",
        f"[{_score_style(mean_help)}]{mean_help:.2f} / 5.00[/{_score_style(mean_help)}]",
    )

    console.print(table)
    console.print()
    console.print(Rule(style="bright_black"))


@app.command(name="report")
def report(
    scores: list[Path] = typer.Option(
        ...,  # required field
        "--scores",
        help="One or more score JSONL files",
    ),
    output: Path = typer.Option(
        Path("evaluation/report.md"),
        "--output",
    ),
) -> None:
    """Generate a comparison report from  one or more score files."""
    all_scores: list[Score] = []
    for score_path in scores:
        with open(score_path) as f:
            for line in f:
                line = line.strip()
                if line:
                    all_scores.append(Score.model_validate_json(line))

    if not all_scores:
        typer.echo("No scores found in provided files.", err=True)
        raise typer.Exit(code=1)

    configs_by_name: dict[str, list[Score]] = {}
    for s in all_scores:
        configs_by_name.setdefault(s.config_name, []).append(s)

    summaries = [compute_summary(group) for group in configs_by_name.values()]

    report_obj = ComparisonReport(
        generated_at=datetime.datetime.now(),
        configs=summaries,
        total_questions=max(len(g) for g in configs_by_name.values()),
    )

    markdown = render_markdown(report_obj)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(markdown)
    typer.echo(f"Report written to {output}")
