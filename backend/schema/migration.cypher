# ═══════════════════════════════════════════════════════════════════════
# Blaze — Neo4j Schema Migration
# ═══════════════════════════════════════════════════════════════════════
# Run with:  cat migration.cypher | cypher-shell -u neo4j -p burner_social_dev
# Or via Python: python -m backend.schema.load
# ═══════════════════════════════════════════════════════════════════════

// ─── Constraints (uniqueness) ───────────────────────────────────────

CREATE CONSTRAINT user_id_unique IF NOT EXISTS
FOR (u:User) REQUIRE u.user_id IS UNIQUE;

CREATE CONSTRAINT username_unique IF NOT EXISTS
FOR (u:User) REQUIRE u.username IS UNIQUE;

CREATE CONSTRAINT user_email_unique IF NOT EXISTS
FOR (u:User) REQUIRE u.email IS UNIQUE;

CREATE CONSTRAINT profile_id_unique IF NOT EXISTS
FOR (p:BurnerProfile) REQUIRE p.profile_id IS UNIQUE;

CREATE CONSTRAINT event_id_unique IF NOT EXISTS
FOR (e:Event) REQUIRE e.event_id IS UNIQUE;

CREATE CONSTRAINT camp_id_unique IF NOT EXISTS
FOR (c:Camp) REQUIRE c.camp_id IS UNIQUE;

CREATE CONSTRAINT group_id_unique IF NOT EXISTS
FOR (g:Group) REQUIRE g.group_id IS UNIQUE;

CREATE CONSTRAINT post_id_unique IF NOT EXISTS
FOR (p:Post) REQUIRE p.post_id IS UNIQUE;

// ─── Indexes (performance) ──────────────────────────────────────────

CREATE INDEX user_display_name_index IF NOT EXISTS
FOR (u:User) ON (u.display_name);

CREATE INDEX burner_profile_name_index IF NOT EXISTS
FOR (p:BurnerProfile) ON (p.burner_name);

CREATE INDEX event_year_index IF NOT EXISTS
FOR (e:Event) ON (e.year);

CREATE INDEX post_created_at_index IF NOT EXISTS
FOR (p:Post) ON (p.created_at);

CREATE INDEX post_tags_index IF NOT EXISTS
FOR (p:Post) ON (p.tags);

// ─── Sample Data ────────────────────────────────────────────────────

// Users
CREATE (u1:User {user_id: "user-1", username: "sparklepony", email: "sparkle@burner.me", display_name: "Sparkle Pony", created_at: datetime()})
CREATE (u2:User {user_id: "user-2", username: "dustdevil", email: "dusty@playa.org", display_name: "Dust Devil", created_at: datetime()})
CREATE (u3:User {user_id: "user-3", username: "firebird", email: "phoenix@burn.bright", display_name: "Firebird Rising", created_at: datetime()})
CREATE (u4:User {user_id: "user-4", username: "moonshadow", email: "luna@dark.side", display_name: "Moonshadow", created_at: datetime()})
CREATE (u5:User {user_id: "user-5", username: "artcar", email: "art@wheelz.io", display_name: "Art Car Aficionado", created_at: datetime()})

// Burner Profiles
CREATE (p1:BurnerProfile {profile_id: "profile-1", burner_name: "Captain Sparkles", home_camp: "Spanky's Wine Bar", years_active: [2022, 2023, 2024, 2025]})
CREATE (p2:BurnerProfile {profile_id: "profile-2", burner_name: "Dust Muffin", home_camp: "Distrikt", years_active: [2021, 2022, 2023, 2024, 2025]})
CREATE (p3:BurnerProfile {profile_id: "profile-3", burner_name: "Ember", home_camp: "Comfort & Joy", years_active: [2023, 2024, 2025]})

// Events
CREATE (e25:Event {event_id: "bm-2025", name: "Burning Man 2025", year: 2025, location: "Black Rock City, NV", start_date: "2025-08-24", end_date: "2025-09-01"})
CREATE (e24:Event {event_id: "bm-2024", name: "Burning Man 2024", year: 2024, location: "Black Rock City, NV", start_date: "2024-08-25", end_date: "2024-09-02"})
CREATE (er1:Event {event_id: "regional-2025", name: "Burnal Equinox 2025", year: 2025, location: "Santa Cruz, CA", start_date: "2025-03-21", end_date: "2025-03-23"})

// Camps
CREATE (c1:Camp {camp_id: "camp-spankys", name: "Spanky's Wine Bar", description: "The longest-running wine bar on the playa", location_on_playa: "7:15 & Esplanade"})
CREATE (c2:Camp {camp_id: "camp-distrikt", name: "Distrikt", description: "Burning Man's premiere nightlife experience", location_on_playa: "9:00 & C"})
CREATE (c3:Camp {camp_id: "camp-cj", name: "Comfort & Joy", description: "A sanctuary of comfort and good cheer", location_on_playa: "5:30 & Esplanade"})

// Groups
CREATE (g1:Group {group_id: "group-burners", name: "Bay Area Burners", description: "SF Bay Area burner community", is_public: true})
CREATE (g2:Group {group_id: "group-art", name: "Art Project Collective", description: "Collaborative art installations", is_public: true})
CREATE (g3:Group {group_id: "group-bike", name: "Playa Bike Crew", description: "Yellow bike enthusiasts", is_public: false})

// Posts
CREATE (post1:Post {post_id: "post-1", content: "Can't wait to be back on the playa! The dust is calling 🌵✨", tags: ["excited", "burningman"], created_at: datetime()})
CREATE (post2:Post {post_id: "post-2", content: "Our camp theme for 2025: 'Celestial Oasis' — come find us! 🏜️🌙", tags: ["camp", "theme"], created_at: datetime()})
CREATE (post3:Post {post_id: "post-3", content: "Anyone need a ride from SF? I have space in my cargo van.", tags: ["rideshare", "sf"], created_at: datetime()})
CREATE (post4:Post {post_id: "post-4", content: "The sunrise set at Robot Heart was transcendent. 🎶🌅", tags: ["music", "robotheart"], created_at: datetime()})
CREATE (post5:Post {post_id: "post-5", content: "Volunteering with the Lamplighters again this year — best way to greet the dawn!", tags: ["volunteer", "lamplighters"], created_at: datetime()})

// ─── Relationships ───────────────────────────────────────────────────

// User → BurnerProfile (HAS_PROFILE)
MATCH (u:User {user_id: "user-1"}), (p:BurnerProfile {profile_id: "profile-1"})
CREATE (u)-[:HAS_PROFILE]->(p);
MATCH (u:User {user_id: "user-2"}), (p:BurnerProfile {profile_id: "profile-2"})
CREATE (u)-[:HAS_PROFILE]->(p);
MATCH (u:User {user_id: "user-3"}), (p:BurnerProfile {profile_id: "profile-3"})
CREATE (u)-[:HAS_PROFILE]->(p);

// FRIENDS_WITH (bidirectional — one edge represents the friendship)
MATCH (u1:User {user_id: "user-1"}), (u2:User {user_id: "user-2"})
CREATE (u1)-[:FRIENDS_WITH {since: date("2022-08-28")}]->(u2);
MATCH (u1:User {user_id: "user-1"}), (u3:User {user_id: "user-3"})
CREATE (u1)-[:FRIENDS_WITH {since: date("2023-08-27")}]->(u3);
MATCH (u2:User {user_id: "user-2"}), (u4:User {user_id: "user-4"})
CREATE (u2)-[:FRIENDS_WITH {since: date("2024-08-30")}]->(u4);
MATCH (u3:User {user_id: "user-3"}), (u5:User {user_id: "user-5"})
CREATE (u3)-[:FRIENDS_WITH {since: date("2025-08-25")}]->(u5);

// ATTENDED
MATCH (u:User {user_id: "user-1"}), (e:Event {event_id: "bm-2025"})
CREATE (u)-[:ATTENDED {role: "participant"}]->(e);
MATCH (u:User {user_id: "user-1"}), (e:Event {event_id: "bm-2024"})
CREATE (u)-[:ATTENDED {role: "participant"}]->(e);
MATCH (u:User {user_id: "user-2"}), (e:Event {event_id: "bm-2025"})
CREATE (u)-[:ATTENDED {role: "volunteer"}]->(e);
MATCH (u:User {user_id: "user-3"}), (e:Event {event_id: "bm-2025"})
CREATE (u)-[:ATTENDED {role: "artist"}]->(e);
MATCH (u:User {user_id: "user-5"}), (e:Event {event_id: "bm-2025"})
CREATE (u)-[:ATTENDED {role: "participant"}]->(e);

// MEMBER_OF
MATCH (u:User {user_id: "user-1"}), (c:Camp {camp_id: "camp-spankys"})
CREATE (u)-[:MEMBER_OF {role: "member"}]->(c);
MATCH (u:User {user_id: "user-2"}), (c:Camp {camp_id: "camp-distrikt"})
CREATE (u)-[:MEMBER_OF {role: "lead"}]->(c);
MATCH (u:User {user_id: "user-3"}), (c:Camp {camp_id: "camp-cj"})
CREATE (u)-[:MEMBER_OF {role: "member"}]->(c);
MATCH (u:User {user_id: "user-1"}), (g:Group {group_id: "group-burners"})
CREATE (u)-[:MEMBER_OF {role: "member"}]->(g);
MATCH (u:User {user_id: "user-2"}), (g:Group {group_id: "group-burners"})
CREATE (u)-[:MEMBER_OF {role: "member"}]->(g);
MATCH (u:User {user_id: "user-3"}), (g:Group {group_id: "group-art"})
CREATE (u)-[:MEMBER_OF {role: "member"}]->(g);
MATCH (u:User {user_id: "user-5"}), (g:Group {group_id: "group-bike"})
CREATE (u)-[:MEMBER_OF {role: "member"}]->(g);

// HOSTED_BY (Camp → Event)
MATCH (c:Camp {camp_id: "camp-spankys"}), (e:Event {event_id: "bm-2025"})
CREATE (c)-[:HOSTED_BY]->(e);
MATCH (c:Camp {camp_id: "camp-distrikt"}), (e:Event {event_id: "bm-2025"})
CREATE (c)-[:HOSTED_BY]->(e);
MATCH (c:Camp {camp_id: "camp-cj"}), (e:Event {event_id: "bm-2025"})
CREATE (c)-[:HOSTED_BY]->(e);

// POSTED
MATCH (u:User {user_id: "user-1"}), (p:Post {post_id: "post-1"})
CREATE (u)-[:POSTED {at: datetime()}]->(p);
MATCH (u:User {user_id: "user-1"}), (p:Post {post_id: "post-2"})
CREATE (u)-[:POSTED {at: datetime()}]->(p);
MATCH (u:User {user_id: "user-2"}), (p:Post {post_id: "post-3"})
CREATE (u)-[:POSTED {at: datetime()}]->(p);
MATCH (u:User {user_id: "user-3"}), (p:Post {post_id: "post-4"})
CREATE (u)-[:POSTED {at: datetime()}]->(p);
MATCH (u:User {user_id: "user-4"}), (p:Post {post_id: "post-5"})
CREATE (u)-[:POSTED {at: datetime()}]->(p);

// LIKES
MATCH (u:User {user_id: "user-2"}), (p:Post {post_id: "post-1"})
CREATE (u)-[:LIKES]->(p);
MATCH (u:User {user_id: "user-3"}), (p:Post {post_id: "post-1"})
CREATE (u)-[:LIKES]->(p);
MATCH (u:User {user_id: "user-1"}), (p:Post {post_id: "post-3"})
CREATE (u)-[:LIKES]->(p);
MATCH (u:User {user_id: "user-4"}), (p:Post {post_id: "post-4"})
CREATE (u)-[:LIKES]->(p);
MATCH (u:User {user_id: "user-5"}), (p:Post {post_id: "post-4"})
CREATE (u)-[:LIKES]->(p);

// COMMENTED_ON
MATCH (u:User {user_id: "user-2"}), (p:Post {post_id: "post-1"})
CREATE (u)-[:COMMENTED_ON {content: "See you there! 🙌", at: datetime()}]->(p);
MATCH (u:User {user_id: "user-3"}), (p:Post {post_id: "post-3"})
CREATE (u)-[:COMMENTED_ON {content: "DM'd you! I need a ride from Oakland 🚐", at: datetime()}]->(p);
MATCH (u:User {user_id: "user-1"}), (p:Post {post_id: "post-4"})
CREATE (u)-[:COMMENTED_ON {content: "That sunrise was everything. ❤️", at: datetime()}]->(p);

// ─── Summary ─────────────────────────────────────────────────────────
RETURN 'Schema migration complete' AS status;
