"""
Code Executor

Sandboxed Python code execution using RestrictedPython.
Provides safe execution of user code with limited imports and no file/network access.
Includes resource limits enforcement (memory, CPU, output size).
"""

import asyncio
import io
import logging
import os
import resource
import signal
import sys
import threading
import time
from typing import Any, Dict, Optional

from RestrictedPython import compile_restricted
from RestrictedPython.Eval import default_guarded_getiter
from RestrictedPython.Guards import safe_builtins
from RestrictedPython.PrintCollector import PrintCollector

logger = logging.getLogger(__name__)


class ExecutionTimeout(Exception):
    """Raised when code execution exceeds the timeout limit."""

    pass


class ResourceLimitExceeded(Exception):
    """Raised when code execution exceeds resource limits."""

    pass


class OutputLimitExceeded(Exception):
    """Raised when code execution produces too much output."""

    pass


class LimitedPrintCollector:
    """PrintCollector with output size limits."""

    def __init__(self, max_output_size: int = 1024 * 1024):
        self.txt = []
        self.max_output_size = max_output_size
        self.current_size = 0

    def __call__(self, *args, **kwargs):
        try:
            s = str(args[0]) if args else str(kwargs.get("sep", " "))
            s += kwargs.get("end", "\n")
            new_size = self.current_size + len(s.encode("utf-8"))
            if new_size > self.max_output_size:
                raise OutputLimitExceeded(
                    f"Output exceeds {self.max_output_size} bytes limit"
                )
            self.txt.append(s)
            self.current_size = new_size
        except Exception:
            self.txt.append(str(args) if args else "")


def _set_resource_limits(memory_limit_mb: int, cpu_limit_seconds: int):
    """Set resource limits using the resource module (Unix only)."""
    if sys.platform != "win32":
        soft_memory = memory_limit_mb * 1024 * 1024
        hard_memory = soft_memory

        try:
            resource.setrlimit(resource.RLIMIT_AS, (soft_memory, hard_memory))
            logger.debug(f"Set memory limit to {memory_limit_mb} MB")
        except (ValueError, OSError) as e:
            logger.warning(f"Could not set memory limit: {e}")

        try:
            resource.setrlimit(
                resource.RLIMIT_CPU, (cpu_limit_seconds, cpu_limit_seconds + 1)
            )
            logger.debug(f"Set CPU time limit to {cpu_limit_seconds} seconds")
        except (ValueError, OSError) as e:
            logger.warning(f"Could not set CPU limit: {e}")

        try:
            resource.setrlimit(resource.RLIMIT_DATA, (soft_memory, hard_memory))
            logger.debug(f"Set data segment limit to {memory_limit_mb} MB")
        except (ValueError, OSError) as e:
            logger.warning(f"Could not set data limit: {e}")

        try:
            resource.setrlimit(
                resource.RLIMIT_STACK, (soft_memory // 4, hard_memory // 4)
            )
            logger.debug(f"Set stack limit to {memory_limit_mb // 4} MB")
        except (ValueError, OSError) as e:
            logger.warning(f"Could not set stack limit: {e}")


def _execute_in_subprocess(
    code_bytecode,
    restricted_globals,
    locals_dict,
    result_queue,
    memory_limit_mb: int,
    cpu_limit_seconds: int,
    output_limit_bytes: int,
):
    """
    Execute code in a subprocess with resource limits.
    This provides true process isolation on Unix systems.
    """
    try:
        _set_resource_limits(memory_limit_mb, cpu_limit_seconds)

        restricted_globals["_print_"] = LimitedPrintCollector(
            max_output_size=output_limit_bytes
        )

        try:
            exec(code_bytecode, restricted_globals, locals_dict)
            result_queue.put(
                {
                    "success": True,
                    "result": locals_dict.get("_"),
                    "error": None,
                }
            )
        except OutputLimitExceeded as e:
            result_queue.put(
                {
                    "success": False,
                    "result": None,
                    "error": str(e),
                    "exception": {
                        "type": "OutputLimitExceeded",
                        "message": str(e),
                    },
                }
            )
        except Exception as e:
            result_queue.put(
                {
                    "success": False,
                    "result": None,
                    "error": str(e),
                    "exception": {
                        "type": type(e).__name__,
                        "message": str(e),
                    },
                }
            )
    except Exception as e:
        result_queue.put(
            {
                "success": False,
                "result": None,
                "error": str(e),
                "exception": {
                    "type": "SubprocessError",
                    "message": str(e),
                },
            }
        )


class CodeExecutor:
    """Sandboxed Python code executor using RestrictedPython with resource limits."""

    def __init__(
        self,
        timeout: int = 30,
        memory_limit_mb: int = 100,
        output_limit_bytes: int = 1024 * 1024,
        use_subprocess: bool = True,
    ):
        """
        Initialize the code executor.

        Args:
            timeout: Execution timeout in seconds (default: 30)
            memory_limit_mb: Memory limit in megabytes (default: 100)
            output_limit_bytes: Maximum output size in bytes (default: 1MB)
            use_subprocess: Use subprocess for true isolation (default: True, Unix only)
        """
        self.timeout = timeout
        self.memory_limit_mb = memory_limit_mb
        self.output_limit_bytes = output_limit_bytes
        self.use_subprocess = use_subprocess and sys.platform != "win32"

        if self.use_subprocess:
            logger.debug("Using subprocess isolation for code execution")
        else:
            logger.debug("Using thread-based execution (limited isolation)")

    def _execute_code_sync(
        self,
        code_bytecode,
        restricted_globals,
        locals_dict,
        result_holder: Dict[str, Any],
    ):
        """Synchronous execution to run in a thread (fallback for Windows)."""
        restricted_globals["_print_"] = LimitedPrintCollector(
            max_output_size=self.output_limit_bytes
        )
        try:
            exec(code_bytecode, restricted_globals, locals_dict)
            result_holder["result"] = locals_dict.get("_")
            result_holder["error"] = None
        except OutputLimitExceeded as e:
            result_holder["result"] = None
            result_holder["error"] = e
        except Exception as e:
            result_holder["result"] = None
            result_holder["error"] = e

    def _get_restricted_globals(self, globals_dict: Optional[Dict[str, Any]] = None):
        """Create the restricted globals dictionary."""
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
            "_hasattr_": hasattr,
            "_repr_": repr,
        }
        if globals_dict:
            restricted_globals.update(globals_dict)
        return restricted_globals

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
        resource_exceeded = False

        try:
            code_bytecode = compile_restricted(code, "<string>", "exec")
            restricted_globals = self._get_restricted_globals(globals_dict)

            execution_time = 0.0
            output = ""

            if self.use_subprocess and sys.platform != "win32":
                import multiprocessing

                result_queue = multiprocessing.Queue()

                process = multiprocessing.Process(
                    target=_execute_in_subprocess,
                    args=(
                        code_bytecode,
                        restricted_globals,
                        locals_dict,
                        result_queue,
                        self.memory_limit_mb,
                        self.timeout,
                        self.output_limit_bytes,
                    ),
                    daemon=True,
                )

                try:
                    process.start()
                    process.join(timeout=self.timeout + 5)

                    if process.is_alive():
                        timed_out = True
                        process.terminate()
                        try:
                            process.join(timeout=1)
                        except:
                            pass

                    if not result_queue.empty():
                        result = result_queue.get_nowait()
                        if (
                            result.get("exception", {}).get("type")
                            == "OutputLimitExceeded"
                        ):
                            resource_exceeded = True
                        success = result.get("success", False)
                        error = result.get("error")
                        output_result = result.get("result")
                        exception = result.get("exception")
                    else:
                        success = False
                        error = "Process returned no result"
                        output_result = None
                        exception = None

                except Exception as e:
                    success = False
                    error = str(e)
                    output_result = None
                    exception = {"type": "ProcessError", "message": str(e)}

                execution_time = time.time() - start_time
                print_obj = locals_dict.get("_print")
                if print_obj and hasattr(print_obj, "txt"):
                    output = "".join(print_obj.txt)
            else:
                result_holder: Dict[str, Any] = {"result": None, "error": None}
                execution_thread = threading.Thread(
                    target=self._execute_code_sync,
                    args=(
                        code_bytecode,
                        restricted_globals,
                        locals_dict,
                        result_holder,
                    ),
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

                success = result_holder.get("success", False)
                error = result_holder.get("error")
                output_result = result_holder.get("result")
                exception = None
                if error:
                    if isinstance(error, OutputLimitExceeded):
                        resource_exceeded = True
                        exception = {
                            "type": "OutputLimitExceeded",
                            "message": str(error),
                        }
                    elif isinstance(error, Exception):
                        exception = {
                            "type": type(error).__name__,
                            "message": str(error),
                        }

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

            if resource_exceeded:
                return {
                    "success": False,
                    "result": None,
                    "output": output,
                    "error": error,
                    "exception": exception,
                    "execution_time": execution_time,
                }

            if not success and error:
                return {
                    "success": False,
                    "result": None,
                    "output": output,
                    "error": str(error),
                    "exception": exception,
                    "execution_time": execution_time,
                }

            return {
                "success": True,
                "result": output_result,
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

        restricted_globals = self._get_restricted_globals(globals_dict)

        timed_out = False

        try:
            code_bytecode = compile_restricted(expression, "<string>", "eval")

            result_holder: Dict[str, Any] = {"result": None, "error": None}

            def eval_in_thread():
                restricted_globals["_print_"] = LimitedPrintCollector(
                    max_output_size=self.output_limit_bytes
                )
                try:
                    result = eval(code_bytecode, restricted_globals)
                    result_holder["result"] = result
                except OutputLimitExceeded as e:
                    result_holder["error"] = e
                except Exception as e:
                    result_holder["error"] = e

            execution_thread = threading.Thread(target=eval_in_thread, daemon=True)
            execution_thread.start()
            execution_thread.join(timeout=self.timeout)

            if execution_thread.is_alive():
                timed_out = True

            execution_time = time.time() - start_time
            output = ""
            print_obj = restricted_globals.get("_print")
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
                        "message": f"Expression evaluation exceeded {self.timeout} second timeout limit",
                    },
                    "execution_time": execution_time,
                }

            error = result_holder.get("error")
            if error:
                if isinstance(error, OutputLimitExceeded):
                    return {
                        "success": False,
                        "result": None,
                        "output": output,
                        "error": str(error),
                        "exception": {
                            "type": "OutputLimitExceeded",
                            "message": str(error),
                        },
                        "execution_time": execution_time,
                    }
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
    memory_limit_mb: int = 100,
    output_limit_bytes: int = 1024 * 1024,
    globals_dict: Optional[Dict[str, Any]] = None,
    locals_dict: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Convenience function to execute Python code.

    Args:
        code: Python code to execute
        timeout: Execution timeout in seconds (default: 30)
        memory_limit_mb: Memory limit in megabytes (default: 100)
        output_limit_bytes: Maximum output size in bytes (default: 1MB)
        globals_dict: Optional global variables to pass to the code
        locals_dict: Optional local variables to pass to the code

    Returns:
        Dictionary with success, result/output, execution_time, and error info
    """
    executor = CodeExecutor(
        timeout=timeout,
        memory_limit_mb=memory_limit_mb,
        output_limit_bytes=output_limit_bytes,
    )
    return await executor.execute(
        code=code,
        globals_dict=globals_dict,
        locals_dict=locals_dict,
    )
