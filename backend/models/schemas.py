# backend/models/schemas.py
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from enum import Enum

class QueryType(str, Enum):
    SELECT = "SELECT"
    INSERT = "INSERT"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    OTHER = "OTHER"

class NLQueryRequest(BaseModel):
    db_name: str = Field(..., description="Database name")
    query: str = Field(..., description="Natural language query")

class SQLGenerationResponse(BaseModel):
    success: bool
    sql: Optional[str] = None
    query_type: Optional[QueryType] = None
    error: Optional[str] = None
    warning: Optional[str] = None

class SQLExecutionRequest(BaseModel):
    db_name: str
    sql: str
    confirm: bool = False

class SQLExecutionResponse(BaseModel):
    success: bool
    data: Optional[List[Dict[str, Any]]] = None
    columns: Optional[List[str]] = None
    row_count: Optional[int] = None
    affected_rows: Optional[int] = None
    error: Optional[str] = None
    retry_sql: Optional[str] = None
    retry_attempt: Optional[int] = None

class AdminCommandRequest(BaseModel):
    db_name: str
    command: str = Field(..., description="Admin command in natural language")

class AdminCommandResponse(BaseModel):
    success: bool
    result: Optional[str] = None
    data: Optional[Any] = None
    error: Optional[str] = None
    
class SchemaResponse(BaseModel):
    success: bool
    schema: Optional[str] = None
    tables: Optional[List[str]] = None
    error: Optional[str] = None