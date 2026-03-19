import asyncio
import os
from dotenv import load_dotenv

load_dotenv()
os.environ["DATABASE_URL"] = "postgresql://postgres:password@localhost:5432/ai_guardian"

from app.services.database.db import init_db, get_conn
from app.services.database.auth import hash_password

async def main():
    await init_db()
    hashed_pw = hash_password("admin123")
    query = """
    INSERT INTO users (username, email, hashed_password, role) 
    VALUES ($1, $2, $3, $4) 
    ON CONFLICT (email) DO UPDATE SET hashed_password = EXCLUDED.hashed_password, role = EXCLUDED.role;
    """
    try:
        async with get_conn() as conn:
            await conn.execute(query, "admin", "admin@guardian.local", hashed_pw, "admin")
            print("==================================================")
            print(" ✅ Admin user created successfully")
            print(" ✨ Username / Email:   admin@guardian.local")
            print(" 🔑 Password:           admin123")
            print("==================================================")
    except Exception as e:
        print(f"Failed to create admin: {e}")

if __name__ == "__main__":
    asyncio.run(main())
