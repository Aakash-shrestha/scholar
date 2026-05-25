import datetime
from pathlib import Path
from textwrap import dedent
from typing import cast

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.prompts.chat import ChatPromptTemplate
from langchain_groq.chat_models import ChatGroq
from pydantic import BaseModel, Field

from scholar.evaluation.runner import EvalRun
from scholar.evaluation.schema import EvalQuestion


class Score(BaseModel):
    """
    scoring format of llm as judge
    """

    question_id: str
    config_name: str  # baseline for now

    faithfulness: int = Field(ge=1, le=5)  # 1-5 scale
    faithfulness_reasoning: str

    helpfulness: int = Field(ge=1, le=5)  # 1-5 scale
    helpfulness_reasoning: str

    judge_model: str  # llama 3.3 70b for now
    timestamp: datetime.datetime


class JudgeOutput(BaseModel):
    """
    output format of the llm as judge
    """

    faithfulness_score: int = Field(ge=1, le=5)  # 1-5 scale
    faithfulness_reasoning: str
    helpfulness_score: int = Field(ge=1, le=5)  # 1-5 scale
    helpfulness_reasoning: str


def build_judge_prompt(
    question, context_chunks, reference_answer, generated_answer
) -> ChatPromptTemplate:
    """
    build prompt for ingesting to the llm as judge function, using ChatPromptTempate
    """
    prompt = ChatPromptTemplate.from_template(
        dedent("""
            You are evaluating a research assistant's answer to a question.

            Question: {question}

            Retrieved context the assistant could use:
            {context_chunks}

            Reference answer (the gold standard):
            {reference_answer}

            Assistant's answer:
            {generated_answer}

            Score the assistant's answer on two dimensions, each 1-5:

            FAITHFULNESS: Does the assistant's answer only state things supported by the
            retrieved context? (1 = makes claims not in the context; 5 = every claim
            is grounded in the context)

            HELPFULNESS: Does the assistant's answer correctly and completely address
            the question, considering the reference answer? (1 = wrong or misses the
            point; 5 = matches or exceeds the reference)

            Provide your scores AND a one-sentence reasoning for each.
        """).strip()
    )

    return prompt


def judge_one(
    eval_run: EvalRun, eval_question: EvalQuestion, model: BaseChatModel, model_name: str
) -> Score:
    """
    Use the provided model to judge the given eval_run and eval_question, returning a Score object.
    """
    context = "\n\n".join(c.text_preview for c in eval_run.retrieved_chunks)  # only first 200 chars
    # preview for now

    prompt_input = {
        "question": eval_question.question,
        "context_chunks": context,
        "reference_answer": eval_question.reference_answer,
        "generated_answer": eval_run.generated_answer,
    }

    prompt: ChatPromptTemplate = build_judge_prompt(
        prompt_input["question"],
        prompt_input["context_chunks"],
        prompt_input["reference_answer"],
        prompt_input["generated_answer"],
    )

    judge_model = model.with_structured_output(JudgeOutput)

    response = judge_model.invoke(prompt.format_messages(**prompt_input))
    response = cast(JudgeOutput, response)

    return Score(
        question_id=eval_question.id,
        config_name=eval_run.config_name,
        faithfulness=response.faithfulness_score,
        faithfulness_reasoning=response.faithfulness_reasoning,
        helpfulness=response.helpfulness_score,
        helpfulness_reasoning=response.helpfulness_reasoning,
        judge_model=model_name,
        timestamp=datetime.datetime.now(),
    )


def run_judge(
    eval_runs: list[EvalRun],
    questions: list[EvalQuestion],
    model: BaseChatModel,
    output_path: Path,
    model_name: str,
) -> list[Score]:
    """
    Run the judge function on a list of eval_runs and questions, saving results to output_path.
    """
    question_by_id = {q.id: q for q in questions}
    scores = []
    for eval_run in eval_runs:
        question = question_by_id.get(eval_run.question_id)
        if question is None:
            print(f"[{eval_run.question_id}] no matching question, skipping")
            continue
        score: Score = judge_one(eval_run, question, model, model_name)
        scores.append(score)

    with open(output_path, "w") as f:
        for score in scores:
            f.write(score.model_dump_json() + "\n")

    return scores
