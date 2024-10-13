import sqlite3


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


def signin_user(db: sqlite3.Connection, email: str) -> int:
    """Check if email exists. If it does, return user_id, else create a user and return its id"""
    
    # Check if the user already exists
    query_check = "SELECT user_id FROM users WHERE email = ?"
    row = db.execute(query_check, (email,)).fetchone()
    if row: return row[0]
    
    # If user doesn't exist, insert the new user
    query_insert = "INSERT INTO users (email) VALUES (?)"
    cursor = db.execute(query_insert, (email,))
    db.commit()
    return cursor.lastrowid


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
