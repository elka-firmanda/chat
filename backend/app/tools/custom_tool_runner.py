"""
Custom tool execution engine using RestrictedPython for sandboxed execution.
"""

import ast
import asyncio
import inspect
import sys
import threading
import time
from datetime import datetime
from io import StringIO
from typing import Any, Callable, Dict, List, Optional, Tuple

from RestrictedPython import compile_restricted
from RestrictedPython.Guards import (
    full_write_guard,
)


class CustomToolError(Exception):
    """Base exception for custom tool errors."""

    def __init__(
        self, message: str, tool_name: Optional[str] = None, step: str = "execution"
    ):
        self.message = message
        self.tool_name = tool_name
        self.step = step
        super().__init__(self.message)


class ValidationError(CustomToolError):
    """Raised when tool code validation fails."""

    pass


class ExecutionError(CustomToolError):
    """Raised when tool execution fails."""

    pass


class TimeoutError(CustomToolError):
    """Raised when tool execution times out."""

    pass


def _create_restricted_globals() -> Dict[str, Any]:
    """
    Create a restricted globals dictionary for sandboxed execution.
    Safe, read-only access to built-ins with additional utility functions.
    """
    # Safe built-ins - read-only access
    safe_builtins = {
        # Math functions
        "abs": abs,
        "divmod": divmod,
        "hex": hex,
        "oct": oct,
        "bin": bin,
        "round": round,
        "pow": pow,
        "sum": sum,
        "min": min,
        "max": max,
        "len": len,
        # Type conversion
        "bool": bool,
        "int": int,
        "float": float,
        "str": str,
        "list": list,
        "dict": dict,
        "tuple": tuple,
        "set": set,
        "frozenset": frozenset,
        "bytes": bytes,
        "bytearray": bytearray,
        "type": type,
        "isinstance": isinstance,
        "issubclass": issubclass,
        # Sequence operations
        "range": range,
        "enumerate": enumerate,
        "zip": zip,
        "reversed": reversed,
        "sorted": sorted,
        "filter": filter,
        "map": map,
        "next": next,
        "iter": iter,
        # String operations
        "ord": ord,
        "chr": chr,
        "repr": repr,
        "format": format,
        # Other utilities
        "help": help,
        "id": id,
        "hash": hash,
        "property": property,
        "staticmethod": staticmethod,
        "classmethod": classmethod,
        "super": super,
        "object": object,
        "Exception": Exception,
        "BaseException": BaseException,
        "ValueError": ValueError,
        "TypeError": TypeError,
        "KeyError": KeyError,
        "IndexError": IndexError,
        "AttributeError": AttributeError,
        "RuntimeError": RuntimeError,
        "ZeroDivisionError": ZeroDivisionError,
        "NameError": NameError,
    }

    # Restricted globals
    restricted_globals = {
        "__builtins__": safe_builtins,
        "_print_": print,  # Allow print for debugging (output captured)
        "_write_": full_write_guard,
        # Allow access to these modules (read-only)
        "math": __import__("math"),
        "random": __import__("random"),
        "statistics": __import__("statistics"),
        "datetime": __import__("datetime"),
        "json": __import__("json"),
        "re": __import__("re"),
        "itertools": __import__("itertools"),
        "functools": __import__("functools"),
        "operator": __import__("operator"),
        "collections": __import__("collections"),
        # Prohibited - these will raise errors
        "__import__": None,
        "open": None,
        "eval": None,
        "exec": None,
        "compile": None,
        "__builtins__": None,  # Prevent access to actual builtins dict
    }

    return restricted_globals


def validate_tool_code(code: str) -> Tuple[bool, Optional[str]]:
    """
    Validate custom tool code for syntax and safety.

    Args:
        code: The Python code to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        # Check for syntax errors
        try:
            ast.parse(code)
        except SyntaxError as e:
            return False, f"Syntax error: {e.msg} (line {e.lineno})"

        # Compile to AST and check for restricted patterns
        result = compile_restricted(code, "<string>", "exec")
        if result.errors:
            return False, f"Security restriction: {', '.join(result.errors)}"

        # Additional security checks
        # Check for dangerous patterns
        dangerous_patterns = [
            ("import", "import statement"),
            ("from ", "from-import statement"),
            ("__import__", "__import__ function"),
            ("open(", "file open"),
            ("eval(", "eval function"),
            ("exec(", "exec function"),
            ("compile(", "compile function"),
            ("os.", "os module access"),
            ("sys.", "sys module access"),
            ("subprocess", "subprocess module"),
            ("socket", "socket module"),
            ("requests", "requests module"),
            ("urllib", "urllib module"),
            ("http.", "http module"),
            ("ftplib", "ftplib module"),
            ("smtplib", "smtplib module"),
            ("pickle", "pickle module"),
            ("marshal", "marshal module"),
            ("shelve", "shelve module"),
            ("dbm", "dbm module"),
            ("sqlite3", "sqlite3 module"),
            ("multiprocessing", "multiprocessing module"),
            ("threading", "threading module"),
            ("subprocess", "subprocess module"),
            ("os.system", "os.system"),
            ("os.popen", "os.popen"),
            ("os.exec", "os.exec"),
            ("os.fork", "os.fork"),
        ]

        for pattern, description in dangerous_patterns:
            if pattern in code:
                return False, f"Disallowed pattern: {description}"

        # Check for function definition
        tree = ast.parse(code)
        has_function = False
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                has_function = True
                # Check function signature
                if len(node.args.posonlyargs) > 0:
                    return False, "Positional-only arguments not allowed"
                for arg in node.args.args:
                    if arg.annotation is not None:
                        return (
                            False,
                            "Type annotations not allowed in function parameters",
                        )
                if node.args.vararg is not None:
                    return False, "*args not allowed"
                if node.args.kwarg is not None:
                    # **kwargs is allowed
                    pass
                break

        if not has_function:
            return False, "Code must define at least one function"

        return True, None

    except Exception as e:
        return False, f"Validation error: {str(e)}"


def extract_function_name(code: str) -> Optional[str]:
    """
    Extract the function name from tool code.

    Args:
        code: The Python code

    Returns:
        Function name or None if not found
    """
    try:
        tree = ast.parse(code)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                return node.name
        return None
    except Exception:
        return None


def extract_function_docstring(code: str) -> Optional[str]:
    """
    Extract the docstring from the main function in tool code.

    Args:
        code: The Python code

    Returns:
        Docstring or None if not found
    """
    try:
        tree = ast.parse(code)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.body:
                if isinstance(node.body[0], ast.Expr) and isinstance(
                    node.body[0].value, ast.Constant
                ):
                    return node.body[0].value.s
        return None
    except Exception:
        return None


class ExecutionTimeout(Exception):
    """Raised when execution times out."""

    pass


def _execute_with_timeout(
    func: Callable,
    args: Dict[str, Any],
    timeout: float,
    result_holder: List,
    error_holder: List,
) -> None:
    """
    Execute a function with timeout protection.

    Args:
        func: The function to execute
        args: Arguments to pass to the function
        timeout: Maximum execution time in seconds
        result_holder: List to store result (index 0)
        error_holder: List to store error (index 0)
    """
    try:
        # Create a thread-safe execution context
        def run_execution():
            try:
                # Capture stdout
                old_stdout = sys.stdout
                sys.stdout = StringIO()

                try:
                    # Execute the function
                    result = func(**args)
                    result_holder[0] = result
                finally:
                    # Restore stdout and capture any printed output
                    output = sys.stdout.getvalue()
                    sys.stdout = old_stdout
                    if output:
                        # Store captured output as part of result
                        result_holder.append(("stdout", output))
            except Exception as e:
                error_holder[0] = e

        thread = threading.Thread(target=run_execution)
        thread.daemon = True
        thread.start()
        thread.join(timeout)

        if thread.is_alive():
            # Thread is still running - timeout occurred
            raise ExecutionTimeout(f"Execution timed out after {timeout} seconds")

        if error_holder[0]:
            raise error_holder[0]

    except ExecutionTimeout as e:
        raise TimeoutError(str(e))
    except Exception as e:
        raise ExecutionError(str(e))


async def execute_custom_tool(
    code: str,
    tool_name: str,
    arguments: Dict[str, Any],
    timeout: float = 30.0,
) -> Dict[str, Any]:
    """
    Execute a custom tool with the given arguments.

    Args:
        code: The tool's Python code
        tool_name: The name of the tool to execute
        arguments: Arguments to pass to the tool function
        timeout: Maximum execution time in seconds (default 30)

    Returns:
        Dict with 'success', 'result', and optionally 'output' (captured stdout)

    Raises:
        ValidationError: If tool code is invalid
        ExecutionError: If execution fails
        TimeoutError: If execution times out
    """
    start_time = time.time()

    # Validate the code first
    is_valid, error_msg = validate_tool_code(code)
    if not is_valid:
        raise ValidationError(
            error_msg or "Unknown validation error", tool_name, "validation"
        )

    # Compile the restricted code
    try:
        result = compile_restricted(code, "<string>", "exec")
        if result.errors:
            raise ValidationError(
                f"Compilation errors: {', '.join(result.errors)}",
                tool_name,
                "compilation",
            )
    except Exception as e:
        raise ValidationError(f"Failed to compile: {str(e)}", tool_name, "compilation")

    # Create restricted globals and execute
    restricted_globals = _create_restricted_globals()

    try:
        exec(result.code, restricted_globals)
    except Exception as e:
        raise ValidationError(f"Execution setup failed: {str(e)}", tool_name, "setup")

    # Get the function
    if tool_name not in restricted_globals:
        raise ValidationError(
            f"Function '{tool_name}' not found in code", tool_name, "lookup"
        )

    func = restricted_globals[tool_name]
    if not callable(func):
        raise ValidationError(f"'{tool_name}' is not callable", tool_name, "type")

    # Execute with timeout protection
    result_holder: List = [None]
    error_holder: List = [None]

    # Run in thread pool for true async safety
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(
        None,
        lambda: _execute_with_timeout(
            func, arguments, timeout, result_holder, error_holder
        ),
    )

    execution_time = time.time() - start_time

    # Build result
    response = {
        "success": True,
        "result": result_holder[0],
        "execution_time": execution_time,
    }

    # Check if there was captured stdout
    if len(result_holder) > 1 and result_holder[1][0] == "stdout":
        response["output"] = result_holder[1][1]

    return response


def load_enabled_custom_tools(session) -> Dict[str, Dict[str, Any]]:
    """
    Load all enabled custom tools from the database.

    Args:
        session: SQLAlchemy async session

    Returns:
        Dict mapping tool names to tool info (code, description, enabled)
    """
    from backend.app.db.models import CustomTool

    tools = {}

    async def _load():
        from sqlalchemy import select

        result = await session.execute(
            select(CustomTool).where(CustomTool.enabled == True)
        )
        db_tools = result.scalars().all()

        for tool in db_tools:
            tools[tool.name] = {
                "id": tool.id,
                "name": tool.name,
                "description": tool.description,
                "code": tool.code,
                "enabled": tool.enabled,
                "created_at": tool.created_at.isoformat() if tool.created_at else None,
            }

    # Run synchronously for tools agent initialization
    import asyncio

    asyncio.run(_load())

    return tools


async def list_custom_tools(
    session,
    include_disabled: bool = False,
) -> List[Dict[str, Any]]:
    """
    List all custom tools from the database.

    Args:
        session: SQLAlchemy async session
        include_disabled: Whether to include disabled tools

    Returns:
        List of tool dictionaries
    """
    from sqlalchemy import select
    from backend.app.db.models import CustomTool

    query = select(CustomTool)
    if not include_disabled:
        query = query.where(CustomTool.enabled == True)

    result = await session.execute(query)
    tools = result.scalars().all()

    return [
        {
            "id": tool.id,
            "name": tool.name,
            "description": tool.description,
            "code": tool.code,
            "enabled": tool.enabled,
            "created_at": tool.created_at.isoformat() if tool.created_at else None,
        }
        for tool in tools
    ]


async def get_custom_tool(session, tool_id: str) -> Optional[Dict[str, Any]]:
    """
    Get a single custom tool by ID.

    Args:
        session: SQLAlchemy async session
        tool_id: The tool's UUID

    Returns:
        Tool dict or None if not found
    """
    from sqlalchemy import select
    from backend.app.db.models import CustomTool

    result = await session.execute(select(CustomTool).where(CustomTool.id == tool_id))
    tool = result.scalar_one_or_none()

    if not tool:
        return None

    return {
        "id": tool.id,
        "name": tool.name,
        "description": tool.description,
        "code": tool.code,
        "enabled": tool.enabled,
        "created_at": tool.created_at.isoformat() if tool.created_at else None,
    }


async def create_custom_tool(
    session,
    name: str,
    code: str,
    description: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Create a new custom tool.

    Args:
        session: SQLAlchemy async session
        name: Unique tool name
        code: Python code defining the tool
        description: Optional description

    Returns:
        Created tool dict

    Raises:
        ValidationError: If tool code is invalid or name already exists
    """
    from sqlalchemy import select
    from backend.app.db.models import CustomTool

    # Validate code
    is_valid, error_msg = validate_tool_code(code)
    if not is_valid:
        raise ValidationError(error_msg or "Unknown validation error")

    # Check if name already exists
    result = await session.execute(select(CustomTool).where(CustomTool.name == name))
    existing = result.scalar_one_or_none()
    if existing:
        raise ValidationError(f"Tool with name '{name}' already exists")

    # Create the tool
    tool = CustomTool(
        name=name,
        description=description,
        code=code,
        enabled=True,
    )
    session.add(tool)
    await session.commit()
    await session.refresh(tool)

    return {
        "id": tool.id,
        "name": tool.name,
        "description": tool.description,
        "code": tool.code,
        "enabled": tool.enabled,
        "created_at": tool.created_at.isoformat() if tool.created_at else None,
    }


async def update_custom_tool(
    session,
    tool_id: str,
    name: Optional[str] = None,
    code: Optional[str] = None,
    description: Optional[str] = None,
    enabled: Optional[bool] = None,
) -> Dict[str, Any]:
    """
    Update an existing custom tool.

    Args:
        session: SQLAlchemy async session
        tool_id: The tool's UUID
        name: New name (optional)
        code: New code (optional)
        description: New description (optional)
        enabled: New enabled status (optional)

    Returns:
        Updated tool dict

    Raises:
        ValidationError: If tool code is invalid or name conflicts
    """
    from sqlalchemy import select, update
    from backend.app.db.models import CustomTool

    # Get existing tool
    result = await session.execute(select(CustomTool).where(CustomTool.id == tool_id))
    tool = result.scalar_one_or_none()

    if not tool:
        raise ValidationError(f"Tool with ID '{tool_id}' not found")

    # Validate code if provided
    if code:
        is_valid, error_msg = validate_tool_code(code)
        if not is_valid:
            raise ValidationError(error_msg or "Unknown validation error")

    # Check name uniqueness if changing name
    if name and name != tool.name:
        result = await session.execute(
            select(CustomTool).where(CustomTool.name == name)
        )
        existing = result.scalar_one_or_none()
        if existing:
            raise ValidationError(f"Tool with name '{name}' already exists")
        tool.name = name

    # Update fields
    if code is not None:
        tool.code = code
    if description is not None:
        tool.description = description
    if enabled is not None:
        tool.enabled = enabled

    await session.commit()
    await session.refresh(tool)

    return {
        "id": tool.id,
        "name": tool.name,
        "description": tool.description,
        "code": tool.code,
        "enabled": tool.enabled,
        "created_at": tool.created_at.isoformat() if tool.created_at else None,
    }


async def delete_custom_tool(session, tool_id: str) -> bool:
    """
    Delete a custom tool.

    Args:
        session: SQLAlchemy async session
        tool_id: The tool's UUID

    Returns:
        True if deleted, False if not found
    """
    from sqlalchemy import delete
    from backend.app.db.models import CustomTool

    result = await session.execute(delete(CustomTool).where(CustomTool.id == tool_id))
    await session.commit()

    return result.rowcount > 0


def get_tool_template() -> str:
    """
    Get a template for creating custom tools.

    Returns:
        Template string with example tool code
    """
    return '''def my_tool(arg1, arg2, **kwargs):
    """
    Describe what your tool does here.
    
    Args:
        arg1: Description of first argument
        arg2: Description of second argument
        **kwargs: Additional keyword arguments
        
    Returns:
        Description of return value
    """
    # Your tool implementation here
    # Available modules: math, random, datetime, json, re, itertools, collections, statistics
    
    # Example: Calculate sum of two numbers
    result = arg1 + arg2
    
    return {
        "result": result,
        "message": f"Calculated {arg1} + {arg2} = {result}"
    }
'''
