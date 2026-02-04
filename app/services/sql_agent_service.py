"""
SQL Agent for structured data (Excel/CSV/DB). Used by the orchestrator for the hybrid pipeline.
"""
from typing import Any, Dict

from app.core.config import settings, get_api_key_manager

# LangChain SQL agent (optional dependency)
try:
    from langchain_community.agent_toolkits import create_sql_agent
    from langchain_community.utilities import SQLDatabase
    from langchain_google_genai import ChatGoogleGenerativeAI
    from sqlalchemy import create_engine
    _SQL_AGENT_AVAILABLE = True
except ImportError:
    _SQL_AGENT_AVAILABLE = False
    create_sql_agent = None
    SQLDatabase = None
    ChatGoogleGenerativeAI = None
    create_engine = None


def _sqlite_uri(path: str) -> str:
    """Convert filesystem path to SQLAlchemy SQLite URI."""
    import os
    path = os.path.abspath(path).replace("\\", "/")
    return f"sqlite:///{path}"


def run_sql_agent(sqlite_path: str, query: str) -> Dict[str, Any]:
    """
    Run the SQL agent on the given SQLite database and return the result.
    Returns dict with "output" (answer text) and "error" if failed.
    """
    if not _SQL_AGENT_AVAILABLE:
        return {
            "output": "SQL agent is not available. Install langchain-community and langchain-google-genai.",
            "error": "SQL_AGENT_UNAVAILABLE",
        }
    try:
        api_key_manager = get_api_key_manager()
        api_key = api_key_manager.get_current_key()
        uri = _sqlite_uri(sqlite_path)
        engine = create_engine(uri)
        db = SQLDatabase(engine, sample_rows_in_table_info=2)
        llm = ChatGoogleGenerativeAI(
            model=settings.gemini_model,
            temperature=0,
            google_api_key=api_key,
        )
        agent = create_sql_agent(
            llm=llm,
            db=db,
            verbose=False,
            handle_parsing_errors=True,
        )
        result = agent.invoke({"input": query})
        output = result.get("output", str(result))
        return {"output": output}
    except Exception as e:
        return {"output": f"Sorry, an error occurred while querying the data: {str(e)}", "error": str(e)}
