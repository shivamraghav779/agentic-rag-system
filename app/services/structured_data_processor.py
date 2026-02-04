"""
Process structured data (Excel, CSV, SQLite DB) for hybrid SQL + RAG pipeline.
Produces: (1) a SQLite database for the SQL agent, (2) LangChain Documents for RAG embedding.
"""
import os
import re
import sqlite3
from pathlib import Path
from typing import List, Optional, Tuple, Union

import pandas as pd
from langchain_core.documents import Document

from app.core.config import settings


def _sanitize_table_name(name: str) -> str:
    """Make a valid SQLite table name (alphanumeric and underscore)."""
    s = re.sub(r"[^\w]", "_", name)
    return s.strip("_") or "table"


def _dataframe_row_to_text(row: pd.Series, table_name: str) -> str:
    """Convert a DataFrame row to a single text line for RAG."""
    parts = [f"{k}: {v}" for k, v in row.items() if pd.notna(v)]
    return f"[{table_name}] " + ", ".join(parts)


def process_csv(file_path: str, sqlite_path: str) -> Tuple[str, List[Document]]:
    """
    Load CSV, write to SQLite (one table), create Documents from rows.
    Returns (sqlite_path, documents).
    """
    df = pd.read_csv(file_path)
    table_name = _sanitize_table_name(Path(file_path).stem)
    if not table_name:
        table_name = "data"
    conn = sqlite3.connect(sqlite_path)
    df.to_sql(table_name, conn, index=False, if_exists="replace")
    conn.close()

    documents = []
    for i, row in df.iterrows():
        text = _dataframe_row_to_text(row, table_name)
        documents.append(
            Document(
                page_content=text,
                metadata={"source": file_path, "table": table_name, "row_id": i},
            )
        )
    return sqlite_path, documents


def process_excel(file_path: str, sqlite_path: str) -> Tuple[str, List[Document]]:
    """
    Load Excel (all sheets), write each sheet to SQLite as a table, create Documents from all rows.
    Returns (sqlite_path, documents).
    """
    xl = pd.ExcelFile(file_path)
    conn = sqlite3.connect(sqlite_path)
    all_docs = []
    for sheet_name in xl.sheet_names:
        df = pd.read_excel(xl, sheet_name=sheet_name)
        table_name = _sanitize_table_name(sheet_name)
        if not table_name:
            table_name = f"sheet_{len(all_docs)}"
        df.to_sql(table_name, conn, index=False, if_exists="replace")
        for i, row in df.iterrows():
            text = _dataframe_row_to_text(row, table_name)
            all_docs.append(
                Document(
                    page_content=text,
                    metadata={
                        "source": file_path,
                        "table": table_name,
                        "sheet": sheet_name,
                        "row_id": i,
                    },
                )
            )
    conn.close()
    return sqlite_path, all_docs


def process_sqlite_db(file_path: str, sqlite_path: str) -> Tuple[str, List[Document]]:
    """
    Use uploaded SQLite file as-is (copy to sqlite_store for consistent path).
    Create Documents from all tables for RAG.
    Returns (sqlite_path, documents).
    """
    if os.path.abspath(file_path) != os.path.abspath(sqlite_path):
        import shutil
        Path(sqlite_path).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(file_path, sqlite_path)

    conn = sqlite3.connect(sqlite_path)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
    )
    tables = [r[0] for r in cursor.fetchall()]
    all_docs = []
    for table in tables:
        df = pd.read_sql_query(f'SELECT * FROM "{table}"', conn)
        for i, row in df.iterrows():
            text = _dataframe_row_to_text(row, table)
            all_docs.append(
                Document(
                    page_content=text,
                    metadata={"source": file_path, "table": table, "row_id": i},
                )
            )
    conn.close()
    return sqlite_path, all_docs


def process_structured(
    file_path: str,
    file_type: str,
    store_name: str,
    output_dir: Optional[Union[str, Path]] = None,
) -> Tuple[str, List[Document]]:
    """
    Process structured file (csv, xlsx, xls, db, sqlite) into SQLite + Documents.
    store_name: base name for sqlite file (e.g. doc_uuid).
    output_dir: If set (e.g. per-org structured_data dir), SQLite is written here; else settings.sqlite_store_dir.
    Returns (sqlite_path, documents).
    """
    if output_dir is not None:
        base_dir = Path(output_dir)
    else:
        base_dir = Path(settings.sqlite_store_dir)
    base_dir.mkdir(parents=True, exist_ok=True)
    sqlite_path = str(base_dir / f"{store_name}.db")
    ft = file_type.lower()

    if ft == "csv":
        return process_csv(file_path, sqlite_path)
    if ft in ("xlsx", "xls"):
        return process_excel(file_path, sqlite_path)
    if ft in ("db", "sqlite"):
        return process_sqlite_db(file_path, sqlite_path)
    raise ValueError(f"Unsupported structured file type: {file_type}")
