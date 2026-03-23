"""Tool agent with calculator, document-search, and DB tools."""

import ast
import operator
from typing import Dict, Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.retrieval_agent import RetrievalAgent
from app.models.document import Document
from app.models.user import User


class ToolAgent:
    """Executes tool-style requests."""

    _OPS = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.Mod: operator.mod,
        ast.Pow: operator.pow,
    }

    def __init__(self, db: AsyncSession, retrieval_agent: RetrievalAgent):
        self.db = db
        self.retrieval_agent = retrieval_agent

    async def answer(
        self,
        *,
        query: str,
        user: User,
        document: Document,
        organization_id: int,
        system_prompt: Optional[str] = None,
    ) -> Dict:
        """Detect tool intent and execute the tool."""
        text = (query or "").strip().lower()

        if self._looks_like_count_documents(text):
            count = await self._count_documents(organization_id=organization_id)
            return {
                "answer": f"There are {count} documents in your organization.",
                "source_documents": [],
                "tool_used": "db_count_documents",
            }

        expression = self._extract_expression(query)
        if expression:
            result = self._safe_eval(expression)
            return {
                "answer": f"Result: {result}",
                "source_documents": [],
                "tool_used": "calculator",
            }

        retrieval_result = self.retrieval_agent.answer(
            query=query,
            document=document,
            system_prompt=system_prompt,
            conversation_history=[],
        )
        retrieval_result["tool_used"] = "document_search"
        return retrieval_result

    async def _count_documents(self, organization_id: int) -> int:
        stmt = select(func.count(Document.id)).where(
            Document.organization_id == organization_id
        )
        result = await self.db.execute(stmt)
        return int(result.scalar() or 0)

    def _looks_like_count_documents(self, text: str) -> bool:
        return (
            "how many document" in text
            or "document count" in text
            or ("count" in text and "document" in text)
        )

    def _extract_expression(self, query: str) -> str:
        stripped = (query or "").strip()
        if stripped.lower().startswith("calculate"):
            return stripped[len("calculate"):].strip()
        if any(ch.isdigit() for ch in stripped) and any(
            op in stripped for op in ("+", "-", "*", "/", "%", "(", ")")
        ):
            return stripped
        return ""

    def _safe_eval(self, expression: str) -> float:
        tree = ast.parse(expression, mode="eval")
        return float(self._eval_node(tree.body))

    def _eval_node(self, node):
        if isinstance(node, ast.BinOp) and type(node.op) in self._OPS:
            left = self._eval_node(node.left)
            right = self._eval_node(node.right)
            return self._OPS[type(node.op)](left, right)
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
            return -self._eval_node(node.operand)
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return node.value
        raise ValueError("Unsupported expression")

