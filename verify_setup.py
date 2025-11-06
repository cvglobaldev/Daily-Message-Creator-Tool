#!/usr/bin/env python3
"""
Database Setup Verification Script
This script verifies that the database is properly configured and accessible.
"""

import os

def verify_database():
    """Verify database connection and setup"""
    try:
        import psycopg2

        # Get connection string from environment
        db_url = os.environ.get('DATABASE_URL', 'postgresql://postgres.vvrmvukgtafnymjbhcho@aws-0-us-west-1.pooler.supabase.com:6543/postgres')

        print("🔍 Verifying database setup...\n")

        # Connect to database
        conn = psycopg2.connect(db_url)
        cur = conn.cursor()

        # Check database version
        cur.execute("SELECT version();")
        version = cur.fetchone()[0]
        print(f"✅ Database connected successfully!")
        print(f"   PostgreSQL version: {version.split(',')[0]}\n")

        # Check tables
        cur.execute("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            ORDER BY table_name;
        """)
        tables = cur.fetchall()
        print(f"✅ Found {len(tables)} tables:")
        for table in tables:
            print(f"   - {table[0]}")

        # Check admin users
        cur.execute("SELECT COUNT(*) FROM admin_users;")
        admin_count = cur.fetchone()[0]
        print(f"\n✅ Admin users in database: {admin_count}")

        if admin_count > 0:
            cur.execute("SELECT username, email, role FROM admin_users LIMIT 1;")
            admin = cur.fetchone()
            print(f"   Sample: {admin[0]} ({admin[2]}) - {admin[1]}")

        # Check RLS
        cur.execute("""
            SELECT tablename, rowsecurity
            FROM pg_tables
            WHERE schemaname = 'public'
            ORDER BY tablename;
        """)
        rls_tables = cur.fetchall()
        rls_enabled = sum(1 for t in rls_tables if t[1])
        print(f"\n✅ Row Level Security (RLS) enabled on {rls_enabled}/{len(rls_tables)} tables")

        cur.close()
        conn.close()

        print("\n" + "="*60)
        print("🎉 DATABASE SETUP VERIFIED SUCCESSFULLY!")
        print("="*60)
        print("\nYour Daily Message Creator Tool is ready to use.")
        print("Run: python3 main.py")
        print("\n")

        return True

    except ImportError:
        print("❌ Error: psycopg2 not installed")
        print("   Install with: apt-get install -y python3-psycopg2")
        return False

    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    verify_database()
