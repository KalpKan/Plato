#!/usr/bin/env python3
"""Query Supabase database using REST API as fallback."""

import requests
import json
import sys

# Supabase project details
PROJECT_REF = "ftcqzuzpyebtwihizqfl"
SUPABASE_URL = f"https://{PROJECT_REF}.supabase.co"

print("=" * 60)
print("Querying Supabase Database")
print("=" * 60)
print(f"Project: {PROJECT_REF}")
print(f"URL: {SUPABASE_URL}")
print()

# Try to get anon key from environment or use a test
# Note: For table listing, we might need to use the database directly
# The REST API requires authentication and specific endpoints

print("Attempting to connect via REST API...")
print("(Note: Direct database queries require proper authentication)")
print()

# Alternative: Try using Supabase Python client
try:
    from supabase import create_client, Client
    
    print("Installing supabase-py...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "supabase", "--quiet"])
    from supabase import create_client, Client
    
    # For now, we'll need the anon key to use the client
    # But we can try to query tables using SQL
    print("✅ Supabase client available")
    print()
    print("To query tables, we need:")
    print("1. Your Supabase anon key (from Settings → API)")
    print("2. Or use direct database connection")
    print()
    print("Let's try the database connection method instead...")
    
except ImportError:
    print("Supabase client not available")
    print("Using direct database connection...")

# Use direct database connection
import psycopg2

# Try connection pooler first (more reliable)
connection_strings = [
    # Connection pooler (recommended)
    f"postgresql://postgres.ftcqzuzpyebtwihizqfl:[Kk4132231441]@aws-0-us-east-1.pooler.supabase.com:6543/postgres",
    # Direct connection
    f"postgresql://postgres:[Kk4132231441]@db.ftcqzuzpyebtwihizqfl.supabase.co:5432/postgres",
]

for i, conn_str in enumerate(connection_strings, 1):
    print(f"\nTrying connection method {i}...")
    try:
        # Hide password in display
        display_str = conn_str.split('@')[1] if '@' in conn_str else conn_str
        print(f"Connecting to: ...@{display_str}")
        
        conn = psycopg2.connect(conn_str)
        cur = conn.cursor()
        
        # Get all tables
        cur.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name;
        """)
        
        tables = cur.fetchall()
        
        print("=" * 60)
        print("✅ Connection successful!")
        print("=" * 60)
        print(f"\nTables in your Supabase database:")
        print("-" * 60)
        
        if tables:
            for table in tables:
                print(f"  ✓ {table[0]}")
            
            # Get detailed info for each table
            print("\n" + "=" * 60)
            print("Table Details:")
            print("=" * 60)
            
            for table in tables:
                table_name = table[0]
                cur.execute(f"""
                    SELECT 
                        column_name, 
                        data_type, 
                        is_nullable,
                        column_default
                    FROM information_schema.columns
                    WHERE table_name = '{table_name}'
                    ORDER BY ordinal_position;
                """)
                columns = cur.fetchall()
                
                print(f"\n📋 Table: {table_name}")
                print("-" * 60)
                
                for col in columns:
                    col_name, data_type, nullable, default = col
                    nullable_str = "NULL" if nullable == "YES" else "NOT NULL"
                    default_str = f" DEFAULT {default}" if default else ""
                    print(f"   • {col_name:20} {data_type:20} ({nullable_str}{default_str})")
                
                # Get row count
                cur.execute(f'SELECT COUNT(*) FROM "{table_name}";')
                count = cur.fetchone()[0]
                print(f"   📊 Total rows: {count}")
        else:
            print("\n💡 No tables found in the 'public' schema.")
            print("   Your database is ready for table creation!")
            print("\n   I can help you create:")
            print("   • extraction_cache - for storing PDF extraction results")
            print("   • user_choices - for storing user selections")
        
        cur.close()
        conn.close()
        
        print("\n" + "=" * 60)
        print("✅ Query completed successfully!")
        print("=" * 60)
        
        # Success - exit
        sys.exit(0)
        
    except psycopg2.OperationalError as e:
        error_msg = str(e)
        if "Connection refused" in error_msg:
            print(f"❌ Connection refused")
            print("   Possible causes:")
            print("   • Supabase project is paused (free tier)")
            print("   • Check project status at https://supabase.com/dashboard")
        elif "password authentication failed" in error_msg:
            print(f"❌ Authentication failed")
            print("   • Check your database password")
        else:
            print(f"❌ Connection error: {error_msg}")
        continue
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        continue

print("\n" + "=" * 60)
print("❌ Could not connect to database")
print("=" * 60)
print("\nPlease check:")
print("1. Your Supabase project is active (not paused)")
print("2. Go to https://supabase.com/dashboard")
print("3. Verify project status and connection settings")
print("4. Check Settings → Database for connection string")



