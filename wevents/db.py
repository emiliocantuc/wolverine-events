import sqlite3
from datetime import datetime

def get_events(db: sqlite3.Connection, event_ids: list[int]):
    """
    Fetch events from the database based on a list of event IDs.
    
    :param db: SQLite database connection.
    :param event_ids: List of event IDs to fetch.
    :return: List of event dictionaries.
    """
    query = f"""
        SELECT 
            e.event_id AS Id,
            e.title AS Title,
            e.type AS EventType,
            e.event_description AS Description,
            e.event_start AS StartDate,
            e.event_end AS EndDate,
            COALESCE(SUM(CASE WHEN v.vote_type = 'U' THEN 1 ELSE 0 END), 0) - 
            COALESCE(SUM(CASE WHEN v.vote_type = 'D' THEN 1 ELSE 0 END), 0) AS VoteDiff,
            e.gcal_link AS CalendarLink,
            e.permalink AS PermaLink,
            e.building_name AS BuildingName
        FROM 
            events e
        LEFT JOIN 
            votes v ON e.event_id = v.event_id
        WHERE
            Id IN ({','.join('?' * len(event_ids))})
        GROUP BY 
            e.event_id, e.title, e.event_description, e.event_start, e.event_end, e.gcal_link, e.permalink, e.building_name
        ORDER BY 
            VoteDiff DESC
    """
    # query = f"SELECT * FROM events WHERE id IN ({','.join('?' * len(event_ids))})"
    print(event_ids)
    cursor = db.execute(query, event_ids)
    results = cursor.fetchall()
    keys = ['Id', 'Title', 'EventType', 'Description', 'StartDate', 'EndDate', 'VoteDiff', 'CalendarLink', 'PermaLink', 'BuildingName']
    events = [dict(zip(keys, row)) for row in results]
    return events

def get_top_events(db, nweek, limit):
    query = """
        SELECT 
            e.event_id AS Id,
            e.title AS Title,
            e.type AS EventType,
            e.event_description AS Description,
            e.event_start AS StartDate,
            e.event_end AS EndDate,
            COALESCE(SUM(CASE WHEN v.vote_type = 'U' THEN 1 ELSE 0 END), 0) - 
            COALESCE(SUM(CASE WHEN v.vote_type = 'D' THEN 1 ELSE 0 END), 0) AS VoteDiff,
            e.gcal_link AS CalendarLink,
            e.permalink AS PermaLink,
            e.building_name AS BuildingName
        FROM 
            events e
        LEFT JOIN 
            votes v ON e.event_id = v.event_id
        WHERE
            e.nweek = ?
        GROUP BY 
            e.event_id, e.title, e.event_description, e.event_start, e.event_end, e.gcal_link, e.permalink, e.building_name
        ORDER BY 
            VoteDiff DESC, RANDOM()
        LIMIT ?
    """
    cursor = db.cursor()
    cursor.execute(query, (nweek, limit))
    results = cursor.fetchall()
    keys = ['Id', 'Title', 'EventType', 'Description', 'StartDate', 'EndDate', 'VoteDiff', 'CalendarLink', 'PermaLink', 'BuildingName']
    events = [dict(zip(keys, row)) for row in results]
    return events


def get_preferences(db: sqlite3.Connection, user_id: int) -> dict:
    query = """
        SELECT interests, keywordsToAvoid
        FROM preferences
        WHERE user_id = ?
    """
    
    row = db.execute(query, (user_id,)).fetchone()

    if row is None: raise Exception(f"No preferences found for user_id {user_id}")

    interests, keywords_to_avoid = row
    # TODO check if we could only return row?
    return {
        'interests': interests,
        'keywordsToAvoid': keywords_to_avoid
    }

def update_preference(db: sqlite3.Connection, user_id: int, pref_key: str, pref_value: str) -> None:
    if pref_key not in ['interests', 'keywordsToAvoid']: raise Exception(f"invalid preference key: {pref_key}")
    query = f"""
        INSERT INTO preferences (user_id, {pref_key})
        VALUES (?, ?)
        ON CONFLICT(user_id)
        DO UPDATE SET {pref_key} = excluded.{pref_key}
    """
    try:
        db.execute(query, (user_id, pref_value))
        db.commit()
    except sqlite3.Error as e: raise Exception(f"could not update preference {pref_key}: {e}")


def signin_user(db: sqlite3.Connection, email: str):
    """
    Returns user_id given email for a user. If the user is new we add it.
    In addition we return whether the user is new.
    """
    
    # Check if the user already exists
    query_check = "SELECT user_id FROM users WHERE email = ?"
    row = db.execute(query_check, (email,)).fetchone()
    if row: return row[0], False
    
    # If user doesn't exist, insert the new user
    query_insert = "INSERT INTO users (email) VALUES (?)"
    cursor = db.execute(query_insert, (email,))
    db.commit()
    return cursor.lastrowid, True


def delete_user(db: sqlite3.Connection, user_id: int) -> None:
    # Begin transaction
    try:
        cursor = db.cursor()
        cursor.execute("BEGIN")
        
        # Delete preferences
        cursor.execute("DELETE FROM preferences WHERE user_id = ?", (user_id,))
        
        # Delete user
        cursor.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
        
        # Commit transaction
        db.commit()
    except sqlite3.Error as e:
        # Rollback transaction in case of error
        db.rollback()
        raise Exception(f"could not delete user: {e}")
    

def vote(db: sqlite3.Connection, user_id: int, event_id: int, vote_type: str) -> None:

    if vote_type not in ("U", "D", "C"): raise ValueError(f"Invalid vote type: {vote_type}")

    query = """
        INSERT INTO votes (user_id, event_id, vote_type, voted_at)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(user_id, event_id)
        DO UPDATE SET vote_type = excluded.vote_type, voted_at = excluded.voted_at
    """

    # Execute the query with the current timestamp
    db.execute(query, (user_id, event_id, vote_type, datetime.now()))
    db.commit()

