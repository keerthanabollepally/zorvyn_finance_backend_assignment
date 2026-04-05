"""Promote a user to admin (no sqlite3 CLI required). Usage:
    python scripts/promote_admin.py you@example.com
Run from the finance_backend directory (where finance.db lives).
"""
import sqlite3
import sys
from pathlib import Path


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: python scripts/promote_admin.py <email>", file=sys.stderr)
        sys.exit(1)
    email = sys.argv[1].strip()
    root = Path(__file__).resolve().parent.parent
    db_path = root / "finance.db"
    if not db_path.is_file():
        print(f"No database at {db_path}. Start the app once and sign up first.", file=sys.stderr)
        sys.exit(1)
    conn = sqlite3.connect(str(db_path))
    cur = conn.execute("UPDATE user SET role = 'admin' WHERE email = ?", (email,))
    conn.commit()
    if cur.rowcount == 0:
        print(f"No user found with email: {email}")
        sys.exit(1)
    row = conn.execute(
        "SELECT id, email, role, is_active FROM user WHERE email = ?", (email,)
    ).fetchone()
    conn.close()
    print("Updated:", row)


if __name__ == "__main__":
    main()
