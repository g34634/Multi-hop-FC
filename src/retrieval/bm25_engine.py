import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


class BM25Engine:
    """
    BM25 engine backed by Pyserini/Lucene.

    Index format is a Lucene directory (not pickle). This class keeps the
    same query return schema used by the existing retriever pipeline.
    """

    def __init__(self, config):
        self.config = config
        self._searcher = None
        self._set_defaults()
        self.load_index()

    def _set_defaults(self) -> None:
        if not hasattr(self.config, "bm25_k1"):
            setattr(self.config, "bm25_k1", 1.5)
        if not hasattr(self.config, "bm25_b"):
            setattr(self.config, "bm25_b", 0.75)
        if not hasattr(self.config, "bm25_threads"):
            setattr(self.config, "bm25_threads", max(1, (os.cpu_count() or 1) // 2))
        if not hasattr(self.config, "bm25_index_path"):
            try:
                default_path = Path(self.config.data_dir) / "processed" / "bm25_lucene_index"
            except Exception:
                default_path = Path("bm25_lucene_index")
            setattr(self.config, "bm25_index_path", default_path)

        # Backward compatibility: if legacy "*.pkl" is passed, convert it to
        # a directory path for Lucene index files.
        self.config.bm25_index_path = self._normalize_index_path(Path(self.config.bm25_index_path))

    @staticmethod
    def _normalize_index_path(path: Path) -> Path:
        if path.suffix.lower() == ".pkl":
            return path.with_suffix("")
        return path

    @staticmethod
    def _require_pyserini_searcher():
        try:
            from pyserini.search.lucene import LuceneSearcher
        except Exception as e:
            raise RuntimeError(
                "Pyserini is required for BM25 retrieval. "
                "Install with `pip install pyserini` and ensure Java is available."
            ) from e
        return LuceneSearcher

    def _run_indexer(self, input_dir: Path, index_dir: Path) -> None:
        cmd = [
            sys.executable,
            "-m",
            "pyserini.index.lucene",
            "--collection",
            "JsonCollection",
            "--input",
            str(input_dir),
            "--index",
            str(index_dir),
            "--generator",
            "DefaultLuceneDocumentGenerator",
            "--threads",
            str(self.config.bm25_threads),
            "--storePositions",
            "--storeDocvectors",
            "--storeRaw",
        ]

        result = subprocess.run(cmd, check=False, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(
                "Failed to build Pyserini index.\n"
                f"Command: {' '.join(cmd)}\n"
                f"STDOUT:\n{result.stdout}\n"
                f"STDERR:\n{result.stderr}"
            )

    def _write_chunks_to_jsonl(self, chunks: list[dict], output_file: Path) -> None:
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with output_file.open("w", encoding="utf-8") as f:
            for chunk in chunks:
                obj = {
                    "id": str(chunk.get("id", "")),
                    "contents": chunk.get("text", "") or "",
                    "metadata": chunk.get("metadata", {}) or {},
                }
                f.write(json.dumps(obj, ensure_ascii=False) + "\n")

    def build_index_from_jsonl_dir(self, input_dir: Path, overwrite: bool = True) -> None:
        input_dir = Path(input_dir)
        index_dir = self.config.bm25_index_path

        if not input_dir.exists():
            raise FileNotFoundError(f"JSONL input directory not found: {input_dir}")

        has_jsonl = any(input_dir.rglob("*.jsonl"))
        if not has_jsonl:
            raise FileNotFoundError(f"No .jsonl files found under: {input_dir}")

        if overwrite and index_dir.exists():
            shutil.rmtree(index_dir)

        index_dir.parent.mkdir(parents=True, exist_ok=True)
        print(f"[BM25/Pyserini] Building Lucene index at: {index_dir}")
        self._run_indexer(input_dir=input_dir, index_dir=index_dir)
        self.load_index()

    def build_index(self, chunks: list[dict]) -> None:
        """
        Build Lucene BM25 index from in-memory chunks.
        Each chunk is {'id': str, 'text': str, 'metadata': dict}.
        """
        if not chunks:
            print("[BM25/Pyserini] No chunks provided to build index.")
            return

        with tempfile.TemporaryDirectory(prefix="bm25_pyserini_") as tmp_dir:
            input_dir = Path(tmp_dir)
            jsonl_path = input_dir / "corpus.jsonl"
            self._write_chunks_to_jsonl(chunks, jsonl_path)
            self.build_index_from_jsonl_dir(input_dir=input_dir, overwrite=True)

    def load_index(self) -> None:
        index_dir = self.config.bm25_index_path
        if not index_dir.exists():
            return

        LuceneSearcher = self._require_pyserini_searcher()
        self._searcher = LuceneSearcher(str(index_dir))
        self._searcher.set_bm25(k1=float(self.config.bm25_k1), b=float(self.config.bm25_b))
        print(f"[BM25/Pyserini] Index loaded from {index_dir}")

    def query(self, query_text: str, n_results: int = 5) -> dict[str, list[list[Any]]]:
        if self._searcher is None:
            return {"ids": [[]], "documents": [[]], "metadatas": [[]], "distances": [[]]}

        hits = self._searcher.search(query_text, k=n_results)

        ids: list[str] = []
        docs: list[str] = []
        metas: list[dict] = []
        scores: list[float] = []

        for hit in hits:
            doc = self._searcher.doc(hit.docid)
            text = ""
            metadata: dict[str, Any] = {}
            chunk_id = hit.docid

            if doc is not None and doc.raw():
                try:
                    payload = json.loads(doc.raw())
                    chunk_id = str(payload.get("id", hit.docid))
                    text = payload.get("contents", "") or ""
                    metadata = payload.get("metadata", {}) or {}
                except Exception:
                    text = ""
                    metadata = {}

            ids.append(chunk_id)
            docs.append(text)
            metas.append(metadata)
            scores.append(float(hit.score))

        return {
            "ids": [ids],
            "documents": [docs],
            "metadatas": [metas],
            "distances": [scores],
        }