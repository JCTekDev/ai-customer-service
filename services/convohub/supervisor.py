import logging
from typing import List, Dict, Any
from .config import settings
from .agents.calendar_scheduler import calendar_scheduler_tool
from .services.ai_service import AIService

logger = logging.getLogger(__name__)

class SupervisorState(dict):
    messages: List[Dict[str, Any]]
    last_tool: str | None
    user_input: str

def build_supervisor_graph():
    tool_registry = {t["name"]: t for t in [calendar_scheduler_tool()]}
    ai_service = AIService()

    async def router(state: SupervisorState):
        logger.debug(f"Accessing router with state: {state}")
        user_input = state.user_input
        logger.debug(f"User input: {user_input}")
        # Use AIService to generate response
        text = await ai_service.generate_response(user_input)
        logger.debug(f"AIService response text: {text}")
        if text.startswith("TOOL:"):
            try:
                _, tool_name, query = text.split(":", 2)
                logger.debug(f"Parsed tool call - Name: {tool_name}, Query: {query}")
                if tool_name in tool_registry:
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
        direct_answer = {"messages": state.get("messages", []) + [
            {"role": "assistant", "content": text}
        ], "last_tool": None}
        return direct_answer

    # For async graph execution, you may need to adapt your graph library usage
    # Here, we assume a synchronous wrapper for demonstration
    class DummyGraph:
        def __init__(self, router_func):
            self.router_func = router_func
        async def invoke(self, state):
            return await self.router_func(state)

    return DummyGraph(router)

class Supervisor:
    def __init__(self):
        self.graph = build_supervisor_graph()

    async def invoke(self, user_input: str) -> str:
        logger.debug(f"Supervisor received input: {user_input}")
        state = {"user_input": user_input, "messages": []}
        logger.debug(f"Supervisor state before invoke: {state}")
        result = await self.graph.invoke(state)
        logger.debug(f"Supervisor result state: {result}")
        msgs = result.get("messages", [])
        logger.debug(f"Supervisor messages: {msgs}")
        if msgs:
            logger.debug(f"Supervisor returning message: {msgs[-1]['content']}")
            return msgs[-1]["content"]
        return "[No response]"
