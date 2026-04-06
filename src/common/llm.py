"""
LLM 생성 팩토리.

LangChain을 쓰는 이유: 모델 백엔드(HuggingFace local, vLLM, OpenAI-compatible 등)를
코드 변경 없이 교체할 수 있도록 BaseLLM 인터페이스로 통일.
"""
from __future__ import annotations

from langchain_core.language_models import BaseLLM
from langchain_community.llms import HuggingFacePipeline
from langchain_openai import ChatOpenAI

from src.common.config import ProgramFCConfig


def create_planner_llm(cfg: ProgramFCConfig) -> ChatOpenAI:
    """Planner: 프로그램 생성용"""
    return ChatOpenAI(
        model=cfg.planner_model,
        api_key=cfg.openai_api_key,
        temperature=cfg.planner_temperature,
        max_tokens=cfg.planner_max_output_tokens,
    )


def create_executor_llm(cfg: ProgramFCConfig) -> BaseLLM:
    """
    Executor LLM
    """
    pipe = HuggingFacePipeline.from_model_id(
        model_id=cfg.executor_model,
        task="text-generation",
        model_kwargs={"trust_remote_code": True, "device_map": "auto", "dtype": "auto"}, # 설정 변경
        pipeline_kwargs={"max_new_tokens": cfg.executor_max_new_tokens, "do_sample": False},
    )
    return pipe
