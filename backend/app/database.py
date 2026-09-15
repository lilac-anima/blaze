"""Persistence configuration and repository boundary.

SQLite is the default local store. Neo4j remains available as a compatibility
backend for the existing graph routes and can be selected explicitly with
``STORAGE_BACKEND=neo4j``.
"""

from __future__ import annotations

import json
import logging
import re
import sqlite3
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from pydantic_settings import BaseSettings

try:  # Neo4j is an optional compatibility backend.
    from neo4j import AsyncGraphDatabase, AsyncDriver
except ImportError:  # pragma: no cover - exercised by SQLite-only installs
    AsyncGraphDatabase = None
    AsyncDriver = Any

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    storage_backend: str = "sqlite"
    sqlite_path: str = "./data/blaze.sqlite3"
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "burner_social_dev"
    jwt_secret_key: str = "blaze-dev-secret-change-in-production"

    model_config = {"env_prefix": "", "env_file": ".env"}


settings = Settings()
_driver: AsyncDriver | None = None
_NEO4J_FAILED = False


SCHEMA_PATH = Path(__file__).resolve().parents[1] / "schema" / "sqlite.sql"
SCHEMA = SCHEMA_PATH.read_text(encoding="utf-8")


class _Result:
    """Small Neo4j AsyncResult-compatible wrapper for SQLite compatibility."""
    def __init__(self, rows: list[dict[str, Any]]):
        self.rows = rows

    async def single(self):
        return self.rows[0] if self.rows else None

    def __aiter__(self):
        return self._iterate()

    async def _iterate(self):
        for row in self.rows:
            yield row


class SQLiteRepository:
    """Small async-compatible repository used by the compatibility API.

    sqlite3 operations are short and serialized by SQLite's connection lock;
    keeping this boundary synchronous internally avoids adding an ORM solely
    for the local-first store while allowing FastAPI's async dependency shape.
    """

    is_sqlite = True

    def __init__(self, path: str):
        if path != ":memory:":
            Path(path).expanduser().parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path, check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.db.executescript(SCHEMA)
        self.db.commit()

    async def run(self, query: str, **params):
        """Execute the small Cypher subset used by the legacy API routers.

        Nodes and relationships are stored as JSON rows so the existing API can
        migrate incrementally without making Neo4j a runtime requirement.
        """
        q = " ".join(query.split())
        self._active_query = q
        if "CREATE (" in q and "RETURN" in q and "CREATE (u:User" in q:
            return await self._create_node("User", params, "u")
        if "CREATE (p:Post" in q:
            result = await self._create_node("Post", params, "p")
            if ")-[:" in q:
                await self._create_relationship(q, params)
            return result
        if "CREATE (e:Event" in q:
            return await self._create_node("Event", params, "e")
        if "CREATE (c:Camp" in q:
            return await self._create_node("Camp", params, "c")
        if "CREATE (g:Group" in q:
            return await self._create_node("Group", params, "g")
        if "SET " in q and "MATCH (" in q:
            return await self._set_node(q, params)
        if "DETACH DELETE" in q and "MATCH (" in q:
            return await self._delete_node(q, params)
        if "DELETE r" in q:
            return await self._delete_relationship(q, params)
        if "CREATE (" in q and ")-[:" in q:
            return await self._create_relationship(q, params)
        return await self._match(q, params)

    def _node_id(self, label: str, params: dict[str, Any]) -> str:
        keys = {"User": "user_id", "Post": "post_id", "Event": "event_id", "Camp": "camp_id", "Group": "group_id"}
        return str(params.get(keys[label]) or params.get("id") or params.get(keys[label].replace("_id", "")))

    async def _create_node(self, label: str, params: dict[str, Any], alias: str) -> _Result:
        node_id = self._node_id(label, params)
        now = params.get("created_at") or __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat()
        fields = {k: v for k, v in params.items() if k not in {"password_hash"}}
        fields.setdefault("created_at", now)
        self.db.execute("INSERT OR REPLACE INTO graph_nodes(label,node_id,data) VALUES (?,?,?)", (label, node_id, json.dumps(fields, default=str)))
        self.db.commit()
        # Keep the append-only local event log and materialized projection in
        # step with compatibility API writes. Neo4j users still use its native
        # transaction path; SQLite gets durable replayable records.
        if label != "User":
            author = fields.get("created_by") or fields.get("author_id") or "local"
            event = {
                "event_id": f"local-{label.lower()}-{node_id}",
                "type": f"{label.lower()}.created",
                "author": str(author),
                "object_id": node_id,
                "created_at": str(now),
                "payload": fields,
            }
            await self.append_event(event, str(now))
            await self.save_projection(label.lower(), node_id, fields, str(now))
        return _Result([{alias: fields}])

    def _find_nodes(self, label: str, params: dict[str, Any]) -> list[dict[str, Any]]:
        rows = self.db.execute("SELECT node_id,data FROM graph_nodes WHERE label=?", (label,)).fetchall()
        result = []
        for row in rows:
            data = json.loads(row["data"])
            data.setdefault("node_id", row["node_id"])
            if all(data.get(k) == v for k, v in params.items() if k.endswith("_id") or k in {"username", "email", "post_id", "event_id", "camp_id", "group_id"}):
                result.append(data)
        return result

    async def _match(self, q: str, params: dict[str, Any]) -> _Result:
        # Feed queries project posts under the ``post`` alias after several
        # optional graph traversals. SQLite keeps the same response shape and
        # returns local posts until friendship/camp projections are migrated.
        if "RETURN post, author" in q:
            rows = []
            for post in self._find_nodes("Post", {}):
                author_row = self.db.execute(
                    "SELECT data FROM graph_nodes WHERE label='User' AND node_id=?",
                    (post.get("author_id"),),
                ).fetchone()
                author = json.loads(author_row["data"]) if author_row else None
                rows.append({
                    "post": post,
                    "author": author,
                    "like_count": self._relationship_count("LIKES", to_id=post.get("post_id")),
                    "comment_count": self._relationship_count("COMMENT_ON", to_id=post.get("post_id")),
                    "is_liked_by_me": False,
                })
            return _Result(rows)
        # Post listings traverse User-[:POSTED]->Post and return both sides.
        # Handle that shape before selecting the first label in the query.
        if "POSTED" in q and "(p:Post)" in q and "RETURN p" in q:
            posts = self._find_nodes("Post", {"author_id": params.get("user_id")})
            rows = []
            for post in posts:
                author_row = self.db.execute(
                    "SELECT data FROM graph_nodes WHERE label='User' AND node_id=?",
                    (post.get("author_id"),),
                ).fetchone()
                author = json.loads(author_row["data"]) if author_row else None
                rows.append({
                    "p": post,
                    "author": author,
                    "like_count": self._relationship_count("LIKES", to_id=post.get("post_id")),
                    "comment_count": self._relationship_count("COMMENT_ON", to_id=post.get("post_id")),
                })
            return _Result(rows)
        # Relationship existence checks (membership, likes, friendship).
        relation = re.search(r"-\[r:(\w+)\]", q)
        if relation and "RETURN u" in q and "AS role" in q:
            rel_type = relation.group(1)
            group_id = params.get("gid")
            rows = []
            for edge in self.db.execute("SELECT * FROM graph_relationships WHERE rel_type=? AND to_id=?", (rel_type, group_id)):
                user = self._node_by_id("User", edge["from_id"])
                if user:
                    data = json.loads(edge["data"] or "{}")
                    rows.append({"u": user, "role": data.get("role")})
            return _Result(rows)
        if relation and "RETURN r" in q:
            rel_type = relation.group(1)
            constraints = []
            for _alias, _label, field, placeholder in re.findall(
                r"\(([A-Za-z]+):(User|Post|Event|Camp|Group)\s*\{\s*(\w+)\s*:\s*\$(\w+)", q
            ):
                if placeholder in params:
                    constraints.append((field, str(params[placeholder])))
            rows = []
            for edge in self.db.execute("SELECT * FROM graph_relationships WHERE rel_type=?", (rel_type,)):
                edge_ids = {str(edge["from_id"]), str(edge["to_id"])}
                if constraints and not all(value in edge_ids for _field, value in constraints):
                    continue
                rows.append({"r": dict(edge)})
            return _Result(rows)

        label_match = re.search(r"\([A-Za-z]+:(User|Post|Event|Camp|Group|Comment)", q)
        if not label_match:
            return _Result([])
        label = label_match.group(1)
        alias = re.search(r"\(([A-Za-z]+):" + label, q).group(1)
        criteria = {}
        prop_block = re.search(rf"\({alias}:{label} \{{([^}}]+)\}}", q)
        if prop_block:
            for field, placeholder in re.findall(r"(\w+)\s*:\s*\$(\w+)", prop_block.group(1)):
                if placeholder in params:
                    criteria[field] = params[placeholder]
        for field, placeholder in re.findall(rf"{alias}\.(\w+)\s*=\s*\$(\w+)", q):
            if placeholder in params:
                criteria[field] = params[placeholder]
        nodes = self._find_nodes(label, criteria)
        if "RETURN count" in q:
            key = re.search(r"AS ([A-Za-z_]+)", q)
            return _Result([{key.group(1) if key else "count": len(nodes)}])
        if "RETURN collect" in q:
            return _Result([{"friend_ids": [n.get("user_id") for n in nodes]}])
        rows = []
        for node in nodes:
            if "-[r:LIKES]->" in q:
                target = params.get("pid") or params.get("post_id")
                if not self.db.execute("SELECT 1 FROM graph_relationships WHERE rel_type='LIKES' AND from_id=? AND to_id=?", (node.get("user_id"), target)).fetchone():
                    continue
            row = {alias: node}
            if "OPTIONAL MATCH" in q and label == "User":
                profile = self.db.execute("SELECT * FROM burner_profiles WHERE user_id=?", (node.get("user_id"),)).fetchone()
                row["p"] = dict(profile) if profile else None
            if label == "Post" and "author:User" in q:
                rel = self.db.execute("SELECT from_id FROM graph_relationships WHERE rel_type='POSTED' AND to_id=? LIMIT 1", (node.get("post_id"),)).fetchone()
                author = self.db.execute("SELECT data FROM graph_nodes WHERE label='User' AND node_id=?", (rel["from_id"],)).fetchone() if rel else None
                row["author"] = json.loads(author["data"]) if author else None
            if "like_count" in q:
                row["like_count"] = self._relationship_count("LIKES", to_id=node.get("post_id"))
                row["comment_count"] = self._relationship_count("COMMENT_ON", to_id=node.get("post_id"))
            for field, output in re.findall(rf"{alias}\.(\w+)\s+AS\s+(\w+)", q):
                row[output] = node.get(field)
            # The legacy routers use ``WITH ... count(...) AS ...`` for
            # aggregate responses.  Preserve those projected fields in the
            # SQLite compatibility result rather than silently dropping them.
            count_match = re.search(r"count\(DISTINCT\s+\w+\)\s+AS\s+(\w+)", q)
            if count_match:
                rel_match = re.search(r"-\[\w+:([A-Z_]+)\]->", q)
                if rel_match:
                    row[count_match.group(1)] = self._relationship_count(
                        rel_match.group(1), to_id=node.get({
                            "User": "user_id", "Post": "post_id", "Event": "event_id",
                            "Camp": "camp_id", "Group": "group_id", "Comment": "comment_id",
                        }.get(label, "node_id"))
                    )
            # Camp responses optionally return their hosted event.
            if label == "Camp" and "RETURN c, member_count, e" in q:
                hosted = self.db.execute(
                    "SELECT to_id FROM graph_relationships WHERE rel_type='HOSTED_BY' AND from_id=? LIMIT 1",
                    (node.get("camp_id"),),
                ).fetchone()
                if hosted:
                    event = self.db.execute(
                        "SELECT data FROM graph_nodes WHERE label='Event' AND node_id=?",
                        (hosted["to_id"],),
                    ).fetchone()
                    row["e"] = json.loads(event["data"]) if event else None
            rows.append(row)
        return _Result(rows)

    def _node_by_id(self, label: str, node_id: str | None) -> dict[str, Any] | None:
        if node_id is None:
            return None
        row = self.db.execute(
            "SELECT node_id, data FROM graph_nodes WHERE label=? AND node_id=?",
            (label, node_id),
        ).fetchone()
        if not row:
            return None
        data = json.loads(row["data"])
        data.setdefault("node_id", row["node_id"])
        return data

    def _relationship_count(self, rel_type: str, *, to_id: str) -> int:
        return self.db.execute("SELECT COUNT(*) AS n FROM graph_relationships WHERE rel_type=? AND to_id=?", (rel_type, to_id)).fetchone()["n"]

    async def _set_node(self, q: str, params: dict[str, Any]) -> _Result:
        label_match = re.search(r"MATCH \([A-Za-z]+:(\w+)", q)
        if not label_match: return _Result([])
        label = label_match.group(1)
        nodes = self._find_nodes(label, self._criteria_from_query(q, params))
        id_key = {"User":"user_id", "Post":"post_id", "Event":"event_id", "Camp":"camp_id", "Group":"group_id"}[label]
        for node in nodes:
            for key, value in params.items():
                if key.endswith("_id") and node.get(key) == value: continue
                if key in {"event_id", "camp_id", "group_id", "post_id", "user_id"}: continue
                node[key] = value
            self.db.execute("UPDATE graph_nodes SET data=? WHERE label=? AND node_id=?", (json.dumps(node, default=str), label, node.get(id_key)))
            if label != "User":
                await self._record_graph_event(label, node[id_key], "updated", node)
        self.db.commit()
        return _Result([])

    async def _delete_node(self, q: str, params: dict[str, Any]) -> _Result:
        label = re.search(r"MATCH \([A-Za-z]+:(\w+)", q).group(1)
        nodes = self._find_nodes(label, self._criteria_from_query(q, params))
        id_key = {"User":"user_id","Post":"post_id","Event":"event_id","Camp":"camp_id","Group":"group_id"}[label]
        for node in nodes:
            self.db.execute("DELETE FROM graph_nodes WHERE label=? AND node_id=?", (label, node[id_key]))
            self.db.execute("DELETE FROM graph_relationships WHERE (from_label=? AND from_id=?) OR (to_label=? AND to_id=?)", (label,node[id_key],label,node[id_key]))
            if label != "User":
                await self._record_graph_event(label, node[id_key], "deleted", {**node, "tombstoned": True})
        self.db.commit()
        return _Result([])

    async def _record_graph_event(self, label: str, node_id: str, action: str, data: dict[str, Any]) -> None:
        created_at = str(data.get("updated_at") or data.get("created_at") or __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat())
        event = {"event_id": f"local-{label.lower()}-{action}-{node_id}-{uuid.uuid4().hex[:12]}", "type": f"{label.lower()}.{action}", "author": str(data.get("created_by") or data.get("author_id") or "local"), "object_id": str(node_id), "created_at": created_at, "payload": data}
        await self.append_event(event, created_at)
        await self.save_projection(label.lower(), str(node_id), data, created_at)

    async def _create_relationship(self, q: str, params: dict[str, Any]) -> _Result:
        rel_match = re.search(r"-\[:(\w+)", q)
        if not rel_match:
            return _Result([])
        rel = rel_match.group(1)
        endpoints = re.findall(r"\(([A-Za-z]+):(\w+)\s*\{\s*(\w+)\s*:\s*\$(\w+)", q)
        if len(endpoints) >= 2:
            from_alias, from_label, from_key, from_param = endpoints[0]
            to_alias, to_label, to_key, to_param = endpoints[1]
            from_id, to_id = params.get(from_param), params.get(to_param)
        else:
            from_label = to_label = "User"
            ids = [v for k, v in params.items() if k.endswith("_id")]
            from_id, to_id = (ids + [None, None])[:2]
        if from_id is not None and to_id is not None:
            self.db.execute("INSERT INTO graph_relationships(rel_type,from_label,from_id,to_label,to_id,data) VALUES (?,?,?,?,?,?)", (rel,from_label,from_id,to_label,to_id,json.dumps(params, default=str)))
            self.db.commit()
        return _Result([])

    async def _delete_relationship(self, q: str, params: dict[str, Any]) -> _Result:
        rel = re.search(r"\[:(\w+)\]", q).group(1)
        ids = [v for k,v in params.items() if k.endswith("_id")]
        cur = self.db.execute("DELETE FROM graph_relationships WHERE rel_type=? AND from_id=? AND to_id=?", (rel, ids[0], ids[1])) if len(ids) >= 2 else None
        self.db.commit()
        return _Result([{"deleted": cur.rowcount if cur else 0}])

    @staticmethod
    def _criteria_from_query(q: str, params: dict[str, Any]) -> dict[str, Any]:
        criteria = {}
        for field, placeholder in re.findall(r"(\w+)\s*:\s*\$(\w+)", q):
            if placeholder in params:
                criteria[field] = params[placeholder]
        for field, placeholder in re.findall(r"\w+\.(\w+)\s*=\s*\$(\w+)", q):
            if placeholder in params:
                criteria[field] = params[placeholder]
        return criteria

    async def close(self) -> None:
        self.db.close()

    async def find_user(self, login: str) -> dict[str, Any] | None:
        row = self.db.execute(
            "SELECT * FROM users WHERE username = ? OR email = ? LIMIT 1", (login, login)
        ).fetchone()
        return dict(row) if row else None

    async def username_exists(self, username: str) -> bool:
        return self.db.execute("SELECT 1 FROM users WHERE username = ?", (username,)).fetchone() is not None

    async def email_exists(self, email: str, except_user_id: str | None = None) -> bool:
        query = "SELECT 1 FROM users WHERE email = ?"
        params: list[Any] = [email]
        if except_user_id:
            query += " AND user_id <> ?"
            params.append(except_user_id)
        return self.db.execute(query, params).fetchone() is not None

    async def create_user(self, *, user_id: str, username: str, email: str | None,
                          password_hash: str, created_at: str, profile_id: str,
                          burner_name: str) -> None:
        self.db.execute(
            "INSERT INTO users(user_id,username,email,password_hash,created_at,updated_at) VALUES (?,?,?,?,?,?)",
            (user_id, username, email, password_hash, created_at, created_at),
        )
        self.db.execute(
            "INSERT INTO burner_profiles(profile_id,user_id,playa_name) VALUES (?,?,?)",
            (profile_id, user_id, burner_name),
        )
        self.db.commit()

    async def get_profile(self, user_id: str) -> dict[str, Any] | None:
        row = self.db.execute(
            "SELECT u.*, p.playa_name, p.home_camp, p.years_attended, p.vibe, p.bio "
            "FROM users u LEFT JOIN burner_profiles p ON p.user_id=u.user_id WHERE u.user_id=?", (user_id,)
        ).fetchone()
        return dict(row) if row else None

    async def update_user(self, user_id: str, values: dict[str, Any], now: str) -> None:
        if values:
            values = {**values, "updated_at": now}
            self.db.execute(
                f"UPDATE users SET {', '.join(k + '=?' for k in values)} WHERE user_id=?",
                [*values.values(), user_id],
            )
            self.db.commit()

    async def update_profile(self, user_id: str, values: dict[str, Any]) -> None:
        if values:
            self.db.execute(
                f"UPDATE burner_profiles SET {', '.join(k + '=?' for k in values)} WHERE user_id=?",
                [*values.values(), user_id],
            )
            self.db.commit()

    async def set_reset_token(self, user_id: str, token: str | None) -> None:
        self.db.execute("UPDATE users SET reset_token=? WHERE user_id=?", (token, user_id))
        self.db.commit()

    async def user_for_reset(self, email: str) -> dict[str, Any] | None:
        row = self.db.execute("SELECT user_id, reset_token FROM users WHERE email=?", (email,)).fetchone()
        return dict(row) if row else None

    async def append_event(self, event: dict[str, Any], accepted_at: str) -> str:
        try:
            self.db.execute(
                "INSERT INTO signed_events(event_id,event_type,author,object_id,created_at,data,accepted_at) VALUES (?,?,?,?,?,?,?)",
                (event["event_id"], event["type"], event["author"], event["object_id"], event["created_at"], json.dumps(event, sort_keys=True), accepted_at),
            )
            self.db.commit()
            return "accepted"
        except sqlite3.IntegrityError:
            return "duplicate"

    async def save_identity(self, *, identity_id: str, public_key: str, created_at: str,
                            user_id: str | None = None) -> str:
        try:
            self.db.execute("INSERT INTO identities(identity_id,public_key,created_at,user_id) VALUES (?,?,?,?)",
                            (identity_id, public_key, created_at, user_id))
            self.db.commit()
            return "accepted"
        except sqlite3.IntegrityError:
            return "duplicate"

    async def get_identity(self, public_key: str) -> dict[str, Any] | None:
        row = self.db.execute("SELECT * FROM identities WHERE public_key=?", (public_key,)).fetchone()
        return dict(row) if row else None

    async def save_projection(self, projection: str, object_id: str, data: dict[str, Any], updated_at: str) -> None:
        self.db.execute("INSERT OR REPLACE INTO projections(projection,object_id,data,updated_at) VALUES (?,?,?,?)",
                        (projection, object_id, json.dumps(data, sort_keys=True), updated_at))
        self.db.commit()

    async def get_projection(self, projection: str, object_id: str) -> dict[str, Any] | None:
        row = self.db.execute("SELECT data FROM projections WHERE projection=? AND object_id=?",
                              (projection, object_id)).fetchone()
        return json.loads(row["data"]) if row else None

    async def list_events(self, *, object_id: str | None = None) -> list[dict[str, Any]]:
        query = "SELECT data FROM signed_events"
        params: tuple[Any, ...] = ()
        if object_id is not None:
            query += " WHERE object_id=?"
            params = (object_id,)
        query += " ORDER BY rowid"
        return [json.loads(row["data"]) for row in self.db.execute(query, params)]


async def get_driver() -> AsyncDriver | None:
    global _driver, _NEO4J_FAILED
    if settings.storage_backend.lower() != "neo4j" or _NEO4J_FAILED or AsyncGraphDatabase is None:
        return None
    if _driver is None:
        try:
            _driver = AsyncGraphDatabase.driver(settings.neo4j_uri, auth=(settings.neo4j_user, settings.neo4j_password), connection_timeout=3)
            async with _driver.session() as session:
                await session.run("RETURN 1")
            logger.info("Connected to Neo4j at %s", settings.neo4j_uri)
        except Exception as exc:
            logger.warning("Neo4j unavailable: %s", exc)
            _NEO4J_FAILED = True
            _driver = None
    return _driver


async def close_driver() -> None:
    global _driver
    if _driver is not None:
        await _driver.close()
        _driver = None


_repository: SQLiteRepository | None = None


async def get_session():
    """Yield the configured repository/session for dependency injection."""
    global _repository
    if settings.storage_backend.lower() == "sqlite":
        if _repository is None:
            _repository = SQLiteRepository(settings.sqlite_path)
        yield _repository
        return
    driver = await get_driver()
    if driver is None:
        from fastapi import HTTPException, status
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database unavailable")
    async with driver.session() as session:
        yield session


async def close_repository() -> None:
    global _repository
    if _repository is not None:
        await _repository.close()
        _repository = None
