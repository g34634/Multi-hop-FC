from src.retrieval.chroma_builder import get_or_create_collection
from src.common.config import Config


def retrieve_for_claim(claim: str, top_k: int, config: Config) -> dict:
    collection = get_or_create_collection(config)
    result = collection.query(
        query_texts=[claim],
        n_results=top_k,
    )
    return result


def batch_retrieve(claim_rows: list[dict], top_k: int, config: Config) -> list[dict]:
    outputs = []

    for row in claim_rows:
        claim = row["claim"]
        retrieval = retrieve_for_claim(claim, top_k=top_k, config=config)

        outputs.append(
            {
                "uid": row["uid"],
                "claim": claim,
                "gold_chunk_ids": row.get("gold_chunk_ids", []),
                "retrieved_ids": retrieval.get("ids", [[]])[0],
                "retrieved_docs": retrieval.get("documents", [[]])[0],
                "retrieved_metadatas": retrieval.get("metadatas", [[]])[0],
                "distances": retrieval.get("distances", [[]])[0],
            }
        )

    return outputs