import json
import logging
import os
import re

# Make sure parent package can be imported by scripts that run from this folder
import sys
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from app.db import async_session_maker
from app.retriever.nfd_docs_hybrid_search import combined_nfd_docs_rrf_search

load_dotenv()

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def load_input(input_file: str) -> list[dict[str, Any]]:
    path = Path(input_file)
    if not path.exists():
        raise FileNotFoundError(f"Input file not found: {input_file}")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def write_results(output_file: str, results: list[dict[str, Any]]) -> None:
    out_path = Path(output_file)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)


async def init_llm(model_name: str):
    """Initialize a chat LLM similar to existing evaluation files.

    Tries OpenAI first (OPENAI_API_KEY), then Gemini/Google (GEMINI_API_KEY/GOOGLE_API_KEY).
    Returns an LLM object with async `ainvoke(messages)` interface.
    """
    # Lazy imports to avoid import-time errors when packages are missing
    if os.environ.get("OPENAI_API_KEY"):
        try:
            from langchain_openai import ChatOpenAI

            logger.info("Initializing ChatOpenAI model %s", model_name)
            return ChatOpenAI(model=model_name, temperature=0.0)
        except Exception:
            logger.exception("Failed to initialize ChatOpenAI")

    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if api_key:
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI

            logger.info("Initializing ChatGoogleGenerativeAI model %s", model_name)
            return ChatGoogleGenerativeAI(
                model=model_name, temperature=0.0, google_api_key=api_key
            )
        except Exception:
            logger.exception("Failed to initialize ChatGoogleGenerativeAI")

    raise ValueError(
        "No supported LLM API key found in environment (OPENAI_API_KEY or GEMINI_API_KEY/GOOGLE_API_KEY)"
    )


async def retrieve_contexts(question: str, top_k: int) -> list[str]:
    async with async_session_maker() as session:
        search_results = await combined_nfd_docs_rrf_search(
            query_text=question, db_session=session, top_k=top_k
        )

    contexts: list[str] = []
    for doc in search_results:
        for chunk in doc.get("chunks", []):
            content = chunk.get("content")
            if content:
                contexts.append(content)
    return contexts


async def generate_answer(
    llm, question: str, contexts: list[str], system_prompt: str
) -> str:
    from langchain_core.messages import HumanMessage, SystemMessage

    contexts_text = "\n\n---\n\n".join(contexts)
    user_prompt = f"Contexts:\n{contexts_text}\n\nQuestion: {question}"
    messages = [SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)]
    try:
        response = await llm.ainvoke(messages)
        return response.content
    except Exception as e:
        logger.exception("LLM invocation failed for question: %s", question)
        return f"Error: {e}"


def _tokenize(text: str) -> list[str]:
    # simple tokenizer: split on non-word characters, lowercase
    tokens = re.findall(r"\w+", text.lower())
    return tokens


def compute_metric_fallback(
    metric_name: str, question: str, answer: str, contexts: list[str], ground_truth: str
) -> float:
    """Compute a simple heuristic metric if RAGAS is not available.

    - faithfulness: fraction of answer tokens that appear in contexts
    - relevance: fraction of answer tokens that overlap with question tokens
    - context_recall: fraction of ground-truth tokens present in contexts
    """
    contexts_text = " ".join(contexts).lower()
    answer_tokens = _tokenize(answer)
    question_tokens = set(_tokenize(question))
    contexts_tokens = set(_tokenize(contexts_text))
    gt_tokens = set(_tokenize(ground_truth))

    if not answer_tokens:
        return 0.0

    if metric_name == "faithfulness":
        matched = sum(1 for t in answer_tokens if t in contexts_tokens)
        return matched / len(answer_tokens)
    if metric_name == "relevance":
        matched = sum(1 for t in answer_tokens if t in question_tokens)
        return matched / len(answer_tokens)
    if metric_name == "context_recall":
        if not gt_tokens:
            return 0.0
        matched = sum(1 for t in gt_tokens if t in contexts_tokens)
        return matched / len(gt_tokens)

    raise ValueError(f"Unknown metric: {metric_name}")


def compute_metric(
    metric_name: str, question: str, answer: str, contexts: list[str], ground_truth: str
) -> float:
    """Attempt to compute metric using RAGAS if available; otherwise fall back to heuristic.

    Currently RAGAS integration is optional: when `ragas` is installed we could
    wire into its evaluator here. For portability this function falls back to
    a lightweight heuristic implementation and logs whether RAGAS was used.
    """
    try:
        import ragas  # type: ignore
    except Exception:
        logger.debug(
            "RAGAS not available; using fallback heuristic for %s", metric_name
        )
        return compute_metric_fallback(
            metric_name, question, answer, contexts, ground_truth
        )

    # If RAGAS is installed, attempt to use a generic evaluation call if available.
    # Because RAGAS' public API can change, keep a defensive approach: if the
    # simple expected API is present use it, otherwise fall back.
    try:
        # Example: ragas.metrics.evaluate(metric_name, ...)
        if hasattr(ragas, "evaluate"):
            # ragas.evaluate should accept a dict with keys; this is a best-effort call
            payload = {
                "metric": metric_name,
                "question": question,
                "answer": answer,
                "contexts": contexts,
                "ground_truths": [ground_truth] if ground_truth else [],
            }
            score = ragas.evaluate(payload)
            logger.debug("RAGAS returned score for %s: %s", metric_name, score)
            return float(score)
    except Exception:
        logger.exception(
            "RAGAS evaluation failed; falling back to heuristic for %s", metric_name
        )

    # Default fallback
    return compute_metric_fallback(
        metric_name, question, answer, contexts, ground_truth
    )
