import sqlite3
from datetime import date, datetime

class Database:
    def __init__(self):
        self.conn = sqlite3.connect("clex.db", check_same_thread=False)
        self.create_tables()

    def create_tables(self):
        c = self.conn.cursor()
        c.execute("""CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY, name TEXT, username TEXT,
            xp INTEGER DEFAULT 0, level INTEGER DEFAULT 1,
            streak INTEGER DEFAULT 0, last_active TEXT, joined TEXT,
            cabinet TEXT, subject TEXT, knowledge_level TEXT DEFAULT 'beginner')""")
        c.execute("""CREATE TABLE IF NOT EXISTS test_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER,
            cabinet TEXT, subject TEXT, score INTEGER, total INTEGER, date TEXT)""")
        c.execute("""CREATE TABLE IF NOT EXISTS badges (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER, badge_name TEXT, earned_date TEXT)""")
        c.execute("""CREATE TABLE IF NOT EXISTS mooc_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER,
            week TEXT, subject TEXT, score INTEGER, total INTEGER,
            certificate_level TEXT, date TEXT)""")
        self.conn.commit()

    def add_user(self, user_id, name, username):
        c = self.conn.cursor()
        c.execute("SELECT user_id FROM users WHERE user_id=?", (user_id,))
        if not c.fetchone():
            c.execute("INSERT INTO users (user_id,name,username,joined,last_active) VALUES (?,?,?,?,?)",
                      (user_id, name, username, str(date.today()), str(date.today())))
            self.conn.commit()

    def get_user(self, user_id):
        c = self.conn.cursor()
        c.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
        row = c.fetchone()
        if row:
            keys = ["user_id","name","username","xp","level","streak",
                    "last_active","joined","cabinet","subject","knowledge_level"]
            return dict(zip(keys, row))
        return None

    def get_user_stats(self, user_id):
        return self.get_user(user_id) or {"xp":0,"level":1,"streak":0}

    def add_xp(self, user_id, amount):
        c = self.conn.cursor()
        c.execute("UPDATE users SET xp=xp+? WHERE user_id=?", (amount, user_id))
        user = self.get_user(user_id)
        if user:
            new_level = (user["xp"] + amount) // 500 + 1
            c.execute("UPDATE users SET level=? WHERE user_id=?", (new_level, user_id))
        self.conn.commit()

    def update_streak(self, user_id):
        c = self.conn.cursor()
        user = self.get_user(user_id)
        if not user:
            return 0
        today = str(date.today())
        if user["last_active"] == today:
            return user["streak"]
        yesterday = str(date.fromordinal(date.today().toordinal()-1))
        new_streak = user["streak"]+1
