# debug_connection.py
"""
Database Connection Debugger
Run this script to diagnose connection issues
"""

import os
import psycopg2
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_connection_detailed():
    """Detailed connection test with diagnostics"""
    
    print("=" * 80)
    print("DATABASE CONNECTION DIAGNOSTICS")
    print("=" * 80)
    
    # Read credentials
    db_host = os.getenv("DB_HOST", "localhost")
    db_port = os.getenv("DB_PORT", "5432")
    db_user = os.getenv("DB_USER", "postgres")
    db_password = os.getenv("DB_PASSWORD", "")
    db_name = "postgres"  # Default database
    
    print("\n📋 CONFIGURATION:")
    print(f"  DB_HOST: {db_host}")
    print(f"  DB_PORT: {db_port}")
    print(f"  DB_USER: {db_user}")
    print(f"  DB_PASSWORD: {'*' * len(db_password) if db_password else '(empty)'}")
    print(f"  DB_NAME: {db_name}")
    
    print("\n🔍 DIAGNOSTIC CHECKS:")
    
    # Check 1: Environment file exists
    if os.path.exists(".env"):
        print("  ✓ .env file found")
        with open(".env", "r") as f:
            content = f.read()
            if "DB_PASSWORD" in content:
                print("  ✓ DB_PASSWORD defined in .env")
            else:
                print("  ✗ DB_PASSWORD NOT found in .env")
    else:
        print("  ✗ .env file NOT found")
    
    # Check 2: Network connectivity
    print("\n🌐 NETWORK CHECK:")
    import socket
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result = sock.connect_ex((db_host, int(db_port)))
        if result == 0:
            print(f"  ✓ Port {db_port} is open on {db_host}")
        else:
            print(f"  ✗ Cannot connect to {db_host}:{db_port}")
            print(f"    Is PostgreSQL running? Check with: sudo systemctl status postgresql")
        sock.close()
    except Exception as e:
        print(f"  ✗ Network error: {e}")
    
    # Check 3: PostgreSQL service status
    print("\n🗄️ POSTGRESQL SERVICE:")
    try:
        import subprocess
        result = subprocess.run(
            ["systemctl", "is-active", "postgresql"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            print("  ✓ PostgreSQL service is active")
        else:
            print("  ✗ PostgreSQL service is NOT active")
            print("    Start with: sudo systemctl start postgresql")
    except FileNotFoundError:
        print("  ⚠ systemctl not available (maybe not Linux?)")
    except Exception as e:
        print(f"  ⚠ Could not check service: {e}")
    
    # Check 4: Try connection with different methods
    print("\n🔐 CONNECTION ATTEMPTS:")
    
    # Method 1: With provided credentials
    print("\n  Method 1: Using .env credentials")
    try:
        conn = psycopg2.connect(
            host=db_host,
            port=int(db_port),
            dbname=db_name,
            user=db_user,
            password=db_password,
            connect_timeout=10
        )
        with conn.cursor() as cur:
            cur.execute("SELECT version();")
            version = cur.fetchone()[0]
            print(f"  ✓ SUCCESS! Connected to PostgreSQL")
            print(f"    Version: {version[:50]}...")
        conn.close()
        return True
        
    except psycopg2.OperationalError as e:
        error_str = str(e)
        print(f"  ✗ Connection failed: {error_str}")
        
        # Detailed error analysis
        if "password authentication failed" in error_str:
            print("\n  ❌ ISSUE: Password authentication failed")
            print("     Solutions:")
            print("     1. Check if password is correct in .env")
            print("     2. Check PostgreSQL pg_hba.conf authentication method")
            print("     3. Try: sudo -u postgres psql -c \"ALTER USER postgres PASSWORD 'newpassword';\"")
            
        elif "does not exist" in error_str:
            print("\n  ❌ ISSUE: Database or user does not exist")
            print("     Solutions:")
            print("     1. Create database: sudo -u postgres createdb postgres")
            print("     2. Create user: sudo -u postgres createuser -s postgres")
            
        elif "could not connect to server" in error_str:
            print("\n  ❌ ISSUE: Cannot reach PostgreSQL server")
            print("     Solutions:")
            print("     1. Start PostgreSQL: sudo systemctl start postgresql")
            print("     2. Check if PostgreSQL is listening: sudo ss -tulpn | grep 5432")
            print("     3. Check firewall: sudo ufw status")
            
        elif "Connection refused" in error_str:
            print("\n  ❌ ISSUE: Connection refused")
            print("     Solutions:")
            print("     1. PostgreSQL is not running: sudo systemctl start postgresql")
            print("     2. Wrong port number in .env")
            print("     3. PostgreSQL not listening on this interface")
            
        elif "timeout" in error_str:
            print("\n  ❌ ISSUE: Connection timeout")
            print("     Solutions:")
            print("     1. Check firewall rules")
            print("     2. Verify host address is correct")
            print("     3. Increase timeout in connection string")
            
    except Exception as e:
        print(f"  ✗ Unexpected error: {type(e).__name__}: {e}")
    
    # Method 2: Try with peer authentication (Unix socket)
    print("\n  Method 2: Unix socket (peer authentication)")
    try:
        conn = psycopg2.connect(
            dbname=db_name,
            user=db_user
        )
        print("  ✓ SUCCESS with Unix socket!")
        conn.close()
        print("    Note: This means PostgreSQL is working, but network auth might be the issue")
    except Exception as e:
        print(f"  ✗ Unix socket also failed: {e}")
    
    return False


def provide_solutions():
    """Provide common solutions"""
    print("\n" + "=" * 80)
    print("🛠️ COMMON SOLUTIONS")
    print("=" * 80)
    
    print("""
1. RESET POSTGRES PASSWORD:
   sudo -u postgres psql
   postgres=# ALTER USER postgres PASSWORD 'your_new_password';
   postgres=# \\q
   
   Then update .env:
   DB_PASSWORD=your_new_password

2. CHECK POSTGRESQL STATUS:
   sudo systemctl status postgresql
   
   If not running:
   sudo systemctl start postgresql

3. ENABLE NETWORK CONNECTIONS (pg_hba.conf):
   sudo nano /etc/postgresql/*/main/pg_hba.conf
   
   Add/modify this line:
   host    all             all             127.0.0.1/32            md5
   
   Then restart:
   sudo systemctl restart postgresql

4. CHECK POSTGRESQL.CONF:
   sudo nano /etc/postgresql/*/main/postgresql.conf
   
   Ensure:
   listen_addresses = 'localhost'
   port = 5432

5. CREATE DATABASE (if needed):
   sudo -u postgres createdb your_database_name

6. TEST CONNECTION MANUALLY:
   psql -h localhost -U postgres -d postgres
   (enter password when prompted)

7. CHECK PORT:
   sudo ss -tulpn | grep 5432
   (should show PostgreSQL listening)

8. CHECK .env FILE LOCATION:
   Must be in project root directory
   
9. VERIFY .env FORMAT:
   DB_HOST=localhost
   DB_PORT=5432
   DB_USER=postgres
   DB_PASSWORD=your_password
   
   No spaces around =
   No quotes unless password contains special characters

10. PERMISSIONS:
    sudo chmod 600 .env
    """)


def quick_fix_script():
    """Generate quick fix commands"""
    print("\n" + "=" * 80)
    print("⚡ QUICK FIX COMMANDS")
    print("=" * 80)
    
    print("""
Run these commands to fix common issues:

# 1. Start PostgreSQL
sudo systemctl start postgresql
sudo systemctl enable postgresql

# 2. Reset postgres user password
sudo -u postgres psql -c "ALTER USER postgres PASSWORD 'postgres';"

# 3. Update your .env file
cat > .env << 'EOF'
DB_HOST=localhost
DB_PORT=5432
DB_USER=postgres
DB_PASSWORD=postgres
OLLAMA_URL=http://localhost:11434
MODEL_NAME=deepseek-r1:1.5b
API_HOST=0.0.0.0
API_PORT=8000
VERBOSE=True
MAX_RETRY_ATTEMPTS=3
EOF

# 4. Test connection
psql -h localhost -U postgres -d postgres

# 5. If step 4 works, restart your application
    """)


if __name__ == "__main__":
    try:
        success = test_connection_detailed()
        
        if not success:
            provide_solutions()
            quick_fix_script()
        else:
            print("\n" + "=" * 80)
            print("✅ CONNECTION SUCCESSFUL!")
            print("=" * 80)
            print("\nYour database connection is working correctly.")
            print("If the UI still shows error, try:")
            print("  1. Restart the backend: Ctrl+C and run again")
            print("  2. Restart the frontend: Ctrl+C and run again")
            print("  3. Clear browser cache and reload")
            
    except KeyboardInterrupt:
        print("\n\nDiagnostics interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()