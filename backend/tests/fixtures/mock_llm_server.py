"""
Mock LLM Server for HTTP-level LLM mocking.

Provides mock HTTP servers that simulate LLM provider APIs at the HTTP level,
allowing tests to verify request/response patterns, headers, and streaming behavior.
"""

import asyncio
import json
import uuid
from datetime import datetime
from typing import AsyncIterator, Dict, Any, Optional, Callable, List
from dataclasses import dataclass
import httpx
import pytest_asyncio


@dataclass
class MockLLMConfig:
    """Configuration for mock LLM responses."""

    provider: str
    model: str
    response_content: str = "This is a mock response."
    stream_chunks: Optional[List[str]] = None
    latency_ms: int = 50
    should_fail: bool = False
    fail_error: str = "Mock API error"
    fail_status_code: int = 500
    rate_limit_delay: Optional[float] = None


class MockAnthropicServer:
    """Mock Anthropic API server for testing."""

    def __init__(self, config: MockLLMConfig):
        self.config = config
        self.request_log: List[Dict[str, Any]] = []

    async def handle_request(self, request: httpx.Request) -> httpx.Response:
        """Handle incoming HTTP request and return mock response."""
        self.request_log.append(
            {
                "timestamp": datetime.utcnow().isoformat(),
                "method": request.method,
                "url": str(request.url),
                "headers": dict(request.headers),
                "body": request.content.decode() if request.content else None,
            }
        )

        if self.config.should_fail:
            return httpx.Response(
                status_code=self.config.fail_status_code,
                content=json.dumps(
                    {"error": {"type": "api_error", "message": self.config.fail_error}}
                ),
                headers={"Content-Type": "application/json"},
            )

        request_body = json.loads(request.content.decode()) if request.content else {}

        if "/messages" in str(request.url):
            if request.method == "POST":
                return await self._handle_completion(request_body)
            elif request.method == "GET":
                return self._handle_get_message()

        return httpx.Response(status_code=404, content='{"error": "Not found"}')

    async def _handle_completion(self, body: Dict[str, Any]) -> httpx.Response:
        """Handle message completion request."""
        await asyncio.sleep(self.config.latency_ms / 1000)

        if self.config.rate_limit_delay:
            return httpx.Response(
                status_code=429,
                content=json.dumps(
                    {
                        "error": {
                            "type": "rate_limit_error",
                            "message": "Rate limit exceeded",
                        }
                    }
                ),
                headers={"Retry-After": str(self.config.rate_limit_delay)},
            )

        messages = body.get("messages", [])
        system_prompt = body.get("system", "")

        content_text = self.config.response_content
        if self.config.stream_chunks:
            content_text = self.config.response_content

        response = {
            "id": f"msg_{uuid.uuid4().hex[:12]}",
            "type": "message",
            "role": "assistant",
            "content": [{"type": "text", "text": content_text}],
            "model": self.config.model,
            "stop_reason": "end_turn",
            "usage": {
                "input_tokens": len(str(messages)) // 4,
                "output_tokens": len(content_text) // 4,
            },
        }

        return httpx.Response(
            status_code=200,
            content=json.dumps(response),
            headers={"Content-Type": "application/json"},
        )

    def _handle_get_message(self) -> httpx.Response:
        """Handle get message request."""
        return httpx.Response(
            status_code=200,
            content=json.dumps(
                {
                    "id": f"msg_{uuid.uuid4().hex[:12]}",
                    "type": "message",
                    "content": [{"type": "text", "text": self.config.response_content}],
                }
            ),
            headers={"Content-Type": "application/json"},
        )

    async def stream_complete(self, body: Dict[str, Any]) -> AsyncIterator[str]:
        """Generate streaming response chunks."""
        await asyncio.sleep(self.config.latency_ms / 1000)

        content = self.config.response_content
        chunks = self.config.stream_chunks or list(content)

        for i, chunk in enumerate(chunks):
            is_last = i == len(chunks) - 1
            event_data = {
                "type": "content_block_delta" if not is_last else "message_delta",
                "index": 0,
                "delta": {"type": "text_delta", "text": chunk},
            }
            yield f"event: {event_data['type']}\ndata: {json.dumps(event_data)}\n\n"

        yield f"event: message_start\ndata: {json.dumps({'type': 'message_start', 'message': {'id': 'msg_test', 'usage': {'input_tokens': 10}}})}\n\n"
        yield f"event: message_stop\ndata: {json.dumps({'type': 'message_stop'})}\n\n"


class MockOpenAIServer:
    """Mock OpenAI API server for testing."""

    def __init__(self, config: MockLLMConfig):
        self.config = config
        self.request_log: List[Dict[str, Any]] = []

    async def handle_request(self, request: httpx.Request) -> httpx.Response:
        """Handle incoming HTTP request and return mock response."""
        self.request_log.append(
            {
                "timestamp": datetime.utcnow().isoformat(),
                "method": request.method,
                "url": str(request.url),
                "headers": dict(request.headers),
                "body": request.content.decode() if request.content else None,
            }
        )

        if self.config.should_fail:
            return httpx.Response(
                status_code=self.config.fail_status_code,
                content=json.dumps(
                    {"error": {"message": self.config.fail_error, "type": "api_error"}}
                ),
                headers={"Content-Type": "application/json"},
            )

        request_body = json.loads(request.content.decode()) if request.content else {}

        if "/chat/completions" in str(request.url):
            if request.method == "POST":
                return await self._handle_completion(request_body)

        return httpx.Response(status_code=404, content='{"error": "Not found"}')

    async def _handle_completion(self, body: Dict[str, Any]) -> httpx.Response:
        """Handle chat completion request."""
        await asyncio.sleep(self.config.latency_ms / 1000)

        if self.config.rate_limit_delay:
            return httpx.Response(
                status_code=429,
                content=json.dumps(
                    {
                        "error": {
                            "message": "Rate limit exceeded",
                            "type": "rate_limit_error",
                        }
                    }
                ),
                headers={"Retry-After": str(self.config.rate_limit_delay)},
            )

        is_streaming = body.get("stream", False)
        content = self.config.response_content

        if is_streaming:
            chunks = self.config.stream_chunks or list(content)
            response_parts = []
            for i, chunk in enumerate(chunks):
                is_last = i == len(chunks) - 1
                chunk_data = {
                    "id": f"chatcmpl_{uuid.uuid4().hex[:12]}",
                    "object": "chat.completion.chunk",
                    "created": int(datetime.utcnow().timestamp()),
                    "model": self.config.model,
                    "choices": [
                        {
                            "index": 0,
                            "delta": {"content": chunk} if chunk else {},
                            "finish_reason": "stop" if is_last else None,
                        }
                    ],
                }
                response_parts.append(f"data: {json.dumps(chunk_data)}\n\n")

            response_parts.append("data: [DONE]\n\n")
            return httpx.Response(
                status_code=200,
                content="".join(response_parts),
                headers={"Content-Type": "text/event-stream"},
            )

        response = {
            "id": f"chatcmpl_{uuid.uuid4().hex[:12]}",
            "object": "chat.completion",
            "created": int(datetime.utcnow().timestamp()),
            "model": self.config.model,
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": content},
                    "finish_reason": "stop",
                }
            ],
            "usage": {
                "prompt_tokens": len(str(body.get("messages", []))) // 4,
                "completion_tokens": len(content) // 4,
                "total_tokens": 0,
            },
        }

        return httpx.Response(
            status_code=200,
            content=json.dumps(response),
            headers={"Content-Type": "application/json"},
        )


class MockOpenRouterServer:
    """Mock OpenRouter API server for testing."""

    def __init__(self, config: MockLLMConfig):
        self.config = config
        self.request_log: List[Dict[str, Any]] = []

    async def handle_request(self, request: httpx.Request) -> httpx.Response:
        """Handle incoming HTTP request and return mock response."""
        self.request_log.append(
            {
                "timestamp": datetime.utcnow().isoformat(),
                "method": request.method,
                "url": str(request.url),
                "headers": dict(request.headers),
                "body": request.content.decode() if request.content else None,
            }
        )

        if self.config.should_fail:
            return httpx.Response(
                status_code=self.config.fail_status_code,
                content=json.dumps({"error": {"message": self.config.fail_error}}),
                headers={"Content-Type": "application/json"},
            )

        request_body = json.loads(request.content.decode()) if request.content else {}

        if "/chat/completions" in str(request.url):
            if request.method == "POST":
                return await self._handle_completion(request_body)

        return httpx.Response(status_code=404, content='{"error": "Not found"}')

    async def _handle_completion(self, body: Dict[str, Any]) -> httpx.Response:
        """Handle chat completion request."""
        await asyncio.sleep(self.config.latency_ms / 1000)

        content = self.config.response_content
        response = {
            "id": f"or_{uuid.uuid4().hex[:12]}",
            "object": "chat.completion",
            "created": int(datetime.utcnow().timestamp()),
            "model": self.config.model,
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": content},
                    "finish_reason": "stop",
                }
            ],
            "usage": {
                "prompt_tokens": 10,
                "completion_tokens": len(content) // 4,
                "total_tokens": 0,
            },
        }

        return httpx.Response(
            status_code=200,
            content=json.dumps(response),
            headers={"Content-Type": "application/json"},
        )


class MockLLMServerManager:
    """Manages mock LLM servers for testing."""

    def __init__(self):
        self._servers: Dict[str, Any] = {}
        self._ports: Dict[str, int] = {}
        self._next_port = 18000

    def create_anthropic_server(
        self, config: Optional[MockLLMConfig] = None
    ) -> MockAnthropicServer:
        """Create a mock Anthropic server."""
        if config is None:
            config = MockLLMConfig(
                provider="anthropic", model="claude-3-5-sonnet-20241022"
            )
        server = MockAnthropicServer(config)
        self._next_port += 1
        self._ports[id(server)] = self._next_port
        return server

    def create_openai_server(
        self, config: Optional[MockLLMConfig] = None
    ) -> MockOpenAIServer:
        """Create a mock OpenAI server."""
        if config is None:
            config = MockLLMConfig(provider="openai", model="gpt-4-turbo")
        server = MockOpenAIServer(config)
        self._next_port += 1
        self._ports[id(server)] = self._next_port
        return server

    def create_openrouter_server(
        self, config: Optional[MockLLMConfig] = None
    ) -> MockOpenRouterServer:
        """Create a mock OpenRouter server."""
        if config is None:
            config = MockLLMConfig(provider="openrouter", model="claude-3-5-sonnet")
        server = MockOpenRouterServer(config)
        self._next_port += 1
        self._ports[id(server)] = self._next_port
        return server

    async def start_server(self, server: Any) -> str:
        """Start a mock server and return its base URL."""
        port = self._ports[id(server)]
        app = httpx.AsyncTransport(server.handle_request)

        async with httpx.AsyncClient(
            transport=app, base_url=f"http://localhost:{port}"
        ) as client:
            pass

        return f"http://localhost:{port}"

    def get_request_log(self, server: Any) -> List[Dict[str, Any]]:
        """Get the request log for a server."""
        return server.request_log


@pytest_asyncio.fixture
async def mock_llm_server():
    """Create a mock LLM server manager for testing."""
    manager = MockLLMServerManager()
    yield manager
    pass


@pytest_asyncio.fixture
async def mock_anthropic_server():
    """Create a mock Anthropic server for testing."""
    config = MockLLMConfig(
        provider="anthropic",
        model="claude-3-5-sonnet-20241022",
        response_content="This is a test response from the mock Anthropic API.",
    )
    server = MockAnthropicServer(config)
    yield server


@pytest_asyncio.fixture
async def mock_openai_server():
    """Create a mock OpenAI server for testing."""
    config = MockLLMConfig(
        provider="openai",
        model="gpt-4-turbo",
        response_content="This is a test response from the mock OpenAI API.",
    )
    server = MockOpenAIServer(config)
    yield server


@pytest_asyncio.fixture
def mock_anthropic_response():
    """Mock Anthropic API response structure."""
    return {
        "id": f"msg_{uuid.uuid4().hex[:12]}",
        "type": "message",
        "role": "assistant",
        "content": [{"type": "text", "text": "This is a mock response."}],
        "model": "claude-3-5-sonnet-20241022",
        "stop_reason": "end_turn",
        "usage": {
            "input_tokens": 50,
            "output_tokens": 100,
        },
    }


@pytest_asyncio.fixture
def mock_openai_response():
    """Mock OpenAI API response structure."""
    return {
        "id": f"chatcmpl_{uuid.uuid4().hex[:12]}",
        "object": "chat.completion",
        "created": int(datetime.utcnow().timestamp()),
        "model": "gpt-4-turbo",
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": "This is a mock response."},
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": 50,
            "completion_tokens": 100,
            "total_tokens": 150,
        },
    }


class MockLLMProvider:
    """Mock LLM provider that can be used in place of real providers."""

    def __init__(self, config: MockLLMConfig):
        self.config = config
        self._request_count = 0
        self._total_tokens = 0

    @property
    def provider_type(self) -> str:
        return self.config.provider

    @property
    def model(self) -> str:
        return self.config.model

    async def complete(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Simulate a completion request."""
        self._request_count += 1
        content = self.config.response_content
        self._total_tokens += len(content) // 4

        return {
            "content": content,
            "provider": self.config.provider,
            "model": self.config.model,
            "total_tokens": self._total_tokens,
            "prompt_tokens": len(str(messages)) // 4,
            "completion_tokens": len(content) // 4,
            "cost": 0.001,
            "latency_ms": self.config.latency_ms,
        }

    async def stream_complete(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> AsyncIterator[Dict[str, Any]]:
        """Simulate a streaming completion request."""
        content = self.config.response_content
        chunks = self.config.stream_chunks or list(content)

        for i, chunk in enumerate(chunks):
            yield {
                "content": content[: i + 1],
                "delta": chunk,
                "is_complete": i == len(chunks) - 1,
                "total_tokens": self._total_tokens + i + 1,
            }

    def get_usage_stats(self) -> Dict[str, Any]:
        """Get usage statistics."""
        return {
            "provider": self.config.provider,
            "model": self.config.model,
            "request_count": self._request_count,
            "total_tokens": self._total_tokens,
        }


@pytest_asyncio.fixture
def mock_llm_provider():
    """Create a mock LLM provider."""

    def _create_provider(config: Optional[MockLLMConfig] = None) -> MockLLMProvider:
        if config is None:
            config = MockLLMConfig(
                provider="anthropic",
                model="claude-3-5-sonnet-20241022",
                response_content="This is a mock response.",
            )
        return MockLLMProvider(config)

    return _create_provider
