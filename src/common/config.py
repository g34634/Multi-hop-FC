from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ProgramFCConfig:
    # Planner
    planner_model: str = "gpt-5.3-codex"
    openai_api_key: Optional[str] = field(
        default_factory=lambda: os.getenv("OPENAI_API_KEY")
    )
    planner_temperature: float = 0.7
    planner_max_output_tokens: int = 800

    # Executor
    executor_model: str = "Qwen/Qwen3-8B"
    executor_max_new_tokens: int = 128 # 단답 형식을 위해 128토큰으로 고정

    # Retrieval
    top_k: int = 10
    closed_book: bool = False

    # Pipeline
    num_programs: int = 5
    error_log_path: str = "outputs/logs/programfc_errors.jsonl"
