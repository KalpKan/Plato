#!/usr/bin/env python3
"""Query Supabase database tables."""

import psycopg2

# Try connection pooler first (more reliable)
connection_strings = [
    # Connection pooler (recommended)
    "${DATABASE_URL}",
    # Direct connection
    "${DATABASE_URL}",
]

for i, conn_str in enumerate(connection_strings, 1):
    method = "Connection Pooler" if i == 1 else "Direct Connection"
    print(f"\n{'='*60}")
    print(f"Trying {method}...")
    print('='*60)
    
    try:
        conn = psycopg2.connect(conn_str, connect_timeout=5)
        cur = conn.cursor()
        
        # Get all tables
        cur.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name;
        """)
        
        tables = cur.fetchall()
        
        print(f"\n✅ Connection successful using {method}!")
        print('='*60)
        print(f"\n📊 Tables in your Supabase database:")
        print('-'*60)
        
        if tables:
            for table in tables:
                print(f"  ✓ {table[0]}")
            
            # Get detailed info for each table
            print("\n" + '='*60)
            print("📋 Table Details:")
            print('='*60)
            
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
                print('-'*60)
                
                for col in columns:
                    col_name, data_type, nullable, default = col
                    nullable_str = "NULL" if nullable == "YES" else "NOT NULL"
                    default_str = f" DEFAULT {default}" if default else ""
                    print(f"   • {col_name:25} {data_type:20} ({nullable_str}{default_str})")
                
                # Get row count
                try:
                    cur.execute(f'SELECT COUNT(*) FROM "{table_name}";')
                    count = cur.fetchone()[0]
                    print(f"   📊 Total rows: {count}")
                except:
                    print(f"   📊 (Could not get row count)")
        else:
            print("\n💡 No tables found in the 'public' schema.")
            print("   Your database is ready for table creation!")
            print("\n   I can help you create:")
            print("   • extraction_cache - for storing PDF extraction results")
            print("   • user_choices - for storing user selections")
        
        cur.close()
        conn.close()
        
        print("\n" + '='*60)
        print("✅ Query completed successfully!")
        print('='*60)
        exit(0)
        
    except psycopg2.OperationalError as e:
        error_msg = str(e)
        if "Connection refused" in error_msg or "timeout" in error_msg.lower():
            print(f"❌ Connection refused or timed out")
            print("   • Supabase project might be paused")
            print("   • Check: https://supabase.com/dashboard/project/ftcqzuzpyebtwihizqfl")
        elif "password authentication failed" in error_msg:
            print(f"❌ Authentication failed")
            print("   • Check your database password in Supabase dashboard")
        else:
            print(f"❌ Connection error: {error_msg[:100]}")
        continue
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        continue

print("\n" + '='*60)
print("❌ Could not connect to database")
print('='*60)
print("\nPlease check:")
print("1. Your Supabase project is active (not paused)")
print("   → https://supabase.com/dashboard/project/ftcqzuzpyebtwihizqfl")
print("2. If paused, click 'Restore' button and wait 1-2 minutes")
print("3. Verify connection string in Settings → Database")


