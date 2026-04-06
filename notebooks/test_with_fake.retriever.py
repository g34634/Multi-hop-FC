"""
FakeRetriever를 사용한 ProgramFC 테스트.

실행:
  python -m tests.test_with_fake_retriever
"""
from __future__ import annotations

from typing import Dict, List, Optional

from langchain_core.callbacks import CallbackManagerForRetrieverRun
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever

from src.common.config import ProgramFCConfig
from src.reasoning.orchestrator import ProgramFactChecker


# ============================================================
# FakeRetriever
# ============================================================

class FakeRetriever(BaseRetriever):
    evidence_map: Dict[str, List[str]] = {}
    fallback: str = "No relevant evidence found."

    def _get_relevant_documents(
        self,
        query: str,
        *,
        run_manager: Optional[CallbackManagerForRetrieverRun] = None,
    ) -> List[Document]:
        query_lower = query.lower()
        matched: List[Document] = []

        for keyword, texts in self.evidence_map.items():
            if keyword.lower() in query_lower:
                matched.extend(Document(page_content=t) for t in texts)

        return matched if matched else [Document(page_content=self.fallback)]


# ============================================================
# 테스트 케이스
# ============================================================

TEST_1_CLAIM = "Both James Cameron and the director of the film Interstellar were born in Canada."
TEST_1_EVIDENCE = {
    "interstellar": [
        "Interstellar is a 2014 epic science fiction film directed by Christopher Nolan.",
        "Christopher Nolan co-wrote the screenplay with his brother Jonathan Nolan.",
    ],
    "james cameron": [
        "James Francis Cameron was born on August 16, 1954, in Kapuskasing, Ontario, Canada.",
        "He is a Canadian filmmaker known for directing Titanic and Avatar.",
    ],
    "christopher nolan": [
        "Sir Christopher Edward Nolan was born on 30 July 1970 in Westminster, London, England.",
        "He holds both British and American citizenship.",
    ],
    "born in canada": [
        "James Cameron was born in Kapuskasing, Ontario, Canada.",
        "Christopher Nolan was born in Westminster, London, England, not in Canada.",
    ],
}

TEST_2_CLAIM = "Howard University Hospital and Providence Hospital are both located in Washington, D.C."
TEST_2_EVIDENCE = {
    "howard university hospital": [
        "Howard University Hospital is a hospital in Washington, D.C., affiliated with Howard University.",
    ],
    "providence hospital": [
        "Providence Hospital is a historic hospital located in Washington, D.C.",
        "It was founded in 1861 and is one of the oldest hospitals in the District of Columbia.",
    ],
    "washington": [
        "Howard University Hospital is located in Washington, D.C.",
        "Providence Hospital is located in Washington, D.C.",
    ],
}

TEST_3_CLAIM = "Eatza Pizza and Your Pie were not founded in the same state."
TEST_3_EVIDENCE = {
    "eatza pizza": [
        "Eatza Pizza is a restaurant chain that was founded in Atlanta, Georgia.",
    ],
    "your pie": [
        "Your Pie is a fast-casual pizza franchise founded in Athens, Georgia in 2008.",
    ],
    "founded": [
        "Eatza Pizza was founded in Atlanta, Georgia.",
        "Your Pie was founded in Athens, Georgia.",
    ],
}

ALL_TESTS = [
    ("TEST 1 (expect REFUTES)",  TEST_1_CLAIM, TEST_1_EVIDENCE),
    ("TEST 2 (expect SUPPORTS)", TEST_2_CLAIM, TEST_2_EVIDENCE),
    ("TEST 3 (expect REFUTES)",  TEST_3_CLAIM, TEST_3_EVIDENCE),
]


# ============================================================
# 실행
# ============================================================

def run_test(name: str, claim: str, checker: ProgramFactChecker) -> None:
    print(f"\n{'=' * 80}")
    print(f" {name}")
    print(f"{'=' * 80}")
    print(f"[CLAIM] {claim}\n")

    try:
        result = checker.fact_check(claim)

        print(f"[FINAL LABEL]      {result.final_label}")
        print(f"[CANDIDATE LABELS] {result.candidate_labels}")

        for trace in result.traces:
            print(f"\n  --- Candidate {trace.candidate_index} (label={trace.final_label}) ---")
            print(f"  Program:")
            for line in trace.program_text.splitlines():
                print(f"    {line}")
            for step in trace.steps:
                print(f"    step#{step['index']} {step['function']}(\"{step['input']}\")")
                print(f"      -> {step['variable']} = {step['output']}")

    except RuntimeError as e:
        print(f"[FAILED] {e}")


def main() -> None:
    cfg = ProgramFCConfig(
        planner_model="gpt-5.3-codex",
        executor_model="Qwen/Qwen3-8B",
        top_k=5,
        num_programs=3,
        planner_temperature=0.7,
        planner_max_output_tokens=800,
        executor_max_new_tokens=128,
        error_log_path="outputs/logs/programfc_errors.jsonl",
        closed_book=False,
    )

    # 모델 한 번만 로드
    print("Loading models...")
    checker = ProgramFactChecker(cfg)
    print("Models loaded.\n")

    # 테스트마다 retriever만 교체
    for name, claim, evidence in ALL_TESTS:
        checker.set_retriever(FakeRetriever(evidence_map=evidence))
        run_test(name, claim, checker)


if __name__ == "__main__":
    main()
