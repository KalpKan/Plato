#!/usr/bin/env python3
"""Check tables in Supabase database."""

import sys

try:
    import psycopg2
except ImportError:
    print("Installing psycopg2-binary...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "psycopg2-binary"])
    import psycopg2

# Connection string
conn_str = 'postgresql://postgres:Kk4132231441@db.ftcqzuzpyebtwihizqfl.supabase.co:5432/postgres'

try:
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
    
    print('=' * 60)
    print('Tables in your Supabase database:')
    print('=' * 60)
    if tables:
        for table in tables:
            print(f'  ✓ {table[0]}')
    else:
        print('  (No tables found in public schema)')
    
    # Get table details if any exist
    if tables:
        print('\n' + '=' * 60)
        print('Table Details:')
        print('=' * 60)
        for table in tables:
            table_name = table[0]
            cur.execute(f"""
                SELECT column_name, data_type, is_nullable, column_default
                FROM information_schema.columns
                WHERE table_name = '{table_name}'
                ORDER BY ordinal_position;
            """)
            columns = cur.fetchall()
            print(f'\n📋 {table_name}:')
            for col in columns:
                nullable = 'NULL' if col[2] == 'YES' else 'NOT NULL'
                default = f' DEFAULT {col[3]}' if col[3] else ''
                print(f'   • {col[0]}: {col[1]} ({nullable}{default})')
            
            # Get row count
            cur.execute(f'SELECT COUNT(*) FROM "{table_name}";')
            count = cur.fetchone()[0]
            print(f'   📊 Rows: {count}')
    else:
        print('\n💡 No tables found. Ready to create tables!')
        print('   I can help you create the extraction_cache and user_choices tables.')
    
    cur.close()
    conn.close()
    print('\n' + '=' * 60)
    print('✅ Connection successful!')
    print('=' * 60)
    
except psycopg2.OperationalError as e:
    print(f'❌ Connection error: {e}')
    print('\nPlease check:')
    print('  1. Your Supabase project is active')
    print('  2. Connection string is correct')
    print('  3. Your IP is not blocked')
except Exception as e:
    print(f'❌ Error: {e}')
    import traceback
    traceback.print_exc()


