import logging
import httpx
import traceback
from ..config import settings

logger = logging.getLogger(__name__)

try:
    from langchain_redis import RedisChatMessageHistory
    from langchain.memory import ConversationBufferMemory
except ImportError:
    RedisChatMessageHistory = None
    ConversationBufferMemory = None
    logger.warning("langchain or langchain-redis not installed; Redis memory functionality will be disabled")

class AIService:
    """Service for handling AI/LLM interactions with Ollama and Redis-based memory"""

    def __init__(self, session_id: str = "default"):
        self.base_url = settings.OLLAMA_BASE_URL
        self.model = settings.SUPERVISOR_MODEL
        self.temperature = settings.SUPERVISOR_TEMPERATURE
        self.redis_url = settings.REDIS_URL
        self.session_id = session_id
        self.system_prompt = settings.SUPERVISOR_SYSTEM_PROMPT
        self.timeout = settings.OLLAMA_TIMEOUT
        self._memory = None
        self.token_budget = getattr(settings, "SUPERVISOR_TOKEN_BUDGET", 8192)
        self.summary_token_budget = getattr(settings, "SUPERVISOR_SUMMARY_TOKEN_BUDGET", 800)
        self.num_of_recent_messages_to_keep = getattr(settings, "SUPERVISOR_RECENT_MESSAGES_WINDOW", 6)
        self.num_of_messages_to_summarize = getattr(settings, "SUPERVISOR_MESSAGES_TO_SUMMARIZE", 8)
        self.summarization_prompt_tokens = getattr(settings, "SUPERVISOR_SUMMARIZATION_PROMPT_TOKENS", 100)
        self.message_summary_char_limit = getattr(settings, "SUPERVISOR_MESSAGE_SUMMARY_CHAR_LIMIT", 600)
        if not self.redis_url:
            logger.warning("No Redis URL found for AI service; memory will be disabled")
        else:
            logger.info(f"Using Redis URL: {self.redis_url}")

    @property
    def memory(self):
        if self._memory is None and RedisChatMessageHistory is not None and ConversationBufferMemory is not None:
            try:
                chat_history = RedisChatMessageHistory(
                    session_id=self.session_id,
                    redis_url=self.redis_url
                )
                self._memory = ConversationBufferMemory(
                    memory_key="chat_history",
                    chat_memory=chat_history,
                    return_messages=True
                )
            except Exception as e:
                logger.error(f"Failed to initialize Redis memory: {str(e)}")
                self._memory = None
        return self._memory

    async def generate_response(self, question: str, language: str = None) -> str:
        try:
            if language is None:
                language = getattr(settings, "DEFAULT_LANGUAGE", "english")
            prompt = f"Answer briefly in {language}: {question}"
            msgs_to_summarize = self._build_msgs_to_summarize()
            context_messages = self._get_context_messages()
            is_summarization_needed = self._is_summarization_needed(context_messages)
            summary_text = None
            if is_summarization_needed:
                summary_text = await self._summarize_messages(msgs_to_summarize, language)
            content = await self._ask(question, summary_text, context_messages)
            if content is None:
                return "[Error: Exception during Ollama API call]"
            self._save_to_memory(prompt, content)
            return content
        except Exception as e:
            logger.error(f"Error generating AI response: {str(e)}")
            logger.error(traceback.format_exc())
            return "[Error: Unable to get response from Ollama LLM]"

    def _build_msgs_to_summarize(self):
        msgs_to_summarize = []
        if self.memory is not None and hasattr(self.memory, "chat_memory") and hasattr(self.memory.chat_memory, "messages"):
            N = self.num_of_recent_messages_to_keep + self.num_of_messages_to_summarize
            chat_memory_msgs = self.memory.chat_memory.messages[-N:-self.num_of_recent_messages_to_keep]
            for m in chat_memory_msgs:
                if hasattr(m, "type") and hasattr(m, "content"):
                    if m.type == "human":
                        msgs_to_summarize.append({"role": "user", "content": m.content})
                    elif m.type == "ai":
                        msgs_to_summarize.append({"role": "assistant", "content": m.content})
        return msgs_to_summarize

    def _msg_to_dict(self, m):
        if hasattr(m, "type") and hasattr(m, "content"):
            role = "user" if m.type == "human" else "assistant"
            return {"role": role, "content": m.content}
        elif isinstance(m, dict):
            return m
        return None

    async def _ask(self, question, summary_text, context_messages):
        messages = []
        if self.system_prompt:
            messages.append({"role": "system", "content": self.system_prompt})
        if summary_text:
            messages.append({"role": "system", "content": summary_text})
        for m in context_messages:
            msg_dict = self._msg_to_dict(m)
            if msg_dict:
                messages.append(msg_dict)
        messages.append({"role": "user", "content": question})
        payload = {
            "model": self.model,
            "temperature": self.temperature,
            "messages": messages,
            "options": {
                "num_ctx": self.token_budget
            }
        }
        content = await self._call_ollama_api(payload)
        return content

    def _estimate_token_count(self, text: str) -> int:
        return max(1, len(text) // 4)

    def _is_summarization_needed(self, messages_to_check) -> bool:
        text_to_check = " ".join([getattr(m, "content", "") for m in messages_to_check])
        total_tokens = self._estimate_token_count(text_to_check)
        threshold = self.token_budget - self.summary_token_budget - self.summarization_prompt_tokens
        return total_tokens > threshold

    async def _summarize_messages(self, messages, language=None):
        if not messages:
            return "Summary: (no content)"
        transcript = "\n".join([f"{m.get('role','user')}: {m.get('content','')[:self.message_summary_char_limit]}" for m in messages])
        lang = language or getattr(settings, "DEFAULT_LANGUAGE", "english")
        summarization_prompt = (
            f"You are an assistant that summarizes a conversation in {lang}. Include user intents, key information provided, and next recommended action. "
            f"Maximum {self.summary_token_budget} tokens. Do not fabricate details. Respond with only the summary."
        )
        user_intro = "Conversation transcript:"
        payload = {
            "model": self.model,
            "temperature": 0.0,
            "messages": [
                {"role": "system", "content": summarization_prompt},
                {"role": "user", "content": f"{user_intro}\n{transcript}"}
            ],
            "options": {
                "num_ctx": self.token_budget
            }
        }
        summary = await self._call_ollama_api(payload)
        return f"Summary: {summary.strip() if summary else '(no content)'}"

    def _get_context_messages(self):
        if self.memory is not None and hasattr(self.memory.chat_memory, "messages"):
            return self.memory.chat_memory.messages[-self.num_of_recent_messages_to_keep:]
        return []

    async def _call_ollama_api(self, payload):
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(f"{self.base_url}/v1/chat/completions", json=payload)
                response.raise_for_status()
                data = response.json()
                content = data["choices"][0]["message"]["content"]
                return content
        except Exception as api_exc:
            logger.error(f"Exception during Ollama API call: {str(api_exc)}")
            logger.error(traceback.format_exc())
            return None

    def _save_to_memory(self, prompt, content):
        if self.memory is not None:
            try:
                self.memory.save_context({"input": prompt}, {"output": content})
            except Exception as memory_error:
                logger.warning(f"Failed to save conversation to Redis memory: {str(memory_error)}")
