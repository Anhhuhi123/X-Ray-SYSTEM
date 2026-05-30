# RAG Evaluation Pipeline

Bộ công cụ đánh giá chất lượng hệ thống RAG (Retrieval-Augmented Generation) của SurfSense.

---

## Cấu trúc thư mục

```
evaluation/
├── data_input/                  # Bộ câu hỏi + ground truth gốc
│   └── 140.json
│
├── generate_results/            # Bước 1: Chạy RAG → sinh ra file kết quả
│   ├── evaluate_gemini.py       # Dùng Gemini làm LLM sinh câu trả lời
│   ├── evaluate_openai.py       # Dùng OpenAI làm LLM sinh câu trả lời
│   └── _eval_utils.py           # Hàm tiện ích dùng chung
│
├── results/                     # Output của bước 1 (file JSON đã có answer + contexts)
│   └── 140_evaluated_gemini.json
│
├── metrics/                     # Bước 2: Tính điểm từng metric
│   ├── evaluate_context_precision.py
│   ├── evaluate_faithfulness.py
│   ├── evaluate_answer_relevancy.py
│   ├── evaluate_context_recall.py
│   └── evaluate_all.py          # Chạy tất cả metrics cùng lúc
│
└── metrics_output/              # Output của bước 2 (file JSON/CSV/Excel điểm số)
```

---

## Quy trình 2 bước

```
Bước 1                          Bước 2
data_input/140.json  →  generate_results/  →  results/*.json  →  metrics/  →  metrics_output/
(câu hỏi + GT)          (chạy RAG + LLM)      (answer+context)   (tính điểm)   (báo cáo)
```

---

## Bước 1 — Sinh kết quả RAG

Chạy hệ thống RAG thực tế: retriever lấy context, LLM sinh câu trả lời.

```bash
# Dùng Gemini
python generate_results/evaluate_gemini.py \
  --input_file  data_input/140.json \
  --output_file results/140_evaluated_gemini.json \
  --model       gemini-2.5-flash \
  --top_k       5

# Dùng OpenAI
python generate_results/evaluate_openai.py \
  --input_file  data_input/140.json \
  --output_file results/140_evaluated_openai.json \
  --model       gpt-4o-mini \
  --top_k       5
```

File output có dạng:
```json
[
  {
    "question": "...",
    "ground_truth": "...",
    "printed_contexts": ["đoạn context 1", "đoạn context 2"],
    "answer": "câu trả lời do LLM sinh ra"
  }
]
```

---

## Bước 2 — Tính điểm metrics

### Tổng quan 4 metrics

| Metric | Đo lường gì | Cần gì |
|---|---|---|
| Context Precision | Context có liên quan câu hỏi không? | question + contexts |
| Faithfulness | Answer có dựa vào contexts không? | answer + contexts |
| Answer Correctness | Answer có đúng với đáp án chuẩn không? | answer + ground_truth |
| Context Recall | Context có chứa đủ thông tin để trả lời không? | contexts + ground_truth |

---

### 1. Context Precision

**Đo gì**: Retriever có lấy ra đúng những đoạn văn bản liên quan đến câu hỏi không?

**Phương pháp**: Embedding cosine similarity
1. Embed `question` và từng `context` bằng `sentence-transformers`
2. Tính `cosine_similarity(question_embedding, context_embedding)` cho từng context
3. `score = mean(all similarities)` → điểm 0.0–1.0

> Không cần API, chạy local hoàn toàn. Không cần `ground_truth`.

```bash
python metrics/evaluate_context_precision.py \
  --input_file results/140_evaluated_gemini.json \
  --language   vi
```

**Output**: `metrics_output/context_precision_scores.json`

---

### 2. Faithfulness

**Đo gì**: Câu trả lời do LLM sinh ra có bịa thêm thông tin ngoài context không? (phát hiện hallucination)

**Phương pháp**: RAGAS LLM-as-Judge
1. LLM chia `answer` thành nhiều *statements* nhỏ
2. Với từng statement: LLM kiểm tra xem statement đó có được support bởi `contexts` không
3. `faithfulness = statements_có_trong_contexts / tổng_statements`

> Nếu không có RAGAS/LLM: tự động fallback về heuristic token overlap (tỉ lệ token của answer xuất hiện trong contexts).

```bash
python metrics/evaluate_faithfulness.py \
  --input_file results/140_evaluated_gemini.json \
  --language   vi \
  --model      gemini-2.5-flash
```

**Output**: `metrics_output/faithfulness_scores.json`

---

### 3. Answer Correctness

**Đo gì**: Câu trả lời có đúng nghĩa với đáp án chuẩn (`ground_truth`) không?

**Phương pháp**: BERTScore
1. Dùng model BERT (`vinai/phobert-base` cho tiếng Việt) để encode `answer` và `ground_truth`
2. Tính Precision, Recall, F1 ở mức token embedding
3. `score chính = F1` — semantic similarity, đo nghĩa chứ không đo từ ngữ chính xác

> Không cần API, chạy local. Cần có `ground_truth` trong file input.

```bash
python metrics/evaluate_answer_relevancy.py \
  --input_file results/140_evaluated_gemini.json \
  --language   vi
```

**Output**: `metrics_output/answer_relevancy_scores.json`

---

### 4. Context Recall

**Đo gì**: Retriever có lấy ra ĐỦ thông tin cần thiết để trả lời câu hỏi không?

**Phương pháp**: RAGAS LLM-as-Judge
1. LLM chia `ground_truth` thành nhiều *statements* nhỏ
2. Với từng statement: LLM kiểm tra xem statement đó có thể suy ra từ `contexts` không
3. `context_recall = statements_có_trong_contexts / tổng_statements`

> Nếu không có RAGAS/LLM: tự động fallback về heuristic token overlap (tỉ lệ token của ground_truth xuất hiện trong contexts). Cần có `ground_truth` trong file input.

```bash
python metrics/evaluate_context_recall.py \
  --input_file results/140_evaluated_gemini.json \
  --language   vi \
  --model      gemini-2.5-flash
```

**Output**: `metrics_output/context_recall_scores.json`

---

### Chạy tất cả cùng lúc — `evaluate_all.py`

Chạy cả 4 metrics và xuất báo cáo tổng hợp ra 3 định dạng (JSON + CSV + Excel).

```bash
# Chạy đầy đủ (mặc định)
python metrics/evaluate_all.py

# Chỉ định file input khác
python metrics/evaluate_all.py \
  --input_file results/140_evaluated_openai.json \
  --language   vi

# Bỏ qua metrics cần API (để test nhanh)
python metrics/evaluate_all.py \
  --skip_metrics faithfulness context_recall
```

**Output** (trong `metrics_output/`):
- `evaluation_report.json` — full data từng câu
- `evaluation_report.csv` — bảng phẳng cho Excel / pandas
- `evaluation_report.xlsx` — Excel với màu sắc (🟢 tốt / 🟡 trung bình / 🔴 thấp) + sheet Summary

---

## Tham số chung

| Tham số | Mô tả | Mặc định |
|---|---|---|
| `--input_file` | File JSON từ bước 1 | `results/140_evaluated_gemini.json` |
| `--output_file` | Nơi lưu kết quả | `metrics_output/<metric>_scores.json` |
| `--language` | `vi` hoặc `en` — ảnh hưởng default model | `vi` |
| `--model` | Override LLM / embedding / BERTScore model | auto-detect theo API key |

---

## Yêu cầu thư viện

```bash
# Bắt buộc cho tất cả
pip install python-dotenv numpy

# Context Precision
pip install sentence-transformers scikit-learn

# Faithfulness + Context Recall (LLM judge)
pip install ragas datasets langchain-google-genai
# hoặc
pip install ragas datasets langchain-openai

# Answer Correctness
pip install bert-score

# Xuất CSV + Excel
pip install pandas openpyxl
```

---

## Biến môi trường (.env)

```env
GEMINI_API_KEY=your_gemini_api_key
# hoặc
OPENAI_API_KEY=your_openai_api_key
```

> Nếu không có API key, các metrics dùng LLM (Faithfulness, Context Recall) sẽ tự động fallback về phương pháp heuristic token overlap — vẫn cho ra kết quả nhưng kém chính xác hơn.
