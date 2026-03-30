# database.py
import sqlite3
import os

DB_NAME = 'employees.db'

def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row  # للوصول إلى الأعمدة بالأسماء
    return conn

def init_db():
    """إنشاء الجداول إذا لم تكن موجودة"""
    conn = get_db_connection()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS employees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            numera TEXT UNIQUE NOT NULL,          -- النمرة (رقم وظيفي فريد)
            rank TEXT,
            name TEXT NOT NULL,
            department TEXT,                       -- الدائرة
            administration TEXT,                  -- الإدارة
            phone TEXT,
            whatsapp TEXT,
            profession TEXT,
            enlistment_date TEXT,                 -- تاريخ التجنيد (YYYY-MM-DD)
            notes TEXT
        )
    ''')
    conn.commit()
    conn.close()