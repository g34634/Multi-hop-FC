from __future__ import annotations

import re
from typing import Optional, Any

from langchain_core.language_models import BaseLLM
from langchain_core.retrievers import BaseRetriever

from src.common.documents import serialize_documents


class QuestionModule:
    ANSWER_MARKER = "The answer is:"
    NOT_FOUND_TOKEN = "NOT_FOUND"
    FALLBACK_ANSWER = "Unknown"

    def __init__(
        self,
        llm: BaseLLM,
        retriever: Optional[BaseRetriever] = None,
        top_k: int = 5,
        closed_book: bool = False,
    ):
        self.llm = llm
        self.retriever = retriever
        self.top_k = top_k
        self.closed_book = closed_book

    def __call__(self, question: str) -> str:
        evidence = self._retrieve(question)
        prompt = self._build_prompt(question=question, evidence=evidence)

        raw = self.llm.invoke(prompt)
        text = self._to_text(raw)
        generated = self._extract_generated_text(text=text, prompt=prompt)
        answer = self._clean_answer(generated)
        answer = self._normalize_sentence_like_answer(answer)

        if not answer or answer.upper() == self.NOT_FOUND_TOKEN:
            return self.FALLBACK_ANSWER

        return answer

    def _build_prompt(self, question: str, evidence: str) -> str:
        instruction = (
            "Return one short entity or phrase.\n"
            f"If the answer is not explicitly supported, return ONLY: {self.NOT_FOUND_TOKEN}\n"
            "Do not explain.\n"
            f"{self.ANSWER_MARKER}"
        )

        if evidence:
            return f"{evidence}\nQ: {question}\n{instruction}"

        return f"Q: {question}\n{instruction}"

    def _retrieve(self, query: str) -> str:
        if self.closed_book or self.retriever is None:
            return ""

        docs = self.retriever.invoke(query)
        if not docs:
            return ""

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

        answer = re.sub(
            r"^(answer\s*:)\s*",
            "",
            answer,
            flags=re.IGNORECASE,
        ).strip()

        answer = answer.strip("`").strip().strip("\"'").strip()
        answer = re.sub(r"[.]+$", "", answer).strip()

        return answer

    def _normalize_sentence_like_answer(self, answer: str) -> str:
        lowered = answer.lower().strip()

        if lowered in {
            "unknown",
            "not found",
            "cannot be determined",
            "cannot determine",
            "insufficient information",
            "not enough information",
            "no direct mention",
            "not mentioned",
        }:
            return self.NOT_FOUND_TOKEN

        marker_patterns = [
            r"(?i)\bthe answer is\b\s*[:\-]?\s*(.+)$",
            r"(?i)\banswer\b\s*[:\-]?\s*(.+)$",
        ]
        for pattern in marker_patterns:
            match = re.search(pattern, answer)
            if match:
                candidate = match.group(1).strip()
                candidate = candidate.strip("`").strip().strip("\"'").strip()
                candidate = re.sub(r"[.]+$", "", candidate).strip()
                if candidate:
                    return candidate

        return answer