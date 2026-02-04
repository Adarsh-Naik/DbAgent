# backend/main.py
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from backend.config import settings
from backend.models.schemas import (
    NLQueryRequest, SQLGenerationResponse, 
    SQLExecutionRequest, SQLExecutionResponse,
    AdminCommandRequest, AdminCommandResponse,
    SchemaResponse
)
from backend.agents.sql_generator import SQLGeneratorAgent
from backend.agents.sql_executor import SQLExecutorAgent
from backend.agents.db_admin import SmartDBAdminAgent  # New import
from backend.database.schema_extractor import SchemaExtractor
from backend.database.postgres_handler import PostgreSQLHandler

app = FastAPI(
    title="NL-to-SQL Multi-Agent System",
    description="CrewAI-powered database query system with intelligent agents",
    version="2.0.0"
)

# CORS middleware for Streamlit
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory cache for schema (in production, use Redis)
schema_cache = {}


# ============================================================================
# NEW: Smart Admin Request Models
# ============================================================================

class SmartAdminGenerateRequest(BaseModel):
    """Request model for smart admin SQL generation"""
    db_name: str
    query: str

class SmartAdminExecuteRequest(BaseModel):
    """Request model for smart admin SQL execution"""
    db_name: str
    sql: str


# ============================================================================
# Helper Functions
# ============================================================================

def get_schema(db_name: str) -> str:
    """Get schema with caching"""
    if db_name not in schema_cache:
        extractor = SchemaExtractor(db_name)
        schema_cache[db_name] = extractor.extract_schema()
    return schema_cache[db_name]


# ============================================================================
# Basic Endpoints
# ============================================================================

@app.get("/")
async def root():
    return {
        "message": "NL-to-SQL Multi-Agent System",
        "version": "2.0.0",
        "agents": ["SQL Generator", "SQL Executor", "DB Admin", "Smart Admin"]
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "ollama_url": settings.OLLAMA_URL}


@app.post("/test-connection")
async def test_connection(db_name: str):
    """Test database connection"""
    try:
        handler = PostgreSQLHandler(db_name)
        connected = handler.test_connection()
        return {
            "success": connected,
            "database": db_name,
            "message": "Connected successfully" if connected else "Connection failed"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


# ============================================================================
# Schema Endpoints
# ============================================================================

@app.post("/schema/extract", response_model=SchemaResponse)
async def extract_schema(db_name: str):
    """Extract database schema"""
    try:
        extractor = SchemaExtractor(db_name)
        schema = extractor.extract_schema()
        tables = extractor.get_all_tables()
        
        # Cache it
        schema_cache[db_name] = schema
        
        return SchemaResponse(
            success=True,
            schema=schema,
            tables=tables
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Agent 1: SQL Generator Endpoints
# ============================================================================

@app.post("/query/generate", response_model=SQLGenerationResponse)
async def generate_sql(request: NLQueryRequest):
    """Agent 1: Generate SQL from natural language"""
    try:
        schema = get_schema(request.db_name)
        generator = SQLGeneratorAgent(request.db_name, schema)
        result = generator.generate(request.query)
        
        return SQLGenerationResponse(**result)
    except Exception as e:
        return SQLGenerationResponse(
            success=False,
            error=str(e)
        )


# ============================================================================
# Agent 2: SQL Executor Endpoints
# ============================================================================

@app.post("/query/execute", response_model=SQLExecutionResponse)
async def execute_sql(request: SQLExecutionRequest):
    """Agent 2: Execute SQL with error handling"""
    try:
        if not request.confirm:
            raise HTTPException(
                status_code=400, 
                detail="Execution requires confirmation"
            )
        
        schema = get_schema(request.db_name)
        executor = SQLExecutorAgent(request.db_name, schema)
        result = executor.execute(request.sql)
        
        return SQLExecutionResponse(**result)
    except HTTPException:
        raise
    except Exception as e:
        return SQLExecutionResponse(
            success=False,
            error=str(e)
        )


# ============================================================================
# Agent 3: DB Admin (Legacy) Endpoints
# ============================================================================

@app.post("/admin/command", response_model=AdminCommandResponse)
async def admin_command(request: AdminCommandRequest):
    """Agent 3: Process admin commands (Legacy)"""
    try:
        admin_agent = DBAdminAgent(request.db_name)
        result = admin_agent.process_command(request.command)
        
        return AdminCommandResponse(**result)
    except Exception as e:
        return AdminCommandResponse(
            success=False,
            error=str(e)
        )


# ============================================================================
# NEW: Smart Admin Endpoints
# ============================================================================

@app.post("/admin/smart/generate")
async def smart_admin_generate(request: SmartAdminGenerateRequest):
    """
    Smart Admin: Generate SQL from natural language query.
    Does not execute - returns SQL for user confirmation.
    
    This endpoint:
    1. Analyzes the natural language query
    2. Detects the intent (list_tables, table_sizes, etc.)
    3. Generates appropriate SQL using schema context
    4. Analyzes safety level
    5. Returns SQL + metadata WITHOUT executing
    
    Args:
        request: Contains db_name and natural language query
        
    Returns:
        Dict with:
            - success: bool
            - sql: Generated SQL query
            - explanation: What the query does
            - safety_level: 'safe', 'modify', 'dangerous', 'unknown'
            - recommendation: Safety advice for user
            - warnings: Optional warnings (for dangerous operations)
            - intent_type: Detected query type
            
    Example:
        POST /admin/smart/generate
        {
            "db_name": "dvdrental",
            "query": "Show all tables"
        }
        
        Response:
        {
            "success": true,
            "sql": "SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename;",
            "explanation": "List all tables in the database",
            "safety_level": "safe",
            "recommendation": "✅ SAFE: Read-only query. Safe to execute.",
            "intent_type": "list_tables"
        }
    """
    try:
        # Initialize smart admin agent
        agent = SmartDBAdminAgent(request.db_name)
        
        # Process query and generate SQL (no execution)
        result = agent.process_query(request.query)
        
        return result
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to generate SQL: {str(e)}",
            "suggestions": [
                "Try: 'Show all tables'",
                "Try: 'Show table sizes'",
                "Try: 'List all indexes'",
                "Try: 'Describe table actor'",
                "Try: 'Show database size'",
                "Try: 'Show row counts'",
                "Try: 'Show active connections'"
            ]
        }


@app.post("/admin/smart/execute")
async def smart_admin_execute(request: SmartAdminExecuteRequest):
    """
    Smart Admin: Execute a confirmed SQL query.
    
    This endpoint executes SQL that was previously generated and
    confirmed by the user through the UI.
    
    Args:
        request: Contains db_name and SQL query to execute
        
    Returns:
        Dict with execution results:
            - success: bool
            - data: Query results (for SELECT queries) - list of dicts
            - columns: Column names (for SELECT queries)
            - row_count: Number of rows returned (for SELECT queries)
            - affected_rows: Number of rows affected (for DML queries)
            - message: Success message
            - error: Error message (if failed)
            - error_type: Type of error (if failed)
            
    Example:
        POST /admin/smart/execute
        {
            "db_name": "dvdrental",
            "sql": "SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename;"
        }
        
        Response:
        {
            "success": true,
            "data": [
                {"tablename": "actor"},
                {"tablename": "address"},
                ...
            ],
            "columns": ["tablename"],
            "row_count": 15
        }
    """
    try:
        # Initialize smart admin agent
        agent = SmartDBAdminAgent(request.db_name)
        
        # Execute the SQL query
        result = agent.execute_sql(request.sql)
        
        return result
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to execute SQL: {str(e)}"
        }


# ============================================================================
# Server Startup
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=True
    )

# # backend/main.py
# from fastapi import FastAPI, HTTPException
# from fastapi.middleware.cors import CORSMiddleware
# from backend.config import settings
# from backend.models.schemas import (
#     NLQueryRequest, SQLGenerationResponse, 
#     SQLExecutionRequest, SQLExecutionResponse,
#     AdminCommandRequest, AdminCommandResponse,
#     SchemaResponse
# )
# from backend.agents.sql_generator import SQLGeneratorAgent
# from backend.agents.sql_executor import SQLExecutorAgent
# from backend.agents.db_admin import DBAdminAgent
# from backend.database.schema_extractor import SchemaExtractor
# from backend.database.postgres_handler import PostgreSQLHandler

# app = FastAPI(
#     title="NL-to-SQL Multi-Agent System",
#     description="CrewAI-powered database query system with intelligent agents",
#     version="2.0.0"
# )

# # CORS middleware for Streamlit
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# # In-memory cache for schema (in production, use Redis)
# schema_cache = {}

# def get_schema(db_name: str) -> str:
#     """Get schema with caching"""
#     if db_name not in schema_cache:
#         extractor = SchemaExtractor(db_name)
#         schema_cache[db_name] = extractor.extract_schema()
#     return schema_cache[db_name]


# @app.get("/")
# async def root():
#     return {
#         "message": "NL-to-SQL Multi-Agent System",
#         "version": "2.0.0",
#         "agents": ["SQL Generator", "SQL Executor", "DB Admin"]
#     }


# @app.post("/schema/extract", response_model=SchemaResponse)
# async def extract_schema(db_name: str):
#     """Extract database schema"""
#     try:
#         extractor = SchemaExtractor(db_name)
#         schema = extractor.extract_schema()
#         tables = extractor.get_all_tables()
        
#         # Cache it
#         schema_cache[db_name] = schema
        
#         return SchemaResponse(
#             success=True,
#             schema=schema,
#             tables=tables
#         )
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))


# @app.post("/query/generate", response_model=SQLGenerationResponse)
# async def generate_sql(request: NLQueryRequest):
#     """Agent 1: Generate SQL from natural language"""
#     try:
#         schema = get_schema(request.db_name)
#         generator = SQLGeneratorAgent(request.db_name, schema)
#         result = generator.generate(request.query)
        
#         return SQLGenerationResponse(**result)
#     except Exception as e:
#         return SQLGenerationResponse(
#             success=False,
#             error=str(e)
#         )


# @app.post("/query/execute", response_model=SQLExecutionResponse)
# async def execute_sql(request: SQLExecutionRequest):
#     """Agent 2: Execute SQL with error handling"""
#     try:
#         if not request.confirm:
#             raise HTTPException(
#                 status_code=400, 
#                 detail="Execution requires confirmation"
#             )
        
#         schema = get_schema(request.db_name)
#         executor = SQLExecutorAgent(request.db_name, schema)
#         result = executor.execute(request.sql)
        
#         return SQLExecutionResponse(**result)
#     except HTTPException:
#         raise
#     except Exception as e:
#         return SQLExecutionResponse(
#             success=False,
#             error=str(e)
#         )


# @app.post("/admin/command", response_model=AdminCommandResponse)
# async def admin_command(request: AdminCommandRequest):
#     """Agent 3: Process admin commands"""
#     try:
#         admin_agent = DBAdminAgent(request.db_name)
#         result = admin_agent.process_command(request.command)
        
#         return AdminCommandResponse(**result)
#     except Exception as e:
#         return AdminCommandResponse(
#             success=False,
#             error=str(e)
#         )


# @app.get("/health")
# async def health_check():
#     """Health check endpoint"""
#     return {"status": "healthy", "ollama_url": settings.OLLAMA_URL}


# @app.post("/test-connection")
# async def test_connection(db_name: str):
#     """Test database connection"""
#     try:
#         handler = PostgreSQLHandler(db_name)
#         connected = handler.test_connection()
#         return {
#             "success": connected,
#             "database": db_name,
#             "message": "Connected successfully" if connected else "Connection failed"
#         }
#     except Exception as e:
#         return {
#             "success": False,
#             "error": str(e)
#         }


# if __name__ == "__main__":
#     import uvicorn
#     uvicorn.run(
#         "backend.main:app",
#         host=settings.API_HOST,
#         port=settings.API_PORT,
#         reload=True
#     )