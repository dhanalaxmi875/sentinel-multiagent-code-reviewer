import sqlite3

def find_user():
    username = input("Enter username: ")
    connection = sqlite3.connect("app.db")
    cursor = connection.cursor()

    query = f"SELECT * FROM users WHERE username = '{username}'"
    cursor.execute(query)

    return cursor.fetchall()