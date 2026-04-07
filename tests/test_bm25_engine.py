import os
from types import SimpleNamespace

from src.retrieval.bm25_engine import BM25Engine


def test_bm25_basic_rank():
    # Minimal config
    config = SimpleNamespace()
    config.bm25_k1 = 1.5
    config.bm25_b = 0.75
    config.data_dir = os.path.join(os.path.dirname(__file__), "..")
    config.bm25_index_path = os.path.join(os.path.dirname(__file__), "..", "data", "processed", "bm25_test_index_for_test.pkl")

    # Create a tiny corpus where the first doc should match the query best
    chunks = [
        {"id": "c_paris", "text": "Paris is the capital of France and has the Eiffel Tower.", "metadata": {"source": "doc_paris"}},
        {"id": "c_python", "text": "Python is a programming language.", "metadata": {"source": "doc_python"}},
        {"id": "c_sport", "text": "Baseball is a popular sport in the US.", "metadata": {"source": "doc_sport"}},
    ]

    engine = BM25Engine(config)
    engine.build_index(chunks)

    res = engine.query("Which city is known for the Eiffel Tower?", n_results=3)

    # Basic assertions about returned structure
    assert isinstance(res, dict)
    assert "ids" in res and "documents" in res
    ids = res.get("ids", [[]])[0]
    assert len(ids) > 0

    # The top result should be the Paris chunk
    assert ids[0] == "c_paris"
