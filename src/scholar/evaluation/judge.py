import datetime
import json
import time
from pathlib import Path
from textwrap import dedent

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts.chat import ChatPromptTemplate
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
            Respond ONLY with a JSON object with keys: faithfulness_score, faithfulness_reasoning,
            helpfulness_score, helpfulness_reasoning. No other text.
        """).strip()
    )

    return prompt


def judge_one(
    eval_run: EvalRun, eval_question: EvalQuestion, model: BaseChatModel, model_name: str
) -> Score:
    context = "\n\n".join(c.text_preview for c in eval_run.retrieved_chunks)

    prompt_input = {
        "question": eval_question.question,
        "context_chunks": context,
        "reference_answer": eval_question.reference_answer,
        "generated_answer": eval_run.generated_answer,
    }

    prompt = build_judge_prompt(
        prompt_input["question"],
        prompt_input["context_chunks"],
        prompt_input["reference_answer"],
        prompt_input["generated_answer"],
    )

    judge_chain = prompt | model | StrOutputParser()

    last_error = None
    for attempt in range(3):
        try:
            raw = judge_chain.invoke(prompt_input)
            clean = raw.strip().replace("```json", "").replace("```", "").strip()
            data = json.loads(clean)
            return Score(
                question_id=eval_question.id,
                config_name=eval_run.config_name,
                faithfulness=data["faithfulness_score"],
                faithfulness_reasoning=data["faithfulness_reasoning"],
                helpfulness=data["helpfulness_score"],
                helpfulness_reasoning=data["helpfulness_reasoning"],
                judge_model=model_name,
                timestamp=datetime.datetime.now(),
            )
        except Exception as e:
            last_error = e
            time.sleep(2**attempt)

    raise RuntimeError("Judge failed after 3 attempts") from last_error


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
