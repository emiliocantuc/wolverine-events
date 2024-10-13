-- Script that creates tables
-- Ran with: sqlite3 main.db < tables.sql

CREATE TABLE users (
    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
    email VARCHAR(100) NOT NULL UNIQUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE preferences (
    user_id INT NOT NULL,
    interests TEXT DEFAULT '',
    keywordsToAvoid TEXT DEFAULT '',
    sendEmail INTEGER DEFAULT 1 CHECK (sendEmail IN (0, 1)),
    PRIMARY KEY (user_id),
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);


CREATE TABLE events (
    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
    nweek INTEGER,
    title VARCHAR(100) NOT NULL,
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


CREATE TABLE votes (
    user_id INTEGER NOT NULL,
    event_id INTEGER NOT NULL,
    vote_type CHAR(1) CHECK (vote_type IN ('U', 'D', 'C', 'N')), -- Upvote, Downvote, Clear, Neutral
    voted_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, event_id),
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (event_id) REFERENCES events(event_id) ON DELETE CASCADE
);


CREATE TABLE statistics (
    nweek INT PRIMARY KEY,
    nusers INT,
    nevents INT
);

INSERT INTO statistics (nweek, nusers, nevents) VALUES (0, 0, 0);

-- Auto create preferences for new user
CREATE TRIGGER after_user_insert
AFTER INSERT ON users
FOR EACH ROW
BEGIN
    INSERT INTO preferences (user_id) VALUES (NEW.user_id);
END;

-- Indexing
CREATE INDEX idx_user_id ON votes (user_id);
CREATE INDEX idx_event_id ON votes (event_id);
CREATE INDEX idx_vote_type ON votes (vote_type);

-- Disable caching? (TODO: check if necessary)
PRAGMA cache_size = 0;
