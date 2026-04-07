from __future__ import annotations

from src.common.config import Config as AppConfig
from src.common.config import ProgramFCConfig
from src.common.documents import serialize_documents
from src.reasoning.orchestrator import ProgramFactChecker
from src.retrieval.retriever import ChromaRetriever


TEST_CLAIM = "Skagen Painter Peder Severin Kr\u00f8yer favored naturalism along with Theodor Esbern Philipsen and the artist Ossian Elgstr\u00f6m studied with in the early 1900s."


def print_retrieved_docs(retrieved_docs: list[dict]) -> None:
    print("\n[Retrieved Docs]")
    for i, doc in enumerate(retrieved_docs, start=1):
        print(f"\n--- Doc {i} ---")
        print("id:", doc.get("id"))
        print("distance:", doc.get("distance"))
        print("metadata:", doc.get("metadata", {}))
        print("text:", doc.get("text", ""))

    print("\n[Context for Prompt]")
    print(serialize_documents(retrieved_docs))


def print_fact_check_result(result) -> None:
    print("\n[Final Result]")
    print("claim:", result.claim)
    print("final_label:", result.final_label)
    print("candidate_labels:", result.candidate_labels)

    for trace in result.traces:
        print(f"\n{'=' * 80}")
        print(f"Candidate {trace.candidate_index} | final_label={trace.final_label}")
        print(f"{'=' * 80}")

        print("\n[Program]")
        print(trace.program_text)

        print("\n[Execution Trace]")
        for step in trace.steps:
            print(
                f"step#{step['index']} "
                f"{step['function']}({step['input']!r})"
            )
            print(f"  -> {step['variable']} = {step['output']}")


def main() -> None:
    cfg = ProgramFCConfig(
        planner_model="gpt-5.3-codex",
        executor_model="Qwen/Qwen3-8B",
        top_k_list=[5],
        num_programs=5,
        planner_temperature=0.7,
        planner_max_output_tokens=800,
        executor_max_new_tokens=128,
        error_log_path="outputs/logs/programfc_errors.jsonl",
        closed_book=False,
    )

    app_cfg = AppConfig()

    # 실제 Chroma 검색기
    retriever = ChromaRetriever(
        config=app_cfg,
        top_k=min(cfg.top_k_list),
    )

    claim = TEST_CLAIM

    # 1) 검색 결과 먼저 확인
    retrieved_docs = retriever.retrieve_for_claim(claim)
    print("\n[Claim]")
    print(claim)
    print_retrieved_docs(retrieved_docs)

    # 2) ProgramFC 전체 파이프라인 실행
    print("\n[ProgramFC] loading models...")
    checker = ProgramFactChecker(cfg=cfg, retriever=retriever)
    print("[ProgramFC] models loaded.")

    result = checker.fact_check(claim)

    # 3) 최종 라벨 + 후보 프로그램 + step trace 출력
    print_fact_check_result(result)


if __name__ == "__main__":
    main()