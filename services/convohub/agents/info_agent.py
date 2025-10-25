import logging
import json
from typing import List, Dict, Any
import httpx
import traceback
from ..config import settings

try:
    from langchain_redis import RedisChatMessageHistory
    from langchain.memory import ConversationBufferMemory
except ImportError:
    RedisChatMessageHistory = None
    ConversationBufferMemory = None

logger = logging.getLogger(__name__)

class InfoAgent:
    """FAQ answering agent backed by an Ollama model with Redis memory and adaptive summarization."""

    def __init__(self, session_id: str = "default"):
        logger.debug(f"Initializing InfoAgent with session_id: {session_id}")
        self.session_id = session_id
        self.base_url = settings.OLLAMA_BASE_URL
        self.model = settings.INFO_AGENT_MODEL
        self.system_prompt = settings.INFO_AGENT_SYSTEM_PROMPT
        self.redis_url = settings.REDIS_URL
        self.token_budget = settings.INFO_AGENT_TOKEN_BUDGET
        self.summary_token_budget = settings.INFO_AGENT_SUMMARY_TOKEN_BUDGET
        self.recent_messages_window = settings.INFO_AGENT_RECENT_MESSAGES_WINDOW
        self.messages_to_summarize = settings.INFO_AGENT_MESSAGES_TO_SUMMARIZE
        self.summarization_prompt_tokens = settings.INFO_AGENT_SUMMARIZATION_PROMPT_TOKENS
        self.message_summary_char_limit = settings.INFO_AGENT_MESSAGE_SUMMARY_CHAR_LIMIT
        self._memory = None
        self.conversation_history: List[Dict[str, str]] = []

    @property
    def memory(self):
        """Lazy initialization of Redis-based memory"""
        logger.debug(f"Accessing memory for InfoAgent with session_id: {self.session_id}")
        if self._memory is None and self.redis_url and RedisChatMessageHistory and ConversationBufferMemory:
            try:
                logger.debug(f"Initializing RedisChatMessageHistory with redis_url: {self.redis_url}")
                chat_history = RedisChatMessageHistory(session_id=self.session_id, redis_url=self.redis_url)
                logger.debug("Initializing ConversationBufferMemory")
                self._memory = ConversationBufferMemory(memory_key="chat_history", chat_memory=chat_history, return_messages=True)
                logger.debug("Redis-based memory initialized successfully")
            except Exception as e:
                logger.warning(f"Redis memory init failed: {e}")
                self._memory = None
        return self._memory

    def _estimate_tokens(self, text: str) -> int:
        return max(1, len(text) // 4)

    def _needs_summary(self) -> bool:
        logger.debug("Checking if summarization is needed")
        msgs = self.conversation_history[: self.messages_to_summarize]
        text = self.system_prompt + " " + " ".join(m.get("content", "") for m in msgs)
        total = self._estimate_tokens(text)
        threshold = self.token_budget - self.summary_token_budget - self.summarization_prompt_tokens
        return total > threshold

    async def _summarize(self, messages: List[Dict[str, str]]) -> str:
        logger.debug("Starting summarization process")
        if not messages:
            logger.debug("No messages to summarize")
            return "Summary: (no content)"
        transcript = "\n".join([
            f"{m.get('role','user')}: {m.get('content','')[:self.message_summary_char_limit]}" for m in messages
        ])
        system_prompt = (
            f"Summarize the conversation. Include intents, key facts, and next step. Max {self.summary_token_budget} tokens."
        )
        payload = {
            "model": self.model,
            "temperature": 0.0,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": transcript},
            ],
            "options": {"num_ctx": self.token_budget},
        }
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                resp = await client.post(f"{self.base_url}/v1/chat/completions", json=payload)
                resp.raise_for_status()
                data = resp.json()
                content = data["choices"][0]["message"]["content"].strip()
                return f"Summary: {content}" if content else "Summary: (no content)"
        except Exception as e:
            logger.error(f"Summarization failed: {e}")
            logger.error(traceback.format_exc())
            return "Summary: (error)"

    def _build_context(self, prompt: str) -> List[Dict[str, str]]:
        msgs: List[Dict[str, str]] = []
        if self.system_prompt:
            msgs.append({"role": "system", "content": self.system_prompt})
        # include summary if present
        for m in self.conversation_history:
            if m.get("role") == "system" and m.get("content", "").startswith("Summary:"):
                msgs.append(m)
                break
        # recent messages
        msgs.extend(self.conversation_history[-self.recent_messages_window :])
        # current prompt
        msgs.append({"role": "user", "content": prompt})
        return msgs

    def _rebuild_history_from_memory(self):
        logger.debug("Rebuilding conversation history from memory")
        history: List[Dict[str, str]] = []
        if self.memory and hasattr(self.memory, "chat_memory"):
            for m in getattr(self.memory.chat_memory, "messages", []):
                if getattr(m, "type", None) == "human":
                    history.append({"role": "user", "content": m.content})
                elif getattr(m, "type", None) == "ai":
                    history.append({"role": "assistant", "content": m.content})
        self.conversation_history = history

    async def ask(self, question: str) -> str:
        logger.debug(f"InfoAgent received question: {question[:50]}")
        self._rebuild_history_from_memory()
        # apply summarization if needed
        if self._needs_summary():
            to_sum = self.conversation_history[: self.messages_to_summarize]
            summary = await self._summarize(to_sum)
            self.conversation_history = [
                {"role": "system", "content": summary}
            ] + self.conversation_history[self.messages_to_summarize :]
        context_messages = self._build_context(question)
        payload = {
            "model": self.model,
            "temperature": 0.2,
            "messages": context_messages,
            "options": {"num_ctx": self.token_budget},
        }
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                resp = await client.post(f"{self.base_url}/v1/chat/completions", json=payload)
                resp.raise_for_status()
                data = resp.json()
                content = data["choices"][0]["message"]["content"].strip()
        except Exception as e:
            logger.error(f"InfoAgent ask failed: {e}")
            logger.error(traceback.format_exc())
            return "[Error: InfoAgent LLM call failed]"

        if self.memory:
            try:
                self.memory.save_context({"input": question}, {"output": content})
            except Exception as e:
                logger.warning(f"Failed saving to memory: {e}")
        return content

    # Tool interface
    async def run(self, query: str) -> str:
        logger.debug(f"Running InfoAgent with query: {query[:50]}")
        return await self.ask(query)

def info_agent_tool() -> Dict[str, Any]:
    """Returns a tool definition for the supervisor."""
    async def _invoke(input_text: str) -> str:
        logger.debug(f"Invoking InfoAgent with input_text: {input_text[:50]}")
        agent = InfoAgent(session_id="global")
        return await agent.run(input_text)
    return {
        "name": "info_agent",
        "description": "Answers FAQ and general info queries.",
        "callable": _invoke,
    }
