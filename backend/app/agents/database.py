"""Database Agent - Queries data warehouse and performs analysis on results.

Uses LLM to generate SQL from natural language queries.
Executes queries against configured data warehouse.
Returns structured results as JSON with analysis and summarization.
"""

import json
import logging
import re
import time
from datetime import datetime
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.base import BaseAgent
from app.config.config_manager import config_manager, get_config
from app.db.session import get_session_factory

logger = logging.getLogger(__name__)


DATABASE_AGENT_SYSTEM_PROMPT = """You are a database query expert for a multi-agent AI system. Your job is to translate natural language questions into SQL queries and execute them against the data warehouse.

## Your Responsibilities

1. **Understand the Request**: Analyze the user's question to determine what data they need
2. **Generate SQL**: Create accurate, efficient SQL queries based on the data warehouse schema
3. **Analyze Results**: Provide insights, trends, and summaries from the query results
4. **Suggest Follow-ups**: Recommend additional queries that might be useful

## Data Warehouse Schema

{schema}

## Query Guidelines

- Use appropriate SQL syntax for the database type (SQLite or PostgreSQL)
- Always use parameterized queries when possible to prevent SQL injection
- Include LIMIT clauses to prevent excessive result sets
- Use proper JOINs when querying multiple tables
- Apply appropriate aggregations (COUNT, SUM, AVG, etc.) for analytical questions
- Format dates and numbers appropriately for readability

## Result Format

Return your response as a JSON object with this structure:
```json
{{
  "sql_query": "The generated SQL query",
  "analysis_plan": "Brief description of what you'll analyze"
}}
```

## Error Handling

If a query fails:
- Analyze the error message to understand what went wrong
- Attempt to fix the SQL syntax or logic
- If you cannot fix it, explain the issue clearly and suggest alternatives
- Never expose raw database errors to users

## Example Interactions

User: "Show me total sales by month for 2024"
SQL: SELECT strftime('%Y-%m', date) as month, SUM(amount) as total FROM sales WHERE strftime('%Y', date) = '2024' GROUP BY month ORDER BY month

User: "How many active sessions do we have?"
SQL: SELECT COUNT(*) as active_sessions FROM chat_sessions WHERE archived = false
"""


DEFAULT_SCHEMA = """The database contains chat sessions, messages, and agent execution data.

Tables:
- chat_sessions: id (UUID), title, created_at, updated_at, archived, metadata (JSON)
- messages: id (UUID), session_id, role, content, agent_type, parent_message_id, created_at, metadata (JSON)
- working_memory: id (UUID), session_id, memory_tree (JSON), timeline (JSON), index_map (JSON), updated_at
- agent_steps: id (UUID), session_id, message_id, step_number, agent_type, description, status, result, logs, created_at, completed_at
- custom_tools: id (UUID), name, description, code, enabled, created_at

Relationships:
- messages.session_id -> chat_sessions.id
- working_memory.session_id -> chat_sessions.id
- agent_steps.session_id -> chat_sessions.id
- agent_steps.message_id -> messages.id
"""


class DatabaseAgent(BaseAgent):
    """Agent for querying data warehouse and analyzing results."""

    def __init__(self):
        """Initialize the database agent."""
        config = get_config()
        agent_config = config.agents.database

        schema = agent_config.data_warehouse_schema or DEFAULT_SCHEMA
        agent_config.system_prompt = DATABASE_AGENT_SYSTEM_PROMPT.format(schema=schema)

        super().__init__("database", agent_config, config_manager)

    async def execute(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """Execute a database query and analyze the results.

        Args:
            input_data: Dict with "query" key for the natural language query

        Returns:
            Dict with query results and analysis
        """
        query = input_data.get("query", "")
        context = input_data.get("context", "")

        try:
            sql_query = await self._generate_sql(query, context)

            if not sql_query or sql_query.startswith("--"):
                return {
                    "error": "Could not generate a valid SQL query",
                    "summary": f"Unable to create query for: {query}",
                    "success": False,
                }

            result = await self._execute_query(sql_query)

            if not result["success"]:
                return result

            analysis = await self._analyze_results(query, sql_query, result)

            return {
                "query": query,
                "sql_query": sql_query,
                "results": result["results"],
                "row_count": result["row_count"],
                "column_names": result["column_names"],
                "execution_time_ms": result["execution_time_ms"],
                "analysis": analysis,
                "summary": analysis,
                "success": True,
                "timestamp": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error(f"Database agent error: {e}")
            return {
                "query": query,
                "error": str(e),
                "summary": f"Database query failed: {str(e)}",
                "success": False,
                "timestamp": datetime.utcnow().isoformat(),
            }

    async def _generate_sql(self, query: str, context: str = "") -> str:
        """Generate SQL query from natural language using LLM."""
        prompt = f"""Generate a SQL query for this request:

Query: {query}

{f"Context: {context}" if context else ""}

Return ONLY a JSON object with sql_query and analysis_plan fields."""

        response = await self.chat(prompt)
        return self._extract_sql(response)

    def _extract_sql(self, content: str) -> str:
        """Extract SQL query from LLM response."""
        json_match = re.search(r"\{.*\}", content, re.DOTALL)
        if json_match:
            try:
                data = json.loads(json_match.group())
                if "sql_query" in data:
                    return data["sql_query"]
            except json.JSONDecodeError:
                pass

        content = content.strip()
        if "```sql" in content:
            content = content.split("```sql")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]

        content = content.strip()
        if content.lower().startswith("sql:"):
            content = content[4:].strip()

        return content

    async def _execute_query(self, sql_query: str) -> dict[str, Any]:
        """Execute a SQL query against the database."""
        start_time = time.perf_counter()

        session_factory = get_session_factory()
        session: AsyncSession = session_factory()

        try:
            stmt = text(sql_query)
            result = await session.execute(stmt)

            column_names = list(result.keys())
            rows = []
            all_rows = result.fetchall()

            for row in all_rows:
                row_dict = {}
                for i, col_name in enumerate(column_names):
                    value = row[i]
                    if isinstance(value, datetime):
                        value = value.isoformat()
                    row_dict[col_name] = value
                rows.append(row_dict)

            execution_time_ms = (time.perf_counter() - start_time) * 1000

            return {
                "success": True,
                "results": rows,
                "row_count": len(rows),
                "column_names": column_names,
                "execution_time_ms": execution_time_ms,
            }

        except Exception as e:
            execution_time_ms = (time.perf_counter() - start_time) * 1000
            logger.error(f"Query execution failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "sql_query": sql_query,
                "execution_time_ms": execution_time_ms,
                "results": [],
                "row_count": 0,
                "column_names": [],
            }

        finally:
            await session.close()

    async def _analyze_results(
        self,
        original_query: str,
        sql_query: str,
        result: dict[str, Any],
    ) -> str:
        """Analyze query results and generate insights."""
        if not result.get("results"):
            return "The query returned no results."

        results = result["results"]
        row_count = result["row_count"]
        columns = result["column_names"]

        sample_size = min(20, row_count)
        sample_data = json.dumps(results[:sample_size], indent=2, default=str)

        analysis_prompt = f"""Analyze these database query results:

Original Question: {original_query}

SQL Query: {sql_query}

Results ({row_count} rows, columns: {", ".join(columns)}):
{sample_data}
{f"... and {row_count - sample_size} more rows" if row_count > sample_size else ""}

Provide a concise analysis that:
1. Summarizes the key findings
2. Highlights notable patterns or insights
3. Answers the original question
Keep the response focused and actionable."""

        return await self.chat(analysis_prompt)
