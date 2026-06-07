"""
evaluate_answer_relevancy.py
────────────────────────────
Metric: Answer Relevancy
Câu hỏi: Answer có trả lời đúng câu hỏi không? (so với ground truth)

Cách tính (BERTScore):
    P, R, F1 = BERTScore(answer, ground_truth)
    score chính = F1  ← semantic similarity, token-level BERT embeddings

Ưu điểm:
    - Không cần API (local model)
    - Semantic-aware: token khác, nghĩa giống → vẫn score cao
    - Deterministic
    - Miễn phí

Default models theo ngôn ngữ:
    --language vi  → bert-base-multilingual-cased
    --language en  → roberta-large        (mặc định BERTScore cho tiếng Anh)
    --model <any>  → override cả hai

Input  : file JSON đã generate (vd: 140_evaluated_gemini.json)
Output : file JSON chứa scores từng item + summary tổng thể

Params:
    --input_file   : file kết quả đã có (default: results/140_evaluated_gemini.json)
    --output_file  : file output scores
    --language     : 'vi' hoặc 'en' — chọn default BERTScore model
    --model        : override BERTScore model bất kỳ (HuggingFace model ID)
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np

# ──────────────────────────────────────────────────────────────────────────────
# Default BERTScore models per language
# ──────────────────────────────────────────────────────────────────────────────
DEFAULT_MODELS: dict[str, str] = {
    "vi": "bert-base-multilingual-cased",
    "en": "roberta-large",
}

# BERTScore `lang` param per model (used for idf rescaling baselines)
BERTSCORE_LANG: dict[str, str] = {
    "vi": "vi",
    "en": "en",
}


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


def _resolve_num_layers(model_name: str) -> int | None:
    """Resolve a fallback layer count for BERTScore when the model is unsupported."""
    try:
        from transformers import AutoConfig
    except ImportError:
        return None

    try:
        config = AutoConfig.from_pretrained(model_name)
    except Exception:
        return None

    for attr in ("num_hidden_layers", "n_layer"):
        num_layers = getattr(config, attr, None)
        if isinstance(num_layers, int) and num_layers > 0:
            return num_layers

    return None


# ──────────────────────────────────────────────────────────────────────────────
# BERTScore computation
# ──────────────────────────────────────────────────────────────────────────────
def _compute_bertscore(
    candidates: list[str],
    references: list[str],
    model_name: str,
    lang: str,
) -> tuple[list[float], list[float], list[float]]:
    """
    Trả về (precisions, recalls, f1s) dạng list[float].
    """
    try:
        from bert_score import score as bert_score_fn
    except ImportError:
        print(
            "[ERROR] bert-score not installed. Run: pip install bert-score",
            file=sys.stderr,
        )
        sys.exit(1)

    print(f"Computing BERTScore with model: {model_name}  lang: {lang}")
    print(f"  Candidates: {len(candidates)} items")

    # bert_score trả về tensors (Precision, Recall, F1)
    score_kwargs = {
        "cands": candidates,
        "refs": references,
        "model_type": model_name,
        "lang": lang,
        "verbose": True,
        "rescale_with_baseline": False,  # Tắt rescaling để tránh lỗi khi lang baseline chưa có
    }

    try:
        P_tensor, R_tensor, F1_tensor = bert_score_fn(**score_kwargs)
    except KeyError:
        num_layers = _resolve_num_layers(model_name)
        if num_layers is None:
            raise

        print(
            f"[WARN] BERTScore has no built-in layer mapping for {model_name}; "
            f"retrying with num_layers={num_layers}"
        )
        P_tensor, R_tensor, F1_tensor = bert_score_fn(
            **score_kwargs,
            num_layers=num_layers,
        )

    precisions: list[float] = P_tensor.tolist()
    recalls: list[float] = R_tensor.tolist()
    f1s: list[float] = F1_tensor.tolist()

    return precisions, recalls, f1s


# ──────────────────────────────────────────────────────────────────────────────
# Main evaluation logic
# ──────────────────────────────────────────────────────────────────────────────
def compute_answer_relevancy(
    input_file: str,
    output_file: str,
    model_name: str,
    language: str,
) -> None:
    """Evaluate Answer Relevancy using BERTScore (answer vs ground_truth)."""
    data = load_data(input_file)
    print(f"Loaded {len(data)} items from: {input_file}\n")

    # Lọc items có cả answer và ground_truth
    valid_items: list[dict[str, Any]] = []
    skipped: list[int] = []

    for idx, item in enumerate(data):
        answer = item.get("answer", "").strip()
        ground_truth = item.get("ground_truth", "").strip()
        if not answer or not ground_truth:
            skipped.append(idx + 1)
            continue
        valid_items.append(item)

    if skipped:
        print(
            f"⚠  Skipping {len(skipped)} items missing 'answer' or 'ground_truth': items {skipped}"
        )

    if not valid_items:
        print("[ERROR] No valid items to evaluate.", file=sys.stderr)
        sys.exit(1)

    candidates = [it.get("answer", "").strip() for it in valid_items]
    references = [it.get("ground_truth", "").strip() for it in valid_items]
    lang_code = BERTSCORE_LANG.get(language, language)

    # Tính BERTScore một lần cho toàn bộ batch (hiệu quả hơn từng cái một)
    precisions, recalls, f1s = _compute_bertscore(
        candidates=candidates,
        references=references,
        model_name=model_name,
        lang=lang_code,
    )

    print()

    results: list[dict[str, Any]] = []
    skipped_idx = 0

    for idx, item in enumerate(data, start=1):
        question = item.get("question", "")
        answer = item.get("answer", "").strip()
        ground_truth = item.get("ground_truth", "").strip()

        print(f"[{idx}/{len(data)}] {question[:70]}...")

        if not answer or not ground_truth:
            print("  ⚠  Skipped (missing answer or ground_truth)")
            results.append(
                {
                    "question": question,
                    "bertscore_precision": None,
                    "bertscore_recall": None,
                    "bertscore_f1": None,
                    "skipped": True,
                    "skip_reason": "missing answer or ground_truth",
                    "model_used": model_name,
                }
            )
            continue

        # Lấy score tương ứng từ batch kết quả
        p = round(precisions[skipped_idx], 4)
        r = round(recalls[skipped_idx], 4)
        f1 = round(f1s[skipped_idx], 4)
        skipped_idx += 1

        print(f"  P={p:.4f}  R={r:.4f}  F1={f1:.4f}")

        results.append(
            {
                "question": question,
                "answer": answer,
                "ground_truth": ground_truth,
                "bertscore_precision": p,
                "bertscore_recall": r,
                "bertscore_f1": f1,
                "skipped": False,
                "model_used": model_name,
            }
        )

    # ── Summary (chỉ tính trên valid items) ──────────────────────────────────
    valid_results = [r for r in results if not r.get("skipped")]
    f1_scores = [r["bertscore_f1"] for r in valid_results]
    p_scores = [r["bertscore_precision"] for r in valid_results]
    r_scores = [r["bertscore_recall"] for r in valid_results]

    summary: dict[str, Any] = {
        "metric": "answer_relevancy",
        "description": (
            "BERTScore F1 between answer and ground_truth. "
            "Semantic similarity at token-level using BERT embeddings."
        ),
        "mean_bertscore_f1": round(float(np.mean(f1_scores)), 4),
        "std_bertscore_f1": round(float(np.std(f1_scores)), 4),
        "min_bertscore_f1": round(float(np.min(f1_scores)), 4),
        "max_bertscore_f1": round(float(np.max(f1_scores)), 4),
        "mean_bertscore_precision": round(float(np.mean(p_scores)), 4),
        "mean_bertscore_recall": round(float(np.mean(r_scores)), 4),
        "num_items_evaluated": len(valid_results),
        "num_items_skipped": len(results) - len(valid_results),
        "model_used": model_name,
        "language": language,
    }

    output = {"summary": summary, "results": results}
    save_results(output_file, output)

    print("\n" + "─" * 60)
    print("Answer Relevancy Summary (BERTScore)")
    print("─" * 60)
    print(f"  Model     : {model_name}")
    print(f"  Language  : {language}")
    print(f"  Evaluated : {summary['num_items_evaluated']}")
    print(f"  Skipped   : {summary['num_items_skipped']}")
    print(f"  Mean F1   : {summary['mean_bertscore_f1']}")
    print(f"  Std  F1   : {summary['std_bertscore_f1']}")
    print(f"  Min  F1   : {summary['min_bertscore_f1']}")
    print(f"  Max  F1   : {summary['max_bertscore_f1']}")
    print(f"  Mean P    : {summary['mean_bertscore_precision']}")
    print(f"  Mean R    : {summary['mean_bertscore_recall']}")
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
        backend_dir / "evaluation" / "metrics_output" / "answer_relevancy_scores.json"
    )

    parser = argparse.ArgumentParser(
        description=(
            "Evaluate Answer Relevancy using BERTScore. "
            "Compares answer vs ground_truth using contextual BERT token embeddings. "
            "Semantic-aware, no API needed, deterministic."
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
        help="Path to save answer relevancy scores. Default: %(default)s",
    )
    parser.add_argument(
        "--language",
        type=str,
        choices=["vi", "en"],
        default="vi",
        help=(
            "Language of the data. Determines default BERTScore model: "
            "'vi' → bert-base-multilingual-cased, "
            "'en' → roberta-large. "
            "Default: %(default)s"
        ),
    )
    parser.add_argument(
        "--model",
        type=str,
        default=None,
        help=(
            "Override BERTScore model (any HuggingFace model ID). "
            "Takes priority over --language default. "
            "Examples: 'bert-base-multilingual-cased', 'roberta-large', "
            "'bert-base-multilingual-cased'"
        ),
    )

    args = parser.parse_args()

    # Resolve final model name
    model_name: str = args.model if args.model else DEFAULT_MODELS[args.language]

    compute_answer_relevancy(
        input_file=args.input_file,
        output_file=args.output_file,
        model_name=model_name,
        language=args.language,
    )


if __name__ == "__main__":
    main()
