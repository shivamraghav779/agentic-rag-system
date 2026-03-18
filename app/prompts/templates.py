"""
Centralized prompt templates for the RAG pipeline.

Keeping prompt text out of the core logic makes it easier to iterate safely and
swap templates without touching the RAG implementation.
"""


# ===== Answer generation prompts =====

ANSWER_PROMPT_WITH_HISTORY = """{system_part}

{date_context}

{history_context}

Context from documents:
{context}

Current Question: {question}

{instruction_prompt}

Answer:"""


ANSWER_PROMPT_NO_HISTORY = """{system_part}

{date_context}

Context from documents:
{context}

Question: {question}

{instruction_prompt}

Answer:"""


# ===== Conversation title prompt =====

CONVERSATION_TITLE_PROMPT = """Generate a concise, descriptive title for a conversation that starts with this question: "{question}"

Requirements:
- The title should be a short, clear summary of what the conversation is about
- Maximum 100 characters
- Do not include quotation marks or special formatting
- Return only the title, nothing else

Title:"""


# ===== Query processor prompts =====

REWRITE_QUERY_PROMPT = """Rewrite the following query to be more effective for retrieving relevant documents.
Make it more specific, include relevant terms, and maintain the original intent.

Original query: {query}

Rewritten query (just the query, no explanation):"""


EXPAND_QUERY_PROMPT = """Expand the following query with relevant synonyms and related terms.
Return the expanded query with additional relevant keywords. Keep it concise.

Original query: {query}

Expanded query (include original + synonyms, keep it concise):"""


COMPRESS_CONTEXT_PROMPT = """Compress the following context to {target_length} characters or less,
while preserving all information relevant to answering this query: "{query}"

Context to compress:
{context}

Compressed context (only the compressed text, no explanation):"""


# ===== SQL vs RAG classification prompt =====

CLASSIFY_QUERY_PROMPT = """Classify the following query as either 'sql' or 'rag'.
SQL = aggregations, counts, calculations, comparisons, performance metrics, totals, averages.
RAG = descriptive information, explanations, details about specific entities.

Query: {query}

Respond with only 'sql' or 'rag':"""


# ===== Faithfulness / grounding verification =====

GROUNDING_VERIFY_PROMPT = """You are a strict verifier for retrieval-augmented generation.

Given:
1) The user's question
2) The model's proposed answer
3) The retrieved context snippets

Your job:
- Determine whether the proposed answer is supported by the retrieved context.
- If supported, return the same answer.
- If not supported, return a corrected answer that ONLY states what is supported by the context.
- If the context does not contain enough information, return a refusal that says you cannot find enough evidence in the provided documents.

Return ONLY valid JSON with the following schema:
{
  "supported": true/false,
  "corrected_answer": "string"
}

Do not include any extra keys.

Question:
{question}

Proposed Answer:
{answer}

Retrieved Context:
{context}
"""

