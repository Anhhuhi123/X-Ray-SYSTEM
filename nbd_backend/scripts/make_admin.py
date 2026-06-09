import asyncio
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import select, update

from app.db import User, async_session_maker


async def make_admin(email: str):
    async with async_session_maker() as session:
        result = await session.execute(select(User).filter(User.email == email))
        user = result.scalars().first()

        if not user:
            print(f"User with email {email} not found.")
            return

        await session.execute(
            update(User).where(User.email == email).values(is_superuser=True)
        )
        await session.commit()
        print(f"Success: User {email} is now a superuser.")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python make_admin.py <email>")
        sys.exit(1)

    email = sys.argv[1]
    asyncio.run(make_admin(email))
