import mysql.connector

def get_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="root",
        database="notes_db",
        buffered=True    # <-- ADD THIS LINE
    )
