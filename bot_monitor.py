"""
نظام مراقبة البوتات
Bot Monitoring System
"""
import asyncio
import logging
import requests
import threading
import time
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from database_manager import db
from config import Config, EMOJIS

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BotMonitor:
    def __init__(self):
        self.monitoring = False
        self.monitor_thread = None
        self.bot_statuses = {}
        self.last_check = None
        
    def start_monitoring(self):
        """بدء مراقبة البوتات"""
        if self.monitoring:
            return
            
        self.monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        logger.info("🔍 تم بدء نظام مراقبة البوتات")
    
    def stop_monitoring(self):
        """إيقاف مراقبة البوتات"""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        logger.info("⏹️ تم إيقاف نظام مراقبة البوتات")
    
    def _monitor_loop(self):
        """حلقة المراقبة الرئيسية"""
        while self.monitoring:
            try:
                self._check_all_bots()
                self.last_check = datetime.now()
                time.sleep(Config.MONITOR_INTERVAL)
            except Exception as e:
                logger.error(f"خطأ في حلقة المراقبة: {e}")
                time.sleep(60)  # انتظار دقيقة في حالة الخطأ
    
    def _check_all_bots(self):
        """فحص جميع البوتات النشطة"""
        active_bots = db.get_all_bots()
        
        for bot in active_bots:
            if bot['status'] == 'active':
                status = self._check_bot_health(bot['token'])
                self.bot_statuses[bot['id']] = {
                    'status': status,
                    'last_check': datetime.now().isoformat(),
                    'bot_info': bot
                }
                
                # تحديث حالة البوت في قاعدة البيانات
                if status == 'offline':
                    self._handle_bot_offline(bot)
    
    def _check_bot_health(self, token: str) -> str:
        """فحص حالة بوت واحد"""
        try:
            url = f"https://api.telegram.org/bot{token}/getMe"
            response = requests.get(url, timeout=Config.HEALTH_CHECK_TIMEOUT)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('ok'):
                    return 'online'
                else:
                    return 'error'
            else:
                return 'offline'
                
        except requests.exceptions.Timeout:
            return 'timeout'
        except requests.exceptions.RequestException:
            return 'offline'
        except Exception as e:
            logger.error(f"خطأ في فحص البوت: {e}")
            return 'error'
    
    def _handle_bot_offline(self, bot: Dict):
        """التعامل مع البوت المتوقف"""
        logger.warning(f"⚠️ البوت {bot['id']} متوقف")
        
        # تسجيل النشاط
        db.log_activity(
            user_id=bot['owner_id'],
            action='bot_offline',
            details=f"البوت {bot['bot_username'] or bot['id']} متوقف"
        )
    
    def get_bot_status(self, bot_id: int) -> Optional[Dict]:
        """الحصول على حالة بوت محدد"""
        return self.bot_statuses.get(bot_id)
    
    def get_all_statuses(self) -> Dict:
        """الحصول على حالة جميع البوتات"""
        return {
            'bots': self.bot_statuses,
            'last_check': self.last_check.isoformat() if self.last_check else None,
            'monitoring': self.monitoring
        }
    
    def get_monitoring_report(self) -> str:
        """إنشاء تقرير مراقبة مفصل"""
        if not self.bot_statuses:
            return f"{EMOJIS['info']} لم يتم فحص أي بوتات بعد"
        
        online_count = sum(1 for status in self.bot_statuses.values() 
                          if status['status'] == 'online')
        offline_count = sum(1 for status in self.bot_statuses.values() 
                           if status['status'] == 'offline')
        error_count = sum(1 for status in self.bot_statuses.values() 
                         if status['status'] == 'error')
        
        total_bots = len(self.bot_statuses)
        
        report = f"""
{EMOJIS['monitor']} **تقرير مراقبة البوتات**

📊 **الإحصائيات:**
{EMOJIS['active']} متصل: {online_count}
{EMOJIS['inactive']} منقطع: {offline_count}
{EMOJIS['error']} خطأ: {error_count}
📈 المجموع: {total_bots}

⏰ **آخر فحص:** {self.last_check.strftime('%Y-%m-%d %H:%M:%S') if self.last_check else 'لم يتم'}

🔄 **حالة المراقبة:** {'نشط' if self.monitoring else 'متوقف'}
"""
        
        # إضافة تفاصيل البوتات المتوقفة
        offline_bots = [
            status for status in self.bot_statuses.values()
            if status['status'] in ['offline', 'error']
        ]
        
        if offline_bots:
            report += f"\n{EMOJIS['warning']} **البوتات المتوقفة:**\n"
            for bot_status in offline_bots[:5]:  # أول 5 بوتات فقط
                bot_info = bot_status['bot_info']
                report += f"• {bot_info.get('bot_username', f'Bot {bot_info[\"id\"]}')} - {bot_status['status']}\n"
        
        return report
    
    def force_check_bot(self, bot_id: int) -> Dict:
        """فحص فوري لبوت محدد"""
        bot_info = db.get_bot_info(bot_id)
        if not bot_info:
            return {'error': 'البوت غير موجود'}
        
        status = self._check_bot_health(bot_info['token'])
        result = {
            'bot_id': bot_id,
            'status': status,
            'checked_at': datetime.now().isoformat(),
            'bot_info': bot_info
        }
        
        self.bot_statuses[bot_id] = result
        return result

class BotAnalytics:
    """نظام تحليل أداء البوتات"""
    
    @staticmethod
    def get_bot_performance(bot_id: int, days: int = 7) -> Dict:
        """تحليل أداء بوت لفترة محددة"""
        try:
            with db.get_connection() as conn:
                cursor = conn.cursor()
                
                # الحصول على إحصائيات آخر أسبوع
                start_date = (datetime.now() - timedelta(days=days)).date().isoformat()
                
                cursor.execute('''
                    SELECT date, messages_count, users_count, groups_count
                    FROM bot_stats
                    WHERE bot_id = ? AND date >= ?
                    ORDER BY date
                ''', (bot_id, start_date))
                
                stats = cursor.fetchall()
                
                if not stats:
                    return {'error': 'لا توجد إحصائيات متاحة'}
                
                # حساب المتوسطات والمجاميع
                total_messages = sum(row['messages_count'] for row in stats)
                total_users = max(row['users_count'] for row in stats) if stats else 0
                avg_messages_per_day = total_messages / len(stats) if stats else 0
                
                # اتجاه النمو
                if len(stats) >= 2:
                    recent_avg = sum(row['messages_count'] for row in stats[-3:]) / min(3, len(stats))
                    old_avg = sum(row['messages_count'] for row in stats[:3]) / min(3, len(stats))
                    growth_trend = 'up' if recent_avg > old_avg else 'down' if recent_avg < old_avg else 'stable'
                else:
                    growth_trend = 'unknown'
                
                return {
                    'bot_id': bot_id,
                    'period_days': days,
                    'total_messages': total_messages,
                    'total_users': total_users,
                    'avg_messages_per_day': round(avg_messages_per_day, 2),
                    'growth_trend': growth_trend,
                    'daily_stats': [dict(row) for row in stats]
                }
                
        except Exception as e:
            logger.error(f"خطأ في تحليل أداء البوت {bot_id}: {e}")
            return {'error': str(e)}
    
    @staticmethod
    def get_top_performing_bots(limit: int = 10) -> List[Dict]:
        """الحصول على أفضل البوتات أداءً"""
        try:
            with db.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT b.id, b.bot_username, b.bot_name, b.total_messages, 
                           b.total_users, b.owner_id, u.first_name as owner_name
                    FROM bots b
                    LEFT JOIN users u ON b.owner_id = u.user_id
                    WHERE b.status = 'active'
                    ORDER BY b.total_messages DESC
                    LIMIT ?
                ''', (limit,))
                
                return [dict(row) for row in cursor.fetchall()]
                
        except Exception as e:
            logger.error(f"خطأ في الحصول على أفضل البوتات: {e}")
            return []
    
    @staticmethod
    def generate_analytics_report() -> str:
        """إنشاء تقرير تحليلي شامل"""
        try:
            # إحصائيات النظام العامة
            system_stats = db.get_system_stats()
            
            # أفضل البوتات
            top_bots = BotAnalytics.get_top_performing_bots(5)
            
            report = f"""
📊 **تقرير التحليلات الشامل**

🔢 **إحصائيات النظام:**
• إجمالي البوتات: {system_stats.get('total_bots', 0)}
• إجمالي المستخدمين: {system_stats.get('total_users', 0)}
• إجمالي الرسائل: {system_stats.get('total_messages', 0):,}
• مستخدمي البوتات: {system_stats.get('total_bot_users', 0)}

🏆 **أفضل البوتات أداءً:**
"""
            
            for i, bot in enumerate(top_bots, 1):
                bot_name = bot['bot_username'] or bot['bot_name'] or f"Bot {bot['id']}"
                report += f"{i}. {bot_name} - {bot['total_messages']:,} رسالة\n"
            
            if not top_bots:
                report += "لا توجد بيانات متاحة\n"
            
            report += f"\n📅 **تاريخ التقرير:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            
            return report
            
        except Exception as e:
            logger.error(f"خطأ في إنشاء تقرير التحليلات: {e}")
            return f"{EMOJIS['error']} خطأ في إنشاء التقرير"

# إنشاء مثيل مشترك من نظام المراقبة
monitor = BotMonitor()
