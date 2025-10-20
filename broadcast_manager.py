"""
مدير الإذاعة - Broadcast Manager
"""
import asyncio
import logging
import time
from typing import Dict, List, Any
from telegram import Message
from telegram.error import TelegramError

from database import db
from config import BROADCAST_DELAY, MAX_BROADCAST_RETRIES

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

class BroadcastManager:
    def __init__(self):
        self.active_broadcasts = {}
    
    async def broadcast_to_all(self, message: Message) -> Dict[str, Any]:
        """إذاعة الرسالة لجميع المستخدمين عبر جميع البوتات"""
        start_time = time.time()
        
        # الحصول على جميع المستخدمين المميزين
        all_bots = db.get_all_bots()
        active_bots = [bot for bot in all_bots if bot[5] == 'active']  # status
        
        # جمع معرفات المستخدمين الفريدة
        unique_users = set()
        bot_tokens = {}
        
        for bot in active_bots:
            bot_id, owner_id, token, username, created, status, last_seen, msg_count, user_count = bot
            unique_users.add(owner_id)
            bot_tokens[owner_id] = token
        
        # إحصائيات الإرسال
        total_users = len(unique_users)
        success_count = 0
        failed_count = 0
        
        log.info(f"Starting broadcast to {total_users} users via {len(active_bots)} bots")
        
        # إرسال الرسائل
        for user_id in unique_users:
            try:
                # محاولة الإرسال عبر البوت الرئيسي أولاً
                success = await self.send_via_main_bot(message, user_id)
                
                if not success:
                    # إذا فشل، جرب الإرسال عبر بوت المستخدم
                    user_token = bot_tokens.get(user_id)
                    if user_token:
                        success = await self.send_via_user_bot(message, user_id, user_token)
                
                if success:
                    success_count += 1
                else:
                    failed_count += 1
                
                # تأخير بين الرسائل لتجنب الحظر
                await asyncio.sleep(BROADCAST_DELAY)
                
            except Exception as e:
                log.error(f"Error broadcasting to user {user_id}: {e}")
                failed_count += 1
        
        end_time = time.time()
        duration = end_time - start_time
        
        # تسجيل النتائج
        db.log_activity(
            message.from_user.id,
            'broadcast_completed',
            f'Sent to {success_count}/{total_users} users in {duration:.2f}s'
        )
        
        return {
            'total': total_users,
            'success': success_count,
            'failed': failed_count,
            'duration': duration
        }
    
    async def send_via_main_bot(self, original_message: Message, target_user_id: int) -> bool:
        """إرسال الرسالة عبر البوت الرئيسي"""
        try:
            broadcast_text = f"📢 <b>إذاعة من مصنع البوتات</b>\n\n{original_message.text or original_message.caption or ''}"
            
            if original_message.photo:
                await original_message.bot.send_photo(
                    chat_id=target_user_id,
                    photo=original_message.photo[-1].file_id,
                    caption=broadcast_text,
                    parse_mode='HTML'
                )
            elif original_message.document:
                await original_message.bot.send_document(
                    chat_id=target_user_id,
                    document=original_message.document.file_id,
                    caption=broadcast_text,
                    parse_mode='HTML'
                )
            elif original_message.video:
                await original_message.bot.send_video(
                    chat_id=target_user_id,
                    video=original_message.video.file_id,
                    caption=broadcast_text,
                    parse_mode='HTML'
                )
            else:
                await original_message.bot.send_message(
                    chat_id=target_user_id,
                    text=broadcast_text,
                    parse_mode='HTML'
                )
            
            return True
            
        except TelegramError as e:
            log.debug(f"Failed to send via main bot to {target_user_id}: {e}")
            return False
        except Exception as e:
            log.error(f"Unexpected error sending via main bot to {target_user_id}: {e}")
            return False
    
    async def send_via_user_bot(self, original_message: Message, target_user_id: int, bot_token: str) -> bool:
        """إرسال الرسالة عبر بوت المستخدم"""
        try:
            import aiohttp
            
            # إعداد الرسالة
            broadcast_text = f"📢 <b>إذاعة خاصة</b>\n\n{original_message.text or original_message.caption or ''}"
            
            # إرسال عبر API مباشرة
            url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            
            payload = {
                'chat_id': target_user_id,
                'text': broadcast_text,
                'parse_mode': 'HTML'
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, timeout=10) as response:
                    if response.status == 200:
                        result = await response.json()
                        return result.get('ok', False)
            
            return False
            
        except Exception as e:
            log.debug(f"Failed to send via user bot to {target_user_id}: {e}")
            return False
    
    async def broadcast_to_bot_users(self, bot_id: int, message: Message) -> Dict[str, Any]:
        """إذاعة لمستخدمي بوت محدد"""
        start_time = time.time()
        
        # الحصول على معلومات البوت
        bot_info = db.get_bot_info(bot_id)
        if not bot_info:
            return {'error': 'Bot not found'}
        
        # الحصول على مستخدمي البوت من قاعدة البيانات
        # هذا يتطلب تتبع المستخدمين في البوتات المصنوعة
        # سيتم تنفيذه في النسخة المحدثة من قالب البوت
        
        return {
            'total': 0,
            'success': 0,
            'failed': 0,
            'duration': time.time() - start_time
        }
    
    async def schedule_broadcast(self, message: Message, target_time: str) -> bool:
        """جدولة إذاعة لوقت محدد"""
        try:
            # تحويل الوقت المحدد إلى timestamp
            import datetime
            target_datetime = datetime.datetime.fromisoformat(target_time)
            current_datetime = datetime.datetime.now()
            
            if target_datetime <= current_datetime:
                return False
            
            delay_seconds = (target_datetime - current_datetime).total_seconds()
            
            # جدولة المهمة
            asyncio.create_task(self._delayed_broadcast(message, delay_seconds))
            
            return True
            
        except Exception as e:
            log.error(f"Error scheduling broadcast: {e}")
            return False
    
    async def _delayed_broadcast(self, message: Message, delay: float):
        """تنفيذ الإذاعة المؤجلة"""
        await asyncio.sleep(delay)
        await self.broadcast_to_all(message)
    
    def get_broadcast_stats(self) -> Dict[str, Any]:
        """الحصول على إحصائيات الإذاعة"""
        # الحصول على إحصائيات من قاعدة البيانات
        activity_log = db.get_activity_log(100)
        broadcast_activities = [
            activity for activity in activity_log 
            if activity[1] == 'broadcast_completed'
        ]
        
        if not broadcast_activities:
            return {
                'total_broadcasts': 0,
                'total_messages_sent': 0,
                'average_success_rate': 0,
                'last_broadcast': None
            }
        
        total_broadcasts = len(broadcast_activities)
        last_broadcast = broadcast_activities[0][3] if broadcast_activities else None
        
        # حساب معدل النجاح
        success_rates = []
        total_messages = 0
        
        for activity in broadcast_activities:
            details = activity[2]  # details column
            if details and 'Sent to' in details:
                try:
                    # استخراج الأرقام من النص
                    parts = details.split('/')
                    if len(parts) >= 2:
                        sent = int(parts[0].split()[-1])
                        total = int(parts[1].split()[0])
                        success_rates.append(sent / total * 100)
                        total_messages += total
                except:
                    continue
        
        average_success_rate = sum(success_rates) / len(success_rates) if success_rates else 0
        
        return {
            'total_broadcasts': total_broadcasts,
            'total_messages_sent': total_messages,
            'average_success_rate': round(average_success_rate, 2),
            'last_broadcast': last_broadcast
        }
