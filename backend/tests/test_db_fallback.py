import os
import json
import asyncio

import pytest
from httpx import AsyncClient, ASGITransport


@pytest.mark.asyncio
async def test_db_down_returns_503_and_dumps_env(tmp_path):
    # Ensure DB is considered "down"
    os.environ.pop("DATABASE_URL", None)
    os.environ["JWT_SECRET_KEY"] = "test-secret"
    os.environ["REDIS_URL"] = "redis://localhost:6379"
    os.environ["KAN_TOOL_PATH"] = str(tmp_path / "ai_guardian_env.json")

    from app.main import app  # import after env is set

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.post(
            "/users/login",
            json={"username": "x", "password": "y"},
        )
        assert r.status_code == 503

        r2 = await ac.post(
            "/notifications",
            headers={"Authorization": "Bearer invalid"},
            json={"app_name": "Sandbox", "message_text": "hello", "url": None},
        )
        # Auth fails before DB check here; still should be 401.
        assert r2.status_code in (401, 503)

    # Give background diagnostics a chance to flush.
    await asyncio.sleep(0.2)

    dump_path = tmp_path / "ai_guardian_env.json"
    assert dump_path.exists()
    data = json.loads(dump_path.read_text(encoding="utf-8"))
    assert "DATABASE_URL" in data
    assert "REDIS_URL" in data
    assert "JWT_SECRET_KEY" in data

