"""LLM provider factory service using LangChain."""

from collections.abc import AsyncIterator
from enum import Enum
from typing import Any

from langchain_anthropic import ChatAnthropic
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from app.config.schema import AgentSettings
from app.config.config_manager import ConfigManager


class LLMProvider(str, Enum):
    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    OPENROUTER = "openrouter"


def get_llm(
    agent_config: AgentSettings, config_manager: ConfigManager
) -> BaseChatModel:
    """Factory function to create an LLM instance based on provider."""
    provider = agent_config.provider
    model = agent_config.model
    max_tokens = agent_config.max_tokens
    temperature = agent_config.temperature

    api_keys = config_manager.get_api_keys()

    if provider == LLMProvider.ANTHROPIC or provider == "anthropic":
        return ChatAnthropic(
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            api_key=api_keys.anthropic,
        )

    elif provider == LLMProvider.OPENAI or provider == "openai":
        return ChatOpenAI(
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            api_key=api_keys.openai,
        )

    elif provider == LLMProvider.OPENROUTER or provider == "openrouter":
        return ChatOpenAI(
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            api_key=api_keys.openrouter,
            base_url="https://openrouter.ai/api/v1",
        )

    else:
        raise ValueError(f"Unsupported LLM provider: {provider}")


def create_messages(
    system_prompt: str,
    user_message: str,
    history: list[dict[str, Any]] | None = None,
) -> list[SystemMessage | HumanMessage | AIMessage]:
    """Create a list of messages for the LLM."""
    messages: list[SystemMessage | HumanMessage | AIMessage] = []

    if system_prompt:
        messages.append(SystemMessage(content=system_prompt))

    if history:
        for msg in history:
            role = msg.get("role", "user")
            content = msg.get("content", "")

            if role == "user":
                messages.append(HumanMessage(content=content))
            elif role == "assistant":
                messages.append(AIMessage(content=content))
            elif role == "system":
                messages.append(SystemMessage(content=content))

    messages.append(HumanMessage(content=user_message))

    return messages


async def invoke_llm(
    llm: BaseChatModel,
    system_prompt: str,
    user_message: str,
    history: list[dict[str, Any]] | None = None,
) -> str:
    """Invoke the LLM with a message and return the response."""
    messages = create_messages(system_prompt, user_message, history)
    response = await llm.ainvoke(messages)
    return str(response.content)


async def stream_llm(
    llm: BaseChatModel,
    system_prompt: str,
    user_message: str,
    history: list[dict[str, Any]] | None = None,
) -> AsyncIterator[str]:
    """Stream the LLM response token by token."""
    messages = create_messages(system_prompt, user_message, history)
    async for chunk in llm.astream(messages):
        if chunk.content:
            yield str(chunk.content)


class LLMService:
    """Service class for LLM operations."""

    def __init__(self, agent_config: AgentSettings, config_manager: ConfigManager):
        """Initialize the LLM service."""
        self.agent_config = agent_config
        self.config_manager = config_manager
        self.llm = get_llm(agent_config, config_manager)

    async def chat(
        self,
        message: str,
        history: list[dict[str, Any]] | None = None,
    ) -> str:
        """Send a message and get a response."""
        return await invoke_llm(
            self.llm,
            self.agent_config.system_prompt,
            message,
            history,
        )

    async def chat_stream(
        self,
        message: str,
        history: list[dict[str, Any]] | None = None,
    ) -> AsyncIterator[str]:
        """Stream a response token by token."""
        async for token in stream_llm(
            self.llm,
            self.agent_config.system_prompt,
            message,
            history,
        ):
            yield token

    async def chat_with_system(
        self,
        message: str,
        system_prompt: str,
        history: list[dict[str, Any]] | None = None,
    ) -> str:
        """Send a message with a custom system prompt."""
        return await invoke_llm(
            self.llm,
            system_prompt,
            message,
            history,
        )

    async def chat_with_system_stream(
        self,
        message: str,
        system_prompt: str,
        history: list[dict[str, Any]] | None = None,
    ) -> AsyncIterator[str]:
        """Stream a response with a custom system prompt token by token."""
        async for token in stream_llm(
            self.llm,
            system_prompt,
            message,
            history,
        ):
            yield token
