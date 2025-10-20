"""
أدوات ومساعدات مصنع البوتات
Bot Factory Utilities
"""
import re
import requests
import asyncio
import logging
from typing import Dict, Optional, List, Tuple
from datetime import datetime
from config import Config, EMOJIS, MESSAGES

logger = logging.getLogger(__name__)

class TokenValidator:
    """مدقق صحة التوكنات"""
    
    @staticmethod
    def validate_token_format(token: str) -> bool:
        """التحقق من صيغة التوكن"""
        if not token or not isinstance(token, str):
            return False
        
        # صيغة توكن تيليجرام: NUMBER:STRING
        pattern = r'^\d+:[A-Za-z0-9_-]+$'
        return bool(re.match(pattern, token.strip()))
    
    @staticmethod
    async def validate_token_api(token: str) -> Tuple[bool, Optional[Dict]]:
        """التحقق من صحة التوكن عبر API تيليجرام"""
        if not TokenValidator.validate_token_format(token):
            return False, None
        
        try:
            url = f"https://api.telegram.org/bot{token}/getMe"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('ok'):
                    bot_info = data.get('result', {})
                    return True, bot_info
                else:
                    return False, None
            else:
                return False, None
                
        except Exception as e:
            logger.error(f"خطأ في التحقق من التوكن: {e}")
            return False, None
    
    @staticmethod
    def extract_bot_id(token: str) -> Optional[int]:
        """استخراج معرف البوت من التوكن"""
        if not TokenValidator.validate_token_format(token):
            return None
        
        try:
            bot_id = int(token.split(':')[0])
            return bot_id
        except (ValueError, IndexError):
            return None

class MessageFormatter:
    """منسق الرسائل والنصوص"""
    
    @staticmethod
    def format_bot_info(bot: Dict, include_stats: bool = True) -> str:
        """تنسيق معلومات البوت"""
        bot_name = bot.get('bot_username', '') or bot.get('bot_name', '') or f"Bot {bot['id']}"
        created_date = datetime.fromisoformat(bot['date_created']).strftime('%Y-%m-%d')
        
        text = f"""
{EMOJIS['bot']} **{bot_name}**
🆔 المعرف: `{bot['id']}`
📅 تاريخ الإنشاء: {created_date}
"""
        
        if include_stats:
            text += f"""📊 الرسائل: {bot.get('total_messages', 0):,}
👥 المستخدمين: {bot.get('total_users', 0):,}
"""
        
        # حالة البوت
        status_emoji = EMOJIS['active'] if bot.get('status') == 'active' else EMOJIS['inactive']
        status_text = 'نشط' if bot.get('status') == 'active' else 'متوقف'
        text += f"{status_emoji} الحالة: {status_text}\n"
        
        return text
    
    @staticmethod
    def format_user_stats(user_id: int, bots: List[Dict]) -> str:
        """تنسيق إحصائيات المستخدم"""
        total_messages = sum(bot.get('total_messages', 0) for bot in bots)
        total_users = sum(bot.get('total_users', 0) for bot in bots)
        
        text = f"""
{EMOJIS['user']} **إحصائياتك**

🤖 عدد البوتات: {len(bots)}
📊 إجمالي الرسائل: {total_messages:,}
👥 إجمالي المستخدمين: {total_users:,}
"""
        return text
    
    @staticmethod
    def format_broadcast_result(sent: int, failed: int, total: int) -> str:
        """تنسيق نتيجة الإذاعة"""
        success_rate = (sent / total * 100) if total > 0 else 0
        
        text = f"""
{EMOJIS['broadcast']} **نتيجة الإذاعة**

✅ تم الإرسال: {sent}
❌ فشل الإرسال: {failed}
📊 المجموع: {total}
📈 معدل النجاح: {success_rate:.1f}%
"""
        return text
    
    @staticmethod
    def format_time_ago(timestamp_str: str) -> str:
        """تنسيق الوقت المنقضي"""
        try:
            timestamp = datetime.fromisoformat(timestamp_str)
            now = datetime.now()
            diff = now - timestamp
            
            if diff.days > 0:
                return f"منذ {diff.days} يوم"
            elif diff.seconds > 3600:
                hours = diff.seconds // 3600
                return f"منذ {hours} ساعة"
            elif diff.seconds > 60:
                minutes = diff.seconds // 60
                return f"منذ {minutes} دقيقة"
            else:
                return "الآن"
        except:
            return "غير محدد"

class BroadcastManager:
    """مدير الإذاعة المحسن"""
    
    @staticmethod
    async def send_broadcast_via_factory(bot_instance, message: str, target_users: List[int]) -> Dict:
        """إرسال إذاعة عبر البوت الرئيسي"""
        sent = 0
        failed = 0
        errors = []
        
        for user_id in target_users:
            try:
                await bot_instance.send_message(
                    chat_id=user_id,
                    text=f"{EMOJIS['broadcast']} **إذاعة من مصنع البوتات**\n\n{message}",
                    parse_mode='Markdown'
                )
                sent += 1
                
                # تأخير بسيط لتجنب حدود API
                await asyncio.sleep(Config.BROADCAST_DELAY)
                
            except Exception as e:
                failed += 1
                errors.append(f"User {user_id}: {str(e)}")
                logger.error(f"فشل إرسال الإذاعة للمستخدم {user_id}: {e}")
        
        return {
            'sent': sent,
            'failed': failed,
            'total': len(target_users),
            'errors': errors
        }
    
    @staticmethod
    async def send_broadcast_via_bots(message: str, bot_tokens: List[str], target_users: List[int]) -> Dict:
        """إرسال إذاعة عبر البوتات المصنوعة"""
        sent = 0
        failed = 0
        errors = []
        
        # توزيع المستخدمين على البوتات
        users_per_bot = len(target_users) // len(bot_tokens) if bot_tokens else 0
        
        for i, token in enumerate(bot_tokens):
            start_idx = i * users_per_bot
            end_idx = start_idx + users_per_bot if i < len(bot_tokens) - 1 else len(target_users)
            bot_users = target_users[start_idx:end_idx]
            
            bot_result = await BroadcastManager._send_via_single_bot(token, message, bot_users)
            sent += bot_result['sent']
            failed += bot_result['failed']
            errors.extend(bot_result['errors'])
        
        return {
            'sent': sent,
            'failed': failed,
            'total': len(target_users),
            'errors': errors,
            'bots_used': len(bot_tokens)
        }
    
    @staticmethod
    async def _send_via_single_bot(token: str, message: str, users: List[int]) -> Dict:
        """إرسال عبر بوت واحد"""
        sent = 0
        failed = 0
        errors = []
        
        for user_id in users:
            try:
                url = f"https://api.telegram.org/bot{token}/sendMessage"
                data = {
                    'chat_id': user_id,
                    'text': f"{EMOJIS['broadcast']} {message}",
                    'parse_mode': 'Markdown'
                }
                
                response = requests.post(url, data=data, timeout=10)
                if response.status_code == 200:
                    sent += 1
                else:
                    failed += 1
                    errors.append(f"User {user_id}: HTTP {response.status_code}")
                
                await asyncio.sleep(Config.BROADCAST_DELAY)
                
            except Exception as e:
                failed += 1
                errors.append(f"User {user_id}: {str(e)}")
        
        return {'sent': sent, 'failed': failed, 'errors': errors}

class SecurityManager:
    """مدير الأمان"""
    
    @staticmethod
    def is_owner(user_id: int) -> bool:
        """التحقق من كون المستخدم هو المالك"""
        return user_id == Config.OWNER_ID
    
    @staticmethod
    def can_manage_bot(user_id: int, bot_owner_id: int) -> bool:
        """التحقق من صلاحية إدارة البوت"""
        return user_id == bot_owner_id or SecurityManager.is_owner(user_id)
    
    @staticmethod
    def sanitize_input(text: str, max_length: int = 1000) -> str:
        """تنظيف وتأمين النص المدخل"""
        if not text:
            return ""
        
        # إزالة الأحرف الخطيرة
        text = text.strip()
        text = text[:max_length]  # تحديد الطول الأقصى
        
        # إزالة HTML tags
        text = re.sub(r'<[^>]+>', '', text)
        
        return text
    
    @staticmethod
    def validate_user_limit(current_count: int, limit: int) -> bool:
        """التحقق من حد البوتات للمستخدم"""
        return current_count < limit

class FileManager:
    """مدير الملفات"""
    
    @staticmethod
    def create_bot_file(bot_id: int, token: str, welcome_message: str = None) -> str:
        """إنشاء ملف البوت المخصص"""
        welcome_msg = welcome_message or "مرحباً! أنا بوت تم إنشاؤي عبر مصنع البوتات 🤖"
        
        bot_code = f'''#!/usr/bin/env python3
"""
بوت تم إنشاؤه عبر مصنع البوتات
Bot created via Bot Factory
Bot ID: {bot_id}
Created: {datetime.now().isoformat()}
"""
import os
import json
import random
import logging
import requests
from telebot import TeleBot
from telebot.types import Message

# إعداد التسجيل
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('bot_{bot_id}')

# التوكن
BOT_TOKEN = "{token}"
bot = TeleBot(BOT_TOKEN)

# رسالة الترحيب
WELCOME_MESSAGE = """{welcome_msg}"""

# الرموز التعبيرية للتفاعل
REACTIONS = ["😀", "❤️", "😎", "😉", "🙈", "😊", "👍", "🔥", "🎉", "💯"]

# معرف المالك (سيتم تحديده تلقائياً)
OWNER_ID = None

@bot.message_handler(commands=['start'])
def handle_start(message: Message):
    """معالج أمر البدء"""
    global OWNER_ID
    
    # تحديد المالك عند أول استخدام
    if OWNER_ID is None:
        OWNER_ID = message.from_user.id
        logger.info(f"تم تحديد المالك: {{OWNER_ID}}")
    
    # ترحيب خاص بالمالك
    if message.from_user.id == OWNER_ID:
        welcome_text = f"🎉 مرحباً بك يا مالك البوت!\\n\\n{{WELCOME_MESSAGE}}\\n\\n👑 أنت المالك الآن ولديك صلاحيات كاملة."
    else:
        welcome_text = WELCOME_MESSAGE
    
    bot.reply_to(message, welcome_text)

@bot.message_handler(commands=['help'])
def handle_help(message: Message):
    """معالج أمر المساعدة"""
    help_text = """
🤖 **أوامر البوت:**

/start - بدء البوت
/help - عرض المساعدة
/stats - إحصائيات البوت (للمالك فقط)

🎯 **الميزات:**
• تفاعل تلقائي مع الرسائل
• ترحيب بالأعضاء الجدد
• استجابة ذكية للرسائل

تم إنشاؤه بواسطة مصنع البوتات 🏭
"""
    bot.reply_to(message, help_text)

@bot.message_handler(commands=['stats'])
def handle_stats(message: Message):
    """معالج إحصائيات البوت (للمالك فقط)"""
    if message.from_user.id != OWNER_ID:
        bot.reply_to(message, "❌ هذا الأمر للمالك فقط")
        return
    
    # هنا يمكن إضافة إحصائيات حقيقية
    stats_text = f"""
📊 **إحصائيات البوت:**

🆔 معرف البوت: {bot_id}
👤 المالك: {{message.from_user.first_name}}
📅 تاريخ الإنشاء: {{datetime.now().strftime('%Y-%m-%d')}}
🔄 حالة البوت: نشط ✅

💡 لمزيد من الإحصائيات، راجع لوحة التحكم في مصنع البوتات
"""
    bot.reply_to(message, stats_text)

@bot.message_handler(content_types=['new_chat_members'])
def handle_new_member(message: Message):
    """ترحيب بالأعضاء الجدد"""
    for new_member in message.new_chat_members:
        welcome_text = f"🎉 مرحباً {{new_member.first_name}}!\\n\\n{{WELCOME_MESSAGE}}"
        bot.reply_to(message, welcome_text)

@bot.message_handler(func=lambda message: True)
def handle_all_messages(message: Message):
    """معالج جميع الرسائل"""
    try:
        # تفاعل عشوائي
        if random.random() < 0.3:  # 30% احتمال للتفاعل
            emoji = random.choice(REACTIONS)
            
            # محاولة إضافة تفاعل
            try:
                reaction_url = f"https://api.telegram.org/bot{{BOT_TOKEN}}/setMessageReaction"
                reaction_data = {{
                    'chat_id': message.chat.id,
                    'message_id': message.message_id,
                    'reaction': json.dumps([{{'type': 'emoji', 'emoji': emoji}}])
                }}
                
                response = requests.post(reaction_url, data=reaction_data, timeout=5)
                if response.status_code != 200:
                    # إذا فشل التفاعل، أرسل رد نصي
                    bot.reply_to(message, f"{{emoji}}")
                    
            except Exception as e:
                logger.debug(f"فشل التفاعل: {{e}}")
                # رد نصي كبديل
                bot.reply_to(message, f"{{emoji}}")
        
        # تسجيل النشاط (يمكن إرساله لمصنع البوتات لاحقاً)
        logger.info(f"رسالة من {{message.from_user.id}} في {{message.chat.id}}")
        
    except Exception as e:
        logger.error(f"خطأ في معالجة الرسالة: {{e}}")

if __name__ == '__main__':
    logger.info("🚀 بدء تشغيل البوت...")
    try:
        bot.infinity_polling(timeout=10, long_polling_timeout=5)
    except Exception as e:
        logger.error(f"خطأ في تشغيل البوت: {{e}}")
'''
        
        return bot_code
    
    @staticmethod
    def save_bot_file(bot_id: int, bot_code: str) -> str:
        """حفظ ملف البوت"""
        filename = f"bot_{bot_id}.py"
        filepath = f"/workspace/hema/bots/{filename}"
        
        # إنشاء مجلد البوتات إذا لم يكن موجوداً
        os.makedirs("/workspace/hema/bots", exist_ok=True)
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(bot_code)
            logger.info(f"تم حفظ ملف البوت: {filepath}")
            return filepath
        except Exception as e:
            logger.error(f"خطأ في حفظ ملف البوت: {e}")
            return None
    
    @staticmethod
    def delete_bot_file(bot_id: int) -> bool:
        """حذف ملف البوت"""
        filepath = f"/workspace/hema/bots/bot_{bot_id}.py"
        
        try:
            if os.path.exists(filepath):
                os.remove(filepath)
                logger.info(f"تم حذف ملف البوت: {filepath}")
                return True
            return False
        except Exception as e:
            logger.error(f"خطأ في حذف ملف البوت: {e}")
            return False

# دوال مساعدة إضافية
def format_number(number: int) -> str:
    """تنسيق الأرقام بالفواصل"""
    return f"{number:,}"

def truncate_text(text: str, max_length: int = 100) -> str:
    """اقتطاع النص مع إضافة نقاط"""
    if len(text) <= max_length:
        return text
    return text[:max_length-3] + "..."

def get_user_display_name(user) -> str:
    """الحصول على اسم المستخدم للعرض"""
    if hasattr(user, 'first_name') and user.first_name:
        name = user.first_name
        if hasattr(user, 'last_name') and user.last_name:
            name += f" {user.last_name}"
        return name
    elif hasattr(user, 'username') and user.username:
        return f"@{user.username}"
    else:
        return f"User {user.id}"
