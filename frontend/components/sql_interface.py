# frontend/components/sql_interface.py
import streamlit as st
import requests
import pandas as pd
from typing import Dict, Any, Optional

class SQLInterface:
    """Component for SQL query generation and execution interface"""
    
    def __init__(self, api_base_url: str):
        self.api_base_url = api_base_url
    
    def render(self, db_name: str):
        """Render the SQL interface"""
        if not db_name:
            st.warning("⚠️ Please enter a database name in the sidebar")
            return
        
        st.header("🔍 Natural Language to SQL")
        st.markdown("*Agent 1 (Generator) + Agent 2 (Executor with Error Recovery)*")
        
        # Add helpful examples
        with st.expander("💡 Example Queries", expanded=False):
            st.markdown("""
            **Basic Queries:**
            - Show me all users
            - List the last 10 orders
            - Count total products by category
            
            **Complex Queries:**
            - Show users who registered in the last 30 days
            - Find top 5 customers by total order value
            - List products with inventory below 10 units
            
            **Aggregate Queries:**
            - Calculate average order value per month
            - Show sales trends for the last quarter
            - Count active users by registration date
            """)
        
        # Natural language input
        nl_query = st.text_area(
            "Enter your question in natural language:",
            height=120,
            placeholder="Example: Show me all active users who have placed orders in the last 30 days",
            key="nl_query_input"
        )
        
        # Generation controls
        col1, col2, col3 = st.columns([2, 2, 6])
        with col1:
            generate_btn = st.button("🔄 Generate SQL", key="gen_sql_btn", type="primary")
        with col2:
            if st.button("🗑️ Clear", key="clear_sql"):
                st.session_state.pop("generated_sql", None)
                st.session_state.pop("execution_result", None)
                st.rerun()
        
        # Generate SQL
        if generate_btn and nl_query.strip():
            with st.spinner("🤖 Agent 1 is analyzing your query and generating SQL..."):
                result = self._generate_sql(db_name, nl_query)
            
            if result.get("success"):
                st.session_state["generated_sql"] = result.get("sql")
                st.session_state["query_type"] = result.get("query_type")
                st.session_state["sql_warning"] = result.get("warning")
            else:
                st.error(f"❌ Generation failed: {result.get('error')}")
                return
        
        # Display generated SQL
        if "generated_sql" in st.session_state:
            self._render_generated_sql(db_name, st.session_state["generated_sql"])
    
    def _generate_sql(self, db_name: str, nl_query: str) -> Dict[str, Any]:
        """Call SQL generation API"""
        try:
            response = requests.post(
                f"{self.api_base_url}/query/generate",
                json={"db_name": db_name, "query": nl_query},
                timeout=60
            )
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"success": False, "error": str(e)}
    
    def _render_generated_sql(self, db_name: str, sql: str):
        """Render the generated SQL with execution options"""
        st.markdown("---")
        st.markdown("### 📝 Generated SQL Query")
        
        # Display warning if exists
        if st.session_state.get("sql_warning"):
            st.markdown(
                f'<div style="padding: 1rem; border-radius: 0.5rem; background-color: #fff3cd; '
                f'border: 1px solid #ffeeba; color: #856404;">'
                f'{st.session_state["sql_warning"]}</div>',
                unsafe_allow_html=True
            )
        
        # Display SQL with copy button
        st.code(sql, language="sql")
        
        # Execution section
        st.markdown("### ▶️ Execute Query")
        
        col1, col2 = st.columns([3, 7])
        with col1:
            confirm = st.checkbox(
                "⚠️ I confirm execution",
                key="confirm_exec_checkbox",
                help="Required to execute the query"
            )
        
        with col2:
            exec_btn = st.button(
                "▶️ Execute with Agent 2",
                key="exec_sql_btn",
                type="primary",
                disabled=not confirm
            )
        
        if exec_btn and confirm:
            with st.spinner("🤖 Agent 2 is executing and monitoring the query..."):
                result = self._execute_sql(db_name, sql, confirm)
            
            st.session_state["execution_result"] = result
        
        # Display execution results
        if "execution_result" in st.session_state:
            self._render_execution_result(st.session_state["execution_result"])
    
    def _execute_sql(self, db_name: str, sql: str, confirm: bool) -> Dict[str, Any]:
        """Call SQL execution API"""
        try:
            response = requests.post(
                f"{self.api_base_url}/query/execute",
                json={"db_name": db_name, "sql": sql, "confirm": confirm},
                timeout=90
            )
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"success": False, "error": str(e)}
    
    def _render_execution_result(self, result: Dict[str, Any]):
        """Render execution results"""
        st.markdown("---")
        st.markdown("### 📊 Execution Results")
        
        if result.get("success"):
            # Success message
            if result.get("data"):
                st.success(f"✅ Query executed successfully! ({result.get('row_count', 0)} rows returned)")
                
                # Display data as DataFrame
                df = pd.DataFrame(result["data"])
                
                # Add download button
                csv = df.to_csv(index=False)
                st.download_button(
                    label="📥 Download as CSV",
                    data=csv,
                    file_name="query_results.csv",
                    mime="text/csv",
                    key="download_csv"
                )
                
                # Display dataframe
                st.dataframe(df, use_container_width=True, height=400)
                
                # Display statistics
                with st.expander("📈 Data Statistics", expanded=False):
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Rows", len(df))
                    with col2:
                        st.metric("Columns", len(df.columns))
                    with col3:
                        st.metric("Memory", f"{df.memory_usage(deep=True).sum() / 1024:.2f} KB")
                    
                    st.markdown("**Column Info:**")
                    st.dataframe(df.dtypes.to_frame(name="Type"), use_container_width=True)
            
            elif result.get("affected_rows") is not None:
                st.success(f"✅ Query executed successfully! {result.get('affected_rows')} rows affected")
            
            elif result.get("message"):
                st.info(result["message"])
        
        else:
            # Error handling
            st.error(f"❌ Execution failed")
            
            error_msg = result.get("error", "Unknown error")
            st.code(error_msg, language="text")
            
            # Show error analysis if available
            if result.get("error_analysis"):
                with st.expander("🔍 Agent 2's Error Analysis & Recovery Attempt", expanded=True):
                    st.markdown("**Error Analysis:**")
                    st.text(result["error_analysis"])
                    
                    if result.get("suggestion"):
                        st.markdown("**Suggestion:**")
                        st.info(result["suggestion"])
            
            # Show retry SQL if available
            if result.get("retry_sql"):
                st.markdown("**Agent 2 attempted this corrected SQL:**")
                st.code(result["retry_sql"], language="sql")