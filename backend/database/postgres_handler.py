# backend/database/postgres_handler.py
import psycopg2
from typing import Dict, Any, List
from backend.config import settings
import logging

logger = logging.getLogger(__name__)

class PostgreSQLHandler:
    def __init__(self, db_name: str):
        self.conn_params = {
            "host": settings.DB_HOST,
            "port": settings.DB_PORT,
            "dbname": db_name,
            "user": settings.DB_USER,
            "password": settings.DB_PASSWORD
        }
        self.db_name = db_name
        
        logger.info(f"PostgreSQLHandler initialized for database: {db_name}")
        logger.debug(f"Connection params: host={settings.DB_HOST}, port={settings.DB_PORT}, user={settings.DB_USER}")

    def execute(self, sql: str) -> Dict[str, Any]:
        """Execute SQL query and return structured results"""
        try:
            logger.info(f"Executing SQL: {sql[:100]}...")
            
            with psycopg2.connect(**self.conn_params) as conn:
                with conn.cursor() as cur:
                    cur.execute(sql)
                    
                    sql_upper = sql.strip().upper()
                    
                    if sql_upper.startswith('SELECT') or sql_upper.startswith('WITH'):
                        columns = [desc[0] for desc in cur.description]
                        rows = cur.fetchall()
                        data = [dict(zip(columns, row)) for row in rows]
                        
                        logger.info(f"Query returned {len(rows)} rows")
                        return {
                            "success": True,
                            "data": data,
                            "columns": columns,
                            "row_count": len(rows)
                        }
                    else:
                        conn.commit()
                        logger.info(f"Query affected {cur.rowcount} rows")
                        return {
                            "success": True,
                            "affected_rows": cur.rowcount,
                            "message": f"Query executed successfully. {cur.rowcount} rows affected."
                        }
        except psycopg2.OperationalError as e:
            error_msg = str(e)
            logger.error(f"Operational error: {error_msg}")
            return {
                "success": False,
                "error": error_msg,
                "error_type": "OperationalError"
            }
        except psycopg2.ProgrammingError as e:
            error_msg = str(e)
            logger.error(f"Programming error: {error_msg}")
            return {
                "success": False,
                "error": error_msg,
                "error_type": "ProgrammingError"
            }
        except psycopg2.Error as e:
            error_msg = str(e)
            logger.error(f"Database error: {error_msg}")
            return {
                "success": False,
                "error": error_msg,
                "error_type": type(e).__name__
            }
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg
            }

    def test_connection(self) -> bool:
        """Test database connection"""
        try:
            logger.info(f"Testing connection to database: {self.db_name}")
            logger.debug(f"Connection parameters: {dict(self.conn_params, password='***')}")
            
            with psycopg2.connect(**self.conn_params) as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1")
                    result = cur.fetchone()
                    
                    if result and result[0] == 1:
                        logger.info(f"Connection test successful for {self.db_name}")
                        return True
                    else:
                        logger.error(f"Connection test failed: unexpected result")
                        return False
                        
        except psycopg2.OperationalError as e:
            logger.error(f"Connection failed (OperationalError): {str(e)}")
            return False
        except psycopg2.Error as e:
            logger.error(f"Connection failed (DatabaseError): {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Connection failed (Unexpected): {type(e).__name__}: {str(e)}")
            return False
    
    def get_connection_info(self) -> Dict[str, Any]:
        """Get connection information for diagnostics"""
        return {
            "host": self.conn_params["host"],
            "port": self.conn_params["port"],
            "database": self.conn_params["dbname"],
            "user": self.conn_params["user"],
            "password_set": bool(self.conn_params["password"])
        }








# # backend/database/postgres_handler.py
# import psycopg2
# from typing import Dict, Any, List
# from backend.config import settings

# class PostgreSQLHandler:
#     def __init__(self, db_name: str):
#         self.conn_params = {
#             "host": settings.DB_HOST,
#             "port": settings.DB_PORT,
#             "dbname": db_name,
#             "user": settings.DB_USER,
#             "password": settings.DB_PASSWORD
#         }
#         self.db_name = db_name

#     def execute(self, sql: str) -> Dict[str, Any]:
#         """Execute SQL query and return structured results"""
#         try:
#             with psycopg2.connect(**self.conn_params) as conn:
#                 with conn.cursor() as cur:
#                     cur.execute(sql)
                    
#                     sql_upper = sql.strip().upper()
                    
#                     if sql_upper.startswith('SELECT') or sql_upper.startswith('WITH'):
#                         columns = [desc[0] for desc in cur.description]
#                         rows = cur.fetchall()
#                         data = [dict(zip(columns, row)) for row in rows]
                        
#                         return {
#                             "success": True,
#                             "data": data,
#                             "columns": columns,
#                             "row_count": len(rows)
#                         }
#                     else:
#                         conn.commit()
#                         return {
#                             "success": True,
#                             "affected_rows": cur.rowcount,
#                             "message": f"Query executed successfully. {cur.rowcount} rows affected."
#                         }
#         except psycopg2.Error as e:
#             return {
#                 "success": False,
#                 "error": str(e),
#                 "error_type": type(e).__name__
#             }
#         except Exception as e:
#             return {
#                 "success": False,
#                 "error": f"Unexpected error: {str(e)}"
#             }

#     def test_connection(self) -> bool:
#         """Test database connection"""
#         try:
#             with psycopg2.connect(**self.conn_params) as conn:
#                 with conn.cursor() as cur:
#                     cur.execute("SELECT 1")
#                     return True
#         except:
#             return False


# # backend/database/schema_extractor.py
# import psycopg2
# from typing import List, Tuple, Dict
# from backend.config import settings

# class SchemaExtractor:
#     def __init__(self, db_name: str):
#         self.conn_params = {
#             "host": settings.DB_HOST,
#             "port": settings.DB_PORT,
#             "dbname": db_name,
#             "user": settings.DB_USER,
#             "password": settings.DB_PASSWORD
#         }

#     def get_all_tables(self) -> List[str]:
#         """Get all table names"""
#         try:
#             with psycopg2.connect(**self.conn_params) as conn:
#                 with conn.cursor() as cur:
#                     cur.execute("""
#                         SELECT table_name 
#                         FROM information_schema.tables 
#                         WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
#                         ORDER BY table_name;
#                     """)
#                     return [row[0] for row in cur.fetchall()]
#         except Exception as e:
#             return []

#     def get_table_details(self, table_name: str) -> Dict[str, Any]:
#         """Get detailed table information including constraints"""
#         try:
#             with psycopg2.connect(**self.conn_params) as conn:
#                 with conn.cursor() as cur:
#                     # Get primary keys
#                     cur.execute("""
#                         SELECT kcu.column_name
#                         FROM information_schema.table_constraints tc
#                         JOIN information_schema.key_column_usage kcu
#                             ON tc.constraint_name = kcu.constraint_name
#                         WHERE tc.table_name = %s AND tc.constraint_type = 'PRIMARY KEY';
#                     """, (table_name,))
#                     pk_columns = {row[0] for row in cur.fetchall()}

#                     # Get foreign keys
#                     cur.execute("""
#                         SELECT 
#                             kcu.column_name,
#                             ccu.table_name AS foreign_table,
#                             ccu.column_name AS foreign_column
#                         FROM information_schema.table_constraints tc
#                         JOIN information_schema.key_column_usage kcu
#                             ON tc.constraint_name = kcu.constraint_name
#                         JOIN information_schema.constraint_column_usage ccu
#                             ON ccu.constraint_name = tc.constraint_name
#                         WHERE tc.table_name = %s AND tc.constraint_type = 'FOREIGN KEY';
#                     """, (table_name,))
#                     fk_columns = {col: f"{ref_table}.{ref_col}" 
#                                  for col, ref_table, ref_col in cur.fetchall()}

#                     # Get columns
#                     cur.execute("""
#                         SELECT column_name, data_type, is_nullable, column_default
#                         FROM information_schema.columns
#                         WHERE table_name = %s
#                         ORDER BY ordinal_position;
#                     """, (table_name,))
                    
#                     columns = []
#                     for name, dtype, nullable, default in cur.fetchall():
#                         col_info = {
#                             "name": name,
#                             "type": dtype,
#                             "nullable": nullable == "YES",
#                             "default": default
#                         }
#                         if name in pk_columns:
#                             col_info["constraint"] = "PRIMARY KEY"
#                         elif name in fk_columns:
#                             col_info["constraint"] = f"FOREIGN KEY → {fk_columns[name]}"
#                         columns.append(col_info)
                    
#                     return {
#                         "table_name": table_name,
#                         "columns": columns
#                     }
#         except Exception as e:
#             return {"error": str(e)}

#     def extract_schema(self) -> str:
#         """Extract complete database schema as formatted string"""
#         tables = self.get_all_tables()
#         if not tables:
#             return "No tables found in the database."
        
#         schema_lines = ["DATABASE SCHEMA:\n"]
        
#         for table in tables:
#             details = self.get_table_details(table)
#             if "error" in details:
#                 continue
                
#             schema_lines.append(f"\nTable: {table}")
#             schema_lines.append("-" * 60)
            
#             for col in details["columns"]:
#                 constraint = col.get("constraint", "")
#                 constraint_str = f" [{constraint}]" if constraint else ""
#                 nullable_str = "NULL" if col["nullable"] else "NOT NULL"
#                 schema_lines.append(
#                     f"  {col['name']}: {col['type']} {nullable_str}{constraint_str}"
#                 )
        
#         return "\n".join(schema_lines)