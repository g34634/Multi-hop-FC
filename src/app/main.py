from src.common.config import Config as AppConfig
from src.retrieval import ChromaRetriever
from src.common import ProgramFCConfig

def format_retrieved_docs_for_prompt(retrieved_docs: list[dict]) -> str:
    chunks = []

    for i, doc in enumerate(retrieved_docs, start=1):
        title = doc["metadata"].get("title", "N/A")
        chunk_id = doc["metadata"].get("chunk_id", doc["id"])
        text = doc["text"]

        chunks.append(
            f"[Doc {i}] title={title} | chunk_id={chunk_id}\n{text}"
        )

    return "\n\n".join(chunks)


def main() -> None:
    cfg = ProgramFCConfig(
        planner_model="gpt-5.3-codex",
        executor_model="Qwen/Qwen3-8B",
        top_k=10,
        num_programs=5,
        planner_temperature=0.7,
        planner_max_output_tokens=800,
        executor_max_new_tokens=128,
        error_log_path="outputs/logs/programfc_errors.jsonl",
        closed_book=False,
    )

    app_cfg = AppConfig()

    retriever = ChromaRetriever(
        config=app_cfg,
        top_k=cfg.top_k,
    )

    claim = "The Godfather was directed by Christopher Nolan."

    retrieved_docs = retriever.retrieve_for_claim(claim)
    context_text = format_retrieved_docs_for_prompt(retrieved_docs)

    print("\n[Retrieved Docs]")
    for i, doc in enumerate(retrieved_docs, start=1):
        print(f"\n--- Doc {i} ---")
        print("id:", doc["id"])
        print("distance:", doc["distance"])
        print("metadata:", doc["metadata"])
        print("text:", doc["text"])

    print("\n[Context for Prompt]")
    print(context_text)