"""Tools subagent for executing various utilities."""

import json
from typing import Any

from app.agents.base import BaseAgent
from app.config.config_manager import config_manager, get_config
from app.services.datetime_service import DateTimeService

TOOLS_SYSTEM_PROMPT = """You are a utility tools agent providing precise, reliable support functions for data processing and contextual information.

## Available Tools

### 1. DateTime Tool
Provides comprehensive date and time information:
- Current date and time in configured timezone
- Day of week, week number, quarter
- Unix timestamps
- Custom date formatting
- Timezone conversions

**Use Cases:**
- "What time is it?" → Full datetime context
- "What day of the week is it?" → Day name with date
- Time-sensitive query context

### 2. Calculate Tool
Performs mathematical calculations safely:
- Basic arithmetic: +, -, *, /, %
- Parenthetical expressions: (a + b) * c
- Decimal precision

**Limitations:**
- Only numeric operations
- No variables or function calls
- No scientific notation input

### 3. Format Tool
Transforms data into structured formats:
- JSON pretty-printing
- Data structure formatting

## Response Guidelines

### For DateTime Queries
Always provide:
1. The specific information requested
2. Full context (date, time, timezone)
3. Relevant additional info (e.g., day of week for date queries)

### For Calculations
Show:
1. The extracted expression
2. Step-by-step if complex
3. Final result with appropriate precision

## Error Handling
If a tool cannot process the request:
- Explain what went wrong clearly
- Suggest how to reformulate the request
- Provide partial results if possible"""


class ToolsAgent(BaseAgent):
    def __init__(self):
        config = get_config()
        agent_config = config.agents.tools
        agent_config.system_prompt = TOOLS_SYSTEM_PROMPT
        super().__init__("tools", agent_config, config_manager)

        timezone = config.general.timezone
        if timezone == "auto":
            timezone = "UTC"
        self.datetime_service = DateTimeService(timezone)
        self._tools = {
            "datetime": self._get_datetime,
            "calculate": self._calculate,
            "format_json": self._format_json,
        }

    async def execute(self, input_data: dict[str, Any]) -> dict[str, Any]:
        tool_name = input_data.get("tool", "")
        params = input_data.get("params", {})
        query = input_data.get("query", "")

        if not tool_name and query:
            result = await self.execute_from_query(query)
            return {"result": result}

        if tool_name in self._tools:
            result = await self._tools[tool_name](params)
            return {"tool": tool_name, "result": result}

        return {"error": f"Unknown tool: {tool_name}"}

    async def execute_from_query(self, query: str) -> str:
        query_lower = query.lower()

        datetime_keywords = [
            "time",
            "date",
            "today",
            "now",
            "current",
            "timezone",
            "day",
            "month",
            "year",
            "week",
        ]
        if any(keyword in query_lower for keyword in datetime_keywords):
            datetime_info = await self._get_datetime({})
            context = self.datetime_service.get_context_string()
            return f"DateTime Information:\n{context}\n\nFull data: {json.dumps(datetime_info, indent=2)}"

        calc_keywords = ["calculate", "compute", "math", "sum", "average", "total"]
        if any(keyword in query_lower for keyword in calc_keywords):
            return await self._smart_calculate(query)

        context = f"Current datetime: {self.datetime_service.get_context_string()}"
        return await self.chat_with_context(query, context)

    async def _get_datetime(self, params: dict[str, Any]) -> dict[str, Any]:
        format_str = params.get("format")

        result = {
            "date": self.datetime_service.get_current_date(),
            "time": self.datetime_service.get_current_time(),
            "datetime": self.datetime_service.get_current_datetime_string(),
            "day_of_week": self.datetime_service.get_day_of_week(),
            "timezone": self.datetime_service.timezone_name,
            "timestamp": self.datetime_service.get_timestamp(),
        }

        if format_str:
            result["formatted"] = self.datetime_service.get_formatted_datetime(
                format_str
            )

        return result

    async def _calculate(self, params: dict[str, Any]) -> dict[str, Any]:
        expression = params.get("expression", "")

        if not expression:
            return {"error": "No expression provided"}

        try:
            allowed_chars = set("0123456789+-*/().% ")
            if not all(c in allowed_chars for c in expression):
                return {"error": "Invalid characters in expression"}

            result = eval(expression)
            return {"expression": expression, "result": result}

        except Exception as e:
            return {"expression": expression, "error": str(e)}

    async def _smart_calculate(self, query: str) -> str:
        prompt = f"""Extract any mathematical calculations from this query and compute them.

Query: {query}

If there are calculations to perform, show:
1. The extracted expression
2. The step-by-step calculation
3. The final result

If no calculations are needed, explain why."""

        return await self.llm_service.chat(prompt)

    async def _format_json(self, params: dict[str, Any]) -> dict[str, Any]:
        data = params.get("data")
        indent = params.get("indent", 2)

        if data is None:
            return {"error": "No data provided"}

        try:
            formatted = json.dumps(data, indent=indent, ensure_ascii=False)
            return {"formatted": formatted}
        except Exception as e:
            return {"error": str(e)}

    def update_timezone(self, timezone: str) -> None:
        self.datetime_service.set_timezone(timezone)

    def get_available_tools(self) -> list[str]:
        return list(self._tools.keys())
