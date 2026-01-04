"""
Working Memory Manager

Hybrid data structure combining:
- Tree: Hierarchical relationships between agents
- Timeline: Flat execution log for UI streaming
- Index: Fast lookups by node ID

Thread-safe operations with proper locking.
"""

import asyncio
import time
import uuid
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any, Set
from datetime import datetime
import threading
import json
import logging

logger = logging.getLogger(__name__)


@dataclass
class MemoryNode:
    """A node in the working memory tree."""

    id: str
    agent: str  # 'master', 'planner', 'researcher', 'tools', 'database'
    node_type: str  # 'root', 'step', 'thought', 'result', 'error'
    parent_id: Optional[str] = None
    triggered_by: Optional[str] = (
        None  # Node that triggered this one (e.g., re-planning)
    )
    description: str = ""
    status: str = "pending"  # 'pending', 'running', 'completed', 'failed'
    content: Any = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    completed_at: Optional[str] = None
    children: List[str] = field(default_factory=list)  # Child node IDs

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "agent": self.agent,
            "node_type": self.node_type,
            "parent_id": self.parent_id,
            "triggered_by": self.triggered_by,
            "description": self.description,
            "status": self.status,
            "content": self.content,
            "metadata": self.metadata,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
            "children": self.children,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MemoryNode":
        """Create from dictionary."""
        return cls(
            id=data["id"],
            agent=data["agent"],
            node_type=data["node_type"],
            parent_id=data.get("parent_id"),
            triggered_by=data.get("triggered_by"),
            description=data.get("description", ""),
            status=data.get("status", "pending"),
            content=data.get("content"),
            metadata=data.get("metadata", {}),
            created_at=data.get("created_at", datetime.utcnow().isoformat()),
            completed_at=data.get("completed_at"),
            children=data.get("children", []),
        )


@dataclass
class TimelineEntry:
    """An entry in the timeline for UI streaming."""

    node_id: str
    agent: str
    node_type: str
    description: str
    status: str
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    parent_id: Optional[str] = None
    triggered_by: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "node_id": self.node_id,
            "agent": self.agent,
            "node_type": self.node_type,
            "description": self.description,
            "status": self.status,
            "timestamp": self.timestamp,
            "parent_id": self.parent_id,
            "triggered_by": self.triggered_by,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TimelineEntry":
        """Create from dictionary."""
        return cls(
            node_id=data["node_id"],
            agent=data["agent"],
            node_type=data["node_type"],
            description=data.get("description", ""),
            status=data.get("status", "pending"),
            timestamp=data.get("timestamp", datetime.utcnow().isoformat()),
            parent_id=data.get("parent_id"),
            triggered_by=data.get("triggered_by"),
        )


class WorkingMemory:
    """
    Hybrid working memory manager combining tree, timeline, and index.

    Thread-safe operations using read-write lock pattern.
    """

    def __init__(self, session_id: Optional[str] = None):
        self.session_id = session_id or str(uuid.uuid4())
        self._lock = threading.RLock()
        self._tree: Dict[str, MemoryNode] = {}
        self._timeline: List[TimelineEntry] = []
        self._index: Dict[str, MemoryNode] = {}

        # Initialize root node
        self._create_root()

    def _create_root(self):
        """Create the root node for the tree."""
        root = MemoryNode(
            id="root",
            agent="master",
            node_type="root",
            description="Master agent root",
            status="running",
        )
        self._tree["root"] = root
        self._index["root"] = root
        self._timeline.append(
            TimelineEntry(
                node_id="root",
                agent="master",
                node_type="root",
                description="Session started",
                status="running",
            )
        )

    @property
    def root_id(self) -> str:
        """Get the root node ID."""
        return "root"

    # ==================== Node Operations ====================

    def add_node(
        self,
        agent: str,
        node_type: str,
        description: str,
        parent_id: Optional[str] = None,
        triggered_by: Optional[str] = None,
        content: Optional[Any] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Add a new node to the working memory.

        Args:
            agent: Agent type ('master', 'planner', 'researcher', 'tools', 'database')
            node_type: Type of node ('step', 'thought', 'result', 'error')
            description: Human-readable description
            parent_id: Parent node ID (defaults to root)
            triggered_by: Node that triggered this one (for re-planning)
            content: Node content (thoughts, results, etc.)
            metadata: Additional metadata

        Returns:
            New node ID
        """
        with self._lock:
            node_id = str(uuid.uuid4())

            # Use root as default parent
            if parent_id is None:
                parent_id = "root"

            node = MemoryNode(
                id=node_id,
                agent=agent,
                node_type=node_type,
                parent_id=parent_id,
                triggered_by=triggered_by,
                description=description,
                status="running",
                content=content,
                metadata=metadata or {},
            )

            # Add to tree
            self._tree[node_id] = node
            self._index[node_id] = node

            # Update parent's children list
            if parent_id in self._tree:
                self._tree[parent_id].children.append(node_id)

            # Add to timeline
            timeline_entry = TimelineEntry(
                node_id=node_id,
                agent=agent,
                node_type=node_type,
                description=description,
                status="running",
                parent_id=parent_id,
                triggered_by=triggered_by,
            )
            self._timeline.append(timeline_entry)

            logger.debug(
                f"Added node {node_id} ({agent}/{node_type}) to working memory"
            )
            return node_id

    def update_node(
        self,
        node_id: str,
        status: Optional[str] = None,
        content: Optional[Any] = None,
        metadata: Optional[Dict[str, Any]] = None,
        completed: bool = False,
    ) -> bool:
        """
        Update an existing node.

        Args:
            node_id: Node ID to update
            status: New status
            content: Updated content
            metadata: Updated metadata
            completed: Mark as completed (sets completed_at)

        Returns:
            True if node was found and updated
        """
        with self._lock:
            if node_id not in self._index:
                logger.warning(f"Node {node_id} not found in index")
                return False

            node = self._index[node_id]

            if status is not None:
                node.status = status

            if content is not None:
                node.content = content

            if metadata is not None:
                node.metadata.update(metadata)

            if completed:
                node.completed_at = datetime.utcnow().isoformat()
                # Update timeline entry status
                for entry in reversed(self._timeline):
                    if entry.node_id == node_id:
                        entry.status = node.status
                        break

            logger.debug(f"Updated node {node_id}")
            return True

    def get_node(self, node_id: str) -> Optional[MemoryNode]:
        """Get a node by ID (fast lookup via index)."""
        with self._lock:
            return self._index.get(node_id)

    def get_children(self, node_id: str) -> List[MemoryNode]:
        """Get all direct children of a node."""
        with self._lock:
            node = self._index.get(node_id)
            if node is None:
                return []
            return [
                self._index[child_id]
                for child_id in node.children
                if child_id in self._index
            ]

    def get_subtree(self, node_id: str) -> List[MemoryNode]:
        """
        Get a node and all its descendants (recursive).

        Returns nodes in breadth-first order.
        """
        with self._lock:
            if node_id not in self._index:
                return []

            result = []
            queue = [node_id]
            visited: Set[str] = set()

            while queue:
                current_id = queue.pop(0)
                if current_id in visited:
                    continue
                visited.add(current_id)

                node = self._index.get(current_id)
                if node:
                    result.append(node)
                    queue.extend(node.children)

            return result

    def get_ancestors(self, node_id: str) -> List[MemoryNode]:
        """Get all ancestors of a node (path to root)."""
        with self._lock:
            ancestors = []
            current = self._index.get(node_id)

            while current and current.parent_id:
                parent = self._index.get(current.parent_id)
                if parent:
                    ancestors.append(parent)
                    current = parent
                else:
                    break

            return ancestors

    # ==================== Timeline Operations ====================

    def get_timeline(self, limit: Optional[int] = None) -> List[TimelineEntry]:
        """Get the timeline entries (most recent first if limit set)."""
        with self._lock:
            if limit:
                return list(self._timeline[-limit:])
            return list(self._timeline)

    def get_timeline_by_agent(self, agent: str) -> List[TimelineEntry]:
        """Get timeline entries filtered by agent."""
        with self._lock:
            return [entry for entry in self._timeline if entry.agent == agent]

    # ==================== Tree Operations ====================

    def get_tree(self) -> Dict[str, Dict[str, Any]]:
        """Get a copy of the entire tree (serialized)."""
        with self._lock:
            return {k: v.to_dict() for k, v in self._tree.items()}

    def get_tree_structure(self, node_id: str = "root") -> Dict[str, Any]:
        """
        Get tree structure as nested dicts for serialization.

        Args:
            node_id: Root node ID (defaults to 'root')

        Returns:
            Nested dictionary structure
        """
        with self._lock:

            def build_structure(nid: str) -> Dict[str, Any]:
                node = self._tree.get(nid)
                if not node:
                    return {}

                return {
                    "id": node.id,
                    "agent": node.agent,
                    "node_type": node.node_type,
                    "description": node.description,
                    "status": node.status,
                    "content": node.content,
                    "metadata": node.metadata,
                    "created_at": node.created_at,
                    "completed_at": node.completed_at,
                    "triggered_by": node.triggered_by,
                    "children": [
                        build_structure(child_id)
                        for child_id in node.children
                        if child_id in self._tree
                    ],
                }

            return build_structure(node_id)

    # ==================== Index Operations ====================

    def get_index(self) -> Dict[str, Dict[str, Any]]:
        """Get a copy of the index (serialized)."""
        with self._lock:
            return {k: v.to_dict() for k, v in self._index.items()}

    def find_nodes(
        self,
        agent: Optional[str] = None,
        node_type: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100,
    ) -> List[MemoryNode]:
        """Find nodes matching criteria."""
        with self._lock:
            results = []
            for node in self._index.values():
                if agent and node.agent != agent:
                    continue
                if node_type and node.node_type != node_type:
                    continue
                if status and node.status != status:
                    continue
                results.append(node)
                if len(results) >= limit:
                    break
            return results

    # ==================== Serialization ====================

    def to_dict(self) -> Dict[str, Any]:
        """Serialize entire working memory to dictionary."""
        with self._lock:
            return {
                "session_id": self.session_id,
                "tree": {k: v.to_dict() for k, v in self._tree.items()},
                "timeline": [entry.to_dict() for entry in self._timeline],
                "index": {k: v.to_dict() for k, v in self._index.items()},
            }

    def to_json(self) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WorkingMemory":
        """Deserialize from dictionary."""
        memory = cls(session_id=data.get("session_id"))

        with memory._lock:
            # Rebuild tree
            for node_data in data.get("tree", {}).values():
                node = MemoryNode.from_dict(node_data)
                memory._tree[node.id] = node

            # Rebuild index
            for node_data in data.get("index", {}).values():
                node = MemoryNode.from_dict(node_data)
                memory._index[node.id] = node

            # Rebuild timeline
            for entry_data in data.get("timeline", []):
                entry = TimelineEntry.from_dict(entry_data)
                memory._timeline.append(entry)

        return memory

    @classmethod
    def from_json(cls, json_str: str) -> "WorkingMemory":
        """Deserialize from JSON string."""
        data = json.loads(json_str)
        return cls.from_dict(data)

    # ==================== Statistics ====================

    def get_stats(self) -> Dict[str, Any]:
        """Get working memory statistics."""
        with self._lock:
            agent_counts: Dict[str, int] = {}
            status_counts: Dict[str, int] = {}
            type_counts: Dict[str, int] = {}

            for node in self._index.values():
                agent_counts[node.agent] = agent_counts.get(node.agent, 0) + 1
                status_counts[node.status] = status_counts.get(node.status, 0) + 1
                type_counts[node.node_type] = type_counts.get(node.node_type, 0) + 1

            return {
                "session_id": self.session_id,
                "total_nodes": len(self._index),
                "timeline_length": len(self._timeline),
                "agent_counts": agent_counts,
                "status_counts": status_counts,
                "type_counts": type_counts,
            }

    # ==================== Reset ====================

    def reset(self):
        """Clear all data and reinitialize."""
        with self._lock:
            self._tree.clear()
            self._timeline.clear()
            self._index.clear()
            self._create_root()
            logger.info(f"Working memory reset for session {self.session_id}")


class AsyncWorkingMemory:
    """
    Async wrapper for WorkingMemory with thread-safe operations.

    Uses asyncio lock for async context.
    """

    def __init__(self, session_id: Optional[str] = None):
        self._memory = WorkingMemory(session_id)
        self._lock = asyncio.Lock()

    async def add_node(
        self,
        agent: str,
        node_type: str,
        description: str,
        parent_id: Optional[str] = None,
        triggered_by: Optional[str] = None,
        content: Optional[Any] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Add a new node (async)."""
        async with self._lock:
            return self._memory.add_node(
                agent=agent,
                node_type=node_type,
                description=description,
                parent_id=parent_id,
                triggered_by=triggered_by,
                content=content,
                metadata=metadata,
            )

    async def update_node(
        self,
        node_id: str,
        status: Optional[str] = None,
        content: Optional[Any] = None,
        metadata: Optional[Dict[str, Any]] = None,
        completed: bool = False,
    ) -> bool:
        """Update a node (async)."""
        async with self._lock:
            return self._memory.update_node(
                node_id=node_id,
                status=status,
                content=content,
                metadata=metadata,
                completed=completed,
            )

    async def get_node(self, node_id: str) -> Optional[MemoryNode]:
        """Get a node by ID (async)."""
        async with self._lock:
            return self._memory.get_node(node_id)

    async def get_timeline(self, limit: Optional[int] = None) -> List[TimelineEntry]:
        """Get timeline entries (async)."""
        async with self._lock:
            return self._memory.get_timeline(limit)

    async def get_subtree(self, node_id: str) -> List[MemoryNode]:
        """Get subtree (async)."""
        async with self._lock:
            return self._memory.get_subtree(node_id)

    async def to_dict(self) -> Dict[str, Any]:
        """Serialize to dict (async)."""
        async with self._lock:
            return self._memory.to_dict()

    async def load(self, data: Dict[str, Any]) -> None:
        """Load from dictionary (async)."""
        async with self._lock:
            self._memory = WorkingMemory.from_dict(data)

    async def get_stats(self) -> Dict[str, Any]:
        """Get statistics (async)."""
        async with self._lock:
            return self._memory.get_stats()

    async def reset(self):
        """Reset memory (async)."""
        async with self._lock:
            self._memory.reset()
