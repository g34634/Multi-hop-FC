"""
Question 모듈.

evidence(선택) + 질문 → LLM → 단답 추출.
ProgramFC 논문의 Question() 함수에 해당.
"""
from __future__ import annotations

import re
from typing import Optional, Any

from langchain_core.language_models import BaseLLM
from langchain_core.retrievers import BaseRetriever

from src.common.errors import ProgramFCError
from src.common.documents import serialize_documents

class QuestionModule:
    ANSWER_MARKER = "The answer is:"

    def __init__(
        self,
        llm: BaseLLM,
        retriever: Optional[BaseRetriever] = None,
        top_k: int = 10,
        closed_book: bool = False,
    ):
        self.llm = llm
        self.retriever = retriever
        self.top_k = top_k
        self.closed_book = closed_book

    def __call__(self, question: str) -> str:
        evidence = self._retrieve(question)

        if evidence:
            prompt = (
                f"{evidence}\n"
                f"Q: {question}\n"
                f"Answer with a short entity or phrase only.\n"
                f"Do not output evidence sentences, explanations, or prefixes like [Evidence 1].\n"
                f"{self.ANSWER_MARKER}"
            )
        else:
            prompt = (
                f"Q: {question}\n"
                f"Answer with a short entity or phrase only.\n"
                f"{self.ANSWER_MARKER}"
            )

        raw = self.llm.invoke(prompt)
        text = self._to_text(raw)
        generated = self._extract_generated_text(text=text, prompt=prompt)
        answer = self._clean_answer(generated)

        if not answer:
            raise ProgramFCError(
                category="incorrect_execution",
                subtype="empty_answer",
                message="Question module returned empty answer.",
            )

        if self._looks_like_bad_answer(answer):
            raise ProgramFCError(
                category="incorrect_execution",
                subtype="invalid_question_output",
                message=f"Question module returned non-short answer: {answer}",
            )

        return answer

    def _retrieve(self, query: str) -> str:
        if self.closed_book or self.retriever is None:
            return ""
        docs = self.retriever.invoke(query)
        return serialize_documents(docs[: self.top_k])

    @staticmethod
    def _to_text(raw: Any) -> str:
        if isinstance(raw, str):
            return raw
        content = getattr(raw, "content", None)
        if isinstance(content, str):
            return content
        return str(raw)

    def _extract_generated_text(self, text: str, prompt: str) -> str:
        text = text.strip()
        prompt = prompt.strip()

        if text.startswith(prompt):
            text = text[len(prompt):].lstrip()

        if self.ANSWER_MARKER in text:
            text = text.rsplit(self.ANSWER_MARKER, 1)[-1].strip()

        if "```" in text:
            text = text.split("```", 1)[0].strip()

        return text.strip()

    def _clean_answer(self, text: str) -> str:
        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
        if not lines:
            return ""

        answer = lines[0]

        answer = re.sub(
            r"^(the answer is\s*:)\s*",
            "",
            answer,
            flags=re.IGNORECASE,
        ).strip()

        answer = answer.strip("`").strip().strip("\"'").strip()
        answer = re.sub(r"[.]+$", "", answer).strip()

        return answer

    @staticmethod
    def _looks_like_bad_answer(answer: str) -> bool:
        lowered = answer.lower()

        if lowered.startswith("[evidence"):
            return True
        if lowered.startswith("q:"):
            return True
        if "the answer is:" in lowered:
            return True
        if "\n" in answer:
            return True
        if len(answer.split()) > 12:
            return True

        return False
