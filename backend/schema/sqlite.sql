-- Blaze SQLite compatibility schema (applied by backend.app.database).
-- Append-only events are the durable source for local projections.
CREATE TABLE IF NOT EXISTS users (user_id TEXT PRIMARY KEY, username TEXT NOT NULL UNIQUE, email TEXT UNIQUE, password_hash TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL, reset_token TEXT);
CREATE TABLE IF NOT EXISTS burner_profiles (profile_id TEXT PRIMARY KEY, user_id TEXT NOT NULL UNIQUE REFERENCES users(user_id), playa_name TEXT NOT NULL, home_camp TEXT, years_attended TEXT NOT NULL DEFAULT '[]', vibe TEXT, bio TEXT);
CREATE TABLE IF NOT EXISTS identities (identity_id TEXT PRIMARY KEY, public_key TEXT NOT NULL UNIQUE, created_at TEXT NOT NULL, user_id TEXT REFERENCES users(user_id));
CREATE TABLE IF NOT EXISTS signed_events (event_id TEXT PRIMARY KEY, event_type TEXT NOT NULL, author TEXT NOT NULL, object_id TEXT NOT NULL, created_at TEXT NOT NULL, data TEXT NOT NULL, accepted_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS projections (projection TEXT NOT NULL, object_id TEXT NOT NULL, data TEXT NOT NULL, updated_at TEXT NOT NULL, PRIMARY KEY (projection, object_id));
CREATE INDEX IF NOT EXISTS idx_signed_events_object ON signed_events(object_id);
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE TABLE IF NOT EXISTS graph_nodes (
    label TEXT NOT NULL, node_id TEXT NOT NULL, data TEXT NOT NULL,
    PRIMARY KEY (label, node_id)
);
CREATE TABLE IF NOT EXISTS graph_relationships (
    rel_id INTEGER PRIMARY KEY AUTOINCREMENT, rel_type TEXT NOT NULL,
    from_label TEXT NOT NULL, from_id TEXT NOT NULL,
    to_label TEXT NOT NULL, to_id TEXT NOT NULL, data TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_graph_rel_from ON graph_relationships(from_label, from_id, rel_type);
CREATE INDEX IF NOT EXISTS idx_graph_rel_to ON graph_relationships(to_label, to_id, rel_type);
