from __future__ import annotations

from typing import Any, List, Optional

from src.common.config import Config
from src.retrieval.bm25_engine import BM25Engine
from src.retrieval.chroma_builder import get_or_create_collection


class BM25Retriever:
    """BM25 기반 검색기."""

    # BM25 검색 엔진을 초기화하고 기본 top-k 값을 설정한다.
    def __init__(self, config: Config, top_k: int = 10) -> None:
        self.config = config
        self.top_k = top_k
        self.engine = BM25Engine(config)

    # 외부에서 준비한 청크로 BM25 인덱스를 생성/갱신한다.
    def build_from_chunks(self, chunks: List[dict]) -> None:
        """입력 청크 목록으로 BM25 인덱스를 생성하거나 갱신한다."""
        self.engine.build_index(chunks)

    # bm25_engine.query 반환 스키마를 문서 리스트 형식으로 평탄화한다.
    def _normalize(self, raw: dict) -> List[dict]:
        """bm25_engine.query 결과를 표준 결과 리스트로 변환한다."""
        ids = raw.get("ids", [[]])[0]
        docs = raw.get("documents", [[]])[0]
        metas = raw.get("metadatas", [[]])[0]
        scores = raw.get("distances", [[]])[0]

        results: list[dict[str, Any]] = []
        for i, text in enumerate(docs):
            results.append(
                {
                    "id": ids[i] if i < len(ids) else None,
                    "text": text,
                    "metadata": metas[i] if i < len(metas) else {},
                    "score": scores[i] if i < len(scores) else None,
                }
            )
        return results

    # 단일 claim에 대해 top-k BM25 검색 결과를 반환한다.
    def retrieve_for_claim(self, claim: str, top_k: Optional[int] = None) -> List[dict[str, Any]]:
        k = top_k or self.top_k
        raw = self.engine.query(claim, n_results=k)
        return self._normalize(raw)[:k]

    # invoke 인터페이스로 단일 질의 검색을 지원한다.
    def invoke(self, query: str) -> List[dict[str, Any]]:
        return self.retrieve_for_claim(query)

    # claim row 목록을 순회하며 배치 검색 결과를 생성한다.
    def batch_retrieve(self, claim_rows: List[dict[str, Any]], top_k: Optional[int] = None) -> List[dict[str, Any]]:
        outputs: list[dict[str, Any]] = []
        for row in claim_rows:
            uid = row.get("uid")
            claim = row.get("claim", "")
            retrieved = self.retrieve_for_claim(claim, top_k=top_k)
            outputs.append(
                {
                    "uid": uid,
                    "claim": claim,
                    "gold_chunk_ids": row.get("gold_chunk_ids", []),
                    "retrieved_docs": retrieved,
                }
            )
        return outputs


class ChromaRetriever:
    """ChromaDB 기반 dense 검색기."""

    # Chroma 컬렉션을 연결하고 기본 top-k 값을 설정한다.
    def __init__(self, config: Config, top_k: int = 10) -> None:
        self.config = config
        self.top_k = top_k
        self.collection = get_or_create_collection(config)

    # 단일 claim에 대해 벡터 유사도 검색 결과를 반환한다.
    def retrieve_for_claim(self, claim: str, top_k: int | None = None) -> list[dict[str, Any]]:
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

    # invoke 인터페이스로 단일 질의 검색을 지원한다.
    def invoke(self, query: str) -> list[dict[str, Any]]:
        return self.retrieve_for_claim(claim=query)

    # claim row 목록을 순회하며 배치 dense 검색 결과를 생성한다.
    def batch_retrieve(self, claim_rows: list[dict[str, Any]], top_k: int | None = None) -> list[dict[str, Any]]:
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
