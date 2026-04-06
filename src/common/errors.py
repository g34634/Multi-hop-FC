from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional


@dataclass
class ProgramFCError(Exception):
    category: str
    subtype: str
    message: str
    step_index: Optional[int] = None
    raw_program: Optional[str] = None

    def __str__(self) -> str:
        loc = f" step={self.step_index}" if self.step_index is not None else ""
        return f"[{self.category}/{self.subtype}]{loc} {self.message}"


@dataclass
class ErrorLogger:
    path: Path

    def log(self, payload: Dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")
