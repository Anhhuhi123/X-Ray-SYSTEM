"""
evaluate_faithfulness.py
────────────────────────
Metric: Faithfulness
Câu hỏi: Answer có được support bởi contexts không? (phát hiện hallucination)

Cách tính (RAGAS):
    1. Tách answer thành các "statements" nhỏ
    2. Với mỗi statement: LLM judge kiểm tra "statement này có trong contexts không?"
    3. faithfulness = supported_statements / total_statements

Fallback (nếu RAGAS không có):
    Tỉ lệ token của answer xuất hiện trong contexts (heuristic đơn giản)

Input  : file JSON đã generate (vd: 140_evaluated_gemini.json)
Output : file JSON chứa scores từng item + summary tổng thể

Params:
    --input_file   : file kết quả đã có (default: results/140_evaluated_gemini.json)
    --output_file  : file output scores
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

from dotenv import load_dotenv

load_dotenv()

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
# LLM initializer (Gemini hoặc OpenAI, giống pattern của evaluate_gemini.py)
# ──────────────────────────────────────────────────────────────────────────────
def _init_llm(model_name: str):
    """
    Khởi tạo LangChain LLM:
      - Nếu model_name chứa 'gemini' → dùng ChatGoogleGenerativeAI
      - Nếu không  → thử ChatOpenAI
      - Tự động fallback theo API key có sẵn trong env
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
# Heuristic fallback (không cần RAGAS)
# ──────────────────────────────────────────────────────────────────────────────
def _tokenize(text: str) -> list[str]:
    return re.findall(r"\w+", text.lower())


def _heuristic_faithfulness(answer: str, contexts: list[str]) -> float:
    """Tỉ lệ token của answer xuất hiện trong tập hợp token của contexts."""
    contexts_tokens = set(_tokenize(" ".join(contexts)))
    answer_tokens = _tokenize(answer)
    if not answer_tokens:
        return 0.0
    matched = sum(1 for t in answer_tokens if t in contexts_tokens)
    return matched / len(answer_tokens)


# ──────────────────────────────────────────────────────────────────────────────
# RAGAS faithfulness
# ──────────────────────────────────────────────────────────────────────────────
def _ragas_faithfulness(
    items: list[dict[str, Any]], llm
) -> tuple[list[float | None], str]:
    """
    Chạy RAGAS faithfulness metric.
    Trả về (scores_list, method_label).
    scores_list[i] = None nếu item đó bị lỗi.
    """
    try:
        from datasets import Dataset
        from ragas import evaluate as ragas_evaluate
        from ragas.metrics import faithfulness as ragas_faithfulness
    except ImportError as e:
        logger.warning(
            "RAGAS or datasets not installed (%s) → using heuristic fallback", e
        )
        return [None] * len(items), "heuristic_fallback"

    # Wrap LLM cho RAGAS
    try:
        from ragas.llms import LangchainLLMWrapper

        ragas_llm = LangchainLLMWrapper(llm)
        ragas_faithfulness.llm = ragas_llm
    except Exception as e:
        logger.warning("Failed to set RAGAS LLM (%s) → using heuristic fallback", e)
        return [None] * len(items), "heuristic_fallback"

    # Build dataset
    dataset_dict = {
        "user_input": [it.get("question", "") for it in items],
        "response": [it.get("answer", "") for it in items],
        "retrieved_contexts": [
            it.get("printed_contexts", it.get("contexts", [])) for it in items
        ],
    }

    try:
        dataset = Dataset.from_dict(dataset_dict)
        result = ragas_evaluate(dataset, metrics=[ragas_faithfulness])
        # result.to_pandas() contains per-item scores
        df = result.to_pandas()
        scores = df["faithfulness"].tolist()
        return scores, "ragas"
    except Exception as e:
        logger.warning("RAGAS evaluation failed (%s) → using heuristic fallback", e)
        return [None] * len(items), "heuristic_fallback"


# ──────────────────────────────────────────────────────────────────────────────
# Main evaluation logic
# ──────────────────────────────────────────────────────────────────────────────
def compute_faithfulness(
    input_file: str,
    output_file: str,
    model_name: str,
    language: str,
    use_ragas: bool,
) -> None:
    """Evaluate faithfulness: answer vs contexts."""
    import numpy as np

    data = load_data(input_file)
    print(f"Loaded {len(data)} items from: {input_file}\n")

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

    # Thử RAGAS nếu được bật và LLM available
    if use_ragas and llm is not None:
        print("Attempting RAGAS faithfulness evaluation...")
        ragas_scores, method_label = _ragas_faithfulness(data, llm)
    else:
        ragas_scores = [None] * len(data)
        method_label = "heuristic_fallback"

    print(f"Method: {method_label}\n")

    results: list[dict[str, Any]] = []

    for idx, (item, ragas_score) in enumerate(
        zip(data, ragas_scores, strict=False), start=1
    ):
        question = item.get("question", "")
        answer = item.get("answer", "")
        contexts: list[str] = item.get("printed_contexts", item.get("contexts", []))

        print(f"[{idx}/{len(data)}] {question[:70]}...")

        if ragas_score is not None and method_label == "ragas":
            score = float(ragas_score)
            used_method = "ragas"
        else:
            score = _heuristic_faithfulness(answer, contexts)
            used_method = "heuristic_fallback"

        print(f"  faithfulness_score={score:.4f}  method={used_method}")

        results.append(
            {
                "question": question,
                "faithfulness_score": round(score, 4),
                "method": used_method,
                "model_used": model_name if used_method == "ragas" else None,
                "num_contexts": len(contexts),
            }
        )

    # ── Summary ──────────────────────────────────────────────────────────────
    scores = [r["faithfulness_score"] for r in results]
    summary: dict[str, Any] = {
        "metric": "faithfulness",
        "description": (
            "RAGAS faithfulness: fraction of answer statements supported by contexts. "
            "Detects hallucination."
        ),
        "mean_faithfulness": round(float(np.mean(scores)), 4),
        "std_faithfulness": round(float(np.std(scores)), 4),
        "min": round(float(np.min(scores)), 4),
        "max": round(float(np.max(scores)), 4),
        "num_items": len(scores),
        "method_used": method_label,
        "use_ragas": use_ragas,
        "model_used": model_name,
        "language": language,
    }

    output = {"summary": summary, "results": results}
    save_results(output_file, output)

    print("\n" + "─" * 60)
    print("Faithfulness Summary")
    print("─" * 60)
    print(f"  LLM Judge : {model_name}")
    print(f"  Method    : {method_label}")
    print(f"  Use RAGAS : {use_ragas}")
    print(f"  Language  : {language}")
    print(f"  Items     : {summary['num_items']}")
    print(f"  Mean      : {summary['mean_faithfulness']}")
    print(f"  Std       : {summary['std_faithfulness']}")
    print(f"  Min       : {summary['min']}")
    print(f"  Max       : {summary['max']}")
    print("─" * 60)
    print(f"\n✅ Results saved to: {output_file}")


# ──────────────────────────────────────────────────────────────────────────────
# CLI
# ──────────────────────────────────────────────────────────────────────────────
def main() -> None:
    backend_dir = Path(__file__).resolve().parent.parent.parent
    default_input = str(
        backend_dir / "evaluation" / "results" / "140_evaluated_openai.json"
    )
    default_output = str(
        backend_dir / "evaluation" / "metrics_output" / "faithfulness_scores.json"
    )

    # Detect default LLM model from env
    if os.environ.get("OPENAI_API_KEY"):
        default_model = DEFAULT_OPENAI_MODEL
    else:
        default_model = DEFAULT_GEMINI_MODEL

    parser = argparse.ArgumentParser(
        description=(
            "Evaluate Faithfulness: how well the answer is supported by the retrieved "
            "contexts. Uses RAGAS faithfulness metric (LLM-as-judge). "
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
        help="Path to save faithfulness scores. Default: %(default)s",
    )
    parser.add_argument(
        "--language",
        type=str,
        choices=["vi", "en"],
        default="vi",
        help="Language of the data (informational; RAGAS uses LLM which is language-agnostic). Default: %(default)s",
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
        help="Enable RAGAS evaluation for faithfulness. Default: enabled",
    )
    use_ragas_group.add_argument(
        "--no_ragas",
        dest="use_ragas",
        action="store_false",
        help="Disable RAGAS evaluation and always use the heuristic fallback.",
    )
    parser.set_defaults(use_ragas=True)

    args = parser.parse_args()

    compute_faithfulness(
        input_file=args.input_file,
        output_file=args.output_file,
        model_name=args.model,
        language=args.language,
        use_ragas=args.use_ragas,
    )


if __name__ == "__main__":
    main()
