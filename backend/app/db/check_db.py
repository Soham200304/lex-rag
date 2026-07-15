from sqlalchemy import text

from app.db.database import engine


async def check_database():
    async with engine.begin() as conn:
        await conn.execute(text("SELECT 1"))