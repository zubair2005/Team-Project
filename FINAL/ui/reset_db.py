import os
import sqlite3
import sys


def reset_database():
    """Reset the database to clean state."""
    db_path = os.path.join(os.path.dirname(__file__), "data", "camptrack.db")

    if os.path.exists(db_path):
        print(f"Removing existing database at {db_path}")
        os.remove(db_path)

    # Recreate database
    from database import init_db, seed_initial_data
    init_db()
    seed_initial_data()
    print("Database reset complete!")


if __name__ == "__main__":
    reset_database()