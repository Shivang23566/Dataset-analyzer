import asyncio
from asyncpg import connect, DuplicateDatabaseError

# Config from your settings, but connecting to 'postgres' db to create new db
DB_USER = "postgres"
DB_PASS = "SK124578" 

# Constructing the URL for the default 'postgres' database
DATABASE_URL_DEFAULT = "postgresql://postgres:SK%40124578@localhost/postgres"

async def create_database():
    print(f"Connecting to default 'postgres' database...")
    try:
        # Connect to default 'postgres' database
        conn = await connect(DATABASE_URL_DEFAULT)
        
        try:
            print("Attempting to create database 'dataset_analyser'...")
            # CREATE DATABASE cannot run inside a transaction block, so we probably need to handle this.
            # asyncpg connection is not in a transaction by default unless initialized?
            await conn.execute('CREATE DATABASE dataset_analyser')
            print("✅ Database 'dataset_analyser' created successfully!")
        except DuplicateDatabaseError:
            print("⚠️ Database 'dataset_analyser' already exists.")
        except Exception as e:
            print(f"❌ Failed to create database: {e}")
        finally:
            await conn.close()
            
    except Exception as e:
        print(f"❌ Could not connect to 'postgres' database: {e}")
        print("Please check your password and ensure PostgreSQL is running.")

if __name__ == "__main__":
    asyncio.run(create_database())
