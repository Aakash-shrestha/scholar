from operator import itemgetter
from textwrap import dedent

from dotenv import load_dotenv
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableParallel
from langchain_groq import ChatGroq
from rich import print
from rich.rule import Rule

load_dotenv()

factual_model = ChatGroq(model="llama-3.3-70b-versatile", temperature=0)
creative_model = ChatGroq(model="llama-3.3-70b-versatile", temperature=0.8)

abstract = dedent("""
    Large language models (LLMs) have demonstrated remarkable capabilities on a wide
    range of tasks, but they are prone to hallucinating facts. We propose a
    retrieval-augmented generation framework that grounds model outputs in retrieved
    evidence. On three knowledge-intensive benchmarks, our method reduces hallucination
    rates by 47% while preserving fluency.
    """).strip()


# summarize
summarize = (
    ChatPromptTemplate.from_template("""Summarize the abstract in a single concise sentence:
    \n\n{abstract}""")
    | factual_model
    | StrOutputParser()
)

# Classify
classify = (
    ChatPromptTemplate.from_template("""Classify the abstract in a single domain like NLP, Computer
        Vision, etc: \n\n {abstract}""")
    | factual_model
    | StrOutputParser()
)

# objections
objections = (
    ChatPromptTemplate.from_template("""
Generate two skeptical questions that a reviewer may ask from the abstract:\n\n
{abstract}
        """)
    | creative_model
    | StrOutputParser()
)

# single parallel Runnable -> analyzer
analyzer = RunnableParallel(
    summary=summarize,
    classification=classify,
    objections=objections,
    abstract=itemgetter("abstract"),
)

analyzer_response = analyzer.invoke({"abstract": abstract})
print(f"analyzer response: {analyzer_response}")

print(Rule("[bold cyan]Summary[/bold cyan]"))
print(analyzer_response["summary"])
print(Rule("[bold cyan]Classification[/bold cyan]"))
print(analyzer_response["classification"])
print(Rule("[bold cyan]Objections[/bold cyan]"))
print(analyzer_response["objections"])

report_writer = (
    ChatPromptTemplate.from_template("""
Write a short report from the given three topics: {summary}, {classification}, and {objections} by
combining all the useful information from these topics into one.""")
    | factual_model
    | StrOutputParser()
)
full_workflow = analyzer | report_writer

# report = report_writer.invoke(
#     {
#         "summary": analyzer_response["summary"],
#         "classification": analyzer_response["classification"],
#         "objections": analyzer_response["objections"],
#     }
# )

report = full_workflow.invoke({"abstract": abstract})
print(Rule("[bold cyan]Report (from report writer)[/bold cyan]"))
print(report)
