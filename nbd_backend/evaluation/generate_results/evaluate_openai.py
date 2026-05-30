import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

# Add nbd_backend directory to sys.path so we can import app
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from app.db import async_session_maker
from app.retriever.nfd_docs_hybrid_search import combined_nfd_docs_rrf_search

# Load environment variables
load_dotenv()


async def evaluate_openai(
    input_file: str,
    output_file: str,
    model_name: str,
    top_k: int,
    full_output: bool = False,
    output_mode: str = "printed",
):
    # Ensure OPENAI_API_KEY is available
    if not os.environ.get("OPENAI_API_KEY"):
        raise ValueError(
            "OPENAI_API_KEY not found in environment variables. Please set it in your .env file."
        )

    # Initialize the LLM
    llm = ChatOpenAI(model=model_name, temperature=0.0)

    # Load input data
    input_path = Path(input_file)
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_file}")

    with open(input_path, encoding="utf-8") as f:
        data = json.load(f)

    results = []

    # System prompt
    system_prompt = (
        "You are a helpful AI assistant. Your task is to answer the user's question "
        "based strictly on the provided contexts. Do not hallucinate information outside of the contexts."
    )

    async with async_session_maker() as session:
        for item in data:
            question = item.get("question", "")
            ground_truth = item.get("ground_truth", "")

            print(f"Processing question: {question}")

            # Retrieve context using combined_nfd_docs_rrf_search
            search_results = await combined_nfd_docs_rrf_search(
                query_text=question, db_session=session, top_k=top_k
            )

            # Extract chunks for LLM (use all retrieved contexts so retrieval logic is unchanged)
            contexts = []
            for doc in search_results:
                for chunk in doc.get("chunks", []):
                    content = chunk.get("content")
                    if content:
                        contexts.append(content)

            # Prepare printed contexts for human evaluation / output presentation only.
            # By default (full_output=False) we show only the best document (first result)
            # and only the first 10 chunks from that document. If full_output is True,
            # we expose all contexts as before.
            if full_output:
                printed_contexts = list(contexts)
            else:
                printed_contexts = []
                if search_results:
                    best_doc_chunks = search_results[0].get("chunks", [])
                    for chunk in best_doc_chunks[:10]:
                        content = chunk.get("content")
                        if content:
                            printed_contexts.append(content)

            # If we collected more chunks than top_k docs might have conceptually,
            # we just pass them all (or we could limit contexts slice). The request
            # is to configure chunk count returned, top_k limits the *documents* retrieved
            # in combined_nfd_docs_rrf_search, which in turn returns chunks.

            # Prepare prompt for LLM
            contexts_text = "\n\n---\n\n".join(contexts)
            user_prompt = f"Contexts:\n{contexts_text}\n\nQuestion: {question}"

            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt),
            ]

            # Get answer from LLM
            try:
                response = await llm.ainvoke(messages)
                answer = response.content
            except Exception as e:
                print(f"Error calling LLM for question '{question}': {e}")
                answer = f"Error: {e}"

            # Build the result entry according to the requested output_mode.
            # Do not include extra context fields to avoid duplicated/verbose output.
            if output_mode == "printed":
                entry = {
                    "question": question,
                    "ground_truth": ground_truth,
                    "printed_contexts": printed_contexts,
                    "answer": answer,
                }
            else:
                entry = {
                    "question": question,
                    "ground_truth": ground_truth,
                    "contexts": contexts,
                    "answer": answer,
                }

            results.append(entry)

            # Save incrementally
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"Evaluation complete. Results saved to {output_file}")


def main():
    backend_dir = Path(__file__).resolve().parent.parent.parent
    default_input = str(backend_dir / "evaluate" / "data" / "140.json")
    default_output = str(
        backend_dir / "evaluate" / "results" / "140_evaluated_openai.json"
    )

    parser = argparse.ArgumentParser(
        description="Evaluate 140.json using OpenAI models"
    )
    parser.add_argument(
        "--input_file", type=str, default=default_input, help="Path to input JSON file"
    )
    parser.add_argument(
        "--output_file",
        type=str,
        default=default_output,
        help="Path to output JSON file",
    )
    parser.add_argument(
        "--model",
        type=str,
        default="gpt-4o-mini",
        help="OpenAI model to use (e.g., gpt-4o-mini, gpt-4o)",
    )
    parser.add_argument(
        "--top_k",
        type=int,
        default=5,
        help="Number of top documents/chunks to retrieve",
    )
    parser.add_argument(
        "--full_output",
        action="store_true",
        help="If set, include all retrieved contexts in printed output (for debugging). Default: False",
    )
    parser.add_argument(
        "--output_mode",
        type=str,
        choices=["printed", "contexts"],
        default="printed",
        help="Which contexts to include in the output JSON: 'printed' (1 best doc, <=10 chunks) or 'contexts' (all contexts). Default: printed",
    )

    args = parser.parse_args()

    # Ensure output directory exists
    output_path = Path(args.output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    asyncio.run(
        evaluate_openai(
            input_file=args.input_file,
            output_file=args.output_file,
            model_name=args.model,
            top_k=args.top_k,
            full_output=args.full_output,
            output_mode=args.output_mode,
        )
    )


if __name__ == "__main__":
    main()
