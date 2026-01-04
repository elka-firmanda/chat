"""
py-spy profiling configuration for performance analysis.

Usage:
    # Profile the FastAPI application
    py-spy record -o profile.svg --pid $(pgrep -f "uvicorn app.main:app")

    # Profile with火焰图 (flame graph)
    py-spy record -o profile.svg --format=flame --pid $(pgrep -f "uvicorn")

    # Profile with call stack sampling
    py-spy top --pid $(pgrep -f "uvicorn")

For React DevTools Profiler:
    1. Install React DevTools browser extension
    2. Open DevTools -> React tab
    3. Profile components during interaction
    4. Analyze render times and re-renders

Key metrics to monitor:
- Backend: SSE latency, DB query time, LLM provider instantiation
- Frontend: Bundle size, lazy load performance, component render time
"""

import subprocess
import sys


def install_profiling_tools():
    """Install profiling dependencies."""
    tools = [
        "py-spy",  # Python profiling
    ]

    for tool in tools:
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", tool])
            print(f"Installed {tool}")
        except subprocess.CalledProcessError:
            print(f"Failed to install {tool}")


if __name__ == "__main__":
    install_profiling_tools()
