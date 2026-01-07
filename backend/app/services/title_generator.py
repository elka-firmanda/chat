"""
LLM-based title generation service for chat sessions.

Automatically generates concise, descriptive titles for chat sessions
based on the user's message content.
"""

import logging
from typing import Optional

from app.config.config_manager import get_config, config_manager
from app.services.llm import LLMService

logger = logging.getLogger(__name__)


TITLE_GENERATION_SYSTEM_PROMPT = """You are a title generator for a chat assistant. Your task is to create a concise, descriptive title for a conversation based on the user's message.

Requirements:
- Maximum 60 characters
- Clear and specific to the conversation topic
- Use title case (capitalize first letter of each word)
- Avoid generic titles like "Chat" or "Conversation"
- Capture the key topic or question

Examples:
- "Python File Handling Best Practices"
- "Debugging React State Management"
- "Comparing SQL vs NoSQL Databases"
- "Setting Up CI/CD Pipeline with GitHub Actions"

Generate only the title, no explanation or punctuation at the end."""


class TitleGenerator:
    """Service for generating chat session titles using LLMs."""

    def __init__(self):
        self._llm_service: Optional[LLMService] = None
        self._initialized = False

    def _get_llm_service(self) -> Optional[LLMService]:
        """Lazy initialization of LLM service for title generation."""
        if self._initialized:
            return self._llm_service

        try:
            config = get_config()
            master_config = config.agents.master
            api_keys = config_manager.get_api_keys()

            if master_config.provider and getattr(api_keys, master_config.provider):
                self._llm_service = LLMService(master_config, config_manager)
                self._initialized = True
                return self._llm_service
            else:
                logger.warning(
                    "Cannot initialize title generator: missing provider config"
                )
                return None

        except Exception:
            logger.error("Failed to initialize title generator", exc_info=True)
            return None

    async def generate_title(self, user_message: str) -> Optional[str]:
        """
        Generate a title for a chat session based on the user's message.

        Args:
            user_message: The user's initial message

        Returns:
            Generated title string, or None if generation failed
        """
        if not user_message or not user_message.strip():
            return None

        llm_service = self._get_llm_service()
        if not llm_service:
            return None

        try:
            truncated_message = user_message[:1000]

            user_prompt = f"""Generate a title for this conversation:

User's message: {truncated_message}

Title:"""

            title = await llm_service.chat_with_system(
                message=user_prompt,
                system_prompt=TITLE_GENERATION_SYSTEM_PROMPT,
            )

            if title:
                title = title.strip().rstrip(".")
                if title and len(title) <= 60:
                    logger.info(f"Generated title: '{title}'")
                    return title

            return None

        except Exception as e:
            logger.error(f"Title generation failed: {e}")
            return None


_title_generator: Optional[TitleGenerator] = None


def get_title_generator() -> TitleGenerator:
    """Get the singleton title generator instance."""
    global _title_generator
    if _title_generator is None:
        _title_generator = TitleGenerator()
    return _title_generator


async def generate_session_title(user_message: str) -> Optional[str]:
    """
    Convenience function to generate a session title.

    Args:
        user_message: The user's message

    Returns:
        Generated title or None
    """
    generator = get_title_generator()
    return await generator.generate_title(user_message)
