import psycopg2
from psycopg2 import pool
from psycopg2.extras import RealDictCursor
import os
from datetime import datetime
from typing import Optional, List, Dict

class ShiftDatabase:
    def __init__(self):
        self.database_url = os.getenv("DATABASE_URL")
        if not self.database_url:
            raise ValueError("DATABASE_URL environment variable is required")
        
        self.connection_pool = psycopg2.pool.SimpleConnectionPool(
            1, 10, self.database_url
        )
        
        self.init_database()
    
    def get_connection(self):
        return self.connection_pool.getconn()
    
    def return_connection(self, conn):
        self.connection_pool.putconn(conn)
    
    def init_database(self):
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS shifts (
                    id SERIAL PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    username TEXT NOT NULL,
                    clock_in_time TIMESTAMP NOT NULL,
                    clock_out_time TIMESTAMP,
                    duration_seconds INTEGER,
                    is_active BOOLEAN DEFAULT TRUE
                )
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_user_id ON shifts(user_id)
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_is_active ON shifts(is_active)
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS config (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS warnings (
                    id SERIAL PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    username TEXT NOT NULL,
                    moderator_id TEXT NOT NULL,
                    moderator_name TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_warnings_user_id ON warnings(user_id)
            ''')
            
            conn.commit()
        finally:
            cursor.close()
            self.return_connection(conn)
    
    def clock_in(self, user_id: str, username: str) -> bool:
        if self.is_clocked_in(user_id):
            return False
        
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO shifts (user_id, username, clock_in_time, is_active)
                VALUES (%s, %s, %s, TRUE)
            ''', (user_id, username, datetime.utcnow()))
            conn.commit()
            return True
        finally:
            cursor.close()
            self.return_connection(conn)
    
    def clock_out(self, user_id: str) -> Optional[int]:
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT id, clock_in_time FROM shifts
                WHERE user_id = %s AND is_active = TRUE
                ORDER BY id DESC
                LIMIT 1
            ''', (user_id,))
            
            result = cursor.fetchone()
            if not result:
                return None
            
            shift_id, clock_in_time = result
            clock_out_dt = datetime.utcnow()
            duration = int((clock_out_dt - clock_in_time).total_seconds())
            
            cursor.execute('''
                UPDATE shifts
                SET clock_out_time = %s, duration_seconds = %s, is_active = FALSE
                WHERE id = %s
            ''', (clock_out_dt, duration, shift_id))
            
            conn.commit()
            return duration
        finally:
            cursor.close()
            self.return_connection(conn)
    
    def is_clocked_in(self, user_id: str) -> bool:
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT COUNT(*) FROM shifts
                WHERE user_id = %s AND is_active = TRUE
            ''', (user_id,))
            
            return cursor.fetchone()[0] > 0
        finally:
            cursor.close()
            self.return_connection(conn)
    
    def get_active_users(self) -> List[Dict]:
        conn = self.get_connection()
        try:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            cursor.execute('''
                SELECT user_id, username, clock_in_time
                FROM shifts
                WHERE is_active = TRUE
                ORDER BY clock_in_time ASC
            ''')
            
            results = []
            for row in cursor.fetchall():
                results.append({
                    'user_id': row['user_id'],
                    'username': row['username'],
                    'clock_in_time': row['clock_in_time'].isoformat()
                })
            
            return results
        finally:
            cursor.close()
            self.return_connection(conn)
    
    def get_leaderboard(self, limit: int = 10) -> List[Dict]:
        conn = self.get_connection()
        try:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            cursor.execute('''
                SELECT user_id, username, SUM(duration_seconds) as total_seconds
                FROM shifts
                WHERE is_active = FALSE AND duration_seconds IS NOT NULL
                GROUP BY user_id, username
                ORDER BY total_seconds DESC
                LIMIT %s
            ''', (limit,))
            
            results = []
            for row in cursor.fetchall():
                results.append({
                    'user_id': row['user_id'],
                    'username': row['username'],
                    'total_seconds': int(row['total_seconds'])
                })
            
            return results
        finally:
            cursor.close()
            self.return_connection(conn)
    
    def get_user_total_time(self, user_id: str) -> int:
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT COALESCE(SUM(duration_seconds), 0)
                FROM shifts
                WHERE user_id = %s AND is_active = FALSE AND duration_seconds IS NOT NULL
            ''', (user_id,))
            
            return int(cursor.fetchone()[0])
        finally:
            cursor.close()
            self.return_connection(conn)
    
    def save_config(self, key: str, value: str):
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO config (key, value)
                VALUES (%s, %s)
                ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value
            ''', (key, value))
            conn.commit()
        finally:
            cursor.close()
            self.return_connection(conn)
    
    def get_config(self, key: str) -> Optional[str]:
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT value FROM config WHERE key = %s
            ''', (key,))
            
            result = cursor.fetchone()
            return result[0] if result else None
        finally:
            cursor.close()
            self.return_connection(conn)
    
    def get_all_config(self) -> Dict[str, str]:
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('SELECT key, value FROM config')
            
            return {row[0]: row[1] for row in cursor.fetchall()}
        finally:
            cursor.close()
            self.return_connection(conn)
    
    def add_warning(self, user_id: str, username: str, moderator_id: str, moderator_name: str, reason: str):
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO warnings (user_id, username, moderator_id, moderator_name, reason)
                VALUES (%s, %s, %s, %s, %s)
            ''', (user_id, username, moderator_id, moderator_name, reason))
            conn.commit()
        finally:
            cursor.close()
            self.return_connection(conn)
    
    def get_user_warnings(self, user_id: str) -> List[Dict]:
        conn = self.get_connection()
        try:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            cursor.execute('''
                SELECT id, moderator_name, reason, timestamp
                FROM warnings
                WHERE user_id = %s
                ORDER BY timestamp DESC
            ''', (user_id,))
            
            results = []
            for row in cursor.fetchall():
                results.append({
                    'id': row['id'],
                    'moderator_name': row['moderator_name'],
                    'reason': row['reason'],
                    'timestamp': row['timestamp'].isoformat()
                })
            
            return results
        finally:
            cursor.close()
            self.return_connection(conn)
    
    def get_warning_count(self, user_id: str) -> int:
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT COUNT(*) FROM warnings WHERE user_id = %s
            ''', (user_id,))
            
            return cursor.fetchone()[0]
        finally:
            cursor.close()
            self.return_connection(conn)
    
    def clear_warnings(self, user_id: str):
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('''
                DELETE FROM warnings WHERE user_id = %s
            ''', (user_id,))
            conn.commit()
        finally:
            cursor.close()
            self.return_connection(conn)
    
    def close(self):
        if self.connection_pool:
            self.connection_pool.closeall()
