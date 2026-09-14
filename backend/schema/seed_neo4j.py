"""Load the Cypher migration into Neo4j, statement by statement.
Replaces // comment lines with semicolons to properly separate
data CREATE statements that only have a ; after the last one."""
from neo4j import GraphDatabase


def load_migration():
    migration_path = "C:/Users/Lilac/Projects/burner-social/backend/schema/migration.cypher"
    with open(migration_path, encoding="utf-8") as f:
        raw = f.read()

    # Remove #-style shell comment lines
    lines = [l for l in raw.split("\n") if not l.strip().startswith("#")]

    # Replace // comment lines with semicolons to act as statement separators
    processed = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("//"):
            processed.append(";")  # acts as statement boundary
        elif stripped:
            processed.append(line)
    cleaned = "\n".join(processed)

    # Split on semicolons
    raw_statements = [s.strip() for s in cleaned.split(";") if s.strip()]

    driver = GraphDatabase.driver(
        "bolt://localhost:7687",
        auth=("neo4j", "burner_social_dev"),
    )

    with driver.session() as session:
        executed = 0
        failed = 0
        for i, stmt in enumerate(raw_statements):
            if not stmt:
                continue
            try:
                session.run(stmt)
                executed += 1
                preview = stmt[:100].replace("\n", " ")
                if executed <= 30 or executed % 10 == 0:
                    print(f"  ✓ [{i}] {preview}...")
            except Exception as e:
                failed += 1
                print(f"  ✗ [{i}] ERROR: {e}")
                print(f"    Stmt: {stmt[:120]}")

    driver.close()
    print(f"\n✅ Done! {executed} statements executed, {failed} failed.")


if __name__ == "__main__":
    load_migration()
