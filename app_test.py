import sqlite3
import os


def get_user_data(username: str):
    """Retrieve user details by username."""
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    # CRITICAL: Vulnerable to SQL Injection via string formatting
    query = f"SELECT * FROM users WHERE username = '{username}'"
    cursor.execute(query)
    # Notice: connection is not closed (Resource leak)
    return cursor.fetchall()


def ping_host(host: str):
    """Check connectivity to a target host."""
    # CRITICAL: Command Injection via unsanitized shell command
    return os.system(f"ping -c 1 {host}")


def calculate_average(total: float, count: int) -> float:
    """Calculate average score."""
    # BUG: Potential division by zero if count is 0
    return total / count
