from langchain_core.language_models import BaseChatModel
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate


def rewrite_query(query: str, model: BaseChatModel) -> str:
    prompt = """You are rewriting user questions to retrieve relevant passages \
    from academic papers about machine learning and AI.

    Your job: produce ONE rewritten query that is more likely to match the language \
    used in academic papers, while preserving the exact intent and scope of the original.

    Rules:
    - Add precise technical terms that an ML/AI paper would use (e.g., "BLEU" instead of \
    "translation score", "fine-tuning" instead of "adapting", "attention heads" instead of \
    "attention pieces").
    - Keep the question's intent unchanged. If the original asks about X, the rewritten \
    query must still ask about X — not X and Y.
    - Keep the question's scope unchanged. Do not narrow it to a specific paper, model, or \
    year unless the original did.
    - If the original is already technical and precise, return it unchanged.
    - Output the rewritten query only. No preamble, no explanation, no quotes.

    Examples:

    Original: What is MHA?
    Rewritten: What is multi-head attention in the Transformer architecture?

    Original: How was GPT-3 trained?
    Rewritten: What is the pre-training procedure and training data for GPT-3?

    Original: Why is it faster?
    Rewritten: Why is the Transformer faster to train than recurrent architectures?

    Original: What dropout rate does the Transformer use?
    Rewritten: What dropout rate does the Transformer use?

    Now rewrite this query:

    Original: {query}
    Rewritten:"""

    chain = ChatPromptTemplate.from_template(prompt) | model | StrOutputParser()
    return chain.invoke({"query": query})
