"""
evaluate_context_recall.py
──────────────────────────
Metric: Context Recall
Câu hỏi: Retriever có lấy ra ĐỦ thông tin để sinh đúng câu trả lời không?

Cách tính (RAGAS style):
    1. LLM chia ground_truth thành các "statements" nhỏ
    2. Với từng statement: LLM kiểm tra statement đó có thể được suy ra
       từ contexts không?
    3. context_recall = statements_supported_by_contexts / total_statements

Fallback (nếu RAGAS không có / LLM lỗi):
    Tỉ lệ token của ground_truth xuất hiện trong tập hợp token của contexts
    (heuristic đơn giản, tương tự _eval_utils.compute_metric_fallback)

Input  : file JSON đã generate (vd: results/140_evaluated_gemini.json)
Output : file JSON chứa scores từng item + summary tổng thể

Fields bắt buộc trong input JSON:
    - question
    - ground_truth
    - printed_contexts  (hoặc contexts)

Params:
    --input_file   : file kết quả đã có (default: results/140_evaluated_gemini.json)
    --output_file  : file output scores  (default: metrics_output/context_recall_scores.json)
    --language     : 'vi' hoặc 'en' (thông tin ngôn ngữ, RAGAS dùng LLM nên ít ảnh hưởng)
    --model        : LLM model cho RAGAS judge
                     Gemini: 'gemini-2.5-flash', 'gemini-1.5-pro', ...
                     OpenAI: 'gpt-4o', 'gpt-4o-mini', ...
"""

import argparse
import json
import logging
import os
import re
import sys
from pathlib import Path
from typing import Any

import langchain
from dotenv import load_dotenv

load_dotenv()

langchain.debug = True

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────────────
# Default LLM models per provider
# ──────────────────────────────────────────────────────────────────────────────
DEFAULT_GEMINI_MODEL = "gemini-2.5-flash"
DEFAULT_OPENAI_MODEL = "gpt-4o-mini"


# ──────────────────────────────────────────────────────────────────────────────
# Data helpers
# ──────────────────────────────────────────────────────────────────────────────
def load_data(input_file: str) -> list[dict[str, Any]]:
    path = Path(input_file)
    if not path.exists():
        print(f"[ERROR] Input file not found: {input_file}", file=sys.stderr)
        sys.exit(1)
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save_results(output_file: str, data: dict[str, Any]) -> None:
    out_path = Path(output_file)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ──────────────────────────────────────────────────────────────────────────────
# LLM initializer (giống pattern evaluate_faithfulness.py)
# ──────────────────────────────────────────────────────────────────────────────
def _init_llm(model_name: str):
    """
    Khởi tạo LangChain LLM:
      - Nếu model_name chứa 'gemini' / 'google' → dùng ChatGoogleGenerativeAI
      - Nếu không → thử ChatOpenAI
    """
    model_lower = model_name.lower()

    if "gemini" in model_lower or "google" in model_lower:
        api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError(
                "GEMINI_API_KEY or GOOGLE_API_KEY not found in environment. "
                "Please set it in your .env file."
            )
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI

            logger.info("Using ChatGoogleGenerativeAI: %s", model_name)
            return ChatGoogleGenerativeAI(
                model=model_name, temperature=0.0, google_api_key=api_key
            )
        except ImportError as err:
            raise ImportError(
                "langchain_google_genai not installed. "
                "Run: pip install langchain-google-genai"
            ) from err

    else:  # OpenAI-compatible
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise ValueError(
                "OPENAI_API_KEY not found in environment. "
                "Please set it in your .env file."
            )
        try:
            from langchain_openai import ChatOpenAI

            logger.info("Using ChatOpenAI: %s", model_name)
            return ChatOpenAI(model=model_name, temperature=0.0)
        except ImportError as err:
            raise ImportError(
                "langchain_openai not installed. Run: pip install langchain-openai"
            ) from err


# ──────────────────────────────────────────────────────────────────────────────
# Heuristic fallback — không cần RAGAS hay LLM
# ──────────────────────────────────────────────────────────────────────────────
def _tokenize(text: str) -> list[str]:
    return re.findall(r"\w+", text.lower())


def _heuristic_context_recall(ground_truth: str, contexts: list[str]) -> float:
    """Tỉ lệ token của ground_truth xuất hiện trong tập hợp token của contexts."""
    gt_tokens = _tokenize(ground_truth)
    if not gt_tokens:
        return 0.0
    ctx_tokens = set(_tokenize(" ".join(contexts)))
    matched = sum(1 for t in gt_tokens if t in ctx_tokens)
    return matched / len(gt_tokens)


# ──────────────────────────────────────────────────────────────────────────────
# RAGAS context recall
# ──────────────────────────────────────────────────────────────────────────────
def _ragas_context_recall(
    items: list[dict[str, Any]], llm
) -> tuple[list[float | None], str]:
    """
    Chạy RAGAS context_recall metric.
    Trả về (scores_list, method_label).
    scores_list[i] = None nếu item đó bị lỗi.
    """
    try:
        from datasets import Dataset
        from ragas import evaluate as ragas_evaluate
        from ragas.metrics import context_recall as ragas_context_recall
    except ImportError as e:
        logger.warning(
            "RAGAS or datasets not installed (%s) → using heuristic fallback", e
        )
        return [None] * len(items), "heuristic_fallback"

    # Wrap LLM cho RAGAS
    try:
        from ragas.llms import LangchainLLMWrapper

        ragas_llm = LangchainLLMWrapper(llm)
        ragas_context_recall.llm = ragas_llm
    except Exception as e:
        logger.warning("Failed to set RAGAS LLM (%s) → using heuristic fallback", e)
        return [None] * len(items), "heuristic_fallback"

    # Build dataset — context_recall cần: user_input, retrieved_contexts, reference (tương ứng với ragas >= 0.2.x)
    dataset_dict = {
        "user_input": [it.get("question", "") for it in items],
        "retrieved_contexts": [
            it.get("printed_contexts", it.get("contexts", [])) for it in items
        ],
        "reference": [it.get("ground_truth", "") for it in items],
    }

    try:
        dataset = Dataset.from_dict(dataset_dict)
        result = ragas_evaluate(dataset, metrics=[ragas_context_recall])
        df = result.to_pandas()
        print("DEBUG RAGAS COLUMNS:", df.columns.tolist())
        scores = df["context_recall"].tolist()
        return scores, "ragas"
    except Exception as e:
        logger.warning("RAGAS evaluation failed (%s) → using heuristic fallback", e)
        return [None] * len(items), "heuristic_fallback"


# ──────────────────────────────────────────────────────────────────────────────
# Main evaluation logic
# ──────────────────────────────────────────────────────────────────────────────
def compute_context_recall(
    input_file: str,
    output_file: str,
    model_name: str,
    language: str,
    use_ragas: bool,
) -> dict[str, Any]:
    """
    Evaluate Context Recall: ground_truth coverage by retrieved contexts.

    Returns the full output dict (summary + results) so evaluate_all.py
    can call this function directly without re-loading the JSON file.
    """
    import numpy as np

    data = load_data(input_file)
    print(f"Loaded {len(data)} items from: {input_file}\n")

    # Lọc: cần có ground_truth mới tính được context_recall
    valid_indices = []
    for i, item in enumerate(data):
        gt = item.get("ground_truth", "").strip()
        if not gt:
            logger.warning("Item %d missing 'ground_truth' — will score 0.0", i + 1)
        else:
            valid_indices.append(i)

    # Khởi tạo LLM chỉ khi thật sự cần RAGAS
    llm = None
    if use_ragas:
        try:
            llm = _init_llm(model_name)
            print(f"LLM judge initialized: {model_name}")
        except Exception as e:
            logger.warning(
                "Could not initialize LLM (%s) → will use heuristic fallback", e
            )

    # RAGAS nếu được bật và LLM available
    if use_ragas and llm is not None:
        print("Attempting RAGAS context_recall evaluation...")
        ragas_scores, method_label = _ragas_context_recall(data, llm)
    else:
        ragas_scores = [None] * len(data)
        method_label = "heuristic_fallback"

    print(f"Method: {method_label}\n")

    results: list[dict[str, Any]] = []

    for idx, (item, ragas_score) in enumerate(
        zip(data, ragas_scores, strict=False), start=1
    ):
        question = item.get("question", "")
        ground_truth = item.get("ground_truth", "").strip()
        contexts: list[str] = item.get("printed_contexts", item.get("contexts", []))

        print(f"[{idx}/{len(data)}] {question[:70]}...")

        if not ground_truth:
            score = 0.0
            used_method = "skipped_no_ground_truth"
        elif ragas_score is not None and method_label == "ragas":
            score = float(ragas_score)
            used_method = "ragas"
        else:
            score = _heuristic_context_recall(ground_truth, contexts)
            used_method = "heuristic_fallback"

        print(f"  context_recall_score={score:.4f}  method={used_method}")

        results.append(
            {
                "question": question,
                "context_recall_score": round(score, 4),
                "method": used_method,
                "model_used": model_name if used_method == "ragas" else None,
                "num_contexts": len(contexts),
                "has_ground_truth": bool(ground_truth),
            }
        )

    # ── Summary ──────────────────────────────────────────────────────────────
    scorable = [r["context_recall_score"] for r in results]
    summary: dict[str, Any] = {
        "metric": "context_recall",
        "description": (
            "RAGAS context_recall: fraction of ground_truth statements that "
            "can be attributed to the retrieved contexts. "
            "Measures retriever completeness."
        ),
        "mean_context_recall": round(float(np.mean(scorable)), 4),
        "std_context_recall": round(float(np.std(scorable)), 4),
        "min": round(float(np.min(scorable)), 4),
        "max": round(float(np.max(scorable)), 4),
        "num_items": len(scorable),
        "num_skipped": sum(
            1 for r in results if r["method"] == "skipped_no_ground_truth"
        ),
        "method_used": method_label,
        "use_ragas": use_ragas,
        "model_used": model_name,
        "language": language,
    }

    output = {"summary": summary, "results": results}
    save_results(output_file, output)

    print("\n" + "─" * 60)
    print("Context Recall Summary")
    print("─" * 60)
    print(f"  LLM Judge : {model_name}")
    print(f"  Method    : {method_label}")
    print(f"  Use RAGAS : {use_ragas}")
    print(f"  Language  : {language}")
    print(f"  Items     : {summary['num_items']}")
    print(f"  Skipped   : {summary['num_skipped']}  (no ground_truth)")
    print(f"  Mean      : {summary['mean_context_recall']}")
    print(f"  Std       : {summary['std_context_recall']}")
    print(f"  Min       : {summary['min']}")
    print(f"  Max       : {summary['max']}")
    print("─" * 60)
    print(f"\n✅ Results saved to: {output_file}")

    return output


# ──────────────────────────────────────────────────────────────────────────────
# CLI
# ──────────────────────────────────────────────────────────────────────────────
def main() -> None:
    backend_dir = Path(__file__).resolve().parent.parent.parent
    default_input = str(
        backend_dir / "evaluation" / "results" / "140_evaluated_openai.json"
    )
    default_output = str(
        backend_dir / "evaluation" / "metrics_output" / "context_recall_scores.json"
    )

    # Detect default LLM model from env
    if os.environ.get("OPENAI_API_KEY"):
        default_model = DEFAULT_OPENAI_MODEL
    else:
        default_model = DEFAULT_GEMINI_MODEL

    parser = argparse.ArgumentParser(
        description=(
            "Evaluate Context Recall: how well the retrieved contexts cover the "
            "information needed to answer the question (compared to ground_truth). "
            "Uses RAGAS context_recall metric (LLM-as-judge). "
            "Falls back to token-overlap heuristic if RAGAS/LLM is unavailable."
        )
    )
    parser.add_argument(
        "--input_file",
        type=str,
        default=default_input,
        help="Path to evaluated results JSON (e.g. 140_evaluated_gemini.json). Default: %(default)s",
    )
    parser.add_argument(
        "--output_file",
        type=str,
        default=default_output,
        help="Path to save context recall scores. Default: %(default)s",
    )
    parser.add_argument(
        "--language",
        type=str,
        choices=["vi", "en"],
        default="vi",
        help=(
            "Language of the data (informational; RAGAS uses LLM which is language-agnostic). "
            "Default: %(default)s"
        ),
    )
    parser.add_argument(
        "--model",
        type=str,
        default=default_model,
        help=(
            "LLM model for RAGAS judge. "
            "Gemini: 'gemini-2.5-flash', 'gemini-1.5-pro', ... "
            "OpenAI: 'gpt-4o', 'gpt-4o-mini', ... "
            f"Default: {default_model} (based on available API keys)"
        ),
    )
    use_ragas_group = parser.add_mutually_exclusive_group()
    use_ragas_group.add_argument(
        "--use_ragas",
        dest="use_ragas",
        action="store_true",
        help="Enable RAGAS evaluation for context recall. Default: enabled",
    )
    use_ragas_group.add_argument(
        "--no_ragas",
        dest="use_ragas",
        action="store_false",
        help="Disable RAGAS evaluation and always use the heuristic fallback.",
    )
    parser.set_defaults(use_ragas=True)

    args = parser.parse_args()

    compute_context_recall(
        input_file=args.input_file,
        output_file=args.output_file,
        model_name=args.model,
        language=args.language,
        use_ragas=args.use_ragas,
    )


if __name__ == "__main__":
    main()
