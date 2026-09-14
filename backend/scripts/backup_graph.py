"""
Neo4j Graph Backup / Export Script for Blaze.

Exports the entire graph database to a portable Cypher script and/or JSON dump.

Usage:
    python backend/scripts/backup_graph.py                     # interactive
    python backend/scripts/backup_graph.py --format cypher     # Cypher export
    python backend/scripts/backup_graph.py --format json       # JSON dump
    python backend/scripts/backup_graph.py --format both       # both (default)

Environment variables:
    NEO4J_URI      — Bolt URI (default: bolt://localhost:7687)
    NEO4J_USER     — username (default: neo4j)
    NEO4J_PASSWORD — password (default: burner_social_dev)

Prerequisites:
    pip install neo4j
"""

import argparse
import json
import os
import sys
from datetime import datetime

from neo4j import GraphDatabase


def get_connection():
    """Create a Neo4j driver using env vars or defaults."""
    uri = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
    user = os.environ.get("NEO4J_USER", "neo4j")
    password = os.environ.get("NEO4J_PASSWORD", "burner_social_dev")
    return GraphDatabase.driver(uri, auth=(user, password))


def export_cypher(driver, output_file):
    """Export all nodes and relationships as a portable Cypher script."""
    nodes = {}
    rels = []

    with driver.session() as session:
        # Export all nodes
        result = session.run("MATCH (n) RETURN n, labels(n) AS labels, id(n) AS internal_id")
        for record in result:
            n = record["n"]
            labels = record["labels"]
            internal_id = record["internal_id"]
            props = dict(n)
            node_var = f"n_{internal_id}"

            # Build CREATE statement
            label_str = ":".join(labels) if labels else ""
            props_str = ", ".join(
                f"{k}: ${node_var}_{k}" for k in props.keys()
            )
            cypher = f"CREATE ({node_var}:{label_str} {{{props_str}}})"

            nodes[internal_id] = {
                "node_var": node_var,
                "cypher": cypher,
                "props": props,
                "labels": labels,
            }

        # Export all relationships
        result = session.run(
            """
            MATCH (a)-[r]->(b)
            RETURN a, r, b, type(r) AS rel_type, id(a) AS a_id, id(b) AS b_id, id(r) AS r_id
            """
        )
        for record in result:
            a_id = record["a_id"]
            b_id = record["b_id"]
            r = record["r"]
            rel_type = record["rel_type"]
            rel_props = dict(r)

            a_var = nodes.get(a_id, {}).get("node_var", f"n_{a_id}")
            b_var = nodes.get(b_id, {}).get("node_var", f"n_{b_id}")

            if rel_props:
                props_str = ", ".join(f"{k}: ${a_var}_{k}" for k in rel_props.keys())
                cypher = f"CREATE ({a_var})-[r:{rel_type} {{{props_str}}}]->({b_var})"
            else:
                cypher = f"CREATE ({a_var})-[:{rel_type}]->({b_var})"

            rels.append({
                "cypher": cypher,
                "props": rel_props,
                "a_var": a_var,
                "b_var": b_var,
                "rel_type": rel_type,
            })

    # Write the Cypher script
    with open(output_file, "w") as f:
        f.write(f"// Blaze Graph Backup\n")
        f.write(f"// Generated: {datetime.now().isoformat()}\n")
        f.write(f"// Nodes: {len(nodes)}, Relationships: {len(rels)}\n\n")

        f.write("// ── Nodes ──────────────────────────────────────────────\n\n")
        for node in nodes.values():
            f.write(f"// Labels: {', '.join(node['labels'])}\n")
            f.write(f"// Properties: {json.dumps({k: str(v) for k, v in node['props'].items()})}\n")
            f.write(f"{node['cypher']}\n\n")

        f.write("// ── Relationships ──────────────────────────────────────────\n\n")
        for rel in rels:
            f.write(f"// Type: {rel['rel_type']}\n")
            if rel["props"]:
                f.write(f"// Properties: {json.dumps({k: str(v) for k, v in rel['props'].items()})}\n")
            f.write(f"{rel['cypher']}\n\n")

    return len(nodes), len(rels)


def export_json(driver, output_file):
    """Export all data as a JSON document."""
    with driver.session() as session:
        # Export all nodes
        nodes_result = session.run(
            "MATCH (n) RETURN n, labels(n) AS labels, id(n) AS internal_id"
        )
        nodes = []
        for record in nodes_result:
            n = record["n"]
            nodes.append({
                "id": record["internal_id"],
                "labels": list(record["labels"]),
                "properties": {k: str(v) for k, v in dict(n).items()},
            })

        # Export all relationships
        rels_result = session.run(
            "MATCH (a)-[r]->(b) RETURN id(a) AS source, id(b) AS target, type(r) AS type, r"
        )
        rels = []
        for record in rels_result:
            r = record["r"]
            rels.append({
                "source": record["source"],
                "target": record["target"],
                "type": record["type"],
                "properties": {k: str(v) for k, v in dict(r).items()},
            })

    data = {
        "exported_at": datetime.now().isoformat(),
        "node_count": len(nodes),
        "relationship_count": len(rels),
        "nodes": nodes,
        "relationships": rels,
    }

    with open(output_file, "w") as f:
        json.dump(data, f, indent=2, default=str)

    return len(nodes), len(rels)


def main():
    parser = argparse.ArgumentParser(
        description="Export Blaze Neo4j graph data for backup"
    )
    parser.add_argument(
        "--format",
        choices=["cypher", "json", "both"],
        default="both",
        help="Export format (default: both)",
    )
    parser.add_argument(
        "--output-dir",
        default="backend/backups",
        help="Output directory (default: backend/backups)",
    )
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    print("Connecting to Neo4j...")
    driver = get_connection()

    # Verify connectivity
    try:
        with driver.session() as session:
            result = session.run("MATCH (n) RETURN count(n) AS count")
            record = result.single()
            print(f"Connected. Current node count: {record['count']}")
    except Exception as e:
        print(f"Failed to connect to Neo4j: {e}")
        sys.exit(1)

    exports = []

    if args.format in ("cypher", "both"):
        output = os.path.join(args.output_dir, f"burner_social_backup_{timestamp}.cypher")
        nodes, rels = export_cypher(driver, output)
        exports.append((output, nodes, rels, "Cypher"))

    if args.format in ("json", "both"):
        output = os.path.join(args.output_dir, f"burner_social_backup_{timestamp}.json")
        nodes, rels = export_json(driver, output)
        exports.append((output, nodes, rels, "JSON"))

    for path, nodes, rels, fmt in exports:
        print(f"\n{fmt} export saved: {path}")
        print(f"  Nodes: {nodes}")
        print(f"  Relationships: {rels}")

    print("\nBackup complete!")
    driver.close()


if __name__ == "__main__":
    main()
