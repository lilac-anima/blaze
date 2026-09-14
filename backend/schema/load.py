"""Load the Cypher schema migration into Neo4j."""

import asyncio
from pathlib import Path

from neo4j import AsyncGraphDatabase

from backend.app.database import settings


async def load_migration():
    """Read and execute the Cypher schema migration."""
    migration_path = Path(__file__).parent / "migration.cypher"
    cypher = migration_path.read_text(encoding="utf-8")

    driver = AsyncGraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.neo4j_user, settings.neo4j_password),
    )

    try:
        # Split on semicolons and execute each statement separately
        statements = [
            stmt.strip()
            for stmt in cypher.split(";")
            if stmt.strip() and not stmt.strip().startswith("//") and not stmt.strip().startswith("#")
        ]

        async with driver.session() as session:
            for stmt in statements:
                if stmt:
                    await session.run(stmt)
                    print(f"  ✓ Executed: {stmt[:80]}...")

        print("\n✅ Schema migration complete!")
    finally:
        await driver.close()


if __name__ == "__main__":
    asyncio.run(load_migration())
