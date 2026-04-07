"""
Verify 모듈.

evidence(선택) + 단순 주장 → LLM → True/False.
ProgramFC 논문의 Verify() 함수에 해당.
"""
from __future__ import annotations

import re
from typing import Optional, Any

from langchain_core.language_models import BaseLLM
from langchain_core.retrievers import BaseRetriever

from src.common.errors import ProgramFCError
from src.common.documents import serialize_documents

class VerifyModule:
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

    def __call__(self, claim: str) -> bool:
        evidence = self._retrieve(claim)

        if evidence:
            prompt = (
                f"{evidence}\n"
                f"Q: Is it true that {claim}?\n"
                f"Answer with True or False only.\n"
                f"{self.ANSWER_MARKER}"
            )
        else:
            prompt = (
                f"Q: Is it true that {claim}?\n"
                f"Answer with True or False only.\n"
                f"{self.ANSWER_MARKER}"
            )

        raw = self.llm.invoke(prompt)
        text = self._to_text(raw)
        generated = self._extract_generated_text(text=text, prompt=prompt)
        return self._parse_boolean(generated)

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

    @staticmethod
    def _parse_boolean(raw: str) -> bool:
        lines = [ln.strip() for ln in raw.splitlines() if ln.strip()]
        if not lines:
            raise ProgramFCError(
                category="incorrect_execution",
                subtype="invalid_verify_output",
                message="Verify module returned empty text.",
            )

        first = lines[0]
        first = re.sub(
            r"^(the answer is\s*:)\s*",
            "",
            first,
            flags=re.IGNORECASE,
        ).strip()

        normalized = first.lower()

        if normalized.startswith("true"):
            return True
        if normalized.startswith("false"):
            return False

        raise ProgramFCError(
            category="incorrect_execution",
            subtype="invalid_verify_output",
            message=f"Verify module returned non-boolean text: {raw}",
        )
