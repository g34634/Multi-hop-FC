"""
사용 예시.

Retriever 교체가 핵심 — LangChain 덕분에 한 줄로 가능:
  - FAISS:          vectorstore.as_retriever(search_kwargs={"k": 10})
  - Chroma:         Chroma(...).as_retriever(...)
  - BM25:           BM25Retriever.from_documents(docs, k=10)
  - Elasticsearch:  ElasticSearchBM25Retriever(...)
"""
from src.common.config import ProgramFCConfig
from src.reasoning.orchestrator import ProgramFactChecker
# from src.retrieval.retriever import PlaceholderRetriever # 실제 검색기로 교체


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

    # -------------------------------------------------------
    # 여기만 바꾸면 retriever 교체 완료:
    #
    #   from langchain_community.vectorstores import FAISS
    #   from langchain_openai import OpenAIEmbeddings
    #   vectorstore = FAISS.load_local("my_index", OpenAIEmbeddings())
    #   retriever = vectorstore.as_retriever(search_kwargs={"k": 10})
    # -------------------------------------------------------
    retriever = PlaceholderRetriever()

    checker = ProgramFactChecker(cfg, retriever=retriever)

    claim = "Both James Cameron and the director of the film Interstellar were born in Canada."
    result = checker.fact_check(claim)

    print("=" * 80)
    print("CLAIM:", result.claim)
    print("FINAL LABEL:", result.final_label)
    print("CANDIDATE LABELS:", result.candidate_labels)
    print("=" * 80)

    for trace in result.traces:
        print(f"\n[Candidate {trace.candidate_index}] success={trace.success} final={trace.final_label}")
        print(trace.program_text)
        for step in trace.steps:
            print(f"  - step#{step['index']} {step['function']} -> {step['variable']} = {step['output']}")


if __name__ == "__main__":
    main()
