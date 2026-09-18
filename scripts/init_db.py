"""Create Plato's two cache tables in the Postgres database named by DATABASE_URL.

Safe to run more than once (CREATE TABLE IF NOT EXISTS). Usage:

    DATABASE_URL="postgresql://..." python scripts/init_db.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.supabase_cache import SupabaseCacheManager  # noqa: E402


def main() -> int:
    url = os.getenv("DATABASE_URL")
    if not url:
        print("DATABASE_URL is not set", file=sys.stderr)
        return 1
    mgr = SupabaseCacheManager(url)
    mgr.ensure_schema()
    conn = mgr._get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = 'public' ORDER BY table_name"
        )
        names = [r[0] for r in cur.fetchall()]
    finally:
        conn.close()
    print("tables:", ", ".join(names))
    print("ping:", mgr.ping())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
