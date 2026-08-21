import sqlite3
import json
from datetime import datetime
import os

DB_PATH = "chat_history.db"

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS chats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id TEXT UNIQUE,
            timestamp TEXT,
            title TEXT,
            document_name TEXT,
            pinned BOOLEAN DEFAULT 0
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id TEXT,
            role TEXT,
            content TEXT,
            confidence REAL,
            timestamp TEXT,
            FOREIGN KEY(chat_id) REFERENCES chats(chat_id)
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS timeline_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            event_type TEXT,
            description TEXT
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    ''')
    conn.commit()
    conn.close()

def get_setting(key: str, default: str = None) -> str:
    try:
        conn = get_connection()
        c = conn.cursor()
        c.execute('CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)')
        c.execute('SELECT value FROM settings WHERE key = ?', (key,))
        row = c.fetchone()
        conn.close()
        if row:
            return row['value']
    except Exception:
        pass
    return default

def save_setting(key: str, value: str):
    try:
        conn = get_connection()
        c = conn.cursor()
        c.execute('CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)')
        c.execute('INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)', (key, value))
        conn.commit()
        conn.close()
    except Exception:
        pass

def create_chat(chat_id: str, title: str, document_name: str):
    conn = get_connection()
    c = conn.cursor()
    timestamp = datetime.now().isoformat()
    c.execute('INSERT OR IGNORE INTO chats (chat_id, timestamp, title, document_name) VALUES (?, ?, ?, ?)',
              (chat_id, timestamp, title, document_name))
    conn.commit()
    conn.close()

def save_message(chat_id: str, role: str, content: str, confidence: float = None):
    conn = get_connection()
    c = conn.cursor()
    timestamp = datetime.now().isoformat()
    c.execute('INSERT INTO messages (chat_id, role, content, confidence, timestamp) VALUES (?, ?, ?, ?, ?)',
              (chat_id, role, content, confidence, timestamp))
    conn.commit()
    conn.close()

def get_chat_history(chat_id: str):
    conn = get_connection()
    c = conn.cursor()
    c.execute('SELECT * FROM messages WHERE chat_id = ? ORDER BY id ASC', (chat_id,))
    rows = c.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_all_chats():
    conn = get_connection()
    c = conn.cursor()
    c.execute('SELECT * FROM chats ORDER BY pinned DESC, id DESC')
    rows = c.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def update_chat_title(chat_id: str, title: str):
    conn = get_connection()
    c = conn.cursor()
    c.execute('UPDATE chats SET title = ? WHERE chat_id = ?', (title, chat_id))
    conn.commit()
    conn.close()

def toggle_pin_chat(chat_id: str, pinned: bool):
    conn = get_connection()
    c = conn.cursor()
    c.execute('UPDATE chats SET pinned = ? WHERE chat_id = ?', (1 if pinned else 0, chat_id))
    conn.commit()
    conn.close()

def delete_chat(chat_id: str):
    conn = get_connection()
    c = conn.cursor()
    c.execute('DELETE FROM messages WHERE chat_id = ?', (chat_id,))
    c.execute('DELETE FROM chats WHERE chat_id = ?', (chat_id,))
    try:
        c.execute('DELETE FROM timeline WHERE chat_id = ?', (chat_id,))
    except sqlite3.OperationalError:
        pass
    try:
        c.execute('DELETE FROM timeline_events WHERE chat_id = ?', (chat_id,))
    except sqlite3.OperationalError:
        pass
    conn.commit()
    conn.close()

def search_chats(query: str):
    conn = get_connection()
    c = conn.cursor()
    like_query = f"%{query}%"
    c.execute('''
        SELECT DISTINCT c.id, c.chat_id, c.timestamp, c.title, c.document_name, c.pinned
        FROM chats c
        LEFT JOIN messages m ON c.chat_id = m.chat_id
        WHERE c.title LIKE ? OR c.document_name LIKE ? OR m.content LIKE ?
        ORDER BY c.pinned DESC, c.id DESC
    ''', (like_query, like_query, like_query))
    rows = c.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def record_timeline_event(event_type: str, description: str):
    conn = get_connection()
    c = conn.cursor()
    timestamp = datetime.now().isoformat()
    c.execute('INSERT INTO timeline_events (timestamp, event_type, description) VALUES (?, ?, ?)',
              (timestamp, event_type, description))
    conn.commit()
    conn.close()

def get_timeline_events(limit: int = 50):
    conn = get_connection()
    c = conn.cursor()
    c.execute('SELECT * FROM timeline_events ORDER BY id DESC LIMIT ?', (limit,))
    rows = c.fetchall()
    conn.close()
    return [dict(row) for row in rows]

init_db()
