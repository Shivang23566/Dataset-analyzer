import asyncio
import os
import re

# Config from environment variables — never hardcode credentials
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASS = os.getenv("DB_PASS", "")  # Must be set via environment
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_NAME = os.getenv("DB_NAME", "dataset_analyser")

_SAFE_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,62}$")


async def create_database():
    """Create the application database using asyncpg (PostgreSQL).
    Skipped automatically when using SQLite (the default for local dev).
    """
    if not DB_PASS:
        print("DB_PASS environment variable is not set.")
        print("For local SQLite development, the database is auto-created on startup.")
        print("Set DB_USER, DB_PASS, DB_HOST, DB_NAME env vars for PostgreSQL.")
        return

    if not _SAFE_IDENTIFIER.match(DB_NAME):
        print(f"Invalid DB_NAME '{DB_NAME}'. Must be a valid SQL identifier.")
        return

    from asyncpg import connect, DuplicateDatabaseError
    from urllib.parse import quote_plus

    encoded_pass = quote_plus(DB_PASS)
    database_url = f"postgresql://{DB_USER}:{encoded_pass}@{DB_HOST}/postgres"

    print("Connecting to default 'postgres' database...")
    try:
        conn = await connect(database_url)
        try:
            print(f"Attempting to create database '{DB_NAME}'...")
            await conn.execute(f'CREATE DATABASE "{DB_NAME}"')
            print(f"Database '{DB_NAME}' created successfully!")
        except DuplicateDatabaseError:
            print(f"Database '{DB_NAME}' already exists.")
        except Exception as e:
            print(f"Failed to create database: {e}")
        finally:
            await conn.close()
    except Exception as e:
        print(f"Could not connect to 'postgres' database: {e}")
        print("Please check your credentials and ensure PostgreSQL is running.")


if __name__ == "__main__":
    asyncio.run(create_database())
