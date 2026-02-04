# backend/agents/sql_executor.py
from crewai import Agent, Crew, Task
from backend.config import settings
from backend.database.postgres_handler import PostgreSQLHandler

class SQLExecutorAgent:
    """Agent 2: Executes SQL and handles errors with intelligent retry"""
    
    def __init__(self, db_name: str, schema_context: str):
        self.db_name = db_name
        self.schema_context = schema_context
        self.db_handler = PostgreSQLHandler(db_name)
        
        self.agent = Agent(
            role='SQL Execution Specialist',
            goal='Execute SQL queries safely and resolve errors intelligently',
            backstory=f"""You are a database execution expert specializing in 
            PostgreSQL error diagnosis and query correction.
            
            DATABASE: {db_name}
            
            SCHEMA:
            {schema_context}
            
            CAPABILITIES:
            1. Execute SQL queries against PostgreSQL
            2. Analyze execution errors (syntax, constraints, permissions)
            3. Propose corrected SQL when errors occur
            4. Validate data integrity before modifications
            5. Provide clear error explanations to users
            
            ERROR HANDLING APPROACH:
            - Parse PostgreSQL error messages
            - Identify root cause (syntax, missing column, type mismatch, etc.)
            - Generate corrected SQL that addresses the error
            - Explain what went wrong in user-friendly language
            
            SAFETY RULES:
            - Never execute queries that could corrupt data
            - Always validate schema compliance
            - Warn about operations affecting many rows""",
            verbose=settings.VERBOSE,
            allow_delegation=False,
            llm=settings.get_llm()
        )

    def execute(self, sql: str, retry_count: int = 0) -> dict:
        """Execute SQL with error handling and retry logic"""
        # Execute the SQL
        result = self.db_handler.execute(sql)
        
        if result["success"]:
            return {
                "success": True,
                "data": result.get("data"),
                "columns": result.get("columns"),
                "row_count": result.get("row_count"),
                "affected_rows": result.get("affected_rows"),
                "message": result.get("message")
            }
        
        # Handle errors
        if retry_count >= settings.MAX_RETRY_ATTEMPTS:
            return {
                "success": False,
                "error": result["error"],
                "message": "Max retry attempts reached. Please review the query manually."
            }
        
        # Try to fix the error
        fix_result = self._analyze_and_fix_error(sql, result["error"])
        
        if fix_result["can_retry"] and fix_result["fixed_sql"]:
            # Recursive retry with fixed SQL
            return self.execute(fix_result["fixed_sql"], retry_count + 1)
        
        return {
            "success": False,
            "error": result["error"],
            "error_analysis": fix_result.get("analysis"),
            "suggestion": fix_result.get("suggestion")
        }

    def _analyze_and_fix_error(self, original_sql: str, error: str) -> dict:
        """Analyze error and attempt to generate corrected SQL"""
        task = Task(
            description=f"""
            ORIGINAL SQL:
            {original_sql}
            
            ERROR MESSAGE:
            {error}
            
            DATABASE SCHEMA:
            {self.schema_context}
            
            YOUR TASK:
            1. Analyze the error message
            2. Identify the root cause
            3. Generate corrected SQL that fixes the issue
            4. Explain what was wrong and how you fixed it
            
            COMMON ERROR PATTERNS:
            - Column does not exist: Check schema for correct column names
            - Syntax error: Fix SQL syntax according to PostgreSQL rules
            - Type mismatch: Add proper type casting
            - Constraint violation: Adjust values to meet constraints
            - Permission denied: Cannot fix, report to user
            
            OUTPUT FORMAT (JSON-like structure):
            CAN_RETRY: yes/no
            FIXED_SQL: [corrected SQL if fixable, or "null"]
            ANALYSIS: [brief explanation of the error]
            SUGGESTION: [user-friendly suggestion]
            
            If the error cannot be fixed automatically (permissions, data issues),
            set CAN_RETRY to "no" and provide helpful suggestions.
            """,
            expected_output="Error analysis with potential SQL fix",
            agent=self.agent
        )
        
        crew = Crew(
            agents=[self.agent],
            tasks=[task],
            verbose=settings.VERBOSE
        )
        
        try:
            result = str(crew.kickoff())
            
            # Parse the agent's response
            can_retry = "yes" in result.lower()[:100]
            
            # Extract fixed SQL (simple extraction, you may want more robust parsing)
            fixed_sql = None
            if "FIXED_SQL:" in result:
                lines = result.split("FIXED_SQL:")[1].split("ANALYSIS:")[0].strip()
                fixed_sql = lines.strip().strip('`').strip('"').strip("'")
                if fixed_sql.lower() == "null":
                    fixed_sql = None
            
            return {
                "can_retry": can_retry and fixed_sql is not None,
                "fixed_sql": fixed_sql,
                "analysis": result,
                "suggestion": "Review the error analysis above for details."
            }
        except Exception as e:
            return {
                "can_retry": False,
                "analysis": f"Could not analyze error: {str(e)}",
                "suggestion": "Please review the SQL query manually."
            }