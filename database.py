# database.py
import sqlite3
import os

DB_NAME = 'employees.db'

def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def create_default_admin():
    conn = get_db_connection()
    admin = conn.execute('SELECT * FROM users WHERE username = ?', ('admin',)).fetchone()
    if not admin:
        hashed = generate_password_hash('admin123')
        conn.execute('INSERT INTO users (username, password, role) VALUES (?, ?, ?)',
                     ('admin', hashed, 'admin'))
        conn.commit()
        print("تم إنشاء مستخدم admin افتراضي: admin / admin123")
    conn.close()

# استدعها بعد init_db()
#create_default_admin()

def init_db():
    conn = get_db_connection()
    # جدول الموظفين
    conn.execute('''
        CREATE TABLE IF NOT EXISTS employees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            numera TEXT UNIQUE NOT NULL,
            rank TEXT,
            name TEXT NOT NULL,
            department TEXT,
            administration TEXT,
            phone TEXT,
            whatsapp TEXT,
            profession TEXT,
            enlistment_date TEXT,
            notes TEXT
        )
    ''')
    # جدول المستخدمين
    conn.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'user'
        )
    ''')
    conn.commit()
    conn.close()