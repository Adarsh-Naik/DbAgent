# frontend/app.py
import streamlit as st
import requests
from typing import Dict, Any
import sys
from pathlib import Path
import json

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from frontend.components.sql_interface import SQLInterface
from frontend.components.admin_interface import AdminInterface

# Configuration
API_BASE_URL = "http://localhost:8000"

st.set_page_config(
    page_title="NL-to-SQL Multi-Agent System",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    /* Main theme colors */
    :root {
        --primary-color: #4CAF50;
        --secondary-color: #2196F3;
        --danger-color: #f44336;
        --warning-color: #ff9800;
        --success-color: #4CAF50;
    }
    
    /* Improve spacing */
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
        max-width: 1400px;
    }
    
    /* Custom boxes */
    .success-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        color: #155724;
        margin: 1rem 0;
    }
    
    .error-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #f8d7da;
        border: 1px solid #f5c6cb;
        color: #721c24;
        margin: 1rem 0;
    }
    
    .warning-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #fff3cd;
        border: 1px solid #ffeeba;
        color: #856404;
        margin: 1rem 0;
    }
    
    .info-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #d1ecf1;
        border: 1px solid #bee5eb;
        color: #0c5460;
        margin: 1rem 0;
    }
    
    /* Improve code blocks */
    .stCodeBlock {
        background-color: #f5f5f5;
        border-radius: 0.5rem;
        border: 1px solid #ddd;
    }
    
    /* Better button styling */
    .stButton>button {
        border-radius: 0.5rem;
        font-weight: 500;
        transition: all 0.3s ease;
    }
    
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(0,0,0,0.1);
    }
    
    /* Improve tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 2rem;
    }
    
    .stTabs [data-baseweb="tab"] {
        padding: 1rem 2rem;
        font-weight: 600;
    }
    
    /* Footer styling */
    .footer {
        text-align: center;
        padding: 2rem 0;
        color: #666;
        font-size: 0.9rem;
        border-top: 1px solid #eee;
        margin-top: 3rem;
    }
    
    /* Metrics */
    [data-testid="stMetricValue"] {
        font-size: 2rem;
        font-weight: 700;
    }
</style>
""", unsafe_allow_html=True)


def check_backend_health() -> bool:
    """Check if backend is running"""
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=5)
        return response.status_code == 200
    except Exception as e:
        st.error(f"Backend connection error: {e}")
        return False


def make_request(endpoint: str, method: str = "POST", params: dict = None, json_data: dict = None) -> Dict[str, Any]:
    """Make API request with better error handling"""
    url = f"{API_BASE_URL}{endpoint}"
    try:
        if method == "POST":
            if params:
                response = requests.post(url, params=params, timeout=30)
            elif json_data:
                response = requests.post(url, json=json_data, timeout=60)
            else:
                response = requests.post(url, timeout=30)
        else:
            response = requests.get(url, params=params, timeout=30)
        
        # Check if response is successful
        response.raise_for_status()
        return response.json()
        
        
    except requests.exceptions.Timeout:
        return {"success": False, "error": "Request timeout. Backend is slow or not responding."}
    except requests.exceptions.ConnectionError:
        return {"success": False, "error": "Cannot connect to backend. Is it running on port 8000?"}
    except requests.exceptions.HTTPError as e:
        return {"success": False, "error": f"HTTP Error: {e}"}
    except requests.exceptions.RequestException as e:
        return {"success": False, "error": f"Request failed: {str(e)}"}
    except json.JSONDecodeError:
        return {"success": False, "error": "Invalid response from backend"}
    except Exception as e:
        return {"success": False, "error": f"Unexpected error: {str(e)}"}


def render_sidebar():
    """Render sidebar with database connection"""
    with st.sidebar:
        st.markdown("## 🗄️ Database Connection")
        
        # Check backend health
        backend_status = check_backend_health()
        if backend_status:
            st.success("✅ Backend: Online")
        else:
            st.error("❌ Backend: Offline")
            st.info("Start backend: `python backend/main.py`")
            return None
        
        # Database input
        db_name = st.text_input(
            "Database Name",
            value=st.session_state.get("db_name", ""),
            placeholder="Enter database name (e.g., dvdrental)",
            key="db_name_input",
            help="PostgreSQL database name to connect to"
        )
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("🔌 Connect", key="test_conn", use_container_width=True):
                if db_name:
                    with st.spinner("Testing connection..."):
                        result = make_request("/test-connection", "POST", params={"db_name": db_name})
                    
                    # Debug: Show full response
                    if not result.get("success"):
                        with st.expander("🔍 Debug Info", expanded=True):
                            st.json(result)
                    
                    if result.get("success"):
                        st.success("✅ Connected!")
                        st.session_state["db_name"] = db_name
                        st.session_state["connected"] = True
                        
                        # Load schema
                        with st.spinner("Loading schema..."):
                            schema_result = make_request("/schema/extract", "POST", params={"db_name": db_name})
                            print(schema_result)
                        
                        if schema_result.get("success"):
                            st.session_state["schema"] = schema_result.get("schema")
                            st.session_state["tables"] = schema_result.get("tables", [])
                            st.rerun()
                        else:
                            st.error(f"Schema extraction failed: {schema_result.get('error', 'Unknown error')}")
                    else:
                        error_msg = result.get("error", "Unknown error")
                        st.error(f"❌ Connection failed")
                        st.error(error_msg)
                        
                        # Show diagnostics if available
                        if result.get("diagnostics"):
                            with st.expander("💡 Troubleshooting Tips"):
                                diagnostics = result["diagnostics"]
                                st.write(f"**Host:** {diagnostics.get('host')}")
                                st.write(f"**Port:** {diagnostics.get('port')}")
                                st.write(f"**User:** {diagnostics.get('user')}")
                                
                                if diagnostics.get("suggestions"):
                                    st.write("**Suggestions:**")
                                    for suggestion in diagnostics["suggestions"]:
                                        st.write(f"• {suggestion}")
                else:
                    st.warning("⚠️ Please enter a database name")
        
        with col2:
            if st.button("🔄 Refresh", key="refresh_schema", use_container_width=True):
                if st.session_state.get("connected") and st.session_state.get("db_name"):
                    with st.spinner("Refreshing schema..."):
                        schema_result = make_request("/schema/extract", "POST", params={"db_name": st.session_state["db_name"]})
                    
                    if schema_result.get("success"):
                        st.session_state["schema"] = schema_result.get("schema")
                        st.session_state["tables"] = schema_result.get("tables", [])
                        st.success("✅ Schema refreshed!")
                        st.rerun()
                    else:
                        st.error(f"Failed to refresh: {schema_result.get('error', 'Unknown error')}")
                else:
                    st.warning("⚠️ Connect to a database first")
        
        # Display connection info
        if st.session_state.get("connected"):
            st.markdown("---")
            st.markdown("### 📊 Database Info")
            
            st.metric("Database", st.session_state.get("db_name", "N/A"))
            
            if st.session_state.get("tables"):
                st.metric("Tables", len(st.session_state["tables"]))
                
                with st.expander("📋 View Tables", expanded=False):
                    for table in st.session_state["tables"]:
                        st.text(f"  • {table}")
            
            # Show schema preview
            if st.session_state.get("schema"):
                with st.expander("🔍 Schema Preview", expanded=False):
                    schema_preview = st.session_state["schema"][:500]
                    st.text(schema_preview + "..." if len(st.session_state["schema"]) > 500 else schema_preview)
        
        # Settings
        st.markdown("---")
        st.markdown("### ⚙️ Settings")
        
        st.session_state["show_sql_hints"] = st.checkbox(
            "Show SQL hints",
            value=st.session_state.get("show_sql_hints", True),
            help="Display helpful SQL query examples"
        )
        
        st.session_state["auto_limit"] = st.checkbox(
            "Auto-add LIMIT",
            value=st.session_state.get("auto_limit", True),
            help="Automatically add LIMIT 100 to SELECT queries"
        )
        
        # API info
        st.markdown("---")
        st.markdown("### 🔗 API Endpoint")
        st.code(API_BASE_URL, language="text")
        
        if st.button("📚 View API Docs", use_container_width=True):
            st.write(f"[Open API Documentation]({API_BASE_URL}/docs)")
    
    return st.session_state.get("db_name") if st.session_state.get("connected") else None


def main():
    """Main application"""
    
    # Initialize session state
    if "connected" not in st.session_state:
        st.session_state["connected"] = False
    
    # Title
    st.markdown("""
    # 🤖 NL-to-SQL Multi-Agent System
    ### *Powered by CrewAI + Ollama + FastAPI*
    """)
    
    st.markdown("Transform natural language into powerful SQL queries with AI agents")
    
    # Render sidebar and get database name
    db_name = render_sidebar()
    
    # Main content
    if not db_name:
        # Welcome screen
        st.markdown("---")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("""
            ### 🤖 Agent 1
            **SQL Generator**
            
            Converts natural language to PostgreSQL queries with schema validation
            """)
        
        with col2:
            st.markdown("""
            ### 🔧 Agent 2
            **SQL Executor**
            
            Executes queries with intelligent error recovery and auto-retry
            """)
        
        with col3:
            st.markdown("""
            ### 👨‍💼 Agent 3
            **DB Admin**
            
            Independent assistant for database administration tasks
            """)
        
        st.markdown("---")
        st.info("👈 **Get started:** Enter your database name in the sidebar and click Connect")
        
        # System requirements
        with st.expander("📋 System Requirements", expanded=False):
            st.markdown("""
            - **PostgreSQL** database
            - **Ollama** with deepseek-r1:1.5b model
            - **FastAPI** backend running on port 8000
            
            **Setup Commands:**
            ```bash
            # Install Ollama
            curl -fsSL https://ollama.com/install.sh | sh
            
            # Pull model
            ollama pull deepseek-r1:1.5b
            
            # Start backend
            python backend/main.py
            ```
            """)
        
        return
    
    # Tabs for different interfaces
    tab1, tab2, tab3 = st.tabs([
        "🔍 Query Generator",
        "⚡ Direct Executor",
        "👨‍💼 DB Admin"
    ])
    
    # Initialize components
    sql_interface = SQLInterface(API_BASE_URL)
    admin_interface = AdminInterface(API_BASE_URL)
    
    # Tab 1: SQL Query Generator
    with tab1:
        sql_interface.render(db_name)
    
    # Tab 2: Direct SQL Executor
    with tab2:
        st.header("⚡ Direct SQL Execution")
        st.markdown("*Execute SQL directly with Agent 2's error recovery*")
        
        direct_sql = st.text_area(
            "Enter SQL query:",
            height=180,
            placeholder="SELECT * FROM users WHERE active = true LIMIT 10;",
            key="direct_sql_input"
        )
        
        col1, col2 = st.columns([2, 8])
        with col1:
            confirm_direct = st.checkbox(
                "⚠️ Confirm",
                key="confirm_direct",
                help="Required for execution"
            )
        
        with col2:
            exec_direct_btn = st.button(
                "▶️ Execute with Agent 2",
                key="exec_direct_btn",
                type="primary",
                disabled=not confirm_direct
            )
        
        if exec_direct_btn and direct_sql.strip() and confirm_direct:
            with st.spinner("🤖 Agent 2 executing..."):
                result = make_request(
                    "/query/execute",
                    "POST",
                    json_data={
                        "db_name": db_name,
                        "sql": direct_sql,
                        "confirm": confirm_direct
                    }
                )
                
                if result.get("success"):
                    if result.get("data"):
                        st.success(f"✅ Query executed! ({result.get('row_count', 0)} rows)")
                        import pandas as pd
                        df = pd.DataFrame(result["data"])
                        st.dataframe(df, use_container_width=True)
                    elif result.get("affected_rows") is not None:
                        st.success(f"✅ {result.get('affected_rows')} rows affected")
                else:
                    st.error(f"❌ {result.get('error')}")
                    if result.get("error_analysis"):
                        with st.expander("🔍 Error Analysis"):
                            st.text(result["error_analysis"])
    
    # Tab 3: DB Admin
    with tab3:
        admin_interface.render(db_name)
    
    # Footer
    st.markdown("---")
    st.markdown(f"""
    <div class="footer">
        <strong>NL-to-SQL Multi-Agent System v2.0</strong><br>
        Built with ❤️ using CrewAI, Ollama, FastAPI, and Streamlit<br>
        <a href="https://github.com/yourusername/nl-to-sql" target="_blank">GitHub</a> | 
        <a href="{API_BASE_URL}/docs" target="_blank">API Docs</a> | 
        <a href="https://docs.crewai.com" target="_blank">CrewAI Docs</a>
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()



# # frontend/app.py
# import streamlit as st
# import requests
# import pandas as pd
# from typing import Dict, Any
# import json

# # Configuration
# API_BASE_URL = "http://localhost:8000"

# st.set_page_config(
#     page_title="NL-to-SQL Multi-Agent System",
#     page_icon="🤖",
#     layout="wide"
# )

# # Custom CSS
# st.markdown("""
# <style>
#     .success-box {
#         padding: 1rem;
#         border-radius: 0.5rem;
#         background-color: #d4edda;
#         border: 1px solid #c3e6cb;
#         color: #155724;
#     }
#     .error-box {
#         padding: 1rem;
#         border-radius: 0.5rem;
#         background-color: #f8d7da;
#         border: 1px solid #f5c6cb;
#         color: #721c24;
#     }
#     .warning-box {
#         padding: 1rem;
#         border-radius: 0.5rem;
#         background-color: #fff3cd;
#         border: 1px solid #ffeeba;
#         color: #856404;
#     }
#     .info-box {
#         padding: 1rem;
#         border-radius: 0.5rem;
#         background-color: #d1ecf1;
#         border: 1px solid #bee5eb;
#         color: #0c5460;
#     }
# </style>
# """, unsafe_allow_html=True)


# def make_request(endpoint: str, method: str = "POST", **kwargs) -> Dict[str, Any]:
#     """Make API request"""
#     url = f"{API_BASE_URL}{endpoint}"
#     try:
#         if method == "POST":
#             response = requests.post(url, json=kwargs, timeout=60)
#         else:
#             response = requests.get(url, params=kwargs, timeout=30)
#         return response.json()
#     except requests.exceptions.RequestException as e:
#         return {"success": False, "error": str(e)}


# def display_result(result: Dict[str, Any], result_type: str = "data"):
#     """Display query results"""
#     if not result.get("success", False):
#         st.markdown(f'<div class="error-box">❌ Error: {result.get("error", "Unknown error")}</div>', 
#                    unsafe_allow_html=True)
#         return
    
#     if result_type == "data" and result.get("data"):
#         st.success(f"✅ Query executed successfully! ({result.get('row_count', 0)} rows)")
#         df = pd.DataFrame(result["data"])
#         st.dataframe(df, use_container_width=True)
#     elif result.get("affected_rows") is not None:
#         st.success(f"✅ {result.get('affected_rows')} rows affected")
#     elif result.get("message"):
#         st.info(result["message"])


# # Title
# st.title("🤖 NL-to-SQL Multi-Agent System")
# st.markdown("*Powered by CrewAI + Ollama + FastAPI*")

# # Sidebar - Database Connection
# with st.sidebar:
#     st.header("📊 Database Connection")
#     db_name = st.text_input("Database Name", value="", key="db_name")
    
#     if st.button("Test Connection", key="test_conn"):
#         if db_name:
#             with st.spinner("Testing connection..."):
#                 result = make_request("/test-connection", "POST", db_name=db_name)
#                 if result.get("success"):
#                     st.success("✅ Connected!")
#                     # Load schema
#                     schema_result = make_request("/schema/extract", "POST", db_name=db_name)
#                     if schema_result.get("success"):
#                         st.session_state["schema"] = schema_result.get("schema")
#                         st.session_state["tables"] = schema_result.get("tables", [])
#                 else:
#                     st.error(f"❌ {result.get('error', 'Connection failed')}")
    
#     if "tables" in st.session_state:
#         st.markdown("---")
#         st.subheader("📋 Tables")
#         for table in st.session_state.get("tables", []):
#             st.text(f"• {table}")

# # Main Content - Tabs
# tab1, tab2, tab3 = st.tabs(["🔍 Query Generator", "⚙️ Direct Executor", "👨‍💼 DB Admin"])

# # TAB 1: SQL Query Generator (Agent 1 + Agent 2)
# with tab1:
#     st.header("Natural Language to SQL")
#     st.markdown("*Agent 1 (Generator) + Agent 2 (Executor with Error Recovery)*")
    
#     if not db_name:
#         st.warning("⚠️ Please enter a database name in the sidebar")
#     else:
#         nl_query = st.text_area(
#             "Enter your question in natural language:",
#             height=100,
#             placeholder="Example: Show me all users who registered in the last 30 days"
#         )
        
#         col1, col2 = st.columns([1, 4])
#         with col1:
#             generate_btn = st.button("🔄 Generate SQL", key="gen_sql", type="primary")
        
#         if generate_btn and nl_query:
#             with st.spinner("🤖 Agent 1 is generating SQL..."):
#                 result = make_request(
#                     "/query/generate",
#                     db_name=db_name,
#                     query=nl_query
#                 )
            
#             if result.get("success"):
#                 sql = result.get("sql")
#                 st.session_state["generated_sql"] = sql
                
#                 # Display warning if exists
#                 if result.get("warning"):
#                     st.markdown(f'<div class="warning-box">{result["warning"]}</div>', 
#                                unsafe_allow_html=True)
                
#                 st.markdown("### Generated SQL:")
#                 st.code(sql, language="sql")
                
#                 # Execute button
#                 st.markdown("### Execution")
#                 confirm = st.checkbox("⚠️ I confirm I want to execute this query", key="confirm_exec")
                
#                 if st.button("▶️ Execute Query", key="exec_sql", disabled=not confirm):
#                     with st.spinner("🤖 Agent 2 is executing and monitoring..."):
#                         exec_result = make_request(
#                             "/query/execute",
#                             db_name=db_name,
#                             sql=sql,
#                             confirm=confirm
#                         )
                    
#                     if exec_result.get("success"):
#                         display_result(exec_result, "data")
#                     else:
#                         st.error(f"❌ Execution failed: {exec_result.get('error')}")
#                         if exec_result.get("error_analysis"):
#                             with st.expander("🔍 Error Analysis & Suggestion"):
#                                 st.text(exec_result["error_analysis"])
#             else:
#                 st.error(f"❌ Generation failed: {result.get('error')}")

# # TAB 2: Direct SQL Executor
# with tab2:
#     st.header("Direct SQL Execution")
#     st.markdown("*Execute SQL directly with Agent 2's error recovery*")
    
#     if not db_name:
#         st.warning("⚠️ Please enter a database name in the sidebar")
#     else:
#         direct_sql = st.text_area(
#             "Enter SQL query:",
#             height=150,
#             placeholder="SELECT * FROM users WHERE active = true LIMIT 10;"
#         )
        
#         confirm_direct = st.checkbox("⚠️ I confirm I want to execute this query", key="confirm_direct")
        
#         if st.button("▶️ Execute", key="exec_direct", type="primary", disabled=not confirm_direct):
#             if direct_sql.strip():
#                 with st.spinner("🤖 Executing with Agent 2..."):
#                     result = make_request(
#                         "/query/execute",
#                         db_name=db_name,
#                         sql=direct_sql,
#                         confirm=confirm_direct
#                     )
                
#                 if result.get("success"):
#                     display_result(result, "data")
#                 else:
#                     st.error(f"❌ {result.get('error')}")
#                     if result.get("error_analysis"):
#                         with st.expander("🔍 Error Analysis"):
#                             st.text(result["error_analysis"])

# # TAB 3: DB Admin Assistant
# with tab3:
#     st.header("Database Administration Assistant")
#     st.markdown("*Agent 3: Independent DB admin for schema, maintenance, and diagnostics*")
    
#     if not db_name:
#         st.warning("⚠️ Please enter a database name in the sidebar")
#     else:
#         st.markdown("""
#         **Examples of admin commands:**
#         - "Show all tables with their row counts"
#         - "Create an index on users.email"
#         - "Analyze the performance of the orders table"
#         - "Show table sizes"
#         - "Check for missing indexes on foreign keys"
#         """)
        
#         admin_command = st.text_area(
#             "Enter admin command:",
#             height=100,
#             placeholder="Example: Show me all indexes on the users table"
#         )
        
#         if st.button("🚀 Execute Admin Command", key="exec_admin", type="primary"):
#             if admin_command.strip():
#                 with st.spinner("🤖 Agent 3 is processing..."):
#                     result = make_request(
#                         "/admin/command",
#                         db_name=db_name,
#                         command=admin_command
#                     )
                
#                 if result.get("success"):
#                     # Display action
#                     if result.get("action"):
#                         st.markdown(f'<div class="info-box"><strong>Action:</strong> {result["action"]}</div>', 
#                                    unsafe_allow_html=True)
                    
#                     # Display SQL
#                     if result.get("sql"):
#                         st.markdown("### Generated SQL:")
#                         st.code(result["sql"], language="sql")
                    
#                     # Display explanation
#                     if result.get("explanation"):
#                         with st.expander("📖 Explanation", expanded=True):
#                             st.text(result["explanation"])
                    
#                     # Display warnings
#                     if result.get("warnings"):
#                         st.markdown(f'<div class="warning-box"><strong>⚠️ Warnings:</strong><br>{result["warnings"]}</div>', 
#                                    unsafe_allow_html=True)
                    
#                     # Display execution results if available
#                     if result.get("execution_result"):
#                         st.markdown("### Results:")
#                         display_result(result["execution_result"], "data")
                    
#                     # Show raw response in expander
#                     with st.expander("🔍 Full Response"):
#                         st.text(result.get("raw_response", ""))
#                 else:
#                     st.error(f"❌ {result.get('error')}")

# # Footer
# st.markdown("---")
# st.markdown("""
# <div style='text-align: center; color: #666;'>
#     Made with ❤️ using CrewAI, Ollama, FastAPI, and Streamlit
# </div>
# """, unsafe_allow_html=True)