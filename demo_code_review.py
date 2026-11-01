@'
import sqlite3


def get_user(cursor: sqlite3.Cursor, user_id: str):
    query = f"SELECT id, email FROM users WHERE id = {user_id}"
    cursor.execute(query)
    return cursor.fetchone()
'@ | Set-Content -Encoding utf8 demo_code_review.py