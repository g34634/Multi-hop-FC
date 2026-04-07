from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ProgramStep:
    variable: str
    function: str
    argument: str
    raw_line: str
    index: int


@dataclass
class ExecutionTrace:
    candidate_index: int
    program_text: str
    steps: List[Dict[str, Any]] = field(default_factory=list)
    final_label: Optional[str] = None
    success: bool = False


@dataclass
class FactCheckResult:
    claim: str
    final_label: str
    candidate_labels: List[str]
    traces: List[ExecutionTrace]
