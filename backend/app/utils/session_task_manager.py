"""
Session Task Manager

Manages cancellable tasks for each session, enabling proper cancellation
of agent workflows when users navigate away or switch sessions.
"""

import asyncio
import logging
from typing import Dict, Optional, Any, Set
from datetime import datetime
from contextlib import suppress

logger = logging.getLogger(__name__)


class SessionTaskManager:
    """
    Manages cancellable tasks for each session.

    Tracks active agent workflow tasks per session and provides
    cancellation support for when users navigate away.
    """

    def __init__(self):
        self._session_tasks: Dict[str, Set[asyncio.Task]] = {}
        self._session_locks: Dict[str, asyncio.Lock] = {}
        self._cancellation_signals: Dict[str, asyncio.Event] = {}

    def _get_lock(self, session_id: str) -> asyncio.Lock:
        """Get or create a lock for the session."""
        if session_id not in self._session_locks:
            self._session_locks[session_id] = asyncio.Lock()
        return self._session_locks[session_id]

    def _get_cancellation_event(self, session_id: str) -> asyncio.Event:
        """Get or create a cancellation event for the session."""
        if session_id not in self._cancellation_signals:
            self._cancellation_signals[session_id] = asyncio.Event()
        return self._cancellation_signals[session_id]

    def register_task(self, session_id: str, task: asyncio.Task) -> None:
        """
        Register a task for a session.

        Args:
            session_id: Session identifier
            task: The asyncio task to register
        """

        async def _register():
            async with self._get_lock(session_id):
                if session_id not in self._session_tasks:
                    self._session_tasks[session_id] = set()
                self._session_tasks[session_id].add(task)
                logger.debug(f"Registered task for session {session_id}")

        asyncio.get_event_loop().call_soon_threadsafe(
            lambda: asyncio.create_task(_register())
        )

    def unregister_task(self, session_id: str, task: asyncio.Task) -> None:
        """
        Unregister a task from a session.

        Args:
            session_id: Session identifier
            task: The asyncio task to unregister
        """

        async def _unregister():
            async with self._get_lock(session_id):
                if session_id in self._session_tasks:
                    self._session_tasks[session_id].discard(task)
                    if not self._session_tasks[session_id]:
                        del self._session_tasks[session_id]
                logger.debug(f"Unregistered task for session {session_id}")

        asyncio.get_event_loop().call_soon_threadsafe(
            lambda: asyncio.create_task(_unregister())
        )

    def is_cancelled(self, session_id: str) -> bool:
        """
        Check if cancellation has been requested for a session.

        Args:
            session_id: Session identifier

        Returns:
            True if cancellation is requested, False otherwise
        """
        event = self._cancellation_signals.get(session_id)
        if event:
            return event.is_set()
        return False

    def get_cancellation_event(self, session_id: str) -> asyncio.Event:
        """
        Get the cancellation event for a session.

        Args:
            session_id: Session identifier

        Returns:
            The asyncio.Event for cancellation
        """
        return self._get_cancellation_event(session_id)

    async def cancel_session(self, session_id: str) -> bool:
        """
        Cancel all tasks for a session.

        Args:
            session_id: Session identifier

        Returns:
            True if cancellation was initiated
        """
        try:
            cancellation_event = self._get_cancellation_event(session_id)
            cancellation_event.set()

            async with self._get_lock(session_id):
                tasks = self._session_tasks.get(session_id, set()).copy()

            if not tasks:
                logger.debug(f"No active tasks to cancel for session {session_id}")
                return True

            logger.info(f"Cancelling {len(tasks)} tasks for session {session_id}")

            for task in tasks:
                if not task.done():
                    task.cancel()

            self._cleanup_session(session_id)

            return True

        except Exception as e:
            logger.error(f"Failed to cancel session {session_id}: {e}")
            return False

    def _cleanup_session(self, session_id: str) -> None:
        """Clean up session resources after cancellation."""

        async def _cleanup():
            async with self._get_lock(session_id):
                if session_id in self._session_locks:
                    del self._session_locks[session_id]
                if session_id in self._cancellation_signals:
                    del self._cancellation_signals[session_id]
                if session_id in self._session_tasks:
                    del self._session_tasks[session_id]

        asyncio.get_event_loop().call_soon_threadsafe(
            lambda: asyncio.create_task(_cleanup())
        )

    def get_active_session_count(self) -> int:
        """Get the number of sessions with active tasks."""
        return len(self._session_tasks)

    def get_active_task_count(self, session_id: str) -> int:
        """Get the number of active tasks for a session."""
        return len(self._session_tasks.get(session_id, set()))

    async def shutdown_all_sessions(self, timeout: float = 30.0) -> Dict[str, Any]:
        """
        Cancel all active sessions during application shutdown.

        Args:
            timeout: Maximum time to wait for tasks to complete

        Returns:
            Dict with 'cancelled' and 'pending' counts and list of pending sessions
        """
        cancelled_count = 0
        pending_sessions = []

        # Copy session_ids to avoid modification during iteration
        session_ids = list(self._session_tasks.keys())

        for session_id in session_ids:
            try:
                success = await self.cancel_session(session_id)
                if success:
                    cancelled_count += 1
                else:
                    pending_sessions.append(session_id)
            except Exception as e:
                logger.error(f"Error cancelling session {session_id}: {e}")
                pending_sessions.append(session_id)

        # Wait for remaining tasks with timeout
        if pending_sessions:
            logger.info(f"Waiting for {len(pending_sessions)} sessions to complete...")
            try:
                await asyncio.sleep(timeout)
            except asyncio.CancelledError:
                pass

        return {
            "cancelled": cancelled_count,
            "pending": len(pending_sessions),
            "sessions": pending_sessions,
        }


_session_task_manager: Optional[SessionTaskManager] = None


def get_session_task_manager() -> SessionTaskManager:
    """Get the global session task manager instance."""
    global _session_task_manager
    if _session_task_manager is None:
        _session_task_manager = SessionTaskManager()
    return _session_task_manager


class CancellableTaskMixin:
    """
    Mixin for tasks that can be cancelled when user navigates away.

    Usage:
        class MyAgent:
            async def run(self, session_id: str):
                task = asyncio.current_task()
                manager = get_session_task_manager()
                manager.register_task(session_id, task)
                try:
                    await self._do_work()
                finally:
                    manager.unregister_task(session_id, task)
    """

    @staticmethod
    async def check_cancellation(session_id: str) -> bool:
        """
        Check if cancellation was requested for the session.

        Args:
            session_id: Session identifier

        Returns:
            True if cancellation is requested, should stop execution
        """
        manager = get_session_task_manager()
        return manager.is_cancelled(session_id)

    @staticmethod
    async def wait_for_cancellation(
        session_id: str, check_interval: float = 0.5
    ) -> None:
        """
        Wait until cancellation is requested for the session.

        Useful for long-running operations to periodically check for cancellation.

        Args:
            session_id: Session identifier
            check_interval: How often to check for cancellation (seconds)
        """
        manager = get_session_task_manager()
        cancellation_event = manager.get_cancellation_event(session_id)
        try:
            await asyncio.wait_for(cancellation_event.wait(), timeout=check_interval)
        except asyncio.TimeoutError:
            pass
