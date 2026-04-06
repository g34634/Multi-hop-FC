from __future__ import annotations

import ast
import re
from typing import List

from src.common.data import ProgramStep
from src.common.errors import ProgramFCError


class ProgramParser:
    ASSIGN_RE = re.compile(
        r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(Question|Verify|Predict)\((.*)\)\s*$"
    )
    PLACEHOLDER_RE = re.compile(r"\{\s*([A-Za-z_][A-Za-z0-9_]*)\s*\}")

    def parse(self, raw_program: str) -> List[ProgramStep]:
        lines = [ln.rstrip() for ln in raw_program.splitlines() if ln.strip()]
        steps: List[ProgramStep] = []

        for idx, line in enumerate(lines):
            if line.strip().startswith("#"):
                continue
            match = self.ASSIGN_RE.match(line)
            if not match:
                raise ProgramFCError(
                    category="syntactic_error",
                    subtype="parse_failure",
                    message=f"Cannot parse line: {line}",
                    step_index=idx,
                    raw_program=raw_program,
                )
            var, fn_name, arg = match.groups()
            steps.append(
                ProgramStep(
                    variable=var,
                    function=fn_name,
                    argument=arg.strip(),
                    raw_line=line,
                    index=idx,
                )
            )

        self._validate(steps, raw_program)
        return steps

    def _validate(self, steps: List[ProgramStep], raw_program: str) -> None:
        if not steps:
            raise ProgramFCError(
                category="syntactic_error",
                subtype="empty_program",
                message="Generated program is empty.",
                raw_program=raw_program,
            )

        seen_vars: set[str] = set()
        defined_vars: set[str] = set()

        for i, step in enumerate(steps):
            if step.variable in seen_vars:
                raise ProgramFCError(
                    category="semantic_error",
                    subtype="structure",
                    message=f"Duplicate variable assignment: {step.variable}",
                    step_index=i,
                    raw_program=raw_program,
                )
            seen_vars.add(step.variable)

            if step.function not in {"Question", "Verify", "Predict"}:
                raise ProgramFCError(
                    category="semantic_error",
                    subtype="subtask",
                    message=f"Unsupported function: {step.function}",
                    step_index=i,
                    raw_program=raw_program,
                )

            unresolved = self._referenced_variables(step.argument) - defined_vars
            if unresolved:
                raise ProgramFCError(
                    category="semantic_error",
                    subtype="token",
                    message=f"Undefined variables referenced: {sorted(unresolved)}",
                    step_index=i,
                    raw_program=raw_program,
                )

            if step.function == "Predict" and i != len(steps) - 1:
                raise ProgramFCError(
                    category="semantic_error",
                    subtype="structure",
                    message="Predict must be the last step.",
                    step_index=i,
                    raw_program=raw_program,
                )

            if step.function != "Predict" and step.variable.lower() == "label" and i != len(steps) - 1:
                raise ProgramFCError(
                    category="semantic_error",
                    subtype="structure",
                    message="label variable appeared before the final step.",
                    step_index=i,
                    raw_program=raw_program,
                )

            defined_vars.add(step.variable)

        if steps[-1].function != "Predict":
            raise ProgramFCError(
                category="semantic_error",
                subtype="structure",
                message="Final step must be Predict(...).",
                step_index=len(steps) - 1,
                raw_program=raw_program,
            )

    def _referenced_variables(self, arg: str) -> set[str]:
        names = set(self.PLACEHOLDER_RE.findall(arg))
        try:
            tree = ast.parse(arg, mode="eval")
            names |= {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}
        except SyntaxError:
            pass
        return {n for n in names if n not in {"True", "False", "and", "or", "not"}}
