from __future__ import annotations

import re
from typing import List

from langchain_openai import ChatOpenAI

from src.common.config import ProgramFCConfig
from src.reasoning.prompts.hover import HOVER_PROGRAM_PROMPT


class Planner:
    def __init__(self, cfg: ProgramFCConfig, llm: ChatOpenAI):
        self.cfg = cfg
        self.llm = llm

    def generate_programs(self, claim: str) -> List[str]:
        prompt_value = HOVER_PROGRAM_PROMPT.replace("{input_claim}", claim)
        programs: List[str] = []

        for _ in range(self.cfg.num_programs):
            response = self.llm.invoke(prompt_value)
            content = response.content if hasattr(response, "content") else response
            if isinstance(content, list):
                text = "".join(c.get("text", str(c)) if isinstance(c, dict) else str(c) for c in content)
            else:
                text = str(content)
            programs.append(self._normalize_program_text(text.strip()))

        return programs

    @staticmethod
    def _normalize_program_text(text: str) -> str:
        text = text.replace("\r\n", "\n")
        # def program(): 이후만 추출
        matches = list(
            re.finditer(r"def\s+program\s*\(\s*\)\s*:\s*", text, flags=re.IGNORECASE)
        )
        if matches:
            text = text[matches[-1].end():]
        # 마크다운 코드블록, return문 등 제거
        lines = []
        for line in text.splitlines():
            stripped = line.strip()
            if stripped.startswith("```"):
                continue
            if stripped.startswith("return "):
                continue
            lines.append(line)
        return "\n".join(lines).strip()
