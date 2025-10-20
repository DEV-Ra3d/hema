"""
مدير قاعدة البيانات لمصنع البوتات
Database Manager for Bot Factory
"""
import sqlite3
import datetime
import logging
from typing import List, Dict, Optional, Tuple
from contextlib import contextmanager
from config import Config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self, db_path: str = None):
        self.db_path = db_path or Config.DB_PATH
        self.init_database()
    
    @contextmanager
    def get_connection(self):
        """إدارة اتصال قاعدة البيانات بطريقة آمنة"""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row  # للحصول على النتائج كقاموس
            yield conn
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"خطأ في قاعدة البيانات: {e}")
            raise
        finally:
            if conn:
                conn.close()
    
    def init_database(self):
        """إنشاء جداول قاعدة البيانات"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # جدول البوتات المحسن
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS bots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    owner_id INTEGER NOT NULL,
                    token TEXT NOT NULL UNIQUE,
                    bot_username TEXT,
                    bot_name TEXT,
                    date_created TEXT NOT NULL,
                    last_active TEXT,
                    status TEXT NOT NULL DEFAULT 'active',
                    total_users INTEGER DEFAULT 0,
                    total_messages INTEGER DEFAULT 0,
                    settings TEXT DEFAULT '{}',
                    FOREIGN KEY (owner_id) REFERENCES users (user_id)
                )
            ''')
            
            # جدول المستخدمين
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    date_joined TEXT NOT NULL,
                    last_seen TEXT,
                    bot_limit INTEGER DEFAULT 3,
                    is_premium BOOLEAN DEFAULT FALSE,
                    total_bots_created INTEGER DEFAULT 0
                )
            ''')
            
            # جدول إحصائيات البوتات
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS bot_stats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    bot_id INTEGER NOT NULL,
                    date TEXT NOT NULL,
                    messages_count INTEGER DEFAULT 0,
                    users_count INTEGER DEFAULT 0,
                    groups_count INTEGER DEFAULT 0,
                    FOREIGN KEY (bot_id) REFERENCES bots (id)
                )
            ''')
            
            # جدول مستخدمي البوتات المصنوعة
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS bot_users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    bot_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    username TEXT,
                    first_name TEXT,
                    chat_type TEXT,
                    date_joined TEXT NOT NULL,
                    last_interaction TEXT,
                    message_count INTEGER DEFAULT 0,
                    FOREIGN KEY (bot_id) REFERENCES bots (id),
                    UNIQUE(bot_id, user_id)
                )
            ''')
            
            # جدول الإذاعات
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS broadcasts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sender_id INTEGER NOT NULL,
                    message_text TEXT NOT NULL,
                    target_type TEXT NOT NULL,
                    date_sent TEXT NOT NULL,
                    total_sent INTEGER DEFAULT 0,
                    total_failed INTEGER DEFAULT 0,
                    status TEXT DEFAULT 'pending'
                )
            ''')
            
            # جدول سجل الأنشطة
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS activity_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    action TEXT NOT NULL,
                    details TEXT,
                    timestamp TEXT NOT NULL,
                    ip_address TEXT
                )
            ''')
            
            # إنشاء الفهارس لتحسين الأداء
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_bots_owner ON bots(owner_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_bots_status ON bots(status)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_bot_users_bot ON bot_users(bot_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_activity_user ON activity_log(user_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_activity_timestamp ON activity_log(timestamp)')
            
            conn.commit()
            logger.info("✅ تم إنشاء قاعدة البيانات بنجاح")
    
    # === إدارة المستخدمين ===
    def add_or_update_user(self, user_id: int, username: str = None, 
                          first_name: str = None, last_name: str = None) -> bool:
        """إضافة أو تحديث مستخدم"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                now = datetime.datetime.now().isoformat()
                
                cursor.execute('''
                    INSERT INTO users (user_id, username, first_name, last_name, date_joined, last_seen)
                    VALUES (?, ?, ?, ?, ?, ?)
                    ON CONFLICT(user_id) DO UPDATE SET
                        username = excluded.username,
                        first_name = excluded.first_name,
                        last_name = excluded.last_name,
                        last_seen = excluded.last_seen
                ''', (user_id, username, first_name, last_name, now, now))
                
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"خطأ في إضافة المستخدم {user_id}: {e}")
            return False
    
    def get_user_limit(self, user_id: int) -> int:
        """الحصول على حد البوتات للمستخدم"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT bot_limit FROM users WHERE user_id = ?', (user_id,))
                result = cursor.fetchone()
                return result['bot_limit'] if result else Config.DEFAULT_LIMIT
        except Exception as e:
            logger.error(f"خطأ في الحصول على حد المستخدم {user_id}: {e}")
            return Config.DEFAULT_LIMIT
    
    def set_user_limit(self, user_id: int, limit: int) -> bool:
        """تعديل حد البوتات للمستخدم"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE users SET bot_limit = ? WHERE user_id = ?
                ''', (limit, user_id))
                
                if cursor.rowcount == 0:
                    # إنشاء المستخدم إذا لم يكن موجوداً
                    now = datetime.datetime.now().isoformat()
                    cursor.execute('''
                        INSERT INTO users (user_id, bot_limit, date_joined, last_seen)
                        VALUES (?, ?, ?, ?)
                    ''', (user_id, limit, now, now))
                
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"خطأ في تعديل حد المستخدم {user_id}: {e}")
            return False
    
    # === إدارة البوتات ===
    def add_bot(self, owner_id: int, token: str, bot_info: dict = None) -> Optional[int]:
        """إضافة بوت جديد"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                now = datetime.datetime.now().isoformat()
                
                bot_username = bot_info.get('username', '') if bot_info else ''
                bot_name = bot_info.get('first_name', '') if bot_info else ''
                
                cursor.execute('''
                    INSERT INTO bots (owner_id, token, bot_username, bot_name, date_created, status)
                    VALUES (?, ?, ?, ?, ?, 'active')
                ''', (owner_id, token, bot_username, bot_name, now))
                
                bot_id = cursor.lastrowid
                
                # تحديث عداد البوتات للمستخدم
                cursor.execute('''
                    UPDATE users SET total_bots_created = total_bots_created + 1
                    WHERE user_id = ?
                ''', (owner_id,))
                
                conn.commit()
                logger.info(f"✅ تم إضافة البوت {bot_id} للمستخدم {owner_id}")
                return bot_id
        except Exception as e:
            logger.error(f"خطأ في إضافة البوت: {e}")
            return None
    
    def delete_bot(self, bot_id: int, owner_id: int = None) -> bool:
        """حذف بوت"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # التحقق من الملكية إذا تم تحديد المالك
                if owner_id:
                    cursor.execute('''
                        SELECT owner_id FROM bots WHERE id = ? AND status = 'active'
                    ''', (bot_id,))
                    result = cursor.fetchone()
                    if not result or result['owner_id'] != owner_id:
                        return False
                
                # تحديث حالة البوت إلى محذوف
                cursor.execute('''
                    UPDATE bots SET status = 'deleted', last_active = ?
                    WHERE id = ?
                ''', (datetime.datetime.now().isoformat(), bot_id))
                
                conn.commit()
                logger.info(f"✅ تم حذف البوت {bot_id}")
                return True
        except Exception as e:
            logger.error(f"خطأ في حذف البوت {bot_id}: {e}")
            return False
    
    def get_user_bots(self, user_id: int) -> List[Dict]:
        """الحصول على بوتات المستخدم"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT id, token, bot_username, bot_name, date_created, 
                           last_active, total_users, total_messages, status
                    FROM bots 
                    WHERE owner_id = ? AND status = 'active'
                    ORDER BY date_created DESC
                ''', (user_id,))
                
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"خطأ في الحصول على بوتات المستخدم {user_id}: {e}")
            return []
    
    def count_user_bots(self, user_id: int) -> int:
        """عد بوتات المستخدم النشطة"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT COUNT(*) as count FROM bots 
                    WHERE owner_id = ? AND status = 'active'
                ''', (user_id,))
                
                result = cursor.fetchone()
                return result['count'] if result else 0
        except Exception as e:
            logger.error(f"خطأ في عد بوتات المستخدم {user_id}: {e}")
            return 0
    
    def get_all_bots(self) -> List[Dict]:
        """الحصول على جميع البوتات (للمالك)"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT b.*, u.username as owner_username, u.first_name as owner_name
                    FROM bots b
                    LEFT JOIN users u ON b.owner_id = u.user_id
                    ORDER BY b.date_created DESC
                ''')
                
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"خطأ في الحصول على جميع البوتات: {e}")
            return []
    
    def get_bot_info(self, bot_id: int) -> Optional[Dict]:
        """الحصول على معلومات بوت محدد"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT * FROM bots WHERE id = ?
                ''', (bot_id,))
                
                result = cursor.fetchone()
                return dict(result) if result else None
        except Exception as e:
            logger.error(f"خطأ في الحصول على معلومات البوت {bot_id}: {e}")
            return None
    
    # === إدارة مستخدمي البوتات ===
    def add_bot_user(self, bot_id: int, user_id: int, username: str = None, 
                     first_name: str = None, chat_type: str = 'private') -> bool:
        """إضافة مستخدم لبوت معين"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                now = datetime.datetime.now().isoformat()
                
                cursor.execute('''
                    INSERT INTO bot_users (bot_id, user_id, username, first_name, 
                                         chat_type, date_joined, last_interaction)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(bot_id, user_id) DO UPDATE SET
                        last_interaction = excluded.last_interaction,
                        message_count = message_count + 1
                ''', (bot_id, user_id, username, first_name, chat_type, now, now))
                
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"خطأ في إضافة مستخدم البوت: {e}")
            return False
    
    def get_bot_users(self, bot_id: int) -> List[Dict]:
        """الحصول على مستخدمي بوت معين"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT * FROM bot_users 
                    WHERE bot_id = ?
                    ORDER BY last_interaction DESC
                ''', (bot_id,))
                
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"خطأ في الحصول على مستخدمي البوت {bot_id}: {e}")
            return []
    
    # === إدارة الإحصائيات ===
    def update_bot_stats(self, bot_id: int, messages_count: int = 0, 
                        users_count: int = 0, groups_count: int = 0) -> bool:
        """تحديث إحصائيات البوت"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                today = datetime.date.today().isoformat()
                
                cursor.execute('''
                    INSERT INTO bot_stats (bot_id, date, messages_count, users_count, groups_count)
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(bot_id, date) DO UPDATE SET
                        messages_count = messages_count + excluded.messages_count,
                        users_count = excluded.users_count,
                        groups_count = excluded.groups_count
                ''', (bot_id, today, messages_count, users_count, groups_count))
                
                # تحديث الإحصائيات الإجمالية للبوت
                cursor.execute('''
                    UPDATE bots SET 
                        total_messages = total_messages + ?,
                        total_users = (SELECT COUNT(DISTINCT user_id) FROM bot_users WHERE bot_id = ?),
                        last_active = ?
                    WHERE id = ?
                ''', (messages_count, bot_id, datetime.datetime.now().isoformat(), bot_id))
                
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"خطأ في تحديث إحصائيات البوت {bot_id}: {e}")
            return False
    
    def get_system_stats(self) -> Dict:
        """الحصول على إحصائيات النظام العامة"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # إحصائيات عامة
                cursor.execute('SELECT COUNT(*) as total FROM bots WHERE status = "active"')
                total_bots = cursor.fetchone()['total']
                
                cursor.execute('SELECT COUNT(*) as total FROM users')
                total_users = cursor.fetchone()['total']
                
                cursor.execute('SELECT SUM(total_messages) as total FROM bots WHERE status = "active"')
                total_messages = cursor.fetchone()['total'] or 0
                
                cursor.execute('SELECT SUM(total_users) as total FROM bots WHERE status = "active"')
                total_bot_users = cursor.fetchone()['total'] or 0
                
                return {
                    'total_bots': total_bots,
                    'total_users': total_users,
                    'total_messages': total_messages,
                    'total_bot_users': total_bot_users,
                    'timestamp': datetime.datetime.now().isoformat()
                }
        except Exception as e:
            logger.error(f"خطأ في الحصول على إحصائيات النظام: {e}")
            return {}
    
    # === سجل الأنشطة ===
    def log_activity(self, user_id: int, action: str, details: str = None) -> bool:
        """تسجيل نشاط المستخدم"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO activity_log (user_id, action, details, timestamp)
                    VALUES (?, ?, ?, ?)
                ''', (user_id, action, details, datetime.datetime.now().isoformat()))
                
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"خطأ في تسجيل النشاط: {e}")
            return False
    
    def get_recent_activities(self, limit: int = 50) -> List[Dict]:
        """الحصول على الأنشطة الأخيرة"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT a.*, u.username, u.first_name
                    FROM activity_log a
                    LEFT JOIN users u ON a.user_id = u.user_id
                    ORDER BY a.timestamp DESC
                    LIMIT ?
                ''', (limit,))
                
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"خطأ في الحصول على الأنشطة: {e}")
            return []

# إنشاء مثيل مشترك من مدير قاعدة البيانات
db = DatabaseManager()
