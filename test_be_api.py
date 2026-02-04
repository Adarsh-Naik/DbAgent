# test_backend_api.py
"""
Test the backend API directly to isolate the issue
"""

import requests
import json

API_BASE_URL = "http://localhost:8000"

def test_health():
    """Test health endpoint"""
    print("=" * 80)
    print("TEST 1: Health Check")
    print("=" * 80)
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=5)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_connection(db_name="dvdrental"):
    """Test database connection"""
    print("\n" + "=" * 80)
    print(f"TEST 2: Database Connection Test (db_name={db_name})")
    print("=" * 80)
    try:
        response = requests.post(
            f"{API_BASE_URL}/test-connection",
            params={"db_name": db_name},
            timeout=10
        )
        print(f"Status Code: {response.status_code}")
        result = response.json()
        print(f"Response: {json.dumps(result, indent=2)}")
        
        if result.get("success"):
            print("\n✅ Connection successful!")
        else:
            print("\n❌ Connection failed!")
            if "diagnostics" in result:
                print("\n📋 Diagnostics:")
                for suggestion in result["diagnostics"].get("suggestions", []):
                    print(f"  • {suggestion}")
        
        return result.get("success", False)
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_schema_extraction(db_name="dvdrental"):
    """Test schema extraction"""
    print("\n" + "=" * 80)
    print(f"TEST 3: Schema Extraction (db_name={db_name})")
    print("=" * 80)
    try:
        response = requests.post(
            f"{API_BASE_URL}/schema/extract",
            params={"db_name": db_name},
            timeout=30
        )
        print(f"Status Code: {response.status_code}")
        result = response.json()
        
        if result.get("success"):
            print("✅ Schema extraction successful!")
            print(f"Tables found: {len(result.get('tables', []))}")
            if result.get('tables'):
                print("Tables:")
                for table in result['tables'][:10]:  # Show first 10
                    print(f"  • {table}")
        else:
            print("❌ Schema extraction failed!")
            print(f"Error: {result.get('error')}")
        
        return result.get("success", False)
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def check_backend_running():
    """Check if backend is running"""
    print("=" * 80)
    print("CHECKING BACKEND STATUS")
    print("=" * 80)
    try:
        response = requests.get(f"{API_BASE_URL}/", timeout=5)
        if response.status_code == 200:
            print("✅ Backend is running")
            return True
        else:
            print(f"⚠️  Backend returned status code: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ Backend is NOT running!")
        print("\nStart backend with:")
        print("  python backend/main.py")
        print("  or")
        print("  uvicorn backend.main:app --reload")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def main():
    print("\n🔍 BACKEND API TEST SUITE\n")
    
    # Check if backend is running
    if not check_backend_running():
        return
    
    print("\n")
    
    # Test health
    health_ok = test_health()
    
    # Test connection
    connection_ok = test_connection("dvdrental")
    
    # Test schema extraction
    if connection_ok:
        test_schema_extraction("dvdrental")
    
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    print(f"Health Check: {'✅ PASS' if health_ok else '❌ FAIL'}")
    print(f"Connection Test: {'✅ PASS' if connection_ok else '❌ FAIL'}")
    
    if not connection_ok:
        print("\n⚠️  Connection test failed!")
        print("\nPossible issues:")
        print("  1. Backend is not reading .env file correctly")
        print("  2. Database 'postgres' doesn't exist")
        print("  3. Backend code has errors")
        print("\nTroubleshooting:")
        print("  1. Check backend logs in the terminal where you ran 'python backend/main.py'")
        print("  2. Verify .env file is in the project root (same directory as backend/)")
        print("  3. Try restarting the backend")
        print("  4. Check backend logs for detailed error messages")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")