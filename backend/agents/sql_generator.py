# backend/agents/sql_generator.py
from crewai import Agent, Crew, Task
from backend.config import settings
from backend.models.schemas import QueryType

class SQLGeneratorAgent:
    """Agent 1: Converts natural language to SQL queries"""
    
    def __init__(self, db_name: str, schema_context: str):
        self.db_name = db_name
        self.schema_context = schema_context
        
        self.agent = Agent(
            role='PostgreSQL Query Generator',
            goal='Convert natural language queries into precise, executable PostgreSQL SQL',
            backstory=f"""You are an expert PostgreSQL database developer with deep knowledge 
            of SQL optimization and best practices.
            
            DATABASE: {db_name}
            
            SCHEMA INFORMATION:
            {schema_context}
            
            CORE RESPONSIBILITIES:
            1. Generate syntactically correct PostgreSQL queries
            2. Use only tables and columns from the provided schema
            3. Apply appropriate WHERE clauses for UPDATE/DELETE operations
            4. Add LIMIT clauses for large result sets (default LIMIT 100 for SELECT)
            5. Use proper JOIN syntax when multiple tables are involved
            6. Handle string escaping and PostgreSQL-specific syntax
            
            OUTPUT RULES:
            - Return ONLY the raw SQL query
            - NO markdown, quotes, or explanations
            - NO multiple queries (one query per request)
            - End with semicolon
            - Use lowercase SQL keywords for consistency""",
            verbose=settings.VERBOSE,
            allow_delegation=False,
            llm=settings.get_llm()
        )
        # print("Schema context:-------\n", schema_context, "\n---------------")

    def generate(self, nl_query: str) -> dict:
        """Generate SQL from natural language"""
        task = Task(
            description=f"""
            Convert this natural language query to PostgreSQL SQL:
            "{nl_query}"
            
            REQUIREMENTS:
            - Validate against the database schema
            - Use proper table and column names from schema
            - For SELECT: Include relevant columns, add LIMIT if not specified
            - For UPDATE/DELETE: MUST include WHERE clause for safety
            - For INSERT: Match all required columns
            - Use proper PostgreSQL data types and casting
            
            OUTPUT FORMAT:
            Return ONLY the executable SQL query without:
            - Markdown code blocks (```)
            - Quotation marks
            - Explanatory text
            - Multiple queries
            
            The query must be copy-paste executable in psql or any PostgreSQL client.
            """,
            expected_output="A single, executable PostgreSQL SQL query",
            agent=self.agent
        )
        
        crew = Crew(
            agents=[self.agent],
            tasks=[task],
            verbose=settings.VERBOSE
        )
        
        try:
            result = crew.kickoff()
            sql = str(result).strip().strip('`').strip('"').strip("'")
            
            # Detect query type
            query_type = self._detect_query_type(sql)
            
            # Add safety warnings
            warning = None
            if query_type in [QueryType.UPDATE, QueryType.DELETE]:
                if "WHERE" not in sql.upper():
                    warning = "⚠️ WARNING: This query modifies data without a WHERE clause!"
            
            return {
                "success": True,
                "sql": sql,
                "query_type": query_type,
                "warning": warning
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"SQL generation failed: {str(e)}"
            }
    
    def _detect_query_type(self, sql: str) -> QueryType:
        """Detect SQL query type"""
        sql_upper = sql.upper().strip()
        if sql_upper.startswith("SELECT"):
            return QueryType.SELECT
        elif sql_upper.startswith("INSERT"):
            return QueryType.INSERT
        elif sql_upper.startswith("UPDATE"):
            return QueryType.UPDATE
        elif sql_upper.startswith("DELETE"):
            return QueryType.DELETE
        else:
            return QueryType.OTHER