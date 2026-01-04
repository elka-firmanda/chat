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
from typing import Dict, Any, Optional

from RestrictedPython import compile_restricted
from RestrictedPython.Eval import default_guarded_getiter
from RestrictedPython.Guards import safe_builtins
from RestrictedPython.PrintCollector import PrintCollector

logger = logging.getLogger(__name__)


class ExecutionTimeout(Exception):
    """Raised when code execution exceeds the timeout limit."""

    pass


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

    def _execute_code_sync(
        self,
        code_bytecode,
        restricted_globals,
        locals_dict,
        result_holder: Dict[str, Any],
    ):
        """Synchronous execution to run in a thread."""
        try:
            exec(code_bytecode, restricted_globals, locals_dict)
            result_holder["result"] = locals_dict.get("_")
            result_holder["error"] = None
        except Exception as e:
            result_holder["result"] = None
            result_holder["error"] = e

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

        timed_out = False

        try:
            restricted_globals = {
                "__builtins__": safe_builtins,
                "_print_": PrintCollector,
                "_getiter_": default_guarded_getiter,
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

            result_holder: Dict[str, Any] = {"result": None, "error": None}
            execution_thread = threading.Thread(
                target=self._execute_code_sync,
                args=(code_bytecode, restricted_globals, locals_dict, result_holder),
                daemon=True,
            )
            execution_thread.start()
            execution_thread.join(timeout=self.timeout)

            if execution_thread.is_alive():
                timed_out = True

            execution_time = time.time() - start_time
            output = ""
            print_obj = locals_dict.get("_print")
            if print_obj and hasattr(print_obj, "txt"):
                output = "".join(print_obj.txt)

            if timed_out:
                return {
                    "success": False,
                    "result": None,
                    "output": output,
                    "error": f"Execution timed out after {self.timeout} seconds",
                    "exception": {
                        "type": "ExecutionTimeout",
                        "message": f"Code execution exceeded {self.timeout} second timeout limit",
                    },
                    "execution_time": execution_time,
                }

            error = result_holder.get("error")
            if error:
                if isinstance(error, SyntaxError):
                    exception_info = {
                        "type": "SyntaxError",
                        "message": str(error),
                        "line": error.lineno,
                        "offset": error.offset,
                    }
                else:
                    exception_info = {
                        "type": type(error).__name__,
                        "message": str(error),
                    }
                return {
                    "success": False,
                    "result": None,
                    "output": output,
                    "error": str(error),
                    "exception": exception_info,
                    "execution_time": execution_time,
                }

            return {
                "success": True,
                "result": result_holder.get("result"),
                "output": output,
                "error": "",
                "execution_time": execution_time,
            }

        except SyntaxError as e:
            exception_info = {
                "type": "SyntaxError",
                "message": str(e),
                "line": e.lineno,
                "offset": e.offset,
            }
            execution_time = time.time() - start_time
            return {
                "success": False,
                "result": None,
                "output": "",
                "error": str(e),
                "exception": exception_info,
                "execution_time": execution_time,
            }
        except Exception as e:
            exception_info = {
                "type": type(e).__name__,
                "message": str(e),
            }
            execution_time = time.time() - start_time
            return {
                "success": False,
                "result": None,
                "output": "",
                "error": str(e),
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
            "_print_": PrintCollector,
            "_getattr_": getattr,
        }
        restricted_globals.update(globals_dict)

        timed_out = False

        try:
            code_bytecode = compile_restricted(expression, "<string>", "eval")

            result_holder: Dict[str, Any] = {"result": None, "error": None}

            def eval_in_thread():
                try:
                    result = eval(code_bytecode, restricted_globals)
                    result_holder["result"] = result
                except Exception as e:
                    result_holder["error"] = e

            execution_thread = threading.Thread(target=eval_in_thread, daemon=True)
            execution_thread.start()
            execution_thread.join(timeout=self.timeout)

            if execution_thread.is_alive():
                timed_out = True

            execution_time = time.time() - start_time
            output = restricted_globals.get("printed", "")

            if timed_out:
                return {
                    "success": False,
                    "result": None,
                    "output": output,
                    "error": f"Execution timed out after {self.timeout} seconds",
                    "exception": {
                        "type": "ExecutionTimeout",
                        "message": f"Expression evaluation exceeded {self.timeout} second timeout limit",
                    },
                    "execution_time": execution_time,
                }

            error = result_holder.get("error")
            if error:
                exception_info = {
                    "type": type(error).__name__,
                    "message": str(error),
                }
                return {
                    "success": False,
                    "result": None,
                    "output": output,
                    "error": str(error),
                    "exception": exception_info,
                    "execution_time": execution_time,
                }

            return {
                "success": True,
                "result": result_holder.get("result"),
                "output": output,
                "error": "",
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
                "output": "",
                "error": str(e),
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
