"""Router agent for query intent selection."""

from typing import Literal


AgentRoute = Literal["retrieval", "tool", "general"]


class RouterAgent:
    """Simple keyword-based router."""

    _RETRIEVAL_KEYWORDS = (
        "document",
        "docs",
        "pdf",
        "file",
        "policy",
        "knowledge base",
        "from document",
    )
    _TOOL_KEYWORDS = (
        "calculate",
        "sum",
        "add",
        "subtract",
        "multiply",
        "divide",
        "weather",
        "database",
        "db",
        "how many",
        "count",
    )

    def route_query(self, query: str) -> AgentRoute:
        """Route query to retrieval/tool/general agent."""
        text = (query or "").strip().lower()
        if not text:
            return "general"

        if any(keyword in text for keyword in self._TOOL_KEYWORDS):
            return "tool"
        if any(keyword in text for keyword in self._RETRIEVAL_KEYWORDS):
            return "retrieval"
        return "general"

