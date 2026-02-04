# frontend/components/smart_admin_interface.py
import streamlit as st
import requests
import pandas as pd
from typing import Dict, Any
import json

class AdminInterface:
    """Smart Database Administration Interface with confirmation workflow"""
    
    def __init__(self, api_base_url: str):
        self.api_base_url = api_base_url
    
    def render(self, db_name: str):
        """Render the smart admin interface"""
        if not db_name:
            st.warning("⚠️ Please enter a database name in the sidebar")
            return
        
        st.header("🧠 Smart Database Administrator")
        st.markdown("*AI-powered admin that thinks like an experienced DBA*")
        
        # Show example commands
        self._render_examples()
        
        # Query input
        user_query = st.text_area(
            "What would you like to do? (Describe in plain English)",
            height=100,
            placeholder="Example: Show me all tables and their sizes",
            key="smart_admin_query"
        )
        
        # Generate SQL button
        col1, col2 = st.columns([2, 8])
        with col1:
            generate_btn = st.button("🤖 Generate SQL", type="primary", key="gen_admin_sql")
        with col2:
            if st.button("🔄 Reset", key="reset_btn"):
                self._clear_state()
                st.rerun()
        
        # Process query and generate SQL
        if generate_btn and user_query.strip():
            with st.spinner("🤔 Analyzing your request and generating SQL..."):
                result = self._generate_sql(db_name, user_query)
                st.session_state["pending_sql"] = result
        
        # Display generated SQL and confirmation workflow
        if "pending_sql" in st.session_state:
            self._render_confirmation_workflow(db_name, st.session_state["pending_sql"])
        
        # Display execution results if any
        if "execution_result" in st.session_state:
            self._render_execution_results(st.session_state["execution_result"])
    
    def _render_examples(self):
        """Render example queries"""
        with st.expander("💡 Example Queries You Can Ask", expanded=False):
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("""
                **📋 Schema & Structure:**
                - Show all tables
                - Describe the actor table
                - List all indexes
                - Show foreign key relationships
                
                **📊 Size & Performance:**
                - Show table sizes
                - What's the database size?
                - Show row counts for all tables
                - Show table statistics
                """)
            
            with col2:
                st.markdown("""
                **🔌 Connections & Activity:**
                - Show active connections
                - List running queries
                - Who is connected to the database?
                
                **📈 Monitoring:**
                - Show me tables with most rows
                - Which tables use the most disk space?
                - Show index usage statistics
                """)
    
    def _generate_sql(self, db_name: str, query: str) -> Dict[str, Any]:
        """Call API to generate SQL from natural language"""
        try:
            response = requests.post(
                f"{self.api_base_url}/admin/smart/generate",
                json={"db_name": db_name, "query": query},
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.Timeout:
            return {"success": False, "error": "Request timeout"}
        except requests.exceptions.RequestException as e:
            return {"success": False, "error": f"Request failed: {str(e)}"}
        except json.JSONDecodeError:
            return {"success": False, "error": "Invalid response from server"}
        except Exception as e:
            return {"success": False, "error": f"Unexpected error: {str(e)}"}
    
    def _execute_sql(self, db_name: str, sql: str) -> Dict[str, Any]:
        """Call API to execute SQL"""
        try:
            response = requests.post(
                f"{self.api_base_url}/admin/smart/execute",
                json={"db_name": db_name, "sql": sql},
                timeout=90
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.Timeout:
            return {"success": False, "error": "Execution timeout"}
        except requests.exceptions.RequestException as e:
            return {"success": False, "error": f"Request failed: {str(e)}"}
        except json.JSONDecodeError:
            return {"success": False, "error": "Invalid response from server"}
        except Exception as e:
            return {"success": False, "error": f"Unexpected error: {str(e)}"}
    
    def _render_confirmation_workflow(self, db_name: str, result: Dict[str, Any]):
        """Render SQL confirmation and execution workflow"""
        st.markdown("---")
        
        if not result.get("success"):
            st.error("❌ Failed to generate SQL")
            st.error(result.get("error", "Unknown error"))
            
            # Show suggestions if available
            if result.get("suggestions"):
                st.info("💡 Try one of these instead:")
                for suggestion in result["suggestions"]:
                    st.markdown(f"- {suggestion}")
            return
        
        # Display safety level
        safety_level = result.get("safety_level", "unknown")
        self._render_safety_badge(safety_level, result.get("recommendation"))
        
        # Display explanation
        if result.get("explanation"):
            st.info(f"🎯 **What this does:** {result['explanation']}")
        
        # Display warnings
        if result.get("warnings"):
            st.warning(f"⚠️ **Warning:** {result['warnings']}")
        
        # Display generated SQL
        st.markdown("### 📝 Generated SQL Query")
        st.code(result["sql"], language="sql")
        
        # Execution controls
        st.markdown("### 🚀 Execute Query?")
        
        col1, col2, col3 = st.columns([2, 2, 6])
        
        with col1:
            if safety_level == "dangerous":
                confirm = st.checkbox("I understand the risks", key="danger_confirm")
                execute_btn = st.button(
                    "⚠️ Execute Anyway",
                    type="secondary",
                    disabled=not confirm,
                    key="exec_danger_btn"
                )
            elif safety_level == "modify":
                execute_btn = st.button(
                    "⚠️ Execute",
                    type="secondary",
                    key="exec_modify_btn"
                )
            else:
                execute_btn = st.button(
                    "✅ Execute",
                    type="primary",
                    key="exec_safe_btn"
                )
        
        with col2:
            if st.button("✏️ Modify", key="modify_btn"):
                st.session_state["smart_admin_query"] = result["sql"]
                st.session_state.pop("pending_sql", None)
                st.rerun()
        
        with col3:
            st.button("❌ Cancel", key="cancel_btn", on_click=self._clear_state)
        
        # Execute if confirmed
        if execute_btn:
            with st.spinner("⚙️ Executing query..."):
                exec_result = self._execute_sql(db_name, result["sql"])
                st.session_state["execution_result"] = exec_result
                st.session_state.pop("pending_sql", None)
                st.rerun()
    
    def _render_safety_badge(self, safety_level: str, recommendation: str):
        """Render safety level badge"""
        colors = {
            "safe": ("#d4edda", "#155724"),
            "modify": ("#fff3cd", "#856404"),
            "dangerous": ("#f8d7da", "#721c24"),
            "unknown": ("#e7e8ea", "#383d41")
        }
        
        bg_color, text_color = colors.get(safety_level, colors["unknown"])
        
        st.markdown(
            f'<div style="padding: 1rem; border-radius: 0.5rem; background-color: {bg_color}; '
            f'border: 2px solid {text_color}; color: {text_color}; margin-bottom: 1rem;">'
            f'<strong>{recommendation}</strong></div>',
            unsafe_allow_html=True
        )
    
    def _render_execution_results(self, result: Dict[str, Any]):
        """Render execution results"""
        st.markdown("---")
        st.markdown("## 📊 Execution Results")
        
        if not result.get("success"):
            st.error("❌ Execution failed")
            st.error(result.get("error", "Unknown error"))
            return
        
        # Check if it's a data query or command
        if result.get("data"):
            # Data results
            st.success(f"✅ Query executed successfully! ({result.get('row_count', 0)} rows)")
            
            # Convert to DataFrame
            df = pd.DataFrame(result["data"])
            
            # Display table
            st.dataframe(df, use_container_width=True, height=400)
            
            # Download button
            csv = df.to_csv(index=False)
            st.download_button(
                label="📥 Download as CSV",
                data=csv,
                file_name="query_results.csv",
                mime="text/csv",
                key="download_admin_csv"
            )
            
            # Data summary
            with st.expander("📈 Data Summary"):
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Total Rows", len(df))
                    st.metric("Total Columns", len(df.columns))
                with col2:
                    st.write("**Column Types:**")
                    st.dataframe(df.dtypes.to_frame(name="Type"))
        
        elif result.get("message"):
            # Command results (UPDATE, DELETE, etc.)
            st.success("✅ " + result["message"])
            if result.get("affected_rows") is not None:
                st.info(f"Rows affected: {result['affected_rows']}")
        
        else:
            st.success("✅ Query executed successfully!")
        
        # Quick actions
        st.markdown("---")
        st.markdown("### 🔧 Quick Actions")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            if st.button("📋 List Tables", key="quick_tables"):
                st.session_state["smart_admin_query"] = "Show all tables"
                self._clear_state()
                st.rerun()
        
        with col2:
            if st.button("📊 Table Sizes", key="quick_sizes"):
                st.session_state["smart_admin_query"] = "Show table sizes"
                self._clear_state()
                st.rerun()
        
        with col3:
            if st.button("🔍 Indexes", key="quick_indexes"):
                st.session_state["smart_admin_query"] = "List all indexes"
                self._clear_state()
                st.rerun()
        
        with col4:
            if st.button("💾 DB Size", key="quick_dbsize"):
                st.session_state["smart_admin_query"] = "Show database size"
                self._clear_state()
                st.rerun()
    
    def _clear_state(self):
        """Clear session state"""
        keys_to_clear = ["pending_sql", "execution_result"]
        for key in keys_to_clear:
            st.session_state.pop(key, None)


# # frontend/components/admin_interface.py
# import streamlit as st
# import requests
# import pandas as pd
# from typing import Dict, Any

# class AdminInterface:
#     """Component for database administration interface"""
    
#     def __init__(self, api_base_url: str):
#         self.api_base_url = api_base_url
    
#     def render(self, db_name: str):
#         """Render the admin interface"""
#         if not db_name:
#             st.warning("⚠️ Please enter a database name in the sidebar")
#             return
        
#         st.header("👨‍💼 Database Administration Assistant")
#         st.markdown("*Agent 3: Independent DB Admin for Schema, Maintenance & Diagnostics*")
        
#         # Admin command categories
#         self._render_command_examples()
        
#         # Command input
#         admin_command = st.text_area(
#             "Enter administrative command in natural language:",
#             height=120,
#             placeholder="Example: Show me all indexes on the users table",
#             key="admin_command_input"
#         )
        
#         # Execution controls
#         col1, col2, col3 = st.columns([2, 2, 6])
#         with col1:
#             exec_btn = st.button("🚀 Execute Command", key="exec_admin_btn", type="primary")
#         with col2:
#             if st.button("🗑️ Clear Results", key="clear_admin"):
#                 st.session_state.pop("admin_result", None)
#                 st.rerun()
        
#         # Execute command
#         if exec_btn and admin_command.strip():
#             with st.spinner("🤖 Agent 3 is processing your request..."):
#                 result = self._execute_admin_command(db_name, admin_command)
            
#             st.session_state["admin_result"] = result
        
#         # Display results
#         if "admin_result" in st.session_state:
#             self._render_admin_result(st.session_state["admin_result"])
    
#     def _render_command_examples(self):
#         """Render example commands"""
#         with st.expander("💡 Example Admin Commands", expanded=False):
#             col1, col2 = st.columns(2)
            
#             with col1:
#                 st.markdown("""
#                 **📋 Schema Information:**
#                 - Show all tables with row counts
#                 - Describe the structure of users table
#                 - List all foreign keys in the database
#                 - Show columns in orders table
                
#                 **🔍 Performance & Diagnostics:**
#                 - Analyze the performance of users table
#                 - Show table sizes sorted by disk usage
#                 - List all indexes on products table
#                 - Check for missing indexes on foreign keys
#                 """)
            
#             with col2:
#                 st.markdown("""
#                 **⚙️ Maintenance Operations:**
#                 - Create an index on users.email
#                 - Vacuum analyze all tables
#                 - Show database statistics
#                 - Check table bloat
                
#                 **📊 Monitoring:**
#                 - Show active connections
#                 - List long-running queries
#                 - Show database size
#                 - Check replication lag
#                 """)
    
#     def _execute_admin_command(self, db_name: str, command: str) -> Dict[str, Any]:
#         """Call admin command API"""
#         try:
#             response = requests.post(
#                 f"{self.api_base_url}/admin/command",
#                 json={"db_name": db_name, "command": command},
#                 timeout=90
#             )
#             return response.json()
#         except requests.exceptions.RequestException as e:
#             return {"success": False, "error": str(e)}
    
#     def _render_admin_result(self, result: Dict[str, Any]):
#         """Render admin command results"""
#         st.markdown("---")
        
#         if not result.get("success"):
#             st.error(f"❌ Command failed: {result.get('error')}")
#             return
        
#         # Display action
#         if result.get("action"):
#             st.markdown(
#                 f'<div style="padding: 1rem; border-radius: 0.5rem; background-color: #d1ecf1; '
#                 f'border: 1px solid #bee5eb; color: #0c5460;">'
#                 f'<strong>🎯 Action:</strong> {result["action"]}</div>',
#                 unsafe_allow_html=True
#             )
#             st.markdown("")
        
#         # Display warnings first (if any)
#         if result.get("warnings"):
#             st.markdown(
#                 f'<div style="padding: 1rem; border-radius: 0.5rem; background-color: #fff3cd; '
#                 f'border: 1px solid #ffeeba; color: #856404;">'
#                 f'<strong>⚠️ Important Warnings:</strong><br>{result["warnings"]}</div>',
#                 unsafe_allow_html=True
#             )
#             st.markdown("")
        
#         # Display SQL
#         if result.get("sql"):
#             st.markdown("### 📝 Generated SQL")
#             st.code(result["sql"], language="sql")
            
#             # Copy to clipboard
#             st.caption("💡 You can copy this SQL to execute manually if needed")
        
#         # Display explanation
#         if result.get("explanation"):
#             with st.expander("📖 Detailed Explanation", expanded=True):
#                 st.markdown(result["explanation"])
        
#         # Display execution results
#         if result.get("execution_result"):
#             st.markdown("### 📊 Execution Results")
#             exec_result = result["execution_result"]
            
#             if exec_result.get("success"):
#                 if exec_result.get("data"):
#                     st.success(f"✅ Query executed! ({exec_result.get('row_count', 0)} rows)")
                    
#                     # Convert to DataFrame
#                     df = pd.DataFrame(exec_result["data"])
                    
#                     # Display dataframe
#                     st.dataframe(df, use_container_width=True, height=350)
                    
#                     # Download option
#                     csv = df.to_csv(index=False)
#                     st.download_button(
#                         label="📥 Download Results",
#                         data=csv,
#                         file_name="admin_results.csv",
#                         mime="text/csv",
#                         key="download_admin_csv"
#                     )
                
#                 elif exec_result.get("message"):
#                     st.info(exec_result["message"])
            
#             else:
#                 st.error(f"❌ Execution error: {exec_result.get('error')}")
        
#         # Show raw response in collapsible section
#         with st.expander("🔍 Full Agent Response", expanded=False):
#             st.text(result.get("raw_response", "No additional details"))
        
#         # Quick actions
#         st.markdown("---")
#         st.markdown("### 🔧 Quick Actions")
#         col1, col2, col3 = st.columns(3)
        
#         with col1:
#             if st.button("📋 List All Tables", key="quick_tables"):
#                 st.session_state["admin_command_input"] = "Show all tables in the database"
#                 st.rerun()
        
#         with col2:
#             if st.button("📊 Database Size", key="quick_size"):
#                 st.session_state["admin_command_input"] = "Show total database size"
#                 st.rerun()
        
#         with col3:
#             if st.button("🔍 Show Indexes", key="quick_indexes"):
#                 st.session_state["admin_command_input"] = "List all indexes in the database"
#                 st.rerun()