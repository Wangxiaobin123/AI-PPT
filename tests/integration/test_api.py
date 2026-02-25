"""Integration tests for API endpoints."""
import pytest
from httpx import AsyncClient, ASGITransport
from src.main import create_app
from src.skills.registry import SkillRegistry


@pytest.fixture
def app():
    application = create_app()
    # Manually initialize skills registry since lifespan doesn't run in test
    registry = SkillRegistry()
    registry.discover("src/skills/public", "src/skills/user")
    application.state.skills_registry = registry
    return application


@pytest.fixture
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.mark.asyncio
async def test_health_check(client):
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


@pytest.mark.asyncio
async def test_list_skills(client):
    response = await client.get("/api/v1/skills")
    assert response.status_code == 200
    data = response.json()
    assert "skills" in data
    assert len(data["skills"]) > 0


@pytest.mark.asyncio
async def test_submit_intent(client):
    response = await client.post(
        "/api/v1/intent",
        json={"text": "Create a presentation about technology"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ("ready", "needs_clarification")


@pytest.mark.asyncio
async def test_generate_pptx(client):
    response = await client.post(
        "/api/v1/generate",
        json={
            "format": "pptx",
            "content": "# Test\n\n## Slide 1\n- Point 1\n- Point 2",
            "content_format": "markdown",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert len(data["files"]) > 0
