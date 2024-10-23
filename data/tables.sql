-- Script that creates tables
-- Ran with: sqlite3 main.db < tables.sql

CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
    email VARCHAR(100) NOT NULL UNIQUE,
    cluster_ratings BLOB,                  -- To store the ratings array as binary data
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS preferences (
    user_id INT NOT NULL,
    interests TEXT DEFAULT '',
    keywordsToAvoid TEXT DEFAULT '',
    sendEmail INTEGER DEFAULT 1 CHECK (sendEmail IN (0, 1)),
    PRIMARY KEY (user_id),
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);


CREATE TABLE IF NOT EXISTS events (
    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
    emb BLOB,
    dists_to_clusters BLOB,
    cluster INT,
    title VARCHAR(100) NOT NULL,
    to_embed TEXT,
    event_description TEXT,
    event_start DATETIME,
    event_end DATETIME,
    type VARCHAR(50),
    permalink VARCHAR(255),
    building_name VARCHAR(100),
    building_id INTEGER,
    gcal_link VARCHAR(255),
    umich_id VARCHAR(100),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);


CREATE TABLE IF NOT EXISTS votes (
    user_id INTEGER NOT NULL,
    event_id INTEGER NOT NULL,
    vote_type CHAR(1) CHECK (vote_type IN ('U', 'D', 'C', 'N')), -- Upvote, Downvote, Clear, Neutral
    voted_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, event_id),
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (event_id) REFERENCES events(event_id) ON DELETE CASCADE
);


CREATE TABLE IF NOT EXISTS statistics (
    nweek INTEGER PRIMARY KEY AUTOINCREMENT,
    nusers INT,
    nevents INT
);

-- Auto create preferences for new user
CREATE TRIGGER IF NOT EXISTS after_user_insert
AFTER INSERT ON users
FOR EACH ROW
BEGIN
    INSERT INTO preferences (user_id) VALUES (NEW.user_id);
END;

-- Indexing
CREATE INDEX IF NOT EXISTS idx_user_id ON votes (user_id);
CREATE INDEX IF NOT EXISTS idx_event_id ON votes (event_id);
CREATE INDEX IF NOT EXISTS idx_vote_type ON votes (vote_type);

-- Disable caching? (TODO: check if necessary)
PRAGMA cache_size = 0;
