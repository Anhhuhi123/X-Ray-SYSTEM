"""
evaluate_context_precision.py
─────────────────────────────
Metric: Context Precision
Câu hỏi: Retriever có lấy ra các context liên quan đến câu hỏi không?

Cách tính:
    1. Embed question và từng context bằng sentence-transformers
    2. cosine_similarity(embed(question), embed(context_i)) cho mỗi context
    3. score = mean(all similarities)

Input  : file JSON đã generate (vd: 140_evaluated_gemini.json)
Output : file JSON chứa scores từng item + summary tổng thể

Params:
    --input_file   : file kết quả đã có (default: results/140_evaluated_gemini.json)
    --output_file  : file output scores
    --language     : 'vi' (Vietnamese) hoặc 'en' (English) — chọn default model
    --model        : override sentence-transformers model bất kỳ
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np

# ──────────────────────────────────────────────────────────────────────────────
# Default models per language
# ──────────────────────────────────────────────────────────────────────────────
DEFAULT_MODELS: dict[str, str] = {
    "vi": "sentence-transformers/paraphrase-multilingual-mpnet-base-v2",
    "en": "sentence-transformers/all-mpnet-base-v2",
}


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


def compute_context_precision(
    input_file: str,
    output_file: str,
    model_name: str,
    language: str,
) -> None:
    """Compute Context Precision scores using embedding cosine similarity."""
    try:
        from sentence_transformers import SentenceTransformer
        from sklearn.metrics.pairwise import cosine_similarity
    except ImportError as e:
        print(
            f"[ERROR] Missing dependency: {e}\n"
            "Install with: pip install sentence-transformers scikit-learn",
            file=sys.stderr,
        )
        sys.exit(1)

    print(f"Loading model: {model_name}")
    model = SentenceTransformer(model_name)

    data = load_data(input_file)
    print(f"Loaded {len(data)} items from: {input_file}\n")

    results: list[dict[str, Any]] = []

    for idx, item in enumerate(data, start=1):
        question: str = item.get("question", "")
        # Support cả 'printed_contexts' lẫn 'contexts' field
        contexts: list[str] = item.get("printed_contexts", item.get("contexts", []))

        print(f"[{idx}/{len(data)}] {question[:70]}...")

        if not contexts:
            print("  ⚠  No contexts found — score set to 0.0")
            results.append(
                {
                    "question": question,
                    "context_precision_score": 0.0,
                    "individual_similarities": [],
                    "num_contexts": 0,
                    "model_used": model_name,
                }
            )
            continue

        # Embed question và tất cả contexts
        q_embedding = model.encode([question])  # shape (1, dim)
        c_embeddings = model.encode(contexts)  # shape (n, dim)

        # Cosine similarity giữa question và từng context
        sims: list[float] = cosine_similarity(q_embedding, c_embeddings)[0].tolist()
        score: float = float(np.mean(sims))

        print(f"  contexts={len(contexts)}, mean_sim={score:.4f}")

        results.append(
            {
                "question": question,
                "context_precision_score": round(score, 4),
                "individual_similarities": [round(s, 4) for s in sims],
                "num_contexts": len(contexts),
                "model_used": model_name,
            }
        )

    # ── Summary ──────────────────────────────────────────────────────────────
    scores = [r["context_precision_score"] for r in results]
    summary: dict[str, Any] = {
        "metric": "context_precision",
        "description": "Mean cosine similarity between question embedding and context embeddings",
        "mean_context_precision": round(float(np.mean(scores)), 4),
        "std_context_precision": round(float(np.std(scores)), 4),
        "min": round(float(np.min(scores)), 4),
        "max": round(float(np.max(scores)), 4),
        "num_items": len(scores),
        "model_used": model_name,
        "language": language,
    }

    output = {"summary": summary, "results": results}
    save_results(output_file, output)

    print("\n" + "─" * 60)
    print("Context Precision Summary")
    print("─" * 60)
    print(f"  Model     : {model_name}")
    print(f"  Language  : {language}")
    print(f"  Items     : {summary['num_items']}")
    print(f"  Mean      : {summary['mean_context_precision']}")
    print(f"  Std       : {summary['std_context_precision']}")
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
        backend_dir / "evaluation" / "results" / "140_evaluated_gemini.json"
    )
    default_output = str(
        backend_dir / "evaluation" / "metrics_output" / "context_precision_scores.json"
    )

    parser = argparse.ArgumentParser(
        description=(
            "Evaluate Context Precision: cosine similarity between question and "
            "retrieved context embeddings (mean over all chunks)."
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
        help="Path to save context precision scores. Default: %(default)s",
    )
    parser.add_argument(
        "--language",
        type=str,
        choices=["vi", "en"],
        default="vi",
        help=(
            "Language of the data. Determines default embedding model: "
            "'vi' → paraphrase-multilingual-mpnet-base-v2, "
            "'en' → all-mpnet-base-v2. Default: %(default)s"
        ),
    )
    parser.add_argument(
        "--model",
        type=str,
        default=None,
        help=(
            "Override sentence-transformers model (any HuggingFace model ID). "
            "Takes priority over --language default."
        ),
    )

    args = parser.parse_args()

    # Resolve final model name
    model_name: str = args.model if args.model else DEFAULT_MODELS[args.language]

    compute_context_precision(
        input_file=args.input_file,
        output_file=args.output_file,
        model_name=model_name,
        language=args.language,
    )


if __name__ == "__main__":
    main()
