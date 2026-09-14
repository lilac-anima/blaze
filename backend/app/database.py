"""Neo4j async database connection module."""

import logging

from neo4j import AsyncGraphDatabase, AsyncDriver
from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """Application settings loaded from environment or .env file."""

    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "burner_social_dev"
    jwt_secret_key: str = "blaze-dev-secret-change-in-production"

    model_config = {"env_prefix": "", "env_file": ".env"}


settings = Settings()

_driver: AsyncDriver | None = None
_NEO4J_FAILED = False  # Cache connection failure to avoid retrying


async def get_driver() -> AsyncDriver | None:
    """Get or create the singleton Neo4j async driver.

    Returns None if Neo4j is unavailable (graceful degradation).
    Once a connection attempt fails, further attempts are skipped
    for the lifetime of the process.
    """
    global _driver, _NEO4J_FAILED
    if _NEO4J_FAILED:
        return None
    if _driver is None:
        try:
            _driver = AsyncGraphDatabase.driver(
                settings.neo4j_uri,
                auth=(settings.neo4j_user, settings.neo4j_password),
                connection_timeout=3,  # 3s timeout — prevents hanging in tests
            )
            # Verify connectivity
            async with _driver.session() as session:
                await session.run("RETURN 1")
            logger.info("Connected to Neo4j at %s", settings.neo4j_uri)
        except Exception as e:
            logger.warning("Neo4j unavailable: %s", e)
            _NEO4J_FAILED = True
            _driver = None
    return _driver


async def close_driver() -> None:
    """Close the Neo4j driver singleton."""
    global _driver
    if _driver is not None:
        await _driver.close()
        _driver = None


async def get_session():
    """Yield a Neo4j async session for dependency injection.

    Raises HTTPException 503 when Neo4j is unavailable.
    Routes can rely on receiving a valid session.
    """
    driver = await get_driver()
    if driver is None:
        from fastapi import HTTPException, status
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database unavailable")
    async with driver.session() as session:
        yield session
