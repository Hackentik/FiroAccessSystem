import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin

class User(UserMixin):
    def __init__(self, id, username, password_hash, role='user'):
        self.id = id
        self.username = username
        self.password_hash = password_hash
        self.role = role
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Database:
    def __init__(self, db_name='users.db'):
        self.db_name = db_name
        self.init_db()
    
    def get_connection(self):
        conn = sqlite3.connect(self.db_name)
        conn.row_factory = sqlite3.Row
        return conn
    
    def init_db(self):

        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT DEFAULT 'user'
            )
        ''')
        

        cursor.execute("SELECT COUNT(*) as count FROM users")
        count = cursor.fetchone()['count']
        

        if count == 0:
            default_users = [
                ('username', 'password', 'admin')
            ]
            
            for username, password, role in default_users:
                password_hash = generate_password_hash(password)
                cursor.execute(
                    "INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
                    (username, password_hash, role)
                )
            print("Созданы пользователи по умолчанию")
        conn.commit()
        conn.close()
    
    def get_user_by_id(self, user_id):

        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        user_data = cursor.fetchone()
        conn.close()
        
        if user_data:
            return User(
                id=user_data['id'],
                username=user_data['username'],
                password_hash=user_data['password_hash'],
                role=user_data['role']
            )
        return None
    
    def get_user_by_username(self, username):

        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        user_data = cursor.fetchone()
        conn.close()
        
        if user_data:
            return User(
                id=user_data['id'],
                username=user_data['username'],
                password_hash=user_data['password_hash'],
                role=user_data['role']
            )
        return None