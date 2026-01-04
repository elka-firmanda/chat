"""
Database Agent - Queries data warehouse and performs analysis on results.

Uses LLM to generate SQL from natural language queries.
Executes queries against configured data warehouse.
Returns structured results as JSON with analysis and summarization.
"""

import json
import logging
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.config_manager import get_config
from app.llm.providers import LLMProviderFactory, BaseLLMProvider
from app.db.session import get_engine, get_engine_url

from .graph import AgentType, StepStatus
from .memory import AsyncWorkingMemory
from .error_handler import AgentError, ErrorType

logger = logging.getLogger(__name__)


DATABASE_AGENT_SYSTEM_PROMPT = """You are a database query expert for a multi-agent AI system. Your job is to translate natural language questions into SQL queries and execute them against the data warehouse.

## Your Responsibilities

1. **Understand the Request**: Analyze the user's question to determine what data they need
2. **Generate SQL**: Create accurate, efficient SQL queries based on the data warehouse schema
3. **Execute Queries**: Run queries against the configured database
4. **Analyze Results**: Provide insights, trends, and summaries from the query results
5. **Suggest Follow-ups**: Recommend additional queries that might be useful

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
  "results": [array of result rows],
  "row_count": number of rows returned,
  "column_names": ["list", "of", "column", "names"],
  "summary": "Human-readable summary of the results",
  "insights": ["list", "of", "key", "insights"],
  "followup_suggestions": ["suggested", "follow-up", "queries"]
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
SQL: SELECT DATE_FORMAT(date, '%Y-%m') as month, SUM(amount) as total FROM sales WHERE DATE_FORMAT(date, '%Y') = '2024' GROUP BY month ORDER BY month

User: "How many active users do we have?"
SQL: SELECT COUNT(*) as active_users FROM users WHERE status = 'active'
"""


class QueryResult:
    """Container for query execution results."""

    def __init__(
        self,
        sql_query: str,
        success: bool,
        results: Optional[List[Dict[str, Any]]] = None,
        row_count: int = 0,
        column_names: Optional[List[str]] = None,
        error: Optional[str] = None,
        execution_time_ms: float = 0.0,
    ):
        self.sql_query = sql_query
        self.success = success
        self.results = results or []
        self.row_count = row_count
        self.column_names = column_names or []
        self.error = error
        self.execution_time_ms = execution_time_ms

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "sql_query": self.sql_query,
            "success": self.success,
            "results": self.results,
            "row_count": self.row_count,
            "column_names": self.column_names,
            "error": self.error,
            "execution_time_ms": self.execution_time_ms,
        }


class DatabaseAgent:
    """Agent for querying data warehouse and analyzing results."""

    def __init__(
        self,
        llm_provider: Optional[BaseLLMProvider] = None,
        data_warehouse_schema: str = "",
    ):
        """
        Initialize the database agent.

        Args:
            llm_provider: Optional LLM provider for SQL generation.
                         If None, uses default from config.
            data_warehouse_schema: Schema description of the data warehouse.
        """
        self.llm = llm_provider
        self.schema = data_warehouse_schema or self._get_default_schema()
        self.system_prompt = DATABASE_AGENT_SYSTEM_PROMPT.format(schema=self.schema)
        self._engine = None

    def _get_default_schema(self) -> str:
        """Get default schema description."""
        return """The database contains chat sessions, messages, and agent execution data.

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

    def _get_engine(self):
        """Get or create the database engine."""
        if self._engine is None:
            self._engine = get_engine()
        return self._engine

    async def _get_db_connection(self) -> AsyncSession:
        """Get a database session for query execution."""
        from app.db.session import get_session_factory

        session_factory = get_session_factory()
        session = session_factory()
        return session

    async def generate_sql(
        self,
        user_question: str,
        context: Optional[str] = None,
    ) -> str:
        """
        Generate SQL query from natural language using LLM.

        Args:
            user_question: The user's question in natural language
            context: Optional additional context about what data is needed

        Returns:
            Generated SQL query string
        """
        if not self.llm:
            raise AgentError(
                error_type=ErrorType.VALIDATION_ERROR,
                message="LLM provider not configured for SQL generation",
            )

        messages = [
            {"role": "system", "content": self.system_prompt},
            {
                "role": "user",
                "content": f"Generate a SQL query for: {user_question}"
                + (f"\n\nContext: {context}" if context else ""),
            },
        ]

        try:
            response = await self.llm.complete(
                messages=messages,
                temperature=0.3,
                max_tokens=1000,
            )

            sql = self._extract_sql(response.content)
            logger.info(f"Generated SQL: {sql}")
            return sql

        except Exception as e:
            logger.error(f"SQL generation failed: {e}")
            raise AgentError(
                error_type=ErrorType.API_ERROR,
                message=f"Failed to generate SQL: {str(e)}",
                original_exception=e,
            )

    def _extract_sql(self, content: str) -> str:
        """Extract SQL query from LLM response."""
        content = content.strip()

        if "```sql" in content:
            content = content.split("```sql")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]

        content = content.strip()

        if content.lower().startswith("sql:"):
            content = content[4:].strip()

        return content

    async def execute_query(
        self,
        sql_query: str,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> QueryResult:
        """
        Execute a SQL query against the data warehouse.

        Args:
            sql_query: The SQL query to execute
            parameters: Optional parameters for parameterized queries

        Returns:
            QueryResult with results or error information
        """
        start_time = time.perf_counter()

        session = await self._get_db_connection()

        try:
            if parameters:
                stmt = text(sql_query).bindparams(**parameters)
            else:
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

            return QueryResult(
                sql_query=sql_query,
                success=True,
                results=rows,
                row_count=len(rows),
                column_names=column_names,
                execution_time_ms=execution_time_ms,
            )

        except Exception as e:
            execution_time_ms = (time.perf_counter() - start_time) * 1000
            logger.error(f"Query execution failed: {e}")

            error_type = self._classify_sql_error(e)

            raise AgentError(
                error_type=error_type,
                message=f"Query execution failed: {str(e)}",
                original_exception=e,
                context={"sql_query": sql_query},
            )

        finally:
            await session.close()

    def _classify_sql_error(self, exception: Exception) -> ErrorType:
        """Classify SQL error into appropriate ErrorType."""
        error_str = str(exception).lower()

        if "syntax" in error_str or "parse" in error_str:
            return ErrorType.SCHEMA_ERROR
        elif "no such table" in error_str or "undefined table" in error_str:
            return ErrorType.DATA_NOT_FOUND
        elif "column" in error_str and "not found" in error_str:
            return ErrorType.DATA_NOT_FOUND
        elif "constraint" in error_str or "foreign key" in error_str:
            return ErrorType.DATA_CORRUPTION
        elif "timeout" in error_str or "locked" in error_str:
            return ErrorType.EXECUTION_TIMEOUT
        elif "permission" in error_str or "denied" in error_str:
            return ErrorType.API_AUTH

        return ErrorType.EXECUTION_ERROR

    async def analyze_results(
        self,
        query_result: QueryResult,
        original_question: str,
    ) -> Dict[str, Any]:
        """
        Analyze query results and generate insights using LLM.

        Args:
            query_result: The result from query execution
            original_question: The original user question

        Returns:
            Dictionary with analysis, insights, and follow-up suggestions
        """
        if not query_result.success or not self.llm:
            return {
                "summary": f"Query failed: {query_result.error}",
                "insights": [],
                "followup_suggestions": [],
            }

        if not query_result.results:
            return {
                "summary": "No results found for the query.",
                "insights": [],
                "followup_suggestions": [
                    "Try broadening your search criteria",
                    "Check if the data exists in the database",
                ],
            }

        results_json = json.dumps(query_result.results[:50], indent=2, default=str)
        if len(query_result.results) > 50:
            results_json += f"\n... and {len(query_result.results) - 50} more rows"

        messages = [
            {
                "role": "system",
                "content": """You are a data analyst. Analyze query results and provide:
1. A concise summary of what the data shows
2. Key insights or patterns (2-4 bullet points)
3. 2-3 suggested follow-up queries

Keep your response focused and actionable.""",
            },
            {
                "role": "user",
                "content": f"""Original question: {original_question}

Query results ({query_result.row_count} rows, columns: {query_result.column_names}):

{results_json}

Provide:
- Summary: What does this data show?
- Insights: Key observations (2-4 bullet points)
- Follow-up queries: 2-3 related questions worth exploring""",
            },
        ]

        try:
            response = await self.llm.complete(
                messages=messages,
                temperature=0.5,
                max_tokens=1000,
            )

            return self._parse_analysis(response.content, query_result)

        except Exception as e:
            logger.error(f"Analysis failed: {e}")
            return {
                "summary": f"Analysis of {query_result.row_count} rows returned.",
                "insights": [],
                "followup_suggestions": [],
            }

    def _parse_analysis(
        self,
        content: str,
        query_result: QueryResult,
    ) -> Dict[str, Any]:
        """Parse LLM analysis response into structured format."""
        summary = ""
        insights = []
        followup_suggestions = []

        current_section = None
        lines = content.split("\n")

        for line in lines:
            line = line.strip()
            if not line:
                continue

            lower_line = line.lower()
            if "summary" in lower_line and ":" not in line:
                current_section = "summary"
                continue
            elif "insight" in lower_line and ":" not in line:
                current_section = "insights"
                continue
            elif "follow-up" in lower_line or "followup" in lower_line:
                current_section = "followup"
                continue

            if current_section == "summary":
                summary += line + " "
            elif current_section == "insights":
                if line.startswith("-") or line.startswith("*"):
                    insights.append(line[1:].strip())
                elif len(insights) == 0:
                    insights.append(line)
            elif current_section == "followup":
                if line.startswith("-") or line.startswith("*"):
                    followup_suggestions.append(line[1:].strip())
                elif len(followup_suggestions) == 0:
                    followup_suggestions.append(line)

        if not summary:
            summary = content[:200] + "..." if len(content) > 200 else content

        return {
            "summary": summary.strip(),
            "insights": insights,
            "followup_suggestions": followup_suggestions,
        }

    async def query(
        self,
        user_question: str,
        session_id: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Execute a complete database query workflow.

        Args:
            user_question: The user's question
            session_id: Session identifier for working memory
            context: Optional context (previous queries, working memory)

        Returns:
            Complete query result with analysis
        """
        memory = AsyncWorkingMemory(session_id)
        if context and context.get("working_memory"):
            await memory.load(context["working_memory"])

        node_id = await memory.add_node(
            agent=AgentType.DATABASE.value,
            node_type="thought",
            description=f"Processing database query: {user_question[:50]}...",
        )

        try:
            if self.llm:
                sql_query = await self.generate_sql(
                    user_question=user_question,
                    context=context.get("original_plan") if context else None,
                )
            else:
                sql_query = self._generate_simple_query(user_question)

            await memory.update_node(
                node_id,
                content={"sql_generated": True, "query_preview": sql_query[:100]},
            )

            query_result = await self.execute_query(sql_query)

            analysis = await self.analyze_results(
                query_result=query_result,
                original_question=user_question,
            )

            output = {
                "query": user_question,
                "sql_query": query_result.sql_query,
                "results": query_result.results,
                "row_count": query_result.row_count,
                "column_names": query_result.column_names,
                "execution_time_ms": query_result.execution_time_ms,
                "summary": analysis["summary"],
                "insights": analysis["insights"],
                "followup_suggestions": analysis["followup_suggestions"],
                "success": True,
                "timestamp": datetime.utcnow().isoformat(),
            }

            await memory.update_node(
                node_id,
                completed=True,
                status=StepStatus.COMPLETED.value,
                content={
                    "row_count": query_result.row_count,
                    "execution_time_ms": query_result.execution_time_ms,
                },
            )

            result_node_id = await memory.add_node(
                agent=AgentType.DATABASE.value,
                node_type="result",
                description=f"Query returned {query_result.row_count} rows in {query_result.execution_time_ms:.1f}ms",
                parent_id=node_id,
                content=output,
            )

            logger.info(
                f"Database query completed: {query_result.row_count} rows in {query_result.execution_time_ms:.1f}ms"
            )

            return output

        except AgentError as e:
            logger.error(f"Database agent error: {e}")

            output = {
                "query": user_question,
                "error": e.message,
                "error_type": e.error_type.value if e.error_type else None,
                "success": False,
                "timestamp": datetime.utcnow().isoformat(),
            }

            await memory.update_node(
                node_id,
                completed=True,
                status=StepStatus.FAILED.value,
                content={"error": e.message},
            )

            await memory.add_node(
                agent=AgentType.DATABASE.value,
                node_type="error",
                description=f"Query failed: {e.message[:100]}",
                parent_id=node_id,
                content=output,
            )

            return output

    def _generate_simple_query(self, user_question: str) -> str:
        """Generate a simple query without LLM for basic patterns."""
        question_lower = user_question.lower()

        if "session" in question_lower and "count" in question_lower:
            return "SELECT COUNT(*) as count FROM chat_sessions"
        elif "message" in question_lower and "count" in question_lower:
            return "SELECT COUNT(*) as count FROM messages"
        elif "recent" in question_lower:
            return "SELECT * FROM chat_sessions ORDER BY created_at DESC LIMIT 10"
        elif "active" in question_lower and "user" in question_lower:
            return "SELECT COUNT(*) as active_users FROM messages WHERE created_at > datetime('now', '-7 days')"

        return f"-- Unable to generate query for: {user_question}"


def _create_default_database_agent() -> DatabaseAgent:
    """Create a default database agent from configuration."""
    try:
        config = get_config()

        agent_config = config.agents.database

        llm = None
        if agent_config.provider and agent_config.model:
            api_key = (
                config.api_keys.anthropic
                if agent_config.provider == "anthropic"
                else None
            )
            if agent_config.provider == "openai":
                api_key = config.api_keys.openai

            llm = LLMProviderFactory.create(
                provider=agent_config.provider,
                model=agent_config.model,
                api_key=api_key,
                max_tokens=agent_config.max_tokens,
                temperature=0.3,
            )

        return DatabaseAgent(
            llm_provider=llm,
            data_warehouse_schema=agent_config.data_warehouse_schema or "",
        )

    except Exception as e:
        logger.warning(f"Failed to create configured database agent: {e}")
        return DatabaseAgent()


default_database_agent = _create_default_database_agent()


async def database_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Database agent function for LangGraph integration.

    This is the node function that gets called by the graph.

    Args:
        state: AgentState dictionary

    Returns:
        Updated state with database_output
    """
    session_id = state.get("session_id", "default")
    current_step = state.get("current_plan", [])[state.get("active_step", 0)]
    query = current_step.get("query", state.get("user_message", ""))

    context = {
        "original_plan": state.get("current_plan", []),
        "working_memory": state.get("working_memory", {}),
    }

    query_result = await default_database_agent.query(
        user_question=query,
        session_id=session_id,
        context=context,
    )

    state["database_output"] = query_result

    if state.get("working_memory"):
        memory = AsyncWorkingMemory(session_id)
        await memory.load(state["working_memory"])

        result_node_id = await memory.add_node(
            agent=AgentType.DATABASE.value,
            node_type="result",
            description=f"Database query: {query_result.get('row_count', 0)} rows returned",
            content={
                "row_count": query_result.get("row_count", 0),
                "success": query_result.get("success", False),
                "execution_time_ms": query_result.get("execution_time_ms", 0),
            },
        )

        state["working_memory"] = await memory.to_dict()

    return state
