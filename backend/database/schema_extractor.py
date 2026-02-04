# backend/database/schema_extractor.py
import psycopg2
from typing import List, Dict, Any, Tuple, Optional
from backend.config import settings

class SchemaExtractor:
    """
    Extracts and formats database schema information from PostgreSQL.
    Provides detailed table structures, relationships, and constraints.
    """
    
    def __init__(self, db_name: str):
        """
        Initialize schema extractor for a specific database.
        
        Args:
            db_name: Name of the PostgreSQL database
        """
        self.db_name = db_name
        self.conn_params = {
            "host": settings.DB_HOST,
            "port": settings.DB_PORT,
            "dbname": db_name,
            "user": settings.DB_USER,
            "password": settings.DB_PASSWORD
        }
    
    def get_all_tables(self) -> List[str]:
        """
        Get list of all tables in the public schema.
        
        Returns:
            List of table names sorted alphabetically
        """
        try:
            with psycopg2.connect(**self.conn_params) as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT table_name 
                        FROM information_schema.tables 
                        WHERE table_schema = 'public' 
                        AND table_type = 'BASE TABLE'
                        ORDER BY table_name;
                    """)
                    return [row[0] for row in cur.fetchall()]
        except psycopg2.Error as e:
            print(f"Error fetching tables: {e}")
            return []
        except Exception as e:
            print(f"Unexpected error: {e}")
            return []
    
    def get_table_row_count(self, table_name: str) -> int:
        """
        Get approximate row count for a table.
        
        Args:
            table_name: Name of the table
            
        Returns:
            Approximate number of rows
        """
        try:
            with psycopg2.connect(**self.conn_params) as conn:
                with conn.cursor() as cur:
                    # Use pg_class for fast approximate count
                    cur.execute(f"""
                        SELECT reltuples::bigint 
                        FROM pg_class 
                        WHERE relname = %s;
                    """, (table_name,))
                    result = cur.fetchone()
                    return int(result[0]) if result else 0
        except:
            return 0
    
    def get_primary_keys(self, table_name: str) -> List[str]:
        """
        Get primary key columns for a table.
        
        Args:
            table_name: Name of the table
            
        Returns:
            List of primary key column names
        """
        try:
            with psycopg2.connect(**self.conn_params) as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT kcu.column_name
                        FROM information_schema.table_constraints tc
                        JOIN information_schema.key_column_usage kcu
                            ON tc.constraint_name = kcu.constraint_name
                            AND tc.table_schema = kcu.table_schema
                        WHERE tc.table_name = %s 
                        AND tc.table_schema = 'public'
                        AND tc.constraint_type = 'PRIMARY KEY'
                        ORDER BY kcu.ordinal_position;
                    """, (table_name,))
                    return [row[0] for row in cur.fetchall()]
        except psycopg2.Error as e:
            print(f"Error fetching primary keys for {table_name}: {e}")
            return []
    
    def get_foreign_keys(self, table_name: str) -> Dict[str, Tuple[str, str]]:
        """
        Get foreign key relationships for a table.
        
        Args:
            table_name: Name of the table
            
        Returns:
            Dictionary mapping column names to (referenced_table, referenced_column)
        """
        try:
            with psycopg2.connect(**self.conn_params) as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT 
                            kcu.column_name,
                            ccu.table_name AS foreign_table,
                            ccu.column_name AS foreign_column,
                            rc.update_rule,
                            rc.delete_rule
                        FROM information_schema.table_constraints tc
                        JOIN information_schema.key_column_usage kcu
                            ON tc.constraint_name = kcu.constraint_name
                            AND tc.table_schema = kcu.table_schema
                        JOIN information_schema.constraint_column_usage ccu
                            ON ccu.constraint_name = tc.constraint_name
                            AND ccu.table_schema = tc.table_schema
                        JOIN information_schema.referential_constraints rc
                            ON tc.constraint_name = rc.constraint_name
                            AND tc.table_schema = rc.constraint_schema
                        WHERE tc.table_name = %s 
                        AND tc.table_schema = 'public'
                        AND tc.constraint_type = 'FOREIGN KEY'
                        ORDER BY kcu.ordinal_position;
                    """, (table_name,))
                    
                    result = {}
                    for col, ref_table, ref_col, update_rule, delete_rule in cur.fetchall():
                        result[col] = (ref_table, ref_col, update_rule, delete_rule)
                    return result
        except psycopg2.Error as e:
            print(f"Error fetching foreign keys for {table_name}: {e}")
            return {}
    
    def get_unique_constraints(self, table_name: str) -> List[List[str]]:
        """
        Get unique constraints for a table.
        
        Args:
            table_name: Name of the table
            
        Returns:
            List of unique constraint column groups
        """
        try:
            with psycopg2.connect(**self.conn_params) as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT 
                            tc.constraint_name,
                            array_agg(kcu.column_name ORDER BY kcu.ordinal_position) as columns
                        FROM information_schema.table_constraints tc
                        JOIN information_schema.key_column_usage kcu
                            ON tc.constraint_name = kcu.constraint_name
                            AND tc.table_schema = kcu.table_schema
                        WHERE tc.table_name = %s 
                        AND tc.table_schema = 'public'
                        AND tc.constraint_type = 'UNIQUE'
                        GROUP BY tc.constraint_name;
                    """, (table_name,))
                    return [row[1] for row in cur.fetchall()]
        except psycopg2.Error as e:
            print(f"Error fetching unique constraints for {table_name}: {e}")
            return []
    
    def get_indexes(self, table_name: str) -> List[Dict[str, Any]]:
        """
        Get indexes for a table.
        
        Args:
            table_name: Name of the table
            
        Returns:
            List of index information dictionaries
        """
        try:
            with psycopg2.connect(**self.conn_params) as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT 
                            i.relname as index_name,
                            a.attname as column_name,
                            ix.indisunique as is_unique,
                            ix.indisprimary as is_primary,
                            am.amname as index_type
                        FROM pg_class t
                        JOIN pg_index ix ON t.oid = ix.indrelid
                        JOIN pg_class i ON i.oid = ix.indexrelid
                        JOIN pg_attribute a ON a.attrelid = t.oid AND a.attnum = ANY(ix.indkey)
                        JOIN pg_am am ON i.relam = am.oid
                        WHERE t.relname = %s
                        AND t.relkind = 'r'
                        ORDER BY i.relname, a.attnum;
                    """, (table_name,))
                    
                    indexes = {}
                    for idx_name, col_name, is_unique, is_primary, idx_type in cur.fetchall():
                        if idx_name not in indexes:
                            indexes[idx_name] = {
                                'name': idx_name,
                                'columns': [],
                                'unique': is_unique,
                                'primary': is_primary,
                                'type': idx_type
                            }
                        indexes[idx_name]['columns'].append(col_name)
                    
                    return list(indexes.values())
        except psycopg2.Error as e:
            print(f"Error fetching indexes for {table_name}: {e}")
            return []
    
    def get_column_info(self, table_name: str) -> List[Dict[str, Any]]:
        """
        Get detailed column information for a table.
        
        Args:
            table_name: Name of the table
            
        Returns:
            List of column information dictionaries
        """
        try:
            with psycopg2.connect(**self.conn_params) as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT 
                            column_name,
                            data_type,
                            character_maximum_length,
                            numeric_precision,
                            numeric_scale,
                            is_nullable,
                            column_default,
                            udt_name
                        FROM information_schema.columns
                        WHERE table_name = %s 
                        AND table_schema = 'public'
                        ORDER BY ordinal_position;
                    """, (table_name,))
                    
                    columns = []
                    for row in cur.fetchall():
                        col_info = {
                            'name': row[0],
                            'data_type': row[1],
                            'max_length': row[2],
                            'precision': row[3],
                            'scale': row[4],
                            'nullable': row[5] == 'YES',
                            'default': row[6],
                            'udt_name': row[7]
                        }
                        columns.append(col_info)
                    
                    return columns
        except psycopg2.Error as e:
            print(f"Error fetching columns for {table_name}: {e}")
            return []
    
    def get_table_details(self, table_name: str) -> Dict[str, Any]:
        """
        Get comprehensive details for a table.
        
        Args:
            table_name: Name of the table
            
        Returns:
            Dictionary with complete table information
        """
        pk_columns = self.get_primary_keys(table_name)
        fk_columns = self.get_foreign_keys(table_name)
        unique_constraints = self.get_unique_constraints(table_name)
        indexes = self.get_indexes(table_name)
        columns = self.get_column_info(table_name)
        row_count = self.get_table_row_count(table_name)
        
        # Enrich column information with constraints
        for col in columns:
            col['is_primary_key'] = col['name'] in pk_columns
            col['is_foreign_key'] = col['name'] in fk_columns
            
            if col['is_foreign_key']:
                fk_info = fk_columns[col['name']]
                col['references'] = f"{fk_info[0]}.{fk_info[1]}"
                col['on_update'] = fk_info[2]
                col['on_delete'] = fk_info[3]
            
            # Check if part of unique constraint
            col['is_unique'] = any(col['name'] in uc for uc in unique_constraints)
        
        return {
            'table_name': table_name,
            'row_count': row_count,
            'columns': columns,
            'primary_keys': pk_columns,
            'foreign_keys': fk_columns,
            'unique_constraints': unique_constraints,
            'indexes': indexes
        }
    
    def format_data_type(self, col_info: Dict[str, Any]) -> str:
        """
        Format column data type with additional details.
        
        Args:
            col_info: Column information dictionary
            
        Returns:
            Formatted data type string
        """
        dtype = col_info['data_type']
        
        # Map verbose types to common names
        type_mapping = {
            'character varying': 'varchar',
            'character': 'char',
            'timestamp without time zone': 'timestamp',
            'timestamp with time zone': 'timestamptz',
            'double precision': 'float8',
            'integer': 'int',
            'bigint': 'bigint',
            'smallint': 'smallint'
        }
        
        dtype = type_mapping.get(dtype, dtype)
        
        # Add length/precision info
        if col_info['max_length']:
            dtype += f"({col_info['max_length']})"
        elif col_info['precision']:
            if col_info['scale']:
                dtype += f"({col_info['precision']},{col_info['scale']})"
            else:
                dtype += f"({col_info['precision']})"
        
        return dtype
    
    def extract_schema(self) -> str:
        """
        Extract complete database schema as a formatted string.
        
        Returns:
            Formatted schema information for all tables
        """
        tables = self.get_all_tables()
        
        if not tables:
            return f"Database '{self.db_name}': No tables found in public schema."
        
        schema_lines = []
        schema_lines.append(f"DATABASE: '{self.db_name}'")
        schema_lines.append(f"TABLES: {len(tables)}")
        schema_lines.append("=" * 80)
        schema_lines.append("")
        
        for table in tables:
            details = self.get_table_details(table)
            
            # Table header
            schema_lines.append(f"TABLE: {table}")
            if details['row_count'] > 0:
                schema_lines.append(f"Rows: ~{details['row_count']:,}")
            schema_lines.append("-" * 80)
            
            # Columns
            schema_lines.append("COLUMNS:")
            for col in details['columns']:
                # Format column line
                dtype = self.format_data_type(col)
                nullable = "NULL" if col['nullable'] else "NOT NULL"
                
                # Build constraints string
                constraints = []
                if col['is_primary_key']:
                    constraints.append("PRIMARY KEY")
                if col['is_foreign_key']:
                    constraints.append(f"FK → {col['references']}")
                if col['is_unique'] and not col['is_primary_key']:
                    constraints.append("UNIQUE")
                
                constraint_str = f" [{', '.join(constraints)}]" if constraints else ""
                
                # Default value
                default_str = f" DEFAULT {col['default']}" if col['default'] else ""
                
                col_line = f"  • {col['name']}: {dtype} {nullable}{default_str}{constraint_str}"
                schema_lines.append(col_line)
            
            # Indexes (non-primary)
            non_pk_indexes = [idx for idx in details['indexes'] if not idx['primary']]
            if non_pk_indexes:
                schema_lines.append("")
                schema_lines.append("INDEXES:")
                for idx in non_pk_indexes:
                    idx_type = "UNIQUE" if idx['unique'] else "INDEX"
                    cols = ", ".join(idx['columns'])
                    schema_lines.append(f"  • {idx['name']}: {idx_type} ({cols}) [{idx['type']}]")
            
            schema_lines.append("")
        
        return "\n".join(schema_lines)
    
    def extract_schema_compact(self) -> str:
        """
        Extract database schema in compact format (one line per table).
        Useful for LLM context when full schema is too verbose.
        
        Returns:
            Compact schema information
        """
        tables = self.get_all_tables()
        
        if not tables:
            return f"Database '{self.db_name}': No tables found."
        
        schema_lines = [f"Database '{self.db_name}' - {len(tables)} tables:"]
        
        for table in tables:
            details = self.get_table_details(table)
            
            # Build compact column list
            col_strs = []
            for col in details['columns']:
                dtype = self.format_data_type(col)
                
                # Add constraint markers
                markers = []
                if col['is_primary_key']:
                    markers.append("PK")
                if col['is_foreign_key']:
                    ref_table = col['references'].split('.')[0]
                    markers.append(f"FK→{ref_table}")
                
                marker_str = f" [{','.join(markers)}]" if markers else ""
                col_strs.append(f"{col['name']}:{dtype}{marker_str}")
            
            table_line = f"  • {table}: {', '.join(col_strs)}"
            schema_lines.append(table_line)
        
        return "\n".join(schema_lines)
    
    def get_table_relationships(self) -> List[Dict[str, str]]:
        """
        Get all foreign key relationships in the database.
        
        Returns:
            List of relationship dictionaries
        """
        tables = self.get_all_tables()
        relationships = []
        
        for table in tables:
            fk_columns = self.get_foreign_keys(table)
            
            for col, (ref_table, ref_col, update_rule, delete_rule) in fk_columns.items():
                relationships.append({
                    'from_table': table,
                    'from_column': col,
                    'to_table': ref_table,
                    'to_column': ref_col,
                    'on_update': update_rule,
                    'on_delete': delete_rule
                })
        
        return relationships
    
    def validate_connection(self) -> Tuple[bool, Optional[str]]:
        """
        Validate database connection.
        
        Returns:
            Tuple of (success: bool, error_message: Optional[str])
        """
        try:
            with psycopg2.connect(**self.conn_params) as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT version();")
                    version = cur.fetchone()[0]
                    return True, None
        except psycopg2.Error as e:
            return False, str(e)
        except Exception as e:
            return False, f"Unexpected error: {str(e)}"