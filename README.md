# README.md

# 🤖 NL-to-SQL Multi-Agent System

A production-ready application that converts natural language to SQL queries using CrewAI's multi-agent framework, powered by Ollama and PostgreSQL.

## 🌟 Features

### Three Intelligent Agents

1. **Agent 1: SQL Generator** 🔄
   - Converts natural language to PostgreSQL queries
   - Schema-aware with validation
   - Adds safety warnings for dangerous operations

2. **Agent 2: SQL Executor** ⚡
   - Executes SQL with intelligent error recovery
   - Auto-retries with corrected SQL (up to 3 attempts)
   - Provides detailed error analysis

3. **Agent 3: DB Admin Assistant** 👨‍💼
   - Independent database administration
   - Handles schema operations and maintenance
   - Auto-executes safe queries with explanations

### Key Capabilities

✅ Natural language to SQL conversion  
✅ Automatic error detection and correction  
✅ Schema extraction and caching  
✅ Safety confirmations for data modifications  
✅ Beautiful Streamlit UI with 3 interfaces  
✅ RESTful API with FastAPI  
✅ Complete API documentation  
✅ Support for complex queries and joins  
✅ Database administration commands  

## 🏗️ Architecture

```
┌─────────────────────────────────────────┐
│        Streamlit Frontend               │
│  (Query | Direct Execute | DB Admin)    │
└──────────────┬──────────────────────────┘
               │ REST API
┌──────────────▼──────────────────────────┐
│         FastAPI Backend                 │
│  ┌──────────┬───────────┬────────────┐ │
│  │ Agent 1  │  Agent 2  │  Agent 3   │ │
│  │Generator │ Executor  │  DB Admin  │ │
│  └──────────┴───────────┴────────────┘ │
└──────────────┬──────────────────────────┘
               │ psycopg2
┌──────────────▼──────────────────────────┐
│      PostgreSQL Database                │
└─────────────────────────────────────────┘
```

## 📦 Installation

### Prerequisites

- Python 3.10+
- PostgreSQL 12+
- Ollama

### Step 1: Install Ollama

```bash
# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Pull the model
ollama pull deepseek-r1:1.5b

# Verify installation
ollama list
```

### Step 2: Clone & Setup

```bash
# Clone repository
git clone <your-repo-url>
cd DbAgent

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Step 3: Configure Environment

Create `.env` file in project root:

```env
# Database
DB_HOST=localhost
DB_PORT=5432
DB_USER=postgres
DB_PASSWORD=your_password

# Ollama
OLLAMA_URL=http://localhost:11434
MODEL_NAME=deepseek-r1:1.5b

# Backend
API_HOST=0.0.0.0
API_PORT=8000
```

## 🚀 Running the Application

### Terminal 1: Start Backend

```bash
python backend/main.py
```

Backend runs on: `http://localhost:8000`  
API docs: `http://localhost:8000/docs`

### Terminal 2: Start Frontend

```bash
streamlit run frontend/app.py
```

Frontend opens at: `http://localhost:8501`

## 📖 Usage Examples

### Example 1: Simple Query

**Natural Language:**
```
Show me all active users
```

**Generated SQL:**
```sql
SELECT id, username, email, status, created_at 
FROM users 
WHERE status = 'active' 
LIMIT 100;
```

### Example 2: Complex Query with Join

**Natural Language:**
```
Show top 5 customers by total order value in 2024
```

**Generated SQL:**
```sql
SELECT 
    c.id,
    c.name,
    c.email,
    SUM(o.total_amount) as total_spent
FROM customers c
JOIN orders o ON c.id = o.customer_id
WHERE EXTRACT(YEAR FROM o.created_at) = 2024
GROUP BY c.id, c.name, c.email
ORDER BY total_spent DESC
LIMIT 5;
```

### Example 3: Error Recovery

**Original (with error):**
```sql
SELECT id, usrname FROM users;  -- typo
```

**Agent 2 Auto-Fix:**
```sql
SELECT id, username FROM users;  -- corrected
```

### Example 4: DB Admin Command

**Natural Language:**
```
Create an index on users.email for faster lookups
```

**Agent 3 Response:**
```sql
CREATE INDEX idx_users_email ON users(email);
```

**Explanation:**
"This creates a B-tree index on the email column to optimize WHERE clauses and JOIN operations on email. Will briefly lock the table during creation."

## 🔧 API Endpoints

### Core Operations

```bash
# Generate SQL from natural language
POST /query/generate
{
  "db_name": "mydb",
  "query": "show all users"
}

# Execute SQL with error recovery
POST /query/execute
{
  "db_name": "mydb",
  "sql": "SELECT * FROM users;",
  "confirm": true
}

# Admin command
POST /admin/command
{
  "db_name": "mydb",
  "command": "show table sizes"
}

# Extract schema
POST /schema/extract?db_name=mydb

# Test connection
POST /test-connection?db_name=mydb

# Health check
GET /health
```

## 🎯 Features in Detail

### Agent 1: SQL Generator

- **Schema Validation:** Ensures queries use existing tables/columns
- **Safety Warnings:** Alerts for UPDATE/DELETE without WHERE clause
- **Auto-Limit:** Adds LIMIT to prevent large result sets
- **Join Detection:** Automatically creates proper JOIN syntax

### Agent 2: SQL Executor

- **Error Recovery:** Up to 3 retry attempts with corrections
- **Error Types Handled:**
  - Syntax errors
  - Column name typos
  - Type mismatches
  - Constraint violations
- **Detailed Analysis:** Explains what went wrong and how it was fixed

### Agent 3: DB Admin

- **Schema Management:** CREATE, ALTER, DROP operations
- **Index Operations:** Create, analyze, and optimize indexes
- **Maintenance:** VACUUM, ANALYZE, REINDEX
- **Diagnostics:** Table sizes, performance analysis, statistics
- **Safe Execution:** Auto-executes only SELECT queries

## 🔒 Security Features

- ✅ Confirmation required for data modifications
- ✅ SQL injection protection (planned)
- ✅ Environment variable protection
- ✅ Connection pooling (configurable)
- ✅ Query timeout limits

## 🎨 Customization

### Change LLM Model

```env
# .env
MODEL_NAME=llama2:latest
```

### Adjust Retry Attempts

```python
# backend/config.py
MAX_RETRY_ATTEMPTS: int = 5
```

### Modify Agent Behavior

Edit the `backstory` in:
- `backend/agents/sql_generator.py`
- `backend/agents/sql_executor.py`
- `backend/agents/db_admin.py`

## 📊 Project Structure

```
DbAgent/
├── backend/
│   ├── main.py                 # FastAPI server
│   ├── config.py               # Configuration
│   ├── agents/
│   │   ├── sql_generator.py    # Agent 1
│   │   ├── sql_executor.py     # Agent 2
│   │   └── db_admin.py         # Agent 3
│   ├── database/
│   │   ├── postgres_handler.py
│   │   └── schema_extractor.py
│   └── models/
│       └── schemas.py          # Pydantic models
├── frontend/
│   ├── app.py                  # Main Streamlit app
│   └── components/
│       ├── sql_interface.py
│       └── admin_interface.py
├── .env                        # Configuration
├── requirements.txt
└── README.md
```

## 🐛 Troubleshooting

### Ollama Not Responding

```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# Restart Ollama
ollama serve
```

### Database Connection Failed

```bash
# Test PostgreSQL
psql -h localhost -U postgres -d your_database

# Check PostgreSQL status
sudo systemctl status postgresql
```

### Agent Timeouts

Increase timeout in `.env`:
```env
AGENT_TIMEOUT=120
QUERY_TIMEOUT=60
```

## 📈 Performance Tips

1. Use smaller models: `deepseek-r1:1.5b` is fastest
2. Enable schema caching (default: enabled)
3. Add connection pooling for production
4. Use Redis for distributed caching

## 🚢 Production Deployment

### Docker

```dockerfile
FROM python:3.10-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0"]
```

### Docker Compose

```yaml
version: '3.8'
services:
  backend:
    build: .
    ports:
      - "8000:8000"
  frontend:
    build: .
    command: streamlit run frontend/app.py
    ports:
      - "8501:8501"
```
