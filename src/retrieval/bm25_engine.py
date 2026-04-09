import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

try:
    from tqdm.auto import tqdm
except ImportError:  # pragma: no cover
    tqdm = None


class BM25Engine:
    """
    Pyserini/Lucene 기반 BM25 검색 엔진.

    인덱스는 pickle이 아닌 Lucene 디렉터리 형식으로 저장한다.
    기존 retriever 파이프라인과 동일한 query 반환 스키마를 유지한다.
    """

    def __init__(self, config):
        self.config = config
        self._searcher = None
        self._set_defaults()
        self.load_index()

    # BM25 설정 기본값과 인덱스 경로 기본값을 보정한다.
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

        # 하위 호환: legacy "*.pkl" 경로가 들어오면 Lucene 디렉터리 경로로 변환한다.
        self.config.bm25_index_path = self._normalize_index_path(Path(self.config.bm25_index_path))

    @staticmethod
    # legacy pkl 경로를 디렉터리 경로로 정규화한다.
    def _normalize_index_path(path: Path) -> Path:
        if path.suffix.lower() == ".pkl":
            return path.with_suffix("")
        return path

    @staticmethod
    # LuceneSearcher import를 보장하고 실패 시 안내 메시지를 제공한다.
    def _require_pyserini_searcher():
        try:
            from pyserini.search.lucene import LuceneSearcher
        except Exception as e:
            raise RuntimeError(
                "Pyserini is required for BM25 retrieval. "
                "Install with `pip install pyserini` and ensure Java is available."
            ) from e
        return LuceneSearcher

    # pyserini 인덱서 서브프로세스를 실행해 Lucene 인덱스를 생성한다.
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

        expected_docs = int(getattr(self.config, "bm25_expected_docs", 0) or 0)
        pbar = None
        if tqdm is not None:
            pbar_kwargs = {"desc": "Lucene indexing", "unit": "doc", "mininterval": 1.0}
            if expected_docs > 0:
                pbar_kwargs["total"] = expected_docs
            pbar = tqdm(**pbar_kwargs)

        log_lines: list[str] = []
        last_doc_count = 0
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
        )

        assert proc.stdout is not None
        for line in proc.stdout:
            log_lines.append(line.rstrip("\n"))
            doc_count = self._extract_doc_count(line)
            if pbar is not None and doc_count is not None and doc_count >= last_doc_count:
                pbar.update(doc_count - last_doc_count)
                last_doc_count = doc_count

            # 노트북/터미널에서 인덱서 원본 로그를 그대로 확인할 수 있게 출력한다.
            print(line, end="")

        proc.wait()
        if pbar is not None and expected_docs > 0 and proc.returncode == 0 and last_doc_count < expected_docs:
            pbar.update(expected_docs - last_doc_count)
        if pbar is not None:
            pbar.close()

        if proc.returncode != 0:
            stdout_tail = "\n".join(log_lines[-200:])
            raise RuntimeError(
                "Failed to build Pyserini index.\n"
                f"Command: {' '.join(cmd)}\n"
                f"Combined output (tail):\n{stdout_tail}"
            )

    @staticmethod
    # 인덱서 로그 한 줄에서 처리된 문서 수를 추출한다.
    def _extract_doc_count(line: str) -> int | None:
        patterns = (
            r"(\d[\d,]*)\s+docs\s+added",
            r"(\d[\d,]*)\s+documents\s+processed",
            r"documents:\s*(\d[\d,]*)",
        )
        for pattern in patterns:
            match = re.search(pattern, line, flags=re.IGNORECASE)
            if match:
                try:
                    return int(match.group(1).replace(",", ""))
                except ValueError:
                    return None
        return None

    # in-memory 청크를 pyserini 입력 형식(JSONL)으로 저장한다.
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

    # JSONL 디렉터리를 입력으로 Lucene 인덱스를 빌드/재로딩한다.
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
        메모리의 청크 목록에서 Lucene BM25 인덱스를 생성한다.
        각 청크 형식은 {'id': str, 'text': str, 'metadata': dict}이다.
        """
        if not chunks:
            print("[BM25/Pyserini] No chunks provided to build index.")
            return

        with tempfile.TemporaryDirectory(prefix="bm25_pyserini_") as tmp_dir:
            input_dir = Path(tmp_dir)
            jsonl_path = input_dir / "corpus.jsonl"
            self._write_chunks_to_jsonl(chunks, jsonl_path)
            setattr(self.config, "bm25_expected_docs", len(chunks))
            self.build_index_from_jsonl_dir(input_dir=input_dir, overwrite=True)

    # 저장된 Lucene 인덱스를 로딩하고 BM25 파라미터를 적용한다.
    def load_index(self) -> None:
        index_dir = self.config.bm25_index_path
        if not index_dir.exists():
            return

        LuceneSearcher = self._require_pyserini_searcher()
        self._searcher = LuceneSearcher(str(index_dir))
        self._searcher.set_bm25(k1=float(self.config.bm25_k1), b=float(self.config.bm25_b))
        print(f"[BM25/Pyserini] Index loaded from {index_dir}")

    # 쿼리를 실행해 기존 파이프라인 호환 형식으로 검색 결과를 반환한다.
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
