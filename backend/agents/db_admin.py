# backend/agents/smart_db_admin.py
import logging
import re
from typing import Dict, Any, Optional
from backend.database.postgres_handler import PostgreSQLHandler
from backend.database.schema_extractor import SchemaExtractor

logger = logging.getLogger(__name__)

class SmartDBAdminAgent:
    """
    Smart database admin agent that understands schema context,
    generates SQL from natural language, and requires user confirmation.
    """
    
    def __init__(self, db_name: str):
        self.db_name = db_name
        self.db_handler = PostgreSQLHandler(db_name)
        self.schema_extractor = SchemaExtractor(db_name)
        self.schema_context = None
        logger.info(f"SmartDBAdminAgent initialized for database: {db_name}")
    
    def _load_schema_context(self) -> str:
        """Load compact schema for context"""
        if not self.schema_context:
            try:
                self.schema_context = self.schema_extractor.extract_schema_compact()
                logger.info("Schema context loaded successfully")
            except Exception as e:
                logger.error(f"Failed to load schema: {e}")
                self.schema_context = "Schema unavailable"
        return self.schema_context
    
    def process_query(self, natural_language_query: str) -> Dict[str, Any]:
        """
        Process natural language query and generate SQL.
        Returns SQL for user confirmation (does not execute).
        
        Args:
            natural_language_query: User's request in natural language
            
        Returns:
            Dict with:
                - success: bool
                - sql: Generated SQL query
                - explanation: What the query does
                - safety_level: 'safe', 'modify', 'dangerous'
                - recommendation: Advice for the user
        """
        logger.info(f"Processing query: {natural_language_query}")
        
        # Load schema context
        schema = self._load_schema_context()
        
        # Analyze query intent
        intent = self._analyze_intent(natural_language_query)
        logger.info(f"Detected intent: {intent['type']}")
        
        # Generate SQL based on intent
        sql = self._generate_sql(natural_language_query, intent, schema)
        
        if not sql:
            return {
                "success": False,
                "error": "Could not generate SQL query. Please rephrase your request.",
                "suggestions": self._get_suggestions(natural_language_query)
            }
        
        # Analyze safety
        safety = self._analyze_safety(sql)
        
        return {
            "success": True,
            "sql": sql,
            "explanation": intent['explanation'],
            "safety_level": safety['level'],
            "recommendation": safety['recommendation'],
            "warnings": safety.get('warnings'),
            "intent_type": intent['type']
        }
    
    def execute_sql(self, sql: str) -> Dict[str, Any]:
        """
        Execute the confirmed SQL query.
        
        Args:
            sql: SQL query to execute
            
        Returns:
            Execution results from PostgreSQLHandler
        """
        logger.info(f"Executing SQL: {sql[:100]}...")
        return self.db_handler.execute(sql)
    
    def _analyze_intent(self, query: str) -> Dict[str, str]:
        """Analyze user's intent from natural language"""
        query_lower = query.lower().strip()
        
        # Schema information queries
        if any(kw in query_lower for kw in ['show tables', 'list tables', 'what tables', 'all tables']):
            return {
                'type': 'list_tables',
                'explanation': 'List all tables in the database'
            }
        
        if any(kw in query_lower for kw in ['describe', 'table structure', 'columns in', 'show columns', 'schema of']):
            table = self._extract_table_name(query_lower)
            return {
                'type': 'describe_table',
                'explanation': f'Show structure of table: {table}' if table else 'Show table structure',
                'table': table
            }
        
        if any(kw in query_lower for kw in ['show indexes', 'list indexes', 'what indexes', 'all indexes']):
            return {
                'type': 'list_indexes',
                'explanation': 'List all indexes in the database'
            }
        
        if any(kw in query_lower for kw in ['foreign key', 'relationships', 'references', 'constraints']):
            return {
                'type': 'foreign_keys',
                'explanation': 'Show foreign key relationships'
            }
        
        # Size and performance queries
        if any(kw in query_lower for kw in ['table size', 'table sizes', 'disk usage', 'space used']):
            return {
                'type': 'table_sizes',
                'explanation': 'Show table sizes sorted by disk usage'
            }
        
        if any(kw in query_lower for kw in ['database size', 'db size', 'total size']):
            return {
                'type': 'database_size',
                'explanation': 'Show total database size'
            }
        
        if any(kw in query_lower for kw in ['row count', 'table rows', 'count rows', 'how many rows']):
            return {
                'type': 'row_counts',
                'explanation': 'Show row counts for all tables'
            }
        
        # Connection and activity queries
        if any(kw in query_lower for kw in ['connections', 'active sessions', 'who is connected', 'connected users']):
            return {
                'type': 'connections',
                'explanation': 'Show active database connections'
            }
        
        if any(kw in query_lower for kw in ['running queries', 'active queries', 'current queries']):
            return {
                'type': 'active_queries',
                'explanation': 'Show currently running queries'
            }
        
        # Stats and monitoring
        if any(kw in query_lower for kw in ['statistics', 'stats', 'table stats']):
            return {
                'type': 'statistics',
                'explanation': 'Show database statistics'
            }
        
        # Data queries
        if query_lower.startswith(('select', 'show me', 'get', 'find', 'list all')):
            return {
                'type': 'data_query',
                'explanation': 'Retrieve data from database'
            }
        
        # Modification queries
        if query_lower.startswith(('update', 'delete', 'insert', 'create', 'alter', 'drop')):
            return {
                'type': 'modification',
                'explanation': 'Modify database structure or data'
            }
        
        return {
            'type': 'unknown',
            'explanation': 'General database query'
        }
    
    def _generate_sql(self, query: str, intent: Dict, schema: str) -> Optional[str]:
        """Generate SQL based on intent and schema context"""
        intent_type = intent['type']
        
        # Pre-defined safe queries
        if intent_type == 'list_tables':
            return """SELECT 
    schemaname,
    tablename,
    tableowner
FROM pg_tables 
WHERE schemaname = 'public' 
ORDER BY tablename;"""
        
        elif intent_type == 'describe_table':
            table = intent.get('table') or self._extract_table_name(query.lower())
            if table:
                return f"""SELECT 
    column_name,
    data_type,
    character_maximum_length,
    is_nullable,
    column_default
FROM information_schema.columns 
WHERE table_schema = 'public' 
AND table_name = '{table}'
ORDER BY ordinal_position;"""
        
        elif intent_type == 'list_indexes':
            return """SELECT 
    schemaname,
    tablename,
    indexname,
    indexdef
FROM pg_indexes 
WHERE schemaname = 'public' 
ORDER BY tablename, indexname;"""
        
        elif intent_type == 'foreign_keys':
            return """SELECT
    tc.table_name AS from_table,
    kcu.column_name AS from_column,
    ccu.table_name AS to_table,
    ccu.column_name AS to_column,
    tc.constraint_name
FROM information_schema.table_constraints AS tc
JOIN information_schema.key_column_usage AS kcu
    ON tc.constraint_name = kcu.constraint_name
    AND tc.table_schema = kcu.table_schema
JOIN information_schema.constraint_column_usage AS ccu
    ON ccu.constraint_name = tc.constraint_name
    AND ccu.table_schema = tc.table_schema
WHERE tc.constraint_type = 'FOREIGN KEY'
AND tc.table_schema = 'public'
ORDER BY tc.table_name, tc.constraint_name;"""
        
        elif intent_type == 'table_sizes':
            return """SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS total_size,
    pg_size_pretty(pg_relation_size(schemaname||'.'||tablename)) AS table_size,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename) - pg_relation_size(schemaname||'.'||tablename)) AS indexes_size,
    pg_total_relation_size(schemaname||'.'||tablename) AS bytes
FROM pg_tables 
WHERE schemaname = 'public' 
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;"""
        
        elif intent_type == 'database_size':
            return """SELECT 
    current_database() AS database_name,
    pg_size_pretty(pg_database_size(current_database())) AS size;"""
        
        elif intent_type == 'row_counts':
            return """SELECT 
    schemaname,
    relname AS table_name,
    n_live_tup AS row_count,
    n_dead_tup AS dead_rows
FROM pg_stat_user_tables 
WHERE schemaname = 'public' 
ORDER BY n_live_tup DESC;"""
        
        elif intent_type == 'connections':
            return """SELECT 
    datname AS database,
    usename AS user,
    application_name,
    client_addr,
    state,
    COUNT(*) AS connection_count
FROM pg_stat_activity 
WHERE datname = current_database()
GROUP BY datname, usename, application_name, client_addr, state
ORDER BY connection_count DESC;"""
        
        elif intent_type == 'active_queries':
            return """SELECT 
    pid,
    usename AS user,
    datname AS database,
    state,
    query_start,
    LEFT(query, 100) AS query_preview
FROM pg_stat_activity 
WHERE state = 'active'
AND query NOT LIKE '%pg_stat_activity%'
ORDER BY query_start;"""
        
        elif intent_type == 'statistics':
            return """SELECT 
    schemaname,
    relname AS table_name,
    seq_scan AS sequential_scans,
    seq_tup_read AS rows_read_seq,
    idx_scan AS index_scans,
    idx_tup_fetch AS rows_fetched_idx,
    n_tup_ins AS inserts,
    n_tup_upd AS updates,
    n_tup_del AS deletes
FROM pg_stat_user_tables 
WHERE schemaname = 'public' 
ORDER BY relname;"""
        
        elif intent_type == 'data_query':
            # Try to construct a SELECT query from natural language
            return self._construct_select_query(query, schema)
        
        return None
    
    def _construct_select_query(self, query: str, schema: str) -> Optional[str]:
        """Construct SELECT query from natural language"""
        query_lower = query.lower()
        
        # Extract table name
        tables = self._extract_table_names_from_schema(schema)
        table = None
        
        for t in tables:
            if t.lower() in query_lower:
                table = t
                break
        
        if not table:
            return None
        
        # Build basic SELECT
        sql = f"SELECT * FROM {table}"
        
        # Add WHERE clause if conditions mentioned
        if any(kw in query_lower for kw in ['where', 'with', 'having']):
            sql += "\n-- Add WHERE clause as needed"
        
        # Add LIMIT for safety
        if 'limit' not in query_lower and 'all' not in query_lower:
            sql += "\nLIMIT 100"
        
        sql += ";"
        return sql
    
    def _analyze_safety(self, sql: str) -> Dict[str, Any]:
        """Analyze SQL query safety level"""
        sql_upper = sql.upper().strip()
        
        # Check for dangerous operations
        if any(kw in sql_upper for kw in ['DROP', 'TRUNCATE']):
            return {
                'level': 'dangerous',
                'recommendation': '🛑 DANGEROUS: This will permanently delete data or structure. Triple-check before executing!',
                'warnings': 'This operation cannot be undone. Make sure you have a backup.'
            }
        
        # Check for modifications
        if any(kw in sql_upper for kw in ['DELETE', 'UPDATE', 'INSERT', 'ALTER', 'CREATE']):
            return {
                'level': 'modify',
                'recommendation': '⚠️ CAUTION: This will modify data or structure. Review carefully before executing.',
                'warnings': 'Ensure you have reviewed the impact of this change.'
            }
        
        # Safe read-only queries
        if sql_upper.startswith(('SELECT', 'SHOW', 'WITH')):
            return {
                'level': 'safe',
                'recommendation': '✅ SAFE: Read-only query. Safe to execute.',
                'warnings': None
            }
        
        return {
            'level': 'unknown',
            'recommendation': '❓ UNKNOWN: Unable to determine query type. Proceed with caution.',
            'warnings': 'Review the query carefully before executing.'
        }
    
    def _extract_table_name(self, query: str) -> Optional[str]:
        """Extract table name from query"""
        # Look for patterns like "table_name", "in table_name", "from table_name"
        patterns = [
            r'(?:table|from|in|for|of)\s+["\'`]?(\w+)["\'`]?',
            r'["\'`](\w+)["\'`]\s+table',
            r'describe\s+(\w+)',
            r'columns?\s+(?:in|of|for)\s+(\w+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, query)
            if match:
                table_name = match.group(1)
                # Filter out keywords
                if table_name not in ['table', 'from', 'in', 'for', 'of', 'the', 'a', 'an']:
                    return table_name
        
        return None
    
    def _extract_table_names_from_schema(self, schema: str) -> list:
        """Extract table names from schema context"""
        tables = []
        for line in schema.split('\n'):
            if 'Table:' in line:
                parts = line.split('Table:')
                if len(parts) > 1:
                    table_name = parts[1].split()[0].strip()
                    tables.append(table_name)
        return tables
    
    def _get_suggestions(self, failed_query: str) -> list:
        """Provide helpful suggestions when query fails"""
        return [
            "Try: 'Show all tables'",
            "Try: 'Show table sizes'",
            "Try: 'List all indexes'",
            "Try: 'Describe table actor'",
            "Try: 'Show database size'",
            "Try: 'Show active connections'",
            "Try: 'Show row counts'",
            "Try: 'Show foreign keys'"
        ]


# # backend/agents/db_admin.py
# from crewai import Agent, Crew, Task
# from backend.config import settings
# from backend.database.postgres_handler import PostgreSQLHandler
# from backend.database.schema_extractor import SchemaExtractor

# class DBAdminAgent:
#     """Agent 3: Independent database administration assistant"""
    
#     def __init__(self, db_name: str):
#         self.db_name = db_name
#         self.db_handler = PostgreSQLHandler(db_name)
#         self.schema_extractor = SchemaExtractor(db_name)
        
#         # Get fresh schema
#         schema = self.schema_extractor.extract_schema()
        
#         self.agent = Agent(
#             role='PostgreSQL Database Administrator',
#             goal='Assist with database administration tasks through natural language commands',
#             backstory=f"""You are a senior PostgreSQL DBA with expertise in:
#             - Schema management (CREATE, ALTER, DROP operations)
#             - Index optimization and creation
#             - Query performance analysis
#             - User and permission management
#             - Database maintenance (VACUUM, ANALYZE, REINDEX)
#             - Backup and restore operations
#             - Monitoring and diagnostics
            
#             DATABASE: {db_name}
            
#             CURRENT SCHEMA:
#             {schema}
            
#             OPERATIONAL MODES:
#             1. INFORMATIONAL: Provide database statistics, schema info, query explanations
#             2. MAINTENANCE: Generate SQL for indexes, vacuum, analyze operations
#             3. SCHEMA MODIFICATION: Generate DDL for tables, columns, constraints
#             4. DIAGNOSTIC: Analyze performance, locks, connections
            
#             SAFETY PROTOCOLS:
#             - ALWAYS confirm destructive operations (DROP, TRUNCATE)
#             - Validate schema changes against existing structure
#             - Warn about operations that may impact performance
#             - Provide rollback strategies for risky operations
            
#             OUTPUT STYLE:
#             - For read-only operations: Execute and show results
#             - For modifications: Generate SQL and explain impact
#             - For complex tasks: Provide step-by-step guidance
#             - Always explain what the command does""",
#             verbose=settings.VERBOSE,
#             allow_delegation=False,
#             llm=settings.get_llm()
#         )

#     def process_command(self, command: str) -> dict:
#         """Process admin command and return results"""
#         task = Task(
#             description=f"""
#             ADMIN COMMAND:
#             "{command}"
            
#             DATABASE: {self.db_name}
            
#             YOUR TASK:
#             1. Understand the administrative intent
#             2. Determine if this is:
#                - Informational query (show tables, describe table, stats)
#                - Maintenance task (vacuum, analyze, reindex)
#                - Schema modification (create table, add column, create index)
#                - Diagnostic query (check locks, slow queries, connections)
            
#             3. Based on type:
#                - INFORMATIONAL: Generate and execute SELECT query
#                - MAINTENANCE/MODIFICATION: Generate SQL with explanation
#                - DIAGNOSTIC: Generate appropriate system query
            
#             4. Provide clear output:
#                - SQL query to execute (if applicable)
#                - Explanation of what it does
#                - Expected results or impact
#                - Any warnings or prerequisites
            
#             EXAMPLES:
#             Command: "show all tables"
#             → SELECT query on information_schema.tables
            
#             Command: "create index on users email column"
#             → CREATE INDEX statement with explanation
            
#             Command: "show table sizes"
#             → Query pg_class for table sizes
            
#             Command: "analyze performance of users table"
#             → EXPLAIN ANALYZE or table statistics query
            
#             OUTPUT FORMAT:
#             ACTION: [what will be done]
#             SQL: [SQL query if applicable]
#             EXPLANATION: [what this does and why]
#             WARNINGS: [any risks or important notes]
#             """,
#             expected_output="Admin action with SQL and explanation",
#             agent=self.agent
#         )
        
#         crew = Crew(
#             agents=[self.agent],
#             tasks=[task],
#             verbose=settings.VERBOSE
#         )
        
#         try:
#             result = str(crew.kickoff())
            
#             # Parse the response
#             sql = self._extract_sql(result)
#             action = self._extract_section(result, "ACTION")
#             explanation = self._extract_section(result, "EXPLANATION")
#             warnings = self._extract_section(result, "WARNINGS")
            
#             # If SQL is present and looks safe to execute, run it
#             execution_result = None
#             if sql and self._is_safe_to_auto_execute(sql):
#                 execution_result = self.db_handler.execute(sql)
            
#             return {
#                 "success": True,
#                 "action": action,
#                 "sql": sql,
#                 "explanation": explanation,
#                 "warnings": warnings,
#                 "execution_result": execution_result,
#                 "raw_response": result
#             }
#         except Exception as e:
#             return {
#                 "success": False,
#                 "error": f"Admin command processing failed: {str(e)}"
#             }

#     def _extract_sql(self, text: str) -> str:
#         """Extract SQL from agent response"""
#         if "SQL:" in text:
#             sql_part = text.split("SQL:")[1].split("EXPLANATION:")[0]
#             return sql_part.strip().strip('`').strip('"').strip("'")
#         return None

#     def _extract_section(self, text: str, section: str) -> str:
#         """Extract specific section from response"""
#         if f"{section}:" in text:
#             parts = text.split(f"{section}:")[1]
#             # Get until next section or end
#             for next_section in ["ACTION:", "SQL:", "EXPLANATION:", "WARNINGS:"]:
#                 if next_section in parts and next_section != f"{section}:":
#                     parts = parts.split(next_section)[0]
#             return parts.strip()
#         return None

#     def _is_safe_to_auto_execute(self, sql: str) -> bool:
#         """Check if SQL is safe to execute automatically"""
#         sql_upper = sql.upper().strip()
        
#         # Only auto-execute SELECT queries
#         safe_starts = ["SELECT", "SHOW", "DESCRIBE", "EXPLAIN"]
        
#         # Never auto-execute these
#         dangerous_keywords = ["DROP", "DELETE", "TRUNCATE", "UPDATE", "INSERT", 
#                              "ALTER", "CREATE", "GRANT", "REVOKE"]
        
#         starts_safe = any(sql_upper.startswith(cmd) for cmd in safe_starts)
#         has_dangerous = any(keyword in sql_upper for keyword in dangerous_keywords)
        
#         return starts_safe and not has_dangerous