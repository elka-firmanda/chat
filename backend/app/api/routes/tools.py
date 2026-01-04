"""
API routes for custom tools CRUD operations.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.db.session import get_db
from app.tools.custom_tool_runner import (
    validate_tool_code,
    create_custom_tool,
    update_custom_tool,
    delete_custom_tool,
    list_custom_tools,
    get_custom_tool,
    execute_custom_tool,
    ValidationError,
    ExecutionError,
    TimeoutError,
    get_tool_template,
)


router = APIRouter(prefix="/tools", tags=["Custom Tools"])


# Pydantic models for request/response
class ToolCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="Unique tool name")
    description: Optional[str] = Field(None, description="Tool description")
    code: str = Field(..., min_length=10, description="Python code for the tool")


class ToolUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    code: Optional[str] = Field(None, min_length=10)
    enabled: Optional[bool] = None


class ToolResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    code: str
    enabled: bool
    created_at: Optional[str]


class ToolExecuteRequest(BaseModel):
    arguments: dict = Field(
        default_factory=dict, description="Arguments to pass to the tool"
    )


class ToolValidateRequest(BaseModel):
    code: str = Field(..., min_length=10, description="Python code to validate")


class ToolValidateResponse(BaseModel):
    valid: bool
    error: Optional[str] = None


class ToolTemplateResponse(BaseModel):
    template: str


class ToolExecuteResponse(BaseModel):
    success: bool
    result: Optional[dict] = None
    output: Optional[str] = None
    execution_time: float
    error: Optional[str] = None


@router.get("/custom", response_model=List[ToolResponse])
async def list_tools(
    include_disabled: bool = False,
    db=Depends(get_db),
):
    """
    List all custom tools.
    """
    try:
        tools = await list_custom_tools(db, include_disabled=include_disabled)
        return tools
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get("/custom/{tool_id}", response_model=ToolResponse)
async def get_tool(
    tool_id: str,
    db=Depends(get_db),
):
    """
    Get a single custom tool by ID.
    """
    tool = await get_custom_tool(db, tool_id)
    if not tool:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tool with ID '{tool_id}' not found",
        )
    return tool


@router.post(
    "/custom", response_model=ToolResponse, status_code=status.HTTP_201_CREATED
)
async def create_tool(
    request: ToolCreateRequest,
    db=Depends(get_db),
):
    """
    Create a new custom tool.
    """
    try:
        tool = await create_custom_tool(
            db,
            name=request.name,
            code=request.code,
            description=request.description,
        )
        return tool
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.message,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.patch("/custom/{tool_id}", response_model=ToolResponse)
async def update_tool(
    tool_id: str,
    request: ToolUpdateRequest,
    db=Depends(get_db),
):
    """
    Update an existing custom tool.
    """
    try:
        tool = await update_custom_tool(
            db,
            tool_id=tool_id,
            name=request.name,
            code=request.code,
            description=request.description,
            enabled=request.enabled,
        )
        return tool
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.message,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.delete("/custom/{tool_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tool(
    tool_id: str,
    db=Depends(get_db),
):
    """
    Delete a custom tool.
    """
    try:
        deleted = await delete_custom_tool(db, tool_id)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tool with ID '{tool_id}' not found",
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.post("/custom/{tool_id}/execute", response_model=ToolExecuteResponse)
async def execute_tool(
    tool_id: str,
    request: ToolExecuteRequest,
    db=Depends(get_db),
):
    """
    Execute a custom tool with the given arguments.
    """
    # Get the tool
    tool = await get_custom_tool(db, tool_id)
    if not tool:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tool with ID '{tool_id}' not found",
        )

    if not tool["enabled"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Tool '{tool['name']}' is disabled",
        )

    try:
        result = await execute_custom_tool(
            code=tool["code"],
            tool_name=tool["name"],
            arguments=request.arguments,
            timeout=30.0,
        )

        return ToolExecuteResponse(
            success=result["success"],
            result={"output": result["result"]} if result["success"] else None,
            output=result.get("output"),
            execution_time=result["execution_time"],
            error=None,
        )
    except ValidationError as e:
        return ToolExecuteResponse(
            success=False,
            execution_time=0,
            error=f"Validation error: {e.message}",
        )
    except TimeoutError as e:
        return ToolExecuteResponse(
            success=False,
            execution_time=30.0,
            error=f"Timeout: {e.message}",
        )
    except ExecutionError as e:
        return ToolExecuteResponse(
            success=False,
            execution_time=0,
            error=f"Execution error: {e.message}",
        )
    except Exception as e:
        return ToolExecuteResponse(
            success=False,
            execution_time=0,
            error=f"Unexpected error: {str(e)}",
        )


@router.post("/validate", response_model=ToolValidateResponse)
async def validate_tool(
    request: ToolValidateRequest,
):
    """
    Validate custom tool code without saving.
    """
    is_valid, error_msg = validate_tool_code(request.code)
    return ToolValidateResponse(
        valid=is_valid,
        error=error_msg,
    )


@router.get("/template", response_model=ToolTemplateResponse)
async def get_tool_template_endpoint():
    """
    Get a template for creating custom tools.
    """
    return ToolTemplateResponse(
        template=get_tool_template(),
    )
