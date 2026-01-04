"""
Calculator Tool

Mathematical expression evaluation with support for common operations,
basic functions, and statistical calculations.
"""

import ast
import logging
import math
import operator
import re
from functools import reduce
from typing import Any, Callable, Dict, List, Optional, Union

logger = logging.getLogger(__name__)


class Calculator:
    """Mathematical expression calculator with safe evaluation."""

    def __init__(self):
        """Initialize the calculator with available operations."""
        self.operators: Dict[str, Callable] = {
            "Add": operator.add,
            "Sub": operator.sub,
            "Mult": operator.mul,
            "Div": operator.truediv,
            "FloorDiv": operator.floordiv,
            "Mod": operator.mod,
            "Pow": operator.pow,
            "UAdd": operator.pos,
            "USub": operator.neg,
        }

        self.math_functions: Dict[str, Callable] = {
            "abs": abs,
            "round": round,
            "min": min,
            "max": max,
            "sum": sum,
            "len": len,
            "pow": pow,
            "sqrt": lambda x: x**0.5 if x >= 0 else float("nan"),
            "sin": math.sin,
            "cos": math.cos,
            "tan": math.tan,
            "asin": math.asin,
            "acos": math.acos,
            "atan": math.atan,
            "atan2": math.atan2,
            "sinh": math.sinh,
            "cosh": math.cosh,
            "tanh": math.tanh,
            "degrees": math.degrees,
            "radians": math.radians,
            "log": math.log,
            "log10": math.log10,
            "log2": math.log2,
            "exp": math.exp,
            "expm1": math.expm1,
            "factorial": math.factorial,
            "gcd": math.gcd,
            "floor": math.floor,
            "ceil": math.ceil,
            "trunc": math.trunc,
            "fabs": math.fabs,
            "frexp": math.frexp,
            "ldexp": math.ldexp,
            "modf": math.modf,
            "copysign": math.copysign,
        }

    def evaluate(self, expression: str) -> Dict[str, Any]:
        """
        Evaluate a mathematical expression.

        Args:
            expression: Mathematical expression to evaluate

        Returns:
            Dictionary with success, result, and error info
        """
        try:
            result = self._safe_eval(expression)
            return {
                "success": True,
                "result": result,
                "expression": expression,
            }
        except Exception as e:
            logger.error(f"Calculation failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "expression": expression,
            }

    def _safe_eval(self, expression: str) -> Any:
        """
        Safely evaluate a mathematical expression.

        Args:
            expression: Expression to evaluate

        Returns:
            Result of the evaluation
        """
        expression = expression.strip()

        expression = re.sub(r"\s+", "", expression)

        if not re.match(r"^[0-9+\-*/().eE, ]+$", expression):
            raise ValueError("Invalid characters in expression")

        math_constants = {
            "pi": math.pi,
            "e": math.e,
            "tau": math.tau,
            "inf": float("inf"),
        }

        for const_name, const_value in math_constants.items():
            expression = re.sub(
                r"\b" + const_name + r"\b",
                str(const_value),
                expression,
            )

        for func_name, func in self.math_functions.items():
            if func_name in ["pi", "e", "tau", "inf"]:
                continue
            pattern = r"\b" + func_name + r"\("
            expression = re.sub(pattern, f"math.{func_name}(", expression)

        result = eval(expression, {"__builtins__": {}, "math": math}, {})
        return result

    def calculate_list(
        self,
        values: List[float],
        operation: str,
    ) -> Dict[str, Any]:
        """
        Calculate a statistical operation on a list of values.

        Args:
            values: List of numerical values
            operation: Operation to perform (mean, median, mode, std, variance, etc.)

        Returns:
            Dictionary with success, result, and error info
        """
        if not values:
            return {
                "success": False,
                "error": "Empty list",
            }

        try:
            if operation == "mean":
                result = sum(values) / len(values)
            elif operation == "median":
                sorted_values = sorted(values)
                n = len(sorted_values)
                mid = n // 2
                if n % 2 == 0:
                    result = (sorted_values[mid - 1] + sorted_values[mid]) / 2
                else:
                    result = sorted_values[mid]
            elif operation == "mode":
                from collections import Counter

                counter = Counter(values)
                max_count = max(counter.values())
                result = [k for k, v in counter.items() if v == max_count]
                if len(result) == 1:
                    result = result[0]
            elif operation == "std" or operation == "stdev":
                mean = sum(values) / len(values)
                variance = sum((x - mean) ** 2 for x in values) / (len(values) - 1)
                result = math.sqrt(variance)
            elif operation == "variance":
                mean = sum(values) / len(values)
                result = sum((x - mean) ** 2 for x in values) / (len(values) - 1)
            elif operation == "range":
                result = max(values) - min(values)
            elif operation == "sum":
                result = sum(values)
            elif operation == "product":
                result = 1
                for v in values:
                    result *= v
            elif operation == "min":
                result = min(values)
            elif operation == "max":
                result = max(values)
            else:
                return {
                    "success": False,
                    "error": f"Unknown operation: {operation}",
                }

            return {
                "success": True,
                "result": result,
                "operation": operation,
                "values_count": len(values),
            }

        except Exception as e:
            logger.error(f"List calculation failed: {e}")
            return {
                "success": False,
                "error": str(e),
            }


default_calculator = Calculator()


async def calculate(
    expression: str,
) -> Dict[str, Any]:
    """
    Convenience function to evaluate a mathematical expression.

    Args:
        expression: Mathematical expression to evaluate

    Returns:
        Dictionary with success, result, and error info
    """
    return default_calculator.evaluate(expression)
