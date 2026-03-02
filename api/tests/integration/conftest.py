from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from neo4j import AsyncDriver, AsyncGraphDatabase, AsyncSession
from testcontainers.neo4j import Neo4jContainer

from bracc.main import app


def _iter_cypher_statements(path: Path) -> list[str]:
    # Strip comment-only lines before splitting to avoid dropping statements
    # that are preceded by section headers.
    filtered_lines = [
        line for line in path.read_text().splitlines()
        if line.strip() and not line.strip().startswith("//")
    ]
    text = "\n".join(filtered_lines)
    return [stmt.strip() for stmt in text.split(";") if stmt.strip()]


@pytest.fixture(scope="session")
def neo4j_container() -> Neo4jContainer:  # type: ignore[misc]
    """Start a Neo4j container for integration tests."""
    container = Neo4jContainer("neo4j:5-community")
    container.start()
    yield container  # type: ignore[misc]
    container.stop()


@pytest.fixture(scope="session")
def neo4j_uri(neo4j_container: Neo4jContainer) -> str:
    return neo4j_container.get_connection_url()


@pytest.fixture(scope="session")
def neo4j_auth(neo4j_container: Neo4jContainer) -> tuple[str, str]:
    # testcontainers.neo4j API changed: older versions exposed NEO4J_ADMIN_PASSWORD,
    # newer versions expose username/password attributes.
    username = getattr(neo4j_container, "username", "neo4j")
    password = getattr(
        neo4j_container,
        "password",
        getattr(neo4j_container, "NEO4J_ADMIN_PASSWORD", None),
    )
    if password is None:
        msg = "Could not resolve Neo4j testcontainer password"
        raise RuntimeError(msg)
    return (username, password)


@pytest.fixture
async def neo4j_driver(
    neo4j_uri: str, neo4j_auth: tuple[str, str]
) -> AsyncIterator[AsyncDriver]:
    # Function-scoped driver avoids loop affinity issues between async tests.
    driver = AsyncGraphDatabase.driver(neo4j_uri, auth=neo4j_auth)
    async with driver.session() as session:
        # Keep tests deterministic across function scope by resetting test data.
        await session.run("MATCH (n) DETACH DELETE n")
    # Apply schema
    schema_path = Path(__file__).parent.parent.parent.parent / "infra" / "neo4j" / "init.cypher"
    if schema_path.exists():
        async with driver.session() as session:
            for stmt in _iter_cypher_statements(schema_path):
                await session.run(stmt)
    # Seed dev data
    seed_path = (
        Path(__file__).parent.parent.parent.parent / "infra" / "scripts" / "seed-dev.cypher"
    )
    if seed_path.exists():
        async with driver.session() as session:
            for stmt in _iter_cypher_statements(seed_path):
                await session.run(stmt)
    yield driver
    await driver.close()


@pytest.fixture
async def integration_session(neo4j_driver: AsyncDriver) -> AsyncIterator[AsyncSession]:
    async with neo4j_driver.session() as session:
        yield session


@pytest.fixture
async def integration_client(neo4j_driver: AsyncDriver) -> AsyncIterator[AsyncClient]:
    app.state.neo4j_driver = neo4j_driver
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
