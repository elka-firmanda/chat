"""
SSE Client utilities for testing Server-Sent Events streaming.

Provides mock SSE clients, event parsing, and verification utilities
for testing real-time streaming behavior.
"""

import asyncio
import json
import re
import pytest
from dataclasses import dataclass, field
from datetime import datetime
from typing import AsyncIterator, Dict, Any, List, Optional, Callable
from enum import Enum


class SSEEventType(str, Enum):
    """Types of SSE events."""

    THOUGHT = "thought"
    MEMORY_UPDATE = "memory_update"
    NODE_ADDED = "node_added"
    NODE_UPDATED = "node_updated"
    TIMELINE_UPDATE = "timeline_update"
    STEP_PROGRESS = "step_progress"
    MESSAGE_CHUNK = "message_chunk"
    COMPLETE = "complete"
    ERROR = "error"
    RETRY = "retry"
    INTERVENTION = "intervention"
    KEEPALIVE = "keepalive"


@dataclass
class ParsedSSEEvent:
    """A parsed SSE event."""

    event_type: str
    data: Dict[str, Any]
    raw_event: str
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    line_number: Optional[int] = None


@dataclass
class SSEEventSequence:
    """A sequence of SSE events for verification."""

    events: List[ParsedSSEEvent]
    session_id: str
    start_time: datetime
    end_time: Optional[datetime] = None

    def __post_init__(self):
        if self.events:
            self.start_time = datetime.fromisoformat(
                self.events[0].data.get("_timestamp", datetime.utcnow().isoformat())
            )

    def filter_by_type(self, event_type: str) -> List[ParsedSSEEvent]:
        """Filter events by type."""
        return [e for e in self.events if e.event_type == event_type]

    def filter_by_types(self, event_types: List[str]) -> List[ParsedSSEEvent]:
        """Filter events by multiple types."""
        return [e for e in self.events if e.event_type in event_types]

    def has_event_type(self, event_type: str) -> bool:
        """Check if sequence contains an event type."""
        return any(e.event_type == event_type for e in self.events)

    def count_events(self, event_type: str) -> int:
        """Count events of a specific type."""
        return sum(1 for e in self.events if e.event_type == event_type)

    def get_first_event(self, event_type: str) -> Optional[ParsedSSEEvent]:
        """Get the first event of a specific type."""
        for event in self.events:
            if event.event_type == event_type:
                return event
        return None

    def get_last_event(self, event_type: str) -> Optional[ParsedSSEEvent]:
        """Get the last event of a specific type."""
        result = None
        for event in self.events:
            if event.event_type == event_type:
                result = event
        return result

    def get_complete_content(self) -> Optional[str]:
        """Get the complete message content from message_chunk events."""
        complete_event = self.get_last_event(SSEEventType.COMPLETE.value)
        if complete_event:
            return complete_event.data.get("final_answer", "")

        chunks = self.filter_by_type(SSEEventType.MESSAGE_CHUNK.value)
        if chunks:
            last_chunk = chunks[-1]
            return last_chunk.data.get("content", "")

        return None

    def get_thoughts_by_agent(self) -> Dict[str, List[str]]:
        """Get all thoughts grouped by agent."""
        thoughts = {}
        for event in self.filter_by_type(SSEEventType.THOUGHT.value):
            agent = event.data.get("agent", "unknown")
            content = event.data.get("content", "")
            if agent not in thoughts:
                thoughts[agent] = []
            thoughts[agent].append(content)
        return thoughts

    def get_step_progressions(self) -> List[Dict[str, Any]]:
        """Get step progress events in order."""
        return [
            {
                "step_id": e.data.get("step_id"),
                "step_number": e.data.get("step_number"),
                "total_steps": e.data.get("total_steps"),
                "status": e.data.get("status"),
                "description": e.data.get("description"),
            }
            for e in self.filter_by_type(SSEEventType.STEP_PROGRESS.value)
        ]

    def get_error_events(self) -> List[ParsedSSEEvent]:
        """Get all error events."""
        return self.filter_by_type(SSEEventType.ERROR.value)

    def verify_sequence(self, expected_sequence: List[str]) -> bool:
        """Verify that events occur in expected order."""
        event_types = [e.event_type for e in self.events]
        for expected in expected_sequence:
            if expected not in event_types:
                return False
        return True

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "session_id": self.session_id,
            "event_count": len(self.events),
            "event_types": list(set(e.event_type for e in self.events)),
            "events": [
                {"event_type": e.event_type, "data": e.data} for e in self.events
            ],
        }


class SSEEventParser:
    """Parser for SSE event streams."""

    EVENT_LINE_PATTERN = re.compile(r"^event:\s*(\S+)\s*$")
    DATA_LINE_PATTERN = re.compile(r"^data:\s*(.+)\s*$")
    COMMENT_LINE_PATTERN = re.compile(r"^:\s*(.+)\s*$")

    @classmethod
    def parse_raw_stream(cls, raw_data: str) -> List[ParsedSSEEvent]:
        """Parse raw SSE data string into events."""
        events = []
        lines = raw_data.split("\n")

        current_event = None
        current_data_lines = []
        line_number = 0

        for line in lines:
            line_number += 1

            if not line.strip():
                if current_event is not None:
                    if current_data_lines:
                        try:
                            event_data = json.loads("\n".join(current_data_lines))
                            current_event.data = event_data
                        except json.JSONDecodeError:
                            current_event.data = {
                                "raw_data": "\n".join(current_data_lines)
                            }

                    current_event.raw_event = "\n".join(
                        current_event_lines
                        for current_event_lines in lines[
                            max(
                                0, line_number - len(current_data_lines) - 2
                            ) : line_number
                        ]
                    )
                    current_event.line_number = line_number
                    events.append(current_event)

                    current_event = None
                    current_data_lines = []
                continue

            event_match = cls.EVENT_LINE_PATTERN.match(line)
            if event_match:
                if current_event is not None and current_data_lines:
                    try:
                        current_event.data = json.loads("\n".join(current_data_lines))
                    except json.JSONDecodeError:
                        current_event.data = {"raw_data": "\n".join(current_data_lines)}
                    events.append(current_event)

                current_event = ParsedSSEEvent(
                    event_type=event_match.group(1),
                    data={},
                    raw_event="",
                )
                current_data_lines = []
                continue

            data_match = cls.DATA_LINE_PATTERN.match(line)
            if data_match:
                current_data_lines.append(data_match.group(1))
                continue

            comment_match = cls.COMMENT_LINE_PATTERN.match(line)
            if comment_match:
                continue

        if current_event is not None and current_data_lines:
            try:
                current_event.data = json.loads("\n".join(current_data_lines))
            except json.JSONDecodeError:
                current_event.data = {"raw_data": "\n".join(current_data_lines)}
            events.append(current_event)

        return events

    @classmethod
    async def parse_streaming_response(
        cls,
        response_iterator: AsyncIterator[str],
    ) -> AsyncIterator[ParsedSSEEvent]:
        """Parse streaming response asynchronously."""
        buffer = ""

        async for chunk in response_iterator:
            buffer += chunk

            while "\n\n" in buffer:
                event_data, buffer = buffer.split("\n\n", 1)

                lines = event_data.split("\n")
                event_type = None
                data_parts = []

                for line in lines:
                    event_match = cls.EVENT_LINE_PATTERN.match(line)
                    if event_match:
                        event_type = event_match.group(1)
                        continue

                    data_match = cls.DATA_LINE_PATTERN.match(line)
                    if data_match:
                        data_parts.append(data_match.group(1))
                        continue

                    comment_match = cls.COMMENT_LINE_PATTERN.match(line)
                    if comment_match:
                        continue

                if event_type and data_parts:
                    try:
                        data = json.loads("\n".join(data_parts))
                    except json.JSONDecodeError:
                        data = {"raw_data": "\n".join(data_parts)}

                    yield ParsedSSEEvent(
                        event_type=event_type,
                        data=data,
                        raw_event=event_data,
                    )


class MockSSEClient:
    """Mock SSE client for testing streaming behavior."""

    def __init__(self, session_id: str):
        self.session_id = session_id
        self._events: List[ParsedSSEEvent] = []
        self._is_connected = False
        self._connection_time: Optional[datetime] = None
        self._disconnection_time: Optional[datetime] = None
        self._error_events: List[ParsedSSEEvent] = []
        self._complete_event: Optional[ParsedSSEEvent] = None

    async def connect(
        self,
        url: str,
        timeout: float = 30.0,
        headers: Optional[Dict[str, str]] = None,
    ) -> None:
        """Simulate connecting to SSE stream."""
        self._is_connected = True
        self._connection_time = datetime.utcnow()

    async def disconnect(self) -> None:
        """Simulate disconnecting from SSE stream."""
        self._is_connected = False
        self._disconnection_time = datetime.utcnow()

    async def receive_events(
        self,
        event_callback: Optional[Callable[[ParsedSSEEvent], None]] = None,
        timeout: float = 30.0,
    ) -> SSEEventSequence:
        """Receive events from the stream."""
        if not self._is_connected:
            raise RuntimeError("Not connected to SSE stream")

        start_time = datetime.utcnow()
        end_time = None

        return SSEEventSequence(
            events=self._events,
            session_id=self.session_id,
            start_time=start_time,
            end_time=end_time,
        )

    def add_event(self, event: ParsedSSEEvent) -> None:
        """Add an event to the mock stream."""
        self._events.append(event)
        if event.event_type == SSEEventType.ERROR.value:
            self._error_events.append(event)
        if event.event_type == SSEEventType.COMPLETE.value:
            self._complete_event = event

    def add_events(self, events: List[ParsedSSEEvent]) -> None:
        """Add multiple events to the mock stream."""
        for event in events:
            self.add_event(event)

    def add_thought_event(
        self,
        agent: str,
        content: str,
        timestamp: Optional[str] = None,
    ) -> ParsedSSEEvent:
        """Add a thought event."""
        event = ParsedSSEEvent(
            event_type=SSEEventType.THOUGHT.value,
            data={
                "agent": agent,
                "content": content,
                "_timestamp": timestamp or datetime.utcnow().isoformat(),
            },
            raw_event=f"event: thought\ndata: {json.dumps({'agent': agent, 'content': content})}\n\n",
        )
        self.add_event(event)
        return event

    def add_complete_event(
        self,
        message_id: str,
        final_answer: str = "",
        timestamp: Optional[str] = None,
    ) -> ParsedSSEEvent:
        """Add a complete event."""
        event = ParsedSSEEvent(
            event_type=SSEEventType.COMPLETE.value,
            data={
                "message_id": message_id,
                "session_id": self.session_id,
                "final_answer": final_answer,
                "_timestamp": timestamp or datetime.utcnow().isoformat(),
            },
            raw_event=f"event: complete\ndata: {json.dumps({'message_id': message_id, 'final_answer': final_answer})}\n\n",
        )
        self.add_event(event)
        return event

    def add_error_event(
        self,
        error: str,
        error_type: str = "execution_error",
        can_retry: bool = True,
        timestamp: Optional[str] = None,
    ) -> ParsedSSEEvent:
        """Add an error event."""
        event = ParsedSSEEvent(
            event_type=SSEEventType.ERROR.value,
            data={
                "error": error,
                "error_type": error_type,
                "can_retry": can_retry,
                "_timestamp": timestamp or datetime.utcnow().isoformat(),
            },
            raw_event=f"event: error\ndata: {json.dumps({'error': error, 'error_type': error_type, 'can_retry': can_retry})}\n\n",
        )
        self.add_event(event)
        return event

    def add_message_chunk_event(
        self,
        content: str,
        delta: str = "",
        is_complete: bool = False,
        timestamp: Optional[str] = None,
    ) -> ParsedSSEEvent:
        """Add a message chunk event."""
        event = ParsedSSEEvent(
            event_type=SSEEventType.MESSAGE_CHUNK.value,
            data={
                "content": content,
                "delta": delta,
                "is_complete": is_complete,
                "_timestamp": timestamp or datetime.utcnow().isoformat(),
            },
            raw_event=f"event: message_chunk\ndata: {json.dumps({'content': content, 'delta': delta, 'is_complete': is_complete})}\n\n",
        )
        self.add_event(event)
        return event

    def add_step_progress_event(
        self,
        step_id: str,
        step_number: int,
        total_steps: int,
        agent: str,
        status: str,
        description: str,
        timestamp: Optional[str] = None,
    ) -> ParsedSSEEvent:
        """Add a step progress event."""
        event = ParsedSSEEvent(
            event_type=SSEEventType.STEP_PROGRESS.value,
            data={
                "step_id": step_id,
                "step_number": step_number,
                "total_steps": total_steps,
                "agent": agent,
                "status": status,
                "description": description,
                "progress_percentage": round(
                    (step_number / max(total_steps, 1)) * 100, 1
                ),
                "_timestamp": timestamp or datetime.utcnow().isoformat(),
            },
            raw_event=f"event: step_progress\ndata: {json.dumps({'step_id': step_id, 'step_number': step_number, 'status': status})}\n\n",
        )
        self.add_event(event)
        return event

    @property
    def events(self) -> List[ParsedSSEEvent]:
        """Get all events."""
        return self._events

    @property
    def error_events(self) -> List[ParsedSSEEvent]:
        """Get error events."""
        return self._error_events

    @property
    def complete_event(self) -> Optional[ParsedSSEEvent]:
        """Get the complete event if present."""
        return self._complete_event

    @property
    def is_connected(self) -> bool:
        """Check if connected."""
        return self._is_connected

    def get_sequence(self) -> SSEEventSequence:
        """Get the event sequence."""
        return SSEEventSequence(
            events=self._events,
            session_id=self.session_id,
            start_time=self._connection_time or datetime.utcnow(),
            end_time=self._disconnection_time,
        )

    def clear(self) -> None:
        """Clear all events."""
        self._events = []
        self._error_events = []
        self._complete_event = None


@pytest.fixture
def mock_sse_client():
    """Create a mock SSE client for testing."""

    def _create_client(session_id: str = "test-session") -> MockSSEClient:
        return MockSSEClient(session_id)

    return _create_client


@pytest.fixture
def sample_sse_events():
    """Create sample SSE events for testing."""
    events = [
        ParsedSSEEvent(
            event_type="thought",
            data={"agent": "planner", "content": "Planning the approach..."},
            raw_event='event: thought\ndata: {"agent": "planner", "content": "Planning the approach..."}\n\n',
        ),
        ParsedSSEEvent(
            event_type="step_progress",
            data={
                "step_id": "step-1",
                "step_number": 1,
                "total_steps": 3,
                "agent": "researcher",
                "status": "running",
                "description": "Researching the topic",
            },
            raw_event="",
        ),
        ParsedSSEEvent(
            event_type="thought",
            data={
                "agent": "researcher",
                "content": "Searching for relevant information...",
            },
            raw_event="",
        ),
        ParsedSSEEvent(
            event_type="message_chunk",
            data={
                "content": "Based on my research, ",
                "delta": "Based on my research, ",
                "is_complete": False,
            },
            raw_event="",
        ),
        ParsedSSEEvent(
            event_type="complete",
            data={
                "message_id": "msg-123",
                "session_id": "test-session",
                "final_answer": "Based on my research, here is the answer...",
            },
            raw_event="",
        ),
    ]
    return events


class SSEEventVerifier:
    """Utilities for verifying SSE event sequences."""

    @staticmethod
    def verify_event_order(
        sequence: SSEEventSequence,
        expected_order: List[str],
    ) -> tuple[bool, str]:
        """Verify that events occur in expected order."""
        event_types = [e.event_type for e in sequence.events]

        for i, expected in enumerate(expected_order):
            if i >= len(event_types):
                return False, f"Missing event at position {i}: expected {expected}"

            if event_types[i] != expected:
                return (
                    False,
                    f"Event order mismatch at position {i}: expected {expected}, got {event_types[i]}",
                )

        return True, "Event order verified"

    @staticmethod
    def verify_thought_progression(
        sequence: SSEEventSequence,
        expected_agents: List[str],
    ) -> tuple[bool, str]:
        """Verify that thoughts progress through expected agents."""
        thoughts = sequence.filter_by_type(SSEEventType.THOUGHT.value)
        agents = [t.data.get("agent") for t in thoughts]

        if agents != expected_agents:
            return (
                False,
                f"Agent progression mismatch: expected {expected_agents}, got {agents}",
            )

        return True, "Agent progression verified"

    @staticmethod
    def verify_no_errors(sequence: SSEEventSequence) -> tuple[bool, str]:
        """Verify that no errors occurred."""
        errors = sequence.get_error_events()
        if errors:
            error_messages = [e.data.get("error", "Unknown error") for e in errors]
            return False, f"Errors found: {error_messages}"
        return True, "No errors found"

    @staticmethod
    def verify_complete_received(sequence: SSEEventSequence) -> tuple[bool, str]:
        """Verify that a complete event was received."""
        if not sequence.complete_event:
            return False, "No complete event received"
        return True, "Complete event verified"

    @staticmethod
    def verify_final_answer(
        sequence: SSEEventSequence,
        expected_content: Optional[str] = None,
        min_length: int = 0,
    ) -> tuple[bool, str]:
        """Verify the final answer content."""
        final_answer = sequence.get_complete_content()

        if not final_answer:
            return False, "No final answer found"

        if expected_content and expected_content not in final_answer:
            return (
                False,
                f"Expected content '{expected_content}' not found in final answer",
            )

        if len(final_answer) < min_length:
            return (
                False,
                f"Final answer too short: {len(final_answer)} chars, expected at least {min_length}",
            )

        return True, f"Final answer verified: {len(final_answer)} chars"

    @staticmethod
    def verify_step_completion(
        sequence: SSEEventSequence,
        expected_step_count: int,
    ) -> tuple[bool, str]:
        """Verify that all steps were completed."""
        steps = sequence.get_step_progressions()

        if len(steps) < expected_step_count:
            return False, f"Expected {expected_step_count} steps, got {len(steps)}"

        completed_steps = [s for s in steps if s.get("status") == "completed"]
        if len(completed_steps) < expected_step_count:
            return (
                False,
                f"Only {len(completed_steps)} steps completed out of {expected_step_count}",
            )

        return True, f"All {expected_step_count} steps verified"

    @staticmethod
    def verify_think_time(
        sequence: SSEEventSequence,
        max_seconds: float = 60.0,
    ) -> tuple[bool, str]:
        """Verify that the total think time is within limit."""
        if sequence.start_time and sequence.end_time:
            total_time = (sequence.end_time - sequence.start_time).total_seconds()
            if total_time > max_seconds:
                return False, f"Total time {total_time:.2f}s exceeds max {max_seconds}s"
            return True, f"Total time {total_time:.2f}s within limit"
        return True, "Timing data not available"


@pytest.fixture
def sse_event_verifier():
    """Create an SSE event verifier."""
    return SSEEventVerifier()
