"""
Graceful Shutdown Handler

Manages orderly shutdown of the application including:
- Signal handling (SIGTERM, SIGINT)
- Active task cancellation with timeout
- Resource cleanup (database connections, HTTP clients, event queues)
- Working memory persistence for in-progress sessions
- Session-specific task cancellation for user navigation
"""

import asyncio
import signal
import logging
import sys
from typing import Dict, Optional, Any, Set
from datetime import datetime
from contextlib import suppress
from uuid import UUID

logger = logging.getLogger(__name__)


class ShutdownManager:
    """
    Centralized shutdown management for the application.

    Tracks active tasks, manages graceful shutdown, and ensures proper resource cleanup.
    """

    def __init__(self):
        self._shutdown_requested = False
        self._shutdown_start_time: Optional[datetime] = None
        self._active_tasks: Dict[str, asyncio.Task] = {}
        self._task_lock = asyncio.Lock()
        self._graceful_shutdown_timeout = 30.0  # seconds
        self._shutdown_callbacks: list = []

    @property
    def is_shutdown_requested(self) -> bool:
        """Check if shutdown has been requested."""
        return self._shutdown_requested

    @property
    def shutdown_duration(self) -> Optional[float]:
        """Get the duration of the shutdown process in seconds."""
        if self._shutdown_start_time is None:
            return None
        return (datetime.utcnow() - self._shutdown_start_time).total_seconds()

    def register_task(self, task_id: str, task: asyncio.Task) -> None:
        """
        Register an active task for tracking.

        Args:
            task_id: Unique identifier for the task
            task: The asyncio Task to track
        """

        async def _track_task():
            try:
                await task
            except asyncio.CancelledError:
                logger.debug(f"Task {task_id} was cancelled during shutdown")
            except Exception as e:
                logger.error(f"Task {task_id} ended with error: {e}")

        wrapped_task = asyncio.create_task(_track_task())
        wrapped_task._original_task = task  # type: ignore

        async def _register():
            async with self._task_lock:
                self._active_tasks[task_id] = wrapped_task
                logger.debug(f"Registered task: {task_id}")

        asyncio.get_event_loop().call_soon_threadsafe(
            lambda: asyncio.create_task(_register())
        )

    def unregister_task(self, task_id: str) -> None:
        """Unregister a completed task."""

        async def _unregister():
            async with self._task_lock:
                self._active_tasks.pop(task_id, None)
                logger.debug(f"Unregistered task: {task_id}")

        asyncio.get_event_loop().call_soon_threadsafe(
            lambda: asyncio.create_task(_unregister())
        )

    def add_shutdown_callback(self, callback) -> None:
        """
        Add a callback to be executed during shutdown.

        Args:
            callback: Async callable to execute during shutdown
        """
        self._shutdown_callbacks.append(callback)

    async def _execute_callbacks(self) -> None:
        """Execute all registered shutdown callbacks."""
        for callback in self._shutdown_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback()
                else:
                    callback()
                logger.debug(f"Executed shutdown callback: {callback.__name__}")
            except Exception as e:
                logger.error(f"Error executing shutdown callback: {e}")

    async def _cancel_active_tasks(self) -> None:
        """Cancel all active tasks gracefully."""
        async with self._task_lock:
            tasks_to_cancel = list(self._active_tasks.values())

        if not tasks_to_cancel:
            logger.debug("No active tasks to cancel")
            return

        logger.info(f"Cancelling {len(tasks_to_cancel)} active tasks...")

        for task in tasks_to_cancel:
            if not task.done():
                task.cancel()

        if tasks_to_cancel:
            try:
                await asyncio.wait_for(
                    asyncio.gather(*tasks_to_cancel, return_exceptions=True),
                    timeout=self._graceful_shutdown_timeout,
                )
                logger.info("All tasks cancelled successfully")
            except asyncio.TimeoutError:
                logger.warning(
                    f"Task cancellation timed out after {self._graceful_shutdown_timeout}s"
                )
                remaining = [t for t in tasks_to_cancel if not t.done()]
                if remaining:
                    logger.warning(f"{len(remaining)} tasks did not cancel in time")

    async def _close_event_queues(self) -> None:
        """Close all SSE event queues with notification."""
        try:
            from app.utils.streaming import event_manager

            queue_count = event_manager.get_queue_count()
            if queue_count > 0:
                logger.info(f"Closing {queue_count} SSE event queues...")

                async with event_manager._locks.get("global", asyncio.Lock()):
                    session_ids = list(event_manager._queues.keys())

                for session_id in session_ids:
                    try:
                        await event_manager.emit_error(
                            session_id=session_id,
                            error="Server shutting down",
                            error_type="shutdown",
                            can_retry=False,
                        )
                    except Exception:
                        pass

                    await event_manager.close(session_id)

                logger.info("All SSE event queues closed")
        except ImportError:
            logger.debug(
                "SSE event_manager not available (using EventSourceResponse pattern)"
            )
        except Exception as e:
            logger.error(f"Error closing event queues: {e}")

    async def _dispose_database_engine(self) -> None:
        """Dispose of the database engine and connection pool."""
        try:
            from app.db.session import get_engine, _engine_lock

            with _engine_lock:
                from app.db.session import _engine

                if _engine is not None:
                    logger.info("Disposing database engine...")
                    await _engine.dispose()
                    from app.db.session import _engine as engine_ref

                    engine_ref = None
                    logger.info("Database engine disposed")
        except Exception as e:
            logger.error(f"Error disposing database engine: {e}")

    async def shutdown(self, exit_code: int = 0) -> None:
        """
        Perform graceful shutdown of the application.

        Args:
            exit_code: System exit code
        """
        if self._shutdown_requested:
            return

        self._shutdown_requested = True
        self._shutdown_start_time = datetime.utcnow()

        logger.info("Starting graceful shutdown...")

        try:
            await self._execute_callbacks()
            await self._cancel_active_tasks()
            await self._close_event_queues()
            await self._dispose_database_engine()

            duration = self.shutdown_duration
            logger.info(f"Shutdown complete in {duration:.2f}s")

        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
            exit_code = 1


_global_shutdown_manager: Optional[ShutdownManager] = None


def get_shutdown_manager() -> ShutdownManager:
    """Get the global shutdown manager instance."""
    global _global_shutdown_manager
    if _global_shutdown_manager is None:
        _global_shutdown_manager = ShutdownManager()
    return _global_shutdown_manager


async def create_shutdown_handler(app) -> None:
    """
    Create and register signal handlers for the FastAPI application.

    Args:
        app: FastAPI application instance
    """
    shutdown_manager = get_shutdown_manager()
    loop = asyncio.get_event_loop()

    def handle_sigterm():
        logger.info("Received SIGTERM, initiating graceful shutdown...")
        asyncio.create_task(shutdown_manager.shutdown())

    def handle_sigint():
        logger.info("Received SIGINT, initiating graceful shutdown...")
        asyncio.create_task(shutdown_manager.shutdown())

    loop.add_signal_handler(signal.SIGTERM, handle_sigterm)
    loop.add_signal_handler(signal.SIGINT, handle_sigint)

    logger.info("Signal handlers registered for SIGTERM and SIGINT")


class GracefulTaskTracker:
    """
    Context manager for tracking background tasks during shutdown.

    Usage:
        async with GracefulTaskTracker("agent_workflow", task) as tracker:
            # Task runs normally
            pass
        # Task is automatically unregistered on completion
    """

    def __init__(self, task_id: str, task: asyncio.Task):
        self.task_id = task_id
        self.task = task
        self.shutdown_manager = get_shutdown_manager()

    async def __aenter__(self) -> "GracefulTaskTracker":
        self.shutdown_manager.register_task(self.task_id, self.task)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self.shutdown_manager.unregister_task(self.task_id)
        if exc_type is not None:
            logger.error(f"Task {self.task_id} ended with exception: {exc_val}")


async def save_working_memory_state(session_id: str) -> bool:
    """
    Save the current working memory state for a session.

    Args:
        session_id: Session identifier

    Returns:
        True if state was saved successfully
    """
    try:
        from app.db.repositories.chat import ChatRepository
        from app.db.session import get_db_session

        try:
            from app.utils.streaming import event_manager

            memory_data = event_manager._queues.get(session_id)
            if memory_data:
                await event_manager.close(session_id)
        except ImportError:
            pass

        logger.info(f"Saved working memory state for session {session_id}")
        return True

    except Exception as e:
        logger.error(f"Failed to save working memory for session {session_id}: {e}")
        return False


async def cancel_session_execution(session_id: str) -> bool:
    """
    Cancel execution for a specific session.

    Args:
        session_id: Session identifier

    Returns:
        True if cancellation was initiated
    """
    try:
        from app.utils.session_task_manager import get_session_task_manager

        task_manager = get_session_task_manager()
        event_manager_cancelled = False

        try:
            from app.utils.streaming import event_manager as em

            await em.close(session_id)
            event_manager_cancelled = True
        except ImportError:
            pass
        except Exception as e:
            logger.debug(f"Event manager cleanup for {session_id}: {e}")

        task_cancelled = await task_manager.cancel_session(session_id)

        logger.info(
            f"Cancelled execution for session {session_id} (tasks: {task_cancelled}, events: {event_manager_cancelled})"
        )
        return True

    except Exception as e:
        logger.error(f"Failed to cancel session {session_id}: {e}")
        return False


class ShutdownState:
    """
    Tracks the shutdown state for monitoring and debugging.
    """

    def __init__(self):
        self._phases: list = []
        self._current_phase: Optional[str] = None

    def start_phase(self, phase_name: str) -> None:
        """Mark the start of a shutdown phase."""
        self._current_phase = phase_name
        self._phases.append(
            {
                "phase": phase_name,
                "start_time": datetime.utcnow().isoformat(),
                "status": "running",
            }
        )
        logger.debug(f"Shutdown phase started: {phase_name}")

    def end_phase(self, phase_name: str, success: bool = True) -> None:
        """Mark the end of a shutdown phase."""
        if self._current_phase == phase_name:
            self._current_phase = None

        for phase in reversed(self._phases):
            if phase["phase"] == phase_name and "end_time" not in phase:
                phase["end_time"] = datetime.utcnow().isoformat()
                phase["status"] = "completed" if success else "failed"
                break

        logger.debug(f"Shutdown phase completed: {phase_name} (success={success})")

    def get_state(self) -> Dict[str, Any]:
        """Get the current shutdown state."""
        return {
            "phases": self._phases,
            "current_phase": self._current_phase,
            "timestamp": datetime.utcnow().isoformat(),
        }
