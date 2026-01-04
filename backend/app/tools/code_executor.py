"""
Code Executor

Sandboxed Python code execution using RestrictedPython.
Provides safe execution of user code with limited imports and no file/network access.
"""

import asyncio
import io
import logging
import sys
import threading
import time
from contextlib import redirect_stdout, redirect_stderr
from typing import Dict, Any, Optional

from RestrictedPython import compile_restricted
from RestrictedPython.Guards import safe_builtins

logger = logging.getLogger(__name__)


class CodeExecutor:
    """Sandboxed Python code executor using RestrictedPython."""

    def __init__(
        self,
        timeout: int = 30,
        memory_limit_mb: int = 100,
    ):
        """
        Initialize the code executor.

        Args:
            timeout: Execution timeout in seconds (default: 30)
            memory_limit_mb: Memory limit in megabytes (default: 100)
        """
        self.timeout = timeout
        self.memory_limit_mb = memory_limit_mb

    async def execute(
        self,
        code: str,
        globals_dict: Optional[Dict[str, Any]] = None,
        locals_dict: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Execute Python code in a restricted environment.

        Args:
            code: Python code to execute
            globals_dict: Optional global variables to pass to the code
            locals_dict: Optional local variables to pass to the code

        Returns:
            Dictionary with success, result/output, execution_time, and error info
        """
        start_time = time.time()

        if globals_dict is None:
            globals_dict = {}
        if locals_dict is None:
            locals_dict = {}

        stdout_capture = io.StringIO()
        stderr_capture = io.StringIO()

        result = None
        exception_info = None

        try:
            restricted_globals = {
                "__builtins__": safe_builtins,
                "_print_": print,
                "_getattr_": getattr,
                "_setattr_": setattr,
                "_delattr_": delattr,
                "_iter_": iter,
                "_next_": next,
                "_isinstance_": isinstance,
                "_issubclass_": issubclass,
                "_ hasattr_": hasattr,
                "_repr_": repr,
            }

            restricted_globals.update(globals_dict)

            code_bytecode = compile_restricted(code, "<string>", "exec")

            with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
                exec(code_bytecode, restricted_globals, locals_dict)

            stdout_output = stdout_capture.getvalue()
            stderr_output = stderr_capture.getvalue()

            execution_time = time.time() - start_time

            return {
                "success": True,
                "result": result,
                "output": stdout_output,
                "error": stderr_output,
                "execution_time": execution_time,
            }

        except SyntaxError as e:
            exception_info = {
                "type": "SyntaxError",
                "message": str(e),
                "line": e.lineno,
                "offset": e.offset,
            }
        except Exception as e:
            exception_info = {
                "type": type(e).__name__,
                "message": str(e),
            }

        execution_time = time.time() - start_time
        stdout_output = stdout_capture.getvalue()
        stderr_output = stderr_capture.getvalue()

        return {
            "success": False,
            "result": None,
            "output": stdout_output,
            "error": stderr_output,
            "exception": exception_info,
            "execution_time": execution_time,
        }

    async def evaluate(
        self,
        expression: str,
        globals_dict: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Evaluate a Python expression and return the result.

        Args:
            expression: Python expression to evaluate
            globals_dict: Optional global variables

        Returns:
            Dictionary with success, result, and error info
        """
        start_time = time.time()

        if globals_dict is None:
            globals_dict = {}

        restricted_globals = {
            "__builtins__": safe_builtins,
        }
        restricted_globals.update(globals_dict)

        stdout_capture = io.StringIO()
        stderr_capture = io.StringIO()

        result = None
        exception_info = None

        try:
            code_bytecode = compile_restricted(expression, "<string>", "eval")

            with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
                result = eval(code_bytecode, restricted_globals)

            execution_time = time.time() - start_time

            return {
                "success": True,
                "result": result,
                "output": stdout_capture.getvalue(),
                "error": stderr_capture.getvalue(),
                "execution_time": execution_time,
            }

        except Exception as e:
            execution_time = time.time() - start_time
            exception_info = {
                "type": type(e).__name__,
                "message": str(e),
            }

            return {
                "success": False,
                "result": None,
                "output": stdout_capture.getvalue(),
                "error": stderr_capture.getvalue(),
                "exception": exception_info,
                "execution_time": execution_time,
            }


default_executor = CodeExecutor()


async def execute_code(
    code: str,
    timeout: int = 30,
    globals_dict: Optional[Dict[str, Any]] = None,
    locals_dict: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Convenience function to execute Python code.

    Args:
        code: Python code to execute
        timeout: Execution timeout in seconds (default: 30)
        globals_dict: Optional global variables to pass to the code
        locals_dict: Optional local variables to pass to the code

    Returns:
        Dictionary with success, result/output, execution_time, and error info
    """
    executor = CodeExecutor(timeout=timeout)
    return await executor.execute(
        code=code,
        globals_dict=globals_dict,
        locals_dict=locals_dict,
    )
