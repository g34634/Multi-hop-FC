"""
Predict 모듈.

fact_1 and fact_2 같은 boolean 표현식을 AST로 파싱하여 평가.
LLM 호출 없이 순수 Python으로 동작.
ProgramFC 논문의 Predict() 함수에 해당.
"""
from __future__ import annotations

import ast
from typing import Any, Dict

from src.common.errors import ProgramFCError


class PredictModule:
    def __call__(self, expression: str, variables: Dict[str, Any]) -> bool:
        expr = expression.strip()

        try:
            tree = ast.parse(expr, mode="eval")
        except SyntaxError as exc:
            raise ProgramFCError(
                category="syntactic_error",
                subtype="invalid_predict_expression",
                message=str(exc),
            ) from exc

        return self._eval(tree.body, variables)

    def _eval(self, node: ast.AST, variables: Dict[str, Any]) -> bool:
        if isinstance(node, ast.Name):
            if node.id not in variables:
                raise ProgramFCError(
                    category="semantic_error",
                    subtype="token",
                    message=f"Undefined variable in Predict: {node.id}",
                )
            value = variables[node.id]
            if not isinstance(value, bool):
                raise ProgramFCError(
                    category="semantic_error",
                    subtype="structure",
                    message=f"Predict variable is not boolean: {node.id}={value}",
                )
            return value

        if isinstance(node, ast.Constant) and isinstance(node.value, bool):
            return node.value

        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
            return not self._eval(node.operand, variables)

        if isinstance(node, ast.BoolOp):
            values = [self._eval(v, variables) for v in node.values]
            if isinstance(node.op, ast.And):
                return all(values)
            if isinstance(node.op, ast.Or):
                return any(values)

        raise ProgramFCError(
            category="semantic_error",
            subtype="structure",
            message=f"Unsupported Predict AST node: {ast.dump(node)}",
        )
