from __future__ import annotations

from typing import Optional, Any, List

from src.common.config import Config

from src.retrieval.chroma_builder import get_or_create_collection
from src.retrieval.bm25_engine import BM25Engine

class BM25Retriever:
    """BM25 기반 Retriever"""

    def __init__(self, config: Config, top_k: int = 10) -> None:
        self.config = config
        self.top_k = top_k
        self.engine = BM25Engine(config)

    def build_from_chunks(self, chunks: List[dict]) -> None:
        """외부에서 준비한 chunks로 인덱스 생성/갱신."""
        self.engine.build_index(chunks)

    def _normalize(self, raw: dict) -> List[dict]:
        """bm25_engine.query 반환을 평탄화하여 리스트로 변환."""
        ids = raw.get("ids", [[]])[0]
        docs = raw.get("documents", [[]])[0]
        metas = raw.get("metadatas", [[]])[0]
        scores = raw.get("distances", [[]])[0]

        results = []
        for i, text in enumerate(docs):
            results.append({
                "id": ids[i] if i < len(ids) else None,
                "text": text,
                "metadata": metas[i] if i < len(metas) else {},
                "score": scores[i] if i < len(scores) else None,
            })
        return results

    def retrieve_for_claim(self, claim: str, top_k: Optional[int] = None) -> List[dict[str, Any]]:
        k = top_k or self.top_k
        raw = self.engine.query(claim, n_results=k)
        return self._normalize(raw)[:k]

    def invoke(self, query: str) -> List[dict[str, Any]]:
        return self.retrieve_for_claim(query)

    def batch_retrieve(self, claim_rows: List[dict[str, Any]], top_k: Optional[int] = None) -> List[dict[str, Any]]:
        outputs = []
        for row in claim_rows:
            uid = row.get("uid")
            claim = row.get("claim", "")
            retrieved = self.retrieve_for_claim(claim, top_k=top_k)
            outputs.append({
                "uid": uid,
                "claim": claim,
                "gold_chunk_ids": row.get("gold_chunk_ids", []),
                "retrieved_docs": retrieved,
            })
        return outputs
    

class ChromaRetriever:
    """
    chroma db 기반 dense retriever 
    """
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