from functools import partial

from langgraph.graph import END, START, StateGraph

from scholar.evaluation.schema import QuestionType
from scholar.graph.nodes import (
    classify_node,
    decompose_node,
    find_relevant_paper_node,
    generate_node,
    retrieve_baseline_node,
    retrieve_hybrid_node,
    retrieve_multi_node,
)
from scholar.graph.state import ScholarState
from scholar.retrieval.vectorstore import get_embeddings, load_all_vectorstore


def route_question(state: ScholarState) -> str:
    if state["question_type"] == QuestionType.FACTUAL:
        return "retrieve_hybrid"
    elif state["question_type"] == QuestionType.SYNTHESIS:
        return "decompose"
    else:
        return "retrieve_baseline"


def create_graph():
    graph = StateGraph(ScholarState)

    # load all the stores
    stores, chunks = load_all_vectorstore()

    # get embeddings
    embeddings = get_embeddings()
    # add alll the node in the graphsss
    graph.add_node("classify", classify_node)
    graph.add_node(
        "relevant_papers",
        partial(find_relevant_paper_node, stores=stores, embeddings=embeddings),
    )
    graph.add_node("retrieve_baseline", partial(retrieve_baseline_node, stores=stores))
    graph.add_node("retrieve_hybrid", partial(retrieve_hybrid_node, stores=stores, chunks=chunks))
    graph.add_node("decompose", decompose_node)
    graph.add_node("retrieve_multi", partial(retrieve_multi_node, stores=stores))
    graph.add_node("generate", generate_node)

    # edges
    graph.add_edge(START, "classify")
    graph.add_edge("classify", "relevant_papers")
    graph.add_edge("retrieve_baseline", "generate")
    graph.add_edge("retrieve_hybrid", "generate")
    graph.add_edge("decompose", "retrieve_multi")
    graph.add_edge("retrieve_multi", "generate")
    graph.add_edge("generate", END)
    graph.add_conditional_edges("relevant_papers", route_question)

    return graph.compile()
