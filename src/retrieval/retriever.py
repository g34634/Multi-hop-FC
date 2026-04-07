from __future__ import annotations

from typing import Any

from src.retrieval.chroma_builder import get_or_create_collection
from src.common.config import Config

class ChromaRetriever:
    def __init__(self, config: Config, top_k: int = 10) -> None:
        self.config = config
        self.top_k = top_k
        self.collection = get_or_create_collection(config)

    def retrieve_for_claim(
        self,
        claim: str,
        top_k: int | None = None,
    ) -> list[dict[str, Any]]:
        k = top_k if top_k is not None else self.top_k

        result = self.collection.query(
            query_texts=[claim],
            n_results=k,
        )

        ids = result.get("ids", [[]])[0]
        docs = result.get("documents", [[]])[0]
        metadatas = result.get("metadatas", [[]])[0]
        distances = result.get("distances", [[]])[0]

        outputs: list[dict[str, Any]] = []
        for i in range(len(docs)):
            outputs.append(
                {
                    "id": ids[i] if i < len(ids) else None,
                    "text": docs[i],
                    "metadata": metadatas[i] if i < len(metadatas) else {},
                    "distance": distances[i] if i < len(distances) else None,
                }
            )

        return outputs

    def invoke(self, query: str) -> list[dict[str, Any]]:
        return self.retrieve_for_claim(claim=query)

    def batch_retrieve(
        self,
        claim_rows: list[dict[str, Any]],
        top_k: int | None = None,
    ) -> list[dict[str, Any]]:
        outputs: list[dict[str, Any]] = []

        for row in claim_rows:
            claim = row["claim"]
            retrieved_docs = self.retrieve_for_claim(claim=claim, top_k=top_k)

            outputs.append(
                {
                    "uid": row["uid"],
                    "claim": claim,
                    "gold_chunk_ids": row.get("gold_chunk_ids", []),
                    "retrieved_docs": retrieved_docs,
                }
            )

        return outputs