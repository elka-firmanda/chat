"""Working memory stub for backward compatibility.

This module is deprecated. The new MasterAgent uses simple state management.
These stubs are kept for existing subagent compatibility until they are rewritten.
"""

from typing import Any


class WorkingMemory:
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.nodes: dict[str, Any] = {}
        self.timeline: list[dict[str, Any]] = []

    def to_dict(self) -> dict[str, Any]:
        return {"tree": {}, "timeline": self.timeline, "index": self.nodes}


class MemoryNode:
    def __init__(self, **kwargs: Any):
        for k, v in kwargs.items():
            setattr(self, k, v)


class AsyncWorkingMemory:
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.nodes: dict[str, Any] = {}
        self.timeline: list[dict[str, Any]] = []

    async def load(self, data: dict[str, Any]) -> None:
        self.nodes = data.get("index", {})
        self.timeline = data.get("timeline", [])

    async def to_dict(self) -> dict[str, Any]:
        return {"tree": {}, "timeline": self.timeline, "index": self.nodes}

    async def add_node(
        self,
        agent: str,
        node_type: str,
        description: str,
        **kwargs: Any,
    ) -> str:
        import uuid

        node_id = str(uuid.uuid4())[:8]
        self.nodes[node_id] = {
            "agent": agent,
            "node_type": node_type,
            "description": description,
            **kwargs,
        }
        self.timeline.append(
            {"id": node_id, "agent": agent, "description": description}
        )
        return node_id

    async def update_node(self, node_id: str, **kwargs: Any) -> None:
        if node_id in self.nodes:
            self.nodes[node_id].update(kwargs)
