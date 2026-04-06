from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import List, Optional

from langchain_core.retrievers import BaseRetriever

from src.common.config import ProgramFCConfig
from src.common.data import ExecutionTrace, FactCheckResult
from src.common.errors import ErrorLogger
from src.common.llm import create_executor_llm, create_planner_llm
from src.reasoning.executor import ProgramExecutor
from src.reasoning.planner import Planner
from src.reasoning.modules.question import QuestionModule
from src.reasoning.modules.verify import VerifyModule
from src.reasoning.modules.predict import PredictModule


class ProgramFactChecker:
    def __init__(self, cfg: ProgramFCConfig, retriever: Optional[BaseRetriever] = None):
        self.cfg = cfg

        # 로그 폴더 자동 생성
        log_path = Path(cfg.error_log_path)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        self.error_logger = ErrorLogger(log_path)

        self._planner_llm = create_planner_llm(cfg)
        self._executor_llm = create_executor_llm(cfg)

        self.planner = Planner(cfg, llm=self._planner_llm)
        self.predict = PredictModule()

        self._build_executor(retriever)

    def _build_executor(self, retriever: Optional[BaseRetriever]) -> None:
        question = QuestionModule(
            llm=self._executor_llm, retriever=retriever,
            top_k=self.cfg.top_k, closed_book=self.cfg.closed_book,
        )
        verify = VerifyModule(
            llm=self._executor_llm, retriever=retriever,
            top_k=self.cfg.top_k, closed_book=self.cfg.closed_book,
        )
        self.executor = ProgramExecutor(
            cfg=self.cfg, question=question, verify=verify,
            predict=self.predict, error_logger=self.error_logger,
        )

    def set_retriever(self, retriever: BaseRetriever) -> None:
        self._build_executor(retriever)

    def fact_check(self, claim: str) -> FactCheckResult:
        candidate_programs = self.planner.generate_programs(claim)
        traces: List[ExecutionTrace] = []
        candidate_labels: List[str] = []

        for candidate_idx, program in enumerate(candidate_programs):
            print(f"\n  [Program {candidate_idx}]\n{program}\n")
            try:
                trace = self.executor.execute(
                    claim=claim, program_text=program, candidate_index=candidate_idx,
                )
                traces.append(trace)
                if trace.final_label is not None:
                    candidate_labels.append(trace.final_label)
            except Exception as e:
                print(f"  [Candidate {candidate_idx} FAILED] {e}")
                continue

        if not candidate_labels:
            raise RuntimeError(
                "All candidate programs failed. Check the error log."
            )

        final_label = Counter(candidate_labels).most_common(1)[0][0]
        return FactCheckResult(
            claim=claim, final_label=final_label,
            candidate_labels=candidate_labels, traces=traces,
        )
