import asyncio
import os
from sqlalchemy.ext.asyncio import create_async_engine
from dotenv import load_dotenv

async def main():
    load_dotenv()
    url = os.getenv("DATABASE_URL").replace("localhost", "127.0.0.1")
    print("Database URL:", url)
    engine = create_async_engine(url)
    try:
        async with engine.connect() as conn:
            result = await conn.execute("SELECT 1")
            print("Successfully connected and queried 1:", result.scalar())
    except Exception as e:
        print("Connection failed:", e)

if __name__ == "__main__":
    asyncio.run(main())
