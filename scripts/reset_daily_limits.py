import sqlite3, time, argparse
from datetime import datetime


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--db', type = str, help = 'Path to db file', default = 'data/main.db')
    parser.add_argument('--notify', type = str, help = 'ntfy topic to notify status to if not empty', default = '', required = False)
    args = parser.parse_args()

    try:
        db = sqlite3.connect(args.db)
        db.execute("UPDATE users SET daily_interest_updates = 0")
        db.commit()
        print(f"{datetime.now()}: Successfully reset daily limits.")

    except sqlite3.Error as e: print(f"{datetime.now()}: Failed to reset daily limits - {e}")
    finally: db.close()
