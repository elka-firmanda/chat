#!/usr/bin/env python
"""Test script for code executor timeout enforcement."""

import asyncio
import sys

sys.path.insert(0, ".")

from app.tools.code_executor import execute_code, CodeExecutor


async def test_quick_execution():
    print("Test 1: Quick execution (should complete)")
    result = await execute_code("x = 2 + 2")
    print(f"  Success: {result['success']}")
    print(f"  Time: {result['execution_time']:.2f}s")
    assert result["success"] == True
    print("  PASSED\n")


async def test_print_output():
    print("Test 2: Print output (should capture print statements)")
    result = await execute_code('print(2 + 2)\nprint("hello")')
    print(f"  Success: {result['success']}")
    print(f"  Output: {repr(result['output'])}")
    print(f"  Time: {result['execution_time']:.2f}s")
    assert result["success"] == True
    assert "4" in result["output"]
    assert "hello" in result["output"]
    print("  PASSED\n")


async def test_timeout_enforced():
    print("Test 3: Long-running code (should timeout after 2 seconds)")
    result = await execute_code(
        """
for i in range(100):
    print(f"Iteration {i}")
""",
        timeout=2,
    )
    print(f"  Success: {result['success']}")
    print(f"  Error: {result['error']}")
    print(f"  Exception type: {result.get('exception', {}).get('type')}")
    print(f"  Time: {result['execution_time']:.2f}s")
    assert result["success"] == False
    assert "timeout" in result["error"].lower()
    assert result["exception"]["type"] == "ExecutionTimeout"
    assert result["execution_time"] >= 2.0
    print("  PASSED\n")


async def test_syntax_error():
    print("Test 4: Syntax error (should fail with SyntaxError)")
    result = await execute_code('print("hello')
    print(f"  Success: {result['success']}")
    print(f"  Exception type: {result.get('exception', {}).get('type')}")
    assert result["success"] == False
    assert result["exception"]["type"] == "SyntaxError"
    print("  PASSED\n")


async def test_infinite_loop():
    print("Test 5: Infinite loop (should timeout)")
    result = await execute_code(
        """
while True:
    x = 1
""",
        timeout=1,
    )
    print(f"  Success: {result['success']}")
    print(f"  Exception type: {result.get('exception', {}).get('type')}")
    print(f"  Time: {result['execution_time']:.2f}s")
    assert result["success"] == False
    assert result["exception"]["type"] == "ExecutionTimeout"
    assert result["execution_time"] >= 1.0
    print("  PASSED\n")


async def test_calculation():
    print("Test 6: Complex calculation with print")
    result = await execute_code("""
import math
result = math.factorial(10)
print(f"10! = {result}")
""")
    print(f"  Success: {result['success']}")
    print(f"  Output: {result['output'].strip()}")
    assert result["success"] == True
    assert "3628800" in result["output"]
    print("  PASSED\n")


async def test_evaluate():
    print("Test 7: Evaluate expression (should return result)")
    executor = CodeExecutor(timeout=30)
    result = await executor.evaluate("2 + 2 * 3")
    print(f"  Success: {result['success']}")
    print(f"  Result: {result['result']}")
    print(f"  Time: {result['execution_time']:.2f}s")
    assert result["success"] == True
    assert result["result"] == 8
    print("  PASSED\n")


async def test_default_timeout():
    print("Test 8: Default 30 second timeout (very short loop)")
    result = await execute_code("for i in range(10000000): pass", timeout=1)
    print(f"  Success: {result['success']}")
    print(f"  Exception type: {result.get('exception', {}).get('type')}")
    print(f"  Time: {result['execution_time']:.2f}s")
    assert result["success"] == False
    assert result["exception"]["type"] == "ExecutionTimeout"
    print("  PASSED\n")


async def main():
    print("=" * 60)
    print("Testing Code Executor Timeout Enforcement")
    print("=" * 60)
    print()

    await test_quick_execution()
    await test_print_output()
    await test_timeout_enforced()
    await test_syntax_error()
    await test_infinite_loop()
    await test_calculation()
    await test_evaluate()
    await test_default_timeout()

    print("=" * 60)
    print("All tests passed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
