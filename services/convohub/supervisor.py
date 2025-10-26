import logging
from typing import List, Dict, Any, Callable
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain.prompts import ChatPromptTemplate
try:
    # Preferred modern import (post deprecation)
    from langchain_ollama import ChatOllama  # type: ignore
except ImportError:  # Fallback if new package not yet installed
    from langchain_community.chat_models import ChatOllama  # type: ignore
from langgraph.graph import StateGraph, END
from .config import settings
from .agents.calendar_scheduler import calendar_scheduler_tool

logger = logging.getLogger(__name__)

# Define the shared state for the graph
class SupervisorState(dict):
    """State container. Holds messages and the last tool used."""
    messages: List[Dict[str, Any]]
    last_tool: str | None


def build_supervisor_graph():
    # Instantiate tool definitions
    # Build a simple tool registry (no ToolExecutor to avoid version API mismatch)
    tool_registry = {t["name"]: t for t in [calendar_scheduler_tool()]}

    # Instantiate Ollama chat model using new package if available.
    llm = ChatOllama(
        base_url=settings.OLLAMA_BASE_URL,
        model=settings.SUPERVISOR_MODEL,
        temperature=settings.SUPERVISOR_TEMPERATURE,
        timeout=settings.OLLAMA_TIMEOUT
    )

    system_prompt = settings.SUPERVISOR_SYSTEM_PROMPT
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", "{input}")
    ])

    def router(state: SupervisorState):
        logger.debug(f"Accessing router with state: {state}")
        user_input = state.get("user_input", "")
        logger.debug(f"User input: {user_input}")
        chain = prompt | llm
        resp = chain.invoke({"input": user_input})
        logger.debug(f"LLM response: {resp}")
        text = resp.content.strip()
        logger.debug(f"LLM response text: {text}")
        if text.startswith("TOOL:"):
            # parse TOOL:tool_name:query
            logger.debug(f"Detected tool call in LLM response: {text}")
            try:
                _, tool_name, query = text.split(":", 2)
                logger.debug(f"Parsed tool call - Name: {tool_name}, Query: {query}")
                if tool_name in tool_registry:
                    # Direct callable invocation
                    logger.debug(f"Invoking tool: {tool_name} with query: {query}")
                    result = tool_registry[tool_name]["callable"](query)
                    logger.debug(f"Tool {tool_name} returned result: {result}")
                    result_formatted = {"messages": state.get("messages", []) + [
                        {"role": "assistant", "content": f"[Tool {tool_name} result] {result}"}
                    ], "last_tool": tool_name}
                    return result_formatted
            except Exception as e:
                logger.error(f"Error during tool invocation: {e}")
                return {"messages": state.get("messages", []) + [
                    {"role": "assistant", "content": f"[Routing error] {e}"}
                ]}
        # No tool call, direct answer
        logger.debug(f"No tool call detected, returning direct answer.")
        direct_answer = {"messages": state.get("messages", []) + [
            {"role": "assistant", "content": text}
        ], "last_tool": None}
        return direct_answer

    graph = StateGraph(SupervisorState)
    graph.add_node("router", router)
    graph.set_entry_point("router")
    graph.set_finish_point("router")
    compiled = graph.compile()
    return compiled

class Supervisor:
    def __init__(self):
        self.graph = build_supervisor_graph()

    def invoke(self, user_input: str) -> str:
        logger.debug(f"Supervisor received input: {user_input}")
        state = {"user_input": user_input, "messages": []}
        logger.debug(f"Supervisor state before invoke: {state}")
        result = self.graph.invoke(state)
        logger.debug(f"Supervisor result state: {result}")
        msgs = result.get("messages", [])
        logger.debug(f"Supervisor messages: {msgs}")
        if msgs:
            logger.debug(f"Supervisor returning message: {msgs[-1]['content']}")
            return msgs[-1]["content"]
        return "[No response]"
