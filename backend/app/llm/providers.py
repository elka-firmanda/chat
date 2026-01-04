"""
LLM Provider Abstraction Layer

Unified interface for multiple LLM providers (Anthropic, OpenAI, OpenRouter)
with streaming support, error handling, token counting, and cost tracking.
"""

import asyncio
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import AsyncIterator, Dict, List, Optional, Any
from enum import Enum
from functools import lru_cache
import logging

logger = logging.getLogger(__name__)


class ProviderType(str, Enum):
    """Supported LLM providers."""

    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    OPENROUTER = "openrouter"


@dataclass
class LLMResponse:
    """Response from LLM provider."""

    content: str
    provider: str
    model: str
    total_tokens: int
    prompt_tokens: int
    completion_tokens: int
    cost: float
    latency_ms: float
    raw_response: Optional[Any] = None


@dataclass
class StreamChunk:
    """A chunk of a streaming response."""

    content: str
    delta: str
    is_complete: bool = False
    total_tokens: int = 0
    cost: float = 0.0


@dataclass
class ProviderConfig:
    """Configuration for an LLM provider."""

    provider: str
    model: str
    api_key: Optional[str] = None
    max_tokens: int = 4096
    temperature: float = 0.7
    timeout: int = 60
    max_retries: int = 3
    system_prompt: Optional[str] = None
    max_output_tokens: Optional[int] = None


class BaseLLMProvider(ABC):
    """Abstract base class for LLM providers."""

    def __init__(self, config: ProviderConfig):
        self.config = config
        self._request_count = 0
        self._total_tokens = 0
        self._total_cost = 0.0

    @property
    def provider_type(self) -> str:
        """Return the provider type identifier."""
        return self.config.provider

    @property
    def model(self) -> str:
        """Return the model name."""
        return self.config.model

    @abstractmethod
    async def complete(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        """Send a completion request to the LLM."""
        pass

    @abstractmethod
    async def stream_complete(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> AsyncIterator[StreamChunk]:
        """Send a streaming completion request to the LLM."""
        pass

    def get_usage_stats(self) -> Dict[str, Any]:
        """Get usage statistics for this provider."""
        return {
            "provider": self.provider_type,
            "model": self.model,
            "request_count": self._request_count,
            "total_tokens": self._total_tokens,
            "total_cost": self._total_cost,
        }

    def _update_stats(self, tokens: int, cost: float):
        """Update internal usage statistics."""
        self._request_count += 1
        self._total_tokens += tokens
        self._total_cost += cost


class RetryableError(Exception):
    """Exception that should trigger a retry."""

    def __init__(self, message: str, retry_after: Optional[float] = None):
        super().__init__(message)
        self.retry_after = retry_after


class RateLimitError(RetryableError):
    """Rate limit exceeded error."""

    def __init__(
        self, message: str = "Rate limit exceeded", retry_after: Optional[float] = None
    ):
        super().__init__(message, retry_after)


class APIError(RetryableError):
    """API error from the provider."""

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        retry_after: Optional[float] = None,
    ):
        super().__init__(message, retry_after)
        self.status_code = status_code


class AnthropicProvider(BaseLLMProvider):
    """Anthropic Claude provider using the official SDK."""

    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        self._client = None

    @property
    def client(self):
        """Lazy initialization of Anthropic client."""
        if self._client is None:
            try:
                import anthropic

                self._client = anthropic.Anthropic(
                    api_key=self.config.api_key,
                    timeout=self.config.timeout,
                )
            except ImportError:
                raise ImportError(
                    "anthropic SDK not installed. Install with: pip install anthropic"
                )
        return self._client

    def _calculate_cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        """Calculate cost for Anthropic API."""
        pricing = {
            "claude-3-5-sonnet-20241022": {"input": 3.0, "output": 15.0},
            "claude-3-5-sonnet-20240620": {"input": 3.0, "output": 15.0},
            "claude-3-opus-20240229": {"input": 15.0, "output": 75.0},
            "claude-3-haiku-20240307": {"input": 0.25, "output": 1.25},
            "claude-3-sonnet-20240229": {"input": 3.0, "output": 15.0},
        }

        model_pricing = pricing.get(self.config.model, {"input": 3.0, "output": 15.0})
        input_cost = (prompt_tokens / 1_000_000) * model_pricing["input"]
        output_cost = (completion_tokens / 1_000_000) * model_pricing["output"]
        return input_cost + output_cost

    async def _with_retry(self, coro):
        """Execute coroutine with retry logic."""
        last_error = None
        for attempt in range(self.config.max_retries):
            try:
                return await asyncio.wait_for(coro, timeout=self.config.timeout)
            except asyncio.TimeoutError:
                last_error = APIError(
                    f"Request timeout after {self.config.timeout}s", retry_after=1
                )
                logger.warning(
                    f"Anthropic API timeout (attempt {attempt + 1}/{self.config.max_retries})"
                )
            except Exception as e:
                last_error = self._classify_error(e)
                logger.warning(
                    f"Anthropic API error (attempt {attempt + 1}/{self.config.max_retries}): {e}"
                )

            if attempt < self.config.max_retries - 1:
                await asyncio.sleep(self._get_backoff(attempt))

        raise last_error  # type: ignore

    def _classify_error(self, error: Exception) -> RetryableError:
        """Classify error and determine if retryable."""
        error_str = str(error).lower()

        if "rate limit" in error_str or "429" in error_str:
            return RateLimitError(str(error))
        if "overloaded" in error_str or "529" in error_str:
            return RetryableError("Service overloaded", retry_after=5)
        if "authentication" in error_str or "401" in error_str:
            return APIError("Invalid API key", status_code=401)
        if "permission" in error_str or "403" in error_str:
            return APIError("Permission denied", status_code=403)

        return APIError(str(error))

    def _get_backoff(self, attempt: int) -> float:
        """Calculate exponential backoff."""
        return min(2**attempt * 0.5, 30)

    def _prepare_messages(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Prepare messages for Anthropic API."""
        if system_prompt:
            first_msg = messages[0] if messages else None
            if first_msg and first_msg.get("role") == "system":
                system_prompt = f"{system_prompt}\n\n{first_msg['content']}"
                messages = messages[1:]

        return {
            "messages": messages,
            "system": system_prompt,
            "model": self.config.model,
            "max_tokens": self.config.max_output_tokens or self.config.max_tokens,
            "temperature": self.config.temperature,
        }

    async def complete(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        """Send completion request to Anthropic."""
        start_time = time.perf_counter()

        request_body = self._prepare_messages(
            messages, system_prompt or self.config.system_prompt
        )

        def sync_complete():
            return self.client.messages.create(
                **request_body,
                extra_headers={"Anthropic-Version": "2023-06-01"},
            )

        response = await self._with_retry(sync_complete())

        latency_ms = (time.perf_counter() - start_time) * 1000

        content = response.content[0].text if response.content else ""
        prompt_tokens = response.usage.input_tokens
        completion_tokens = response.usage.output_tokens
        total_tokens = prompt_tokens + completion_tokens
        cost = self._calculate_cost(prompt_tokens, completion_tokens)

        self._update_stats(total_tokens, cost)

        return LLMResponse(
            content=content,
            provider=self.provider_type,
            model=self.config.model,
            total_tokens=total_tokens,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            cost=cost,
            latency_ms=latency_ms,
            raw_response=response,
        )

    async def stream_complete(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> AsyncIterator[StreamChunk]:
        """Send streaming completion request to Anthropic."""
        start_time = time.perf_counter()
        accumulated_content = ""
        total_prompt_tokens = 0
        total_completion_tokens = 0

        request_body = self._prepare_messages(
            messages, system_prompt or self.config.system_prompt
        )

        def sync_stream():
            return self.client.messages.stream(
                **request_body,
                extra_headers={"Anthropic-Version": "2023-06-01"},
            )

        stream = await self._with_retry(sync_stream())

        async with stream as event_stream:
            async for event in event_stream:
                if event.type == "content_block_delta":
                    delta = event.delta.text
                    accumulated_content += delta
                    total_completion_tokens += 1

                    yield StreamChunk(
                        content=accumulated_content,
                        delta=delta,
                        is_complete=False,
                        total_tokens=total_prompt_tokens + total_completion_tokens,
                    )

                elif event.type == "message_start":
                    total_prompt_tokens = event.message.usage.input_tokens

                elif event.type == "message_delta":
                    pass

                elif event.type == "message_stop":
                    latency_ms = (time.perf_counter() - start_time) * 1000
                    cost = self._calculate_cost(
                        total_prompt_tokens, total_completion_tokens
                    )
                    self._update_stats(
                        total_prompt_tokens + total_completion_tokens, cost
                    )

                    yield StreamChunk(
                        content=accumulated_content,
                        delta="",
                        is_complete=True,
                        total_tokens=total_prompt_tokens + total_completion_tokens,
                        cost=cost,
                    )


class OpenAIProvider(BaseLLMProvider):
    """OpenAI GPT provider using the official SDK."""

    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        self._client = None

    @property
    def client(self):
        """Lazy initialization of OpenAI client."""
        if self._client is None:
            try:
                from openai import AsyncOpenAI

                self._client = AsyncOpenAI(
                    api_key=self.config.api_key,
                    timeout=self.config.timeout,
                )
            except ImportError:
                raise ImportError(
                    "openai SDK not installed. Install with: pip install openai"
                )
        return self._client

    def _calculate_cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        """Calculate cost for OpenAI API."""
        pricing = {
            "gpt-4-turbo": {"input": 10.0, "output": 30.0},
            "gpt-4-turbo-2024-04-09": {"input": 10.0, "output": 30.0},
            "gpt-4o": {"input": 5.0, "output": 15.0},
            "gpt-4o-2024-05-13": {"input": 5.0, "output": 15.0},
            "gpt-4": {"input": 30.0, "output": 60.0},
            "gpt-4-0613": {"input": 30.0, "output": 60.0},
            "gpt-3.5-turbo": {"input": 0.5, "output": 1.5},
            "gpt-3.5-turbo-1106": {"input": 1.0, "output": 2.0},
        }

        model_pricing = pricing.get(self.config.model, {"input": 0.5, "output": 1.5})
        input_cost = (prompt_tokens / 1_000_000) * model_pricing["input"]
        output_cost = (completion_tokens / 1_000_000) * model_pricing["output"]
        return input_cost + output_cost

    async def _with_retry(self, coro):
        """Execute coroutine with retry logic."""
        last_error = None
        for attempt in range(self.config.max_retries):
            try:
                return await asyncio.wait_for(coro, timeout=self.config.timeout)
            except asyncio.TimeoutError:
                last_error = APIError(
                    f"Request timeout after {self.config.timeout}s", retry_after=1
                )
                logger.warning(
                    f"OpenAI API timeout (attempt {attempt + 1}/{self.config.max_retries})"
                )
            except Exception as e:
                last_error = self._classify_error(e)
                logger.warning(
                    f"OpenAI API error (attempt {attempt + 1}/{self.config.max_retries}): {e}"
                )

            if attempt < self.config.max_retries - 1:
                await asyncio.sleep(self._get_backoff(attempt))

        raise last_error  # type: ignore

    def _classify_error(self, error: Exception) -> RetryableError:
        """Classify error and determine if retryable."""
        error_str = str(error).lower()

        if "rate limit" in error_str or "429" in error_str:
            return RateLimitError(str(error))
        if "overloaded" in error_str or "503" in error_str:
            return RetryableError("Service overloaded", retry_after=5)
        if "invalid api key" in error_str or "401" in error_str:
            return APIError("Invalid API key", status_code=401)
        if "access denied" in error_str or "403" in error_str:
            return APIError("Permission denied", status_code=403)

        return APIError(str(error))

    def _get_backoff(self, attempt: int) -> float:
        """Calculate exponential backoff."""
        return min(2**attempt * 0.5, 30)

    async def complete(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        """Send completion request to OpenAI."""
        start_time = time.perf_counter()

        chat_messages = []
        if system_prompt:
            chat_messages.append({"role": "system", "content": system_prompt})
        elif self.config.system_prompt:
            chat_messages.append(
                {"role": "system", "content": self.config.system_prompt}
            )

        chat_messages.extend(messages)

        request = self.client.chat.completions.create(
            model=self.config.model,
            messages=chat_messages,
            temperature=temperature or self.config.temperature,
            max_tokens=max_tokens
            or self.config.max_output_tokens
            or self.config.max_tokens,
            stream=False,
        )

        response = await self._with_retry(request)

        latency_ms = (time.perf_counter() - start_time) * 1000

        content = response.choices[0].message.content or ""
        usage = response.usage
        prompt_tokens = usage.prompt_tokens
        completion_tokens = usage.completion_tokens
        total_tokens = prompt_tokens + completion_tokens
        cost = self._calculate_cost(prompt_tokens, completion_tokens)

        self._update_stats(total_tokens, cost)

        return LLMResponse(
            content=content,
            provider=self.provider_type,
            model=self.config.model,
            total_tokens=total_tokens,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            cost=cost,
            latency_ms=latency_ms,
            raw_response=response,
        )

    async def stream_complete(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> AsyncIterator[StreamChunk]:
        """Send streaming completion request to OpenAI."""
        start_time = time.perf_counter()
        accumulated_content = ""
        total_prompt_tokens = 0
        total_completion_tokens = 0

        chat_messages = []
        if system_prompt:
            chat_messages.append({"role": "system", "content": system_prompt})
        elif self.config.system_prompt:
            chat_messages.append(
                {"role": "system", "content": self.config.system_prompt}
            )

        chat_messages.extend(messages)

        request = self.client.chat.completions.create(
            model=self.config.model,
            messages=chat_messages,
            temperature=temperature or self.config.temperature,
            max_tokens=max_tokens
            or self.config.max_output_tokens
            or self.config.max_tokens,
            stream=True,
        )

        stream = await self._with_retry(request)

        async for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                delta = chunk.choices[0].delta.content
                accumulated_content += delta
                total_completion_tokens += 1

                yield StreamChunk(
                    content=accumulated_content,
                    delta=delta,
                    is_complete=False,
                    total_tokens=total_prompt_tokens + total_completion_tokens,
                )

            if chunk.usage and total_prompt_tokens == 0:
                total_prompt_tokens = chunk.usage.prompt_tokens

        latency_ms = (time.perf_counter() - start_time) * 1000
        cost = self._calculate_cost(total_prompt_tokens, total_completion_tokens)
        self._update_stats(total_prompt_tokens + total_completion_tokens, cost)

        yield StreamChunk(
            content=accumulated_content,
            delta="",
            is_complete=True,
            total_tokens=total_prompt_tokens + total_completion_tokens,
            cost=cost,
        )


class OpenRouterProvider(BaseLLMProvider):
    """OpenRouter provider using OpenAI-compatible API."""

    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        self._client = None
        self._base_url = "https://openrouter.ai/api/v1"

    @property
    def client(self):
        """Lazy initialization of OpenRouter client."""
        if self._client is None:
            try:
                from openai import AsyncOpenAI

                self._client = AsyncOpenAI(
                    base_url=self._base_url,
                    api_key=self.config.api_key,
                    timeout=self.config.timeout,
                    default_headers={
                        "HTTP-Referer": "https://github.com/your-org/agentic-chatbot",
                        "X-Title": "Agentic Chatbot",
                    },
                )
            except ImportError:
                raise ImportError(
                    "openai SDK not installed. Install with: pip install openai"
                )
        return self._client

    def _calculate_cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        """Calculate cost for OpenRouter API."""
        return 0.0

    async def _with_retry(self, coro):
        """Execute coroutine with retry logic."""
        last_error = None
        for attempt in range(self.config.max_retries):
            try:
                return await asyncio.wait_for(coro, timeout=self.config.timeout)
            except asyncio.TimeoutError:
                last_error = APIError(
                    f"Request timeout after {self.config.timeout}s", retry_after=1
                )
                logger.warning(
                    f"OpenRouter API timeout (attempt {attempt + 1}/{self.config.max_retries})"
                )
            except Exception as e:
                last_error = self._classify_error(e)
                logger.warning(
                    f"OpenRouter API error (attempt {attempt + 1}/{self.config.max_retries}): {e}"
                )

            if attempt < self.config.max_retries - 1:
                await asyncio.sleep(self._get_backoff(attempt))

        raise last_error  # type: ignore

    def _classify_error(self, error: Exception) -> RetryableError:
        """Classify error and determine if retryable."""
        error_str = str(error).lower()

        if "rate limit" in error_str or "429" in error_str:
            return RateLimitError(str(error))
        if "overloaded" in error_str or "503" in error_str:
            return RetryableError("Service overloaded", retry_after=5)
        if "invalid api key" in error_str or "401" in error_str:
            return APIError("Invalid API key", status_code=401)
        if "access denied" in error_str or "403" in error_str:
            return APIError("Permission denied", status_code=403)

        return APIError(str(error))

    def _get_backoff(self, attempt: int) -> float:
        """Calculate exponential backoff."""
        return min(2**attempt * 0.5, 30)

    async def complete(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        """Send completion request to OpenRouter."""
        start_time = time.perf_counter()

        chat_messages = []
        if system_prompt:
            chat_messages.append({"role": "system", "content": system_prompt})
        elif self.config.system_prompt:
            chat_messages.append(
                {"role": "system", "content": self.config.system_prompt}
            )

        chat_messages.extend(messages)

        request = self.client.chat.completions.create(
            model=self.config.model,
            messages=chat_messages,
            temperature=temperature or self.config.temperature,
            max_tokens=max_tokens
            or self.config.max_output_tokens
            or self.config.max_tokens,
            stream=False,
        )

        response = await self._with_retry(request)

        latency_ms = (time.perf_counter() - start_time) * 1000

        content = response.choices[0].message.content or ""
        usage = response.usage
        prompt_tokens = usage.prompt_tokens
        completion_tokens = usage.completion_tokens
        total_tokens = prompt_tokens + completion_tokens
        cost = self._calculate_cost(prompt_tokens, completion_tokens)

        self._update_stats(total_tokens, cost)

        return LLMResponse(
            content=content,
            provider=self.provider_type,
            model=self.config.model,
            total_tokens=total_tokens,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            cost=cost,
            latency_ms=latency_ms,
            raw_response=response,
        )

    async def stream_complete(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> AsyncIterator[StreamChunk]:
        """Send streaming completion request to OpenRouter."""
        start_time = time.perf_counter()
        accumulated_content = ""
        total_prompt_tokens = 0
        total_completion_tokens = 0

        chat_messages = []
        if system_prompt:
            chat_messages.append({"role": "system", "content": system_prompt})
        elif self.config.system_prompt:
            chat_messages.append(
                {"role": "system", "content": self.config.system_prompt}
            )

        chat_messages.extend(messages)

        request = self.client.chat.completions.create(
            model=self.config.model,
            messages=chat_messages,
            temperature=temperature or self.config.temperature,
            max_tokens=max_tokens
            or self.config.max_output_tokens
            or self.config.max_tokens,
            stream=True,
        )

        stream = await self._with_retry(request)

        async for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                delta = chunk.choices[0].delta.content
                accumulated_content += delta
                total_completion_tokens += 1

                yield StreamChunk(
                    content=accumulated_content,
                    delta=delta,
                    is_complete=False,
                    total_tokens=total_prompt_tokens + total_completion_tokens,
                )

            if chunk.usage and total_prompt_tokens == 0:
                total_prompt_tokens = chunk.usage.prompt_tokens

        latency_ms = (time.perf_counter() - start_time) * 1000
        cost = self._calculate_cost(total_prompt_tokens, total_completion_tokens)
        self._update_stats(total_prompt_tokens + total_completion_tokens, cost)

        yield StreamChunk(
            content=accumulated_content,
            delta="",
            is_complete=True,
            total_tokens=total_prompt_tokens + total_completion_tokens,
            cost=cost,
        )


class LLMProviderFactory:
    """Factory for creating LLM providers based on configuration."""

    _providers: Dict[str, type] = {
        ProviderType.ANTHROPIC.value: AnthropicProvider,
        ProviderType.OPENAI.value: OpenAIProvider,
        ProviderType.OPENROUTER.value: OpenRouterProvider,
    }

    _provider_cache: Dict[str, BaseLLMProvider] = {}

    @classmethod
    def register_provider(cls, provider_type: str, provider_class: type):
        """Register a new provider type."""
        cls._providers[provider_type.lower()] = provider_class

    @classmethod
    def create(
        cls,
        provider: str,
        model: str,
        api_key: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        timeout: int = 60,
        max_retries: int = 3,
        system_prompt: Optional[str] = None,
    ) -> BaseLLMProvider:
        """Create an LLM provider instance."""
        provider = provider.lower()

        if provider not in cls._providers:
            raise ValueError(
                f"Unknown provider: {provider}. Supported providers: {list(cls._providers.keys())}"
            )

        cache_key = f"{provider}:{model}:{max_tokens}:{temperature}"
        if cache_key in cls._provider_cache:
            return cls._provider_cache[cache_key]

        provider_class = cls._providers[provider]
        config = ProviderConfig(
            provider=provider,
            model=model,
            api_key=api_key,
            max_tokens=max_tokens,
            temperature=temperature,
            timeout=timeout,
            max_retries=max_retries,
            system_prompt=system_prompt,
        )

        instance = provider_class(config)
        cls._provider_cache[cache_key] = instance
        return instance

    @classmethod
    def clear_cache(cls):
        """Clear the provider cache. Useful when API keys change."""
        cls._provider_cache.clear()

    @classmethod
    def from_agent_config(
        cls,
        agent_config: Dict[str, Any],
        api_keys: Dict[str, str],
    ) -> BaseLLMProvider:
        """Create provider from agent configuration dict."""
        provider = agent_config.get("provider", "anthropic")
        model = agent_config.get("model", "claude-3-5-sonnet-20241022")
        api_key = api_keys.get(provider)
        max_tokens = agent_config.get("max_tokens", 4096)
        temperature = agent_config.get("temperature", 0.7)

        return cls.create(
            provider=provider,
            model=model,
            api_key=api_key,
            max_tokens=max_tokens,
            temperature=temperature,
        )

    @classmethod
    def get_supported_providers(cls) -> List[str]:
        """Get list of supported provider types."""
        return list(cls._providers.keys())
