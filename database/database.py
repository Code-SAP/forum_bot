# database.py
import sqlite3
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

DB_FILE = "users.db"


#   БАЗОВЫЕ ОПЕРАЦИИ

def _connect():
    """Создаёт подключение к БД."""
    return sqlite3.connect(DB_FILE)


def init_db():
    """Инициализация всех таблиц."""
    conn = _connect()
    cursor = conn.cursor()

    # Таблица пользователей
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            vk_id INTEGER PRIMARY KEY,
            username TEXT,
            added_by INTEGER,
            added_date TEXT,
            last_used TEXT,
            is_admin INTEGER DEFAULT 0,
            is_judge INTEGER DEFAULT 0,
            note TEXT
        )
    ''')

    # Таблица повесток
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            judge_id INTEGER NOT NULL,
            judge_peer_id INTEGER,
            judge_name TEXT NOT NULL,
            target_nickname TEXT NOT NULL,
            message TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            processed_by INTEGER,
            processed_by_name TEXT,
            processed_at TIMESTAMP,
            reject_reason TEXT,
            processed_by_peer_id INTEGER
        )
    ''')

    # Таблица бесед ролей
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS role_chats (
            role TEXT PRIMARY KEY,
            chat_id INTEGER NOT NULL,
            registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            registered_by INTEGER
        )
    ''')

    conn.commit()
    conn.close()


#   ПОЛЬЗОВАТЕЛИ
def add_user(vk_id, username, added_by, note=""):
    """Добавляет или обновляет пользователя."""
    conn = _connect()
    cursor = conn.cursor()

    cursor.execute("SELECT vk_id FROM users WHERE vk_id = ?", (vk_id,))
    exists = cursor.fetchone()

    now = datetime.now().isoformat()

    if exists:
        cursor.execute('''
            UPDATE users
            SET username = ?, note = ?, last_used = ?
            WHERE vk_id = ?
        ''', (username, note, now, vk_id))
    else:
        cursor.execute('''
            INSERT INTO users (vk_id, username, added_by, added_date, last_used, note)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (vk_id, username, added_by, now, now, note))

    conn.commit()
    conn.close()
    return True

# АДМИНЫ
def add_admin(vk_id: int, username: str, note: str):
    conn = _connect()
    cur = conn.cursor()

    now = datetime.now().isoformat()

    cur.execute("SELECT vk_id FROM users WHERE vk_id = ?", (vk_id,))
    exists = cur.fetchone()

    if exists:
        cur.execute("""
            UPDATE users
            SET username = ?, is_admin = 1, note = ?, last_used = ?
            WHERE vk_id = ?
        """, (username, note, now, vk_id))
    else:
        cur.execute("""
            INSERT INTO users (vk_id, username, added_by, added_date, last_used, is_admin, is_judge, note)
            VALUES (?, ?, ?, ?, ?, 1, 0, ?)
        """, (vk_id, username, vk_id, now, now, note))

    conn.commit()
    conn.close()

# СУДЬИ
def add_judge(vk_id: int, username: str, note: str):
    conn = _connect()
    cur = conn.cursor()

    now = datetime.now().isoformat()

    cur.execute("SELECT vk_id FROM users WHERE vk_id = ?", (vk_id,))
    exists = cur.fetchone()

    if exists:
        cur.execute("""
            UPDATE users
            SET username = ?, is_judge = 1, note = ?, last_used = ?
            WHERE vk_id = ?
        """, (username, note, now, vk_id))
    else:
        cur.execute("""
            INSERT INTO users (vk_id, username, added_by, added_date, last_used, is_admin, is_judge, note)
            VALUES (?, ?, ?, ?, ?, 0, 1, ?)
        """, (vk_id, username, vk_id, now, now, note))

    conn.commit()
    conn.close()

def remove_user_by_username(username):
    """Удаляет пользователя по username."""
    clean = username.lower().replace("@", "")
    conn = _connect()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM users WHERE LOWER(username) = ?", (clean,))
    deleted = cursor.rowcount > 0

    conn.commit()
    conn.close()
    return deleted


def get_all_users():
    """Возвращает всех пользователей."""
    conn = _connect()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT vk_id, username, added_date, last_used, note, is_admin, is_judge
        FROM users
        ORDER BY added_date DESC
    ''')
    rows = cursor.fetchall()

    conn.close()
    return rows

def get_all_judges():
    conn = _connect()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT vk_id, username, added_date, last_used, note
        FROM users
        WHERE is_judge = 1
        ORDER BY added_date DESC
    ''')
    rows = cursor.fetchall()

    conn.close()
    return rows

def get_all_admins():
    conn = _connect()
    cur = conn.cursor()

    cur.execute("""
        SELECT vk_id, username, note
        FROM users
        WHERE is_admin = 1
        ORDER BY username
    """)

    rows = cur.fetchall()
    conn.close()
    return rows


def get_username_by_vk_id(vk_id):
    conn = _connect()
    cursor = conn.cursor()

    cursor.execute("SELECT username FROM users WHERE vk_id = ?", (vk_id,))
    row = cursor.fetchone()

    conn.close()
    return row[0] if row else None


def is_user_allowed(vk_id):
    """Проверяет, есть ли пользователь в БД."""
    conn = _connect()
    cursor = conn.cursor()

    cursor.execute("SELECT 1 FROM users WHERE vk_id = ?", (vk_id,))
    exists = cursor.fetchone() is not None

    conn.close()
    return exists


def is_user_allowed_by_username(username):
    """Проверяет, есть ли пользователь по username."""
    clean = username.lower().replace("@", "")
    conn = _connect()
    cursor = conn.cursor()

    cursor.execute("SELECT 1 FROM users WHERE LOWER(username) = ?", (clean,))
    exists = cursor.fetchone() is not None

    conn.close()
    return exists


#   РОЛИ (ТОЛЬКО admin + judge)
def is_admin(vk_id):
    conn = _connect()
    cursor = conn.cursor()

    cursor.execute("SELECT is_admin FROM users WHERE vk_id = ?", (vk_id,))
    row = cursor.fetchone()

    conn.close()
    return row and row[0] == 1


def is_admin_by_username(username):
    clean = username.lower().replace("@", "")
    conn = _connect()
    cursor = conn.cursor()

    cursor.execute("SELECT is_admin FROM users WHERE LOWER(username) = ?", (clean,))
    row = cursor.fetchone()

    conn.close()
    return row and row[0] == 1


def is_judge(vk_id):
    conn = _connect()
    cursor = conn.cursor()

    cursor.execute("SELECT is_judge FROM users WHERE vk_id = ?", (vk_id,))
    row = cursor.fetchone()

    conn.close()
    return row and row[0] == 1


#   БЕСЕДЫ РОЛЕЙ
def save_role_chat(role, chat_id, registered_by=None):
    conn = _connect()
    cursor = conn.cursor()

    cursor.execute('''
        INSERT OR REPLACE INTO role_chats (role, chat_id, registered_by, registered_at)
        VALUES (?, ?, ?, CURRENT_TIMESTAMP)
    ''', (role, chat_id, registered_by))

    conn.commit()
    conn.close()


def get_role_chat(role):
    conn = _connect()
    cursor = conn.cursor()

    cursor.execute("SELECT chat_id FROM role_chats WHERE role = ?", (role,))
    row = cursor.fetchone()

    conn.close()
    return row[0] if row else None


def get_all_role_chats():
    conn = _connect()
    cursor = conn.cursor()

    cursor.execute("SELECT role, chat_id FROM role_chats")
    rows = cursor.fetchall()

    conn.close()
    return {role: chat_id for role, chat_id in rows}

def add_notification(judge_id: int, judge_peer_id: int, judge_name: str, 
                     target_nickname: str, message: str) -> int:
    """Добавление повестки"""
    conn = _connect()
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO notifications (judge_id, judge_peer_id, judge_name, target_nickname, message, status)
        VALUES (?, ?, ?, ?, ?, 'pending')
    ''', (judge_id, judge_peer_id, judge_name, target_nickname, message))
    
    notification_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return notification_id


def get_notification(notify_id: int):
    """Получение повестки по ID"""
    conn = _connect()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM notifications WHERE id = ?', (notify_id,))
    row = cursor.fetchone()
    
    conn.close()
    
    if row:
        return {
            "id": row[0],
            "judge_id": row[1],
            "judge_peer_id": row[2],
            "judge_name": row[3],
            "target_nickname": row[4],
            "message": row[5],
            "status": row[6],
            "created_at": row[7],
            "processed_by": row[8],
            "processed_by_name": row[9],
            "processed_at": row[10],
            "reject_reason": row[11],
        }
    return None


def get_judge_notifications(judge_id: int, limit: int = 10):
    """Получение повесток судьи"""
    conn = _connect()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT * FROM notifications WHERE judge_id = ? 
        ORDER BY created_at DESC LIMIT ?
    ''', (judge_id, limit))
    
    rows = cursor.fetchall()
    conn.close()
    
    return [
        {
            "id": row[0],
            "judge_id": row[1],
            "judge_peer_id": row[2],
            "judge_name": row[3],
            "target_nickname": row[4],
            "message": row[5],
            "status": row[6],
            "created_at": row[7],
            "processed_by": row[8],
            "processed_by_name": row[9],
            "processed_at": row[10],
            "reject_reason": row[11],
        }
        for row in rows
    ]


def get_all_notifications(limit: int = 50):
    """Получение всех повесток"""
    conn = _connect()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT * FROM notifications ORDER BY created_at DESC LIMIT ?
    ''', (limit,))
    
    rows = cursor.fetchall()
    conn.close()
    
    return [
        {
            "id": row[0],
            "judge_id": row[1],
            "judge_peer_id": row[2],
            "judge_name": row[3],
            "target_nickname": row[4],
            "message": row[5],
            "status": row[6],
            "created_at": row[7],
            "processed_by": row[8],
            "processed_by_name": row[9],
            "processed_at": row[10],
            "reject_reason": row[11],
        }
        for row in rows
    ]


def update_notification_status(notify_id: int, status: str, 
                                processed_by: int, processed_by_name: str,
                                reject_reason: str = ""):
    """Обновление статуса повестки"""
    conn = _connect()
    cursor = conn.cursor()
    
    cursor.execute('''
        UPDATE notifications 
        SET status = ?, processed_by = ?, processed_by_name = ?, 
            processed_at = CURRENT_TIMESTAMP, reject_reason = ?
        WHERE id = ?
    ''', (status, processed_by, processed_by_name, reject_reason, notify_id))
    
    conn.commit()
    conn.close()


def delete_notification(notify_id: int) -> bool:
    """Удаление повестки"""
    conn = _connect()
    cursor = conn.cursor()
    
    cursor.execute("DELETE FROM notifications WHERE id = ?", (notify_id,))
    deleted = cursor.rowcount > 0
    
    conn.commit()
    conn.close()
    return deleted


def get_vk_id_by_username(username: str):
    """Получение VK ID по username"""
    clean = username.lower().replace("@", "")
    conn = _connect()
    cursor = conn.cursor()
    
    cursor.execute("SELECT vk_id FROM users WHERE LOWER(username) = ?", (clean,))
    row = cursor.fetchone()
    
    conn.close()
    return row[0] if row else None


def set_admin(vk_id: int, is_admin_flag: bool, note: str = ""):
    """Установка/снятие роли админа"""
    conn = _connect()
    cursor = conn.cursor()
    
    cursor.execute('''
        UPDATE users SET is_admin = ?, note = ? WHERE vk_id = ?
    ''', (1 if is_admin_flag else 0, note, vk_id))
    
    conn.commit()
    conn.close()


def set_judge(vk_id: int, is_judge_flag: bool, note: str = ""):
    """Установка/снятие роли судьи"""
    conn = _connect()
    cursor = conn.cursor()
    
    cursor.execute('''
        UPDATE users SET is_judge = ?, note = ? WHERE vk_id = ?
    ''', (1 if is_judge_flag else 0, note, vk_id))
    
    conn.commit()
    conn.close()


def delete_role_chat(role: str):
    """Удаление регистрации беседы"""
    conn = _connect()
    cursor = conn.cursor()
    
    cursor.execute("DELETE FROM role_chats WHERE role = ?", (role,))
    
    conn.commit()
    conn.close()
