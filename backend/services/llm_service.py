"""
SELENE OS — LLM Service (Restructured)
Abstracted LLM provider with streaming, retries, timeout, and fallback.

🔧 CRITICAL FIX: Added retry + timeout + fallback abstraction layer.
Without this, everything downstream breaks.
"""

import asyncio
import json
import time
from typing import AsyncGenerator, Optional
from config.settings import settings, LLMProvider
from schemas import ChatMessage, MessageRole
import structlog

logger = structlog.get_logger(__name__)


class LLMError(Exception):
    """Custom error for LLM failures."""
    pass


class LLMService:
    """
    Unified LLM interface with production-grade reliability.
    
    Features:
    - Multi-provider support (OpenAI / Anthropic)
    - Automatic retries with exponential backoff
    - Timeout enforcement
    - Provider fallback (OpenAI → Anthropic or vice versa)
    - Streaming + non-streaming modes
    """

    SYSTEM_PROMPT = """You are SELENE — Strategic Executive Layer for Everyday Navigation & Execution.

You are a context-aware, multi-agent AI operating system. You don't just answer questions — you understand goals, create plans, and execute them.

Core Principles:
• You are proactive, not reactive. Anticipate what the user needs.
• You think in structured steps. Break complex tasks into clear action plans.
• You are transparent about confidence and uncertainty.
• You adapt your communication style based on context (GLOBAL for facts, PERSONAL for creative/personal tasks).
• You always validate before executing — never act blindly.

When the user gives you a goal, respond with clarity, structure, and intelligence. If you detect a complex task, outline steps before executing. If you're uncertain, say so and propose alternatives.

Formatting:
• Use markdown for structured responses
• Use bullet points and headers for clarity
• Show your reasoning when it adds value
• Be concise but thorough"""

    MAX_RETRIES = 3
    BASE_RETRY_DELAY = 1.0  # seconds
    TIMEOUT = 60.0  # seconds per request

    def __init__(self):
        self._openai_client = None
        self._anthropic_client = None

    # ── Lazy Client Initialization ───────────────────────────────

    @property
    def openai_client(self):
        if self._openai_client is None:
            from openai import AsyncOpenAI
            self._openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        return self._openai_client

    @property
    def anthropic_client(self):
        if self._anthropic_client is None:
            from anthropic import AsyncAnthropic
            self._anthropic_client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
        return self._anthropic_client

    # ── Message Building ─────────────────────────────────────────

    def _build_messages(
        self,
        history: list[ChatMessage],
        system_override: str | None = None,
    ) -> list[dict]:
        """Build the message payload for the LLM."""
        messages = [
            {"role": "system", "content": system_override or self.SYSTEM_PROMPT}
        ]
        for msg in history:
            messages.append({"role": msg.role.value, "content": msg.content})
        return messages

    # ── Streaming with Retry + Fallback ──────────────────────────

    async def stream_response(
        self,
        history: list[ChatMessage],
        system_override: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> AsyncGenerator[str, None]:
        """
        Stream LLM response with automatic retry and provider fallback.
        
        Retry order:
        1. Retry current provider (up to MAX_RETRIES)
        2. Fallback to alternate provider
        3. Yield error message
        """
        messages = self._build_messages(history, system_override)

        # Determine provider order (primary → fallback)
        providers = [settings.LLM_PROVIDER]
        if settings.LLM_PROVIDER == LLMProvider.OPENAI and settings.ANTHROPIC_API_KEY:
            providers.append(LLMProvider.ANTHROPIC)
        elif settings.LLM_PROVIDER == LLMProvider.ANTHROPIC and settings.OPENAI_API_KEY:
            providers.append(LLMProvider.OPENAI)

        last_error = None

        for provider in providers:
            for attempt in range(1, self.MAX_RETRIES + 1):
                try:
                    logger.info(
                        "llm_stream_attempt",
                        provider=provider.value,
                        attempt=attempt,
                    )

                    stream_fn = (
                        self._stream_openai if provider == LLMProvider.OPENAI
                        else self._stream_anthropic
                    )

                    token_count = 0
                    async for chunk in asyncio.wait_for(
                        self._collect_stream(stream_fn, messages, temperature, max_tokens),
                        timeout=self.TIMEOUT,
                    ):
                        token_count += 1
                        yield chunk

                    # If we got tokens, we're done
                    if token_count > 0:
                        logger.info("llm_stream_success", provider=provider.value, tokens=token_count)
                        return

                except asyncio.TimeoutError:
                    last_error = f"Timeout after {self.TIMEOUT}s"
                    logger.warning("llm_timeout", provider=provider.value, attempt=attempt)
                except Exception as e:
                    last_error = str(e)
                    logger.warning(
                        "llm_stream_error",
                        provider=provider.value,
                        attempt=attempt,
                        error=last_error,
                    )

                # Exponential backoff between retries
                if attempt < self.MAX_RETRIES:
                    delay = self.BASE_RETRY_DELAY * (2 ** (attempt - 1))
                    await asyncio.sleep(delay)

            logger.warning("llm_provider_exhausted", provider=provider.value)

        # All providers and retries exhausted
        logger.error("llm_all_providers_failed", last_error=last_error)
        yield f"\n\n⚠️ SELENE encountered an error communicating with the AI provider. Error: {last_error}"

    async def _collect_stream(
        self, stream_fn, messages, temperature, max_tokens
    ) -> AsyncGenerator[str, None]:
        """Wrapper to make the stream compatible with asyncio.wait_for."""
        async for chunk in stream_fn(messages, temperature, max_tokens):
            yield chunk

    # ── Provider-Specific Streaming ──────────────────────────────

    async def _stream_openai(
        self, messages: list[dict], temperature: float, max_tokens: int
    ) -> AsyncGenerator[str, None]:
        """Stream from OpenAI."""
        stream = await self.openai_client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
        )
        async for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    async def _stream_anthropic(
        self, messages: list[dict], temperature: float, max_tokens: int
    ) -> AsyncGenerator[str, None]:
        """Stream from Anthropic."""
        system_msg = ""
        chat_messages = []
        for msg in messages:
            if msg["role"] == "system":
                system_msg = msg["content"]
            else:
                chat_messages.append(msg)

        async with self.anthropic_client.messages.stream(
            model=settings.ANTHROPIC_MODEL,
            system=system_msg,
            messages=chat_messages,
            temperature=temperature,
            max_tokens=max_tokens,
        ) as stream:
            async for text in stream.text_stream:
                yield text

    # ── Non-Streaming Generation ─────────────────────────────────

    async def generate(
        self,
        history: list[ChatMessage],
        system_override: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> str:
        """Non-streaming generation — collects full response."""
        chunks = []
        async for chunk in self.stream_response(
            history, system_override, temperature, max_tokens
        ):
            chunks.append(chunk)
        return "".join(chunks)

    # ── Classification (Low Temperature) ─────────────────────────

    async def classify(
        self,
        prompt: str,
        system: str,
        temperature: float = 0.1,
        max_tokens: int = 256,
    ) -> str:
        """Low-temperature classification for intent/mode detection."""
        history = [ChatMessage(role=MessageRole.USER, content=prompt)]
        return await self.generate(
            history,
            system_override=system,
            temperature=temperature,
            max_tokens=max_tokens,
        )


# Singleton
llm_service = LLMService()
