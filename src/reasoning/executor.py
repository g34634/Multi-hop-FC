"""
프로그램 실행기.

파싱된 각 스텝을 Question/Verify/Predict 모듈에 디스패치.
모듈 내부에 LLM·Retriever 로직이 캡슐화되어 있으므로
이 클래스는 변수 관리 + 에러 로깅 + 흐름 제어만 담당.
"""
from __future__ import annotations

import re
import time
import traceback
from typing import Any, Dict, List

from src.common.config import ProgramFCConfig
from src.common.data import ExecutionTrace, ProgramStep
from src.common.errors import ErrorLogger, ProgramFCError
from src.reasoning.parser import ProgramParser
from src.reasoning.modules.question import QuestionModule
from src.reasoning.modules.verify import VerifyModule
from src.reasoning.modules.predict import PredictModule


class ProgramExecutor:
    VAR_PLACEHOLDER_RE = re.compile(r"\{\s*([A-Za-z_][A-Za-z0-9_]*)\s*\}")

    def __init__(
        self,
        cfg: ProgramFCConfig,
        question: QuestionModule,
        verify: VerifyModule,
        predict: PredictModule,
        error_logger: ErrorLogger,
    ):
        self.cfg = cfg
        self.question = question
        self.verify = verify
        self.predict = predict
        self.error_logger = error_logger

    # ---- public -----------------------------------------------------------

    def execute(self, claim: str, program_text: str, candidate_index: int) -> ExecutionTrace:
        trace = ExecutionTrace(candidate_index=candidate_index, program_text=program_text)
        parser = ProgramParser()
        variables: Dict[str, Any] = {}
        steps = parser.parse(program_text)

        for step in steps:
            try:
                value = self._dispatch(step, variables, program_text)
                variables[step.variable] = value
                trace.steps.append(
                    {
                        "index": step.index,
                        "function": step.function,
                        "variable": step.variable,
                        "input": self._pretty_step_input(step, variables),
                        "output": value,
                    }
                )
            except Exception as exc:
                self.error_logger.log(
                    self._make_error_payload(claim, candidate_index, step, program_text, exc)
                )
                raise

        final_value = variables.get(steps[-1].variable)
        if not isinstance(final_value, bool):
            raise ProgramFCError(
                category="semantic_error",
                subtype="structure",
                message="Final Predict result is not boolean.",
                step_index=steps[-1].index,
                raw_program=program_text,
            )

        trace.final_label = "SUPPORTS" if final_value else "REFUTES"
        trace.success = True
        return trace

    # ---- dispatch ---------------------------------------------------------

    def _dispatch(
        self, step: ProgramStep, variables: Dict[str, Any], program_text: str
    ) -> Any:
        if step.function == "Question":
            rendered = self._resolve_text_argument(step.argument, variables)
            return self.question(rendered)

        if step.function == "Verify":
            rendered = self._resolve_text_argument(step.argument, variables)
            return self.verify(rendered)

        if step.function == "Predict":
            return self.predict(step.argument, variables)

        raise ProgramFCError(
            category="semantic_error",
            subtype="subtask",
            message=f"Unknown subtask: {step.function}",
            step_index=step.index,
            raw_program=program_text,
        )

    # ---- argument resolution ----------------------------------------------

    def _pretty_step_input(self, step: ProgramStep, variables: Dict[str, Any]) -> Any:
        if step.function == "Predict":
            return step.argument
        return self._resolve_text_argument(step.argument, variables)

    def _strip_string_literal(self, raw: str) -> str:
        raw = raw.strip()
        for prefix, quote in [("f\"", "\""), ("f'", "'"), ("\"", "\""), ("'", "'")]:
            if raw.startswith(prefix) and raw.endswith(quote):
                return raw[len(prefix) : -1]
        return raw

    def _resolve_text_argument(self, raw_arg: str, variables: Dict[str, Any]) -> str:
        text = self._strip_string_literal(raw_arg)

        def repl(match: re.Match[str]) -> str:
            name = match.group(1)
            if name not in variables:
                raise ProgramFCError(
                    category="semantic_error",
                    subtype="token",
                    message=f"Missing variable in template substitution: {name}",
                )
            return str(variables[name])

        return self.VAR_PLACEHOLDER_RE.sub(repl, text).strip()

    # ---- error helpers ----------------------------------------------------

    def _make_error_payload(
        self,
        claim: str,
        candidate_index: int,
        step: ProgramStep,
        raw_program: str,
        exc: Exception,
    ) -> Dict[str, Any]:
        if isinstance(exc, ProgramFCError):
            category, subtype, message = exc.category, exc.subtype, exc.message
            step_index = exc.step_index if exc.step_index is not None else step.index
        else:
            category, subtype, message = "incorrect_execution", "runtime", str(exc)
            step_index = step.index

        return {
            "timestamp": time.time(),
            "claim": claim,
            "candidate_index": candidate_index,
            "error_category": category,
            "error_subtype": subtype,
            "message": message,
            "step_index": step_index,
            "step_function": step.function,
            "step_variable": step.variable,
            "step_argument": step.argument,
            "raw_program": raw_program,
            "traceback": traceback.format_exc(),
        }
