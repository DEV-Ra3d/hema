"""
قالب البوت المحسن - يتم استخدامه كأساس للبوتات المُنشأة
Enhanced Bot Template - Used as base for created bots
"""
import os
import json
import random
import logging
import requests
import threading
import time
from datetime import datetime
from telebot import TeleBot
from telebot.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

# إعداد التسجيل
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('bot_template')

class EnhancedBot:
    def __init__(self, token: str, bot_id: int = None):
        self.token = token
        self.bot_id = bot_id
        self.bot = TeleBot(token)
        self.owner_id = None
        self.stats = {
            'messages_count': 0,
            'users_count': 0,
            'groups_count': 0,
            'start_time': datetime.now()
        }
        self.user_cache = set()
        self.group_cache = set()
        
        # إعدادات البوت
        self.settings = {
            'welcome_message': "🎉 مرحباً! أنا بوت تم إنشاؤي عبر مصنع البوتات 🤖\n\nأرسل /help للمساعدة",
            'auto_react': True,
            'reaction_probability': 0.3,
            'welcome_new_members': True,
            'owner_notifications': True,
            'stats_reporting': True
        }
        
        # الرموز التعبيرية للتفاعل
        self.reactions = [
            "😀", "❤️", "😎", "😉", "🙈", "😊", 
            "👍", "🔥", "🎉", "💯", "⭐", "🚀"
        ]
        
        self.setup_handlers()
        logger.info(f"تم إنشاء البوت بنجاح - ID: {bot_id}")
    
    def setup_handlers(self):
        """إعداد معالجات البوت"""
        
        @self.bot.message_handler(commands=['start'])
        def handle_start(message: Message):
            self._handle_start(message)
        
        @self.bot.message_handler(commands=['help'])
        def handle_help(message: Message):
            self._handle_help(message)
        
        @self.bot.message_handler(commands=['stats'])
        def handle_stats(message: Message):
            self._handle_stats(message)
        
        @self.bot.message_handler(commands=['settings'])
        def handle_settings(message: Message):
            self._handle_settings(message)
        
        @self.bot.message_handler(content_types=['new_chat_members'])
        def handle_new_member(message: Message):
            self._handle_new_member(message)
        
        @self.bot.message_handler(content_types=['left_chat_member'])
        def handle_left_member(message: Message):
            self._handle_left_member(message)
        
        @self.bot.message_handler(func=lambda message: True)
        def handle_all_messages(message: Message):
            self._handle_all_messages(message)
        
        @self.bot.callback_query_handler(func=lambda call: True)
        def handle_callback(call: CallbackQuery):
            self._handle_callback(call)
    
    def _handle_start(self, message: Message):
        """معالج أمر البدء"""
        user_id = message.from_user.id
        
        # تحديد المالك عند أول استخدام
        if self.owner_id is None:
            self.owner_id = user_id
            logger.info(f"تم تحديد المالك: {user_id}")
            
            # إشعار المالك
            if self.settings['owner_notifications']:
                self._send_owner_notification(
                    f"🎉 مرحباً بك! تم تعيينك كمالك للبوت.\n\n"
                    f"🤖 معرف البوت: {self.bot_id or 'غير محدد'}\n"
                    f"⏰ وقت التفعيل: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                    f"استخدم /help للحصول على قائمة الأوامر."
                )
        
        # رسالة ترحيب مخصصة للمالك
        if user_id == self.owner_id:
            welcome_text = f"""
👑 **مرحباً بك يا مالك البوت!**

{self.settings['welcome_message']}

🎛️ **أوامرك الخاصة:**
/stats - عرض الإحصائيات
/settings - إعدادات البوت

تم إنشاؤه بواسطة مصنع البوتات 🏭
"""
        else:
            welcome_text = self.settings['welcome_message']
        
        # إنشاء لوحة ترحيب
        keyboard = InlineKeyboardMarkup()
        keyboard.row(
            InlineKeyboardButton("📚 المساعدة", callback_data="help"),
            InlineKeyboardButton("ℹ️ حول البوت", callback_data="about")
        )
        
        self.bot.reply_to(message, welcome_text, reply_markup=keyboard, parse_mode='Markdown')
        self._update_stats(message)
    
    def _handle_help(self, message: Message):
        """معالج أمر المساعدة"""
        help_text = """
🤖 **دليل استخدام البوت**

📋 **الأوامر العامة:**
/start - بدء البوت
/help - عرض هذه المساعدة

🎯 **الميزات:**
• تفاعل تلقائي مع الرسائل
• ترحيب بالأعضاء الجدد
• استجابة ذكية للرسائل
• إحصائيات مفصلة

"""
        
        # إضافة أوامر المالك
        if message.from_user.id == self.owner_id:
            help_text += """
👑 **أوامر المالك:**
/stats - إحصائيات مفصلة
/settings - إعدادات البوت

"""
        
        help_text += "🏭 تم إنشاؤه بواسطة مصنع البوتات"
        
        self.bot.reply_to(message, help_text, parse_mode='Markdown')
        self._update_stats(message)
    
    def _handle_stats(self, message: Message):
        """معالج إحصائيات البوت (للمالك فقط)"""
        if message.from_user.id != self.owner_id:
            self.bot.reply_to(message, "❌ هذا الأمر للمالك فقط")
            return
        
        # حساب وقت التشغيل
        uptime = datetime.now() - self.stats['start_time']
        uptime_str = f"{uptime.days} يوم، {uptime.seconds // 3600} ساعة"
        
        stats_text = f"""
📊 **إحصائيات البوت المفصلة**

🆔 **معرف البوت:** {self.bot_id or 'غير محدد'}
👤 **المالك:** {message.from_user.first_name}
⏰ **وقت التشغيل:** {uptime_str}

📈 **الإحصائيات:**
📨 الرسائل المعالجة: {self.stats['messages_count']:,}
👥 المستخدمين الفريدين: {len(self.user_cache)}
🏘️ المجموعات النشطة: {len(self.group_cache)}

⚙️ **الإعدادات الحالية:**
🎭 التفاعل التلقائي: {'نشط' if self.settings['auto_react'] else 'متوقف'}
🎉 ترحيب الأعضاء: {'نشط' if self.settings['welcome_new_members'] else 'متوقف'}
📊 تقارير الإحصائيات: {'نشط' if self.settings['stats_reporting'] else 'متوقف'}

💡 لمزيد من الإحصائيات، راجع لوحة التحكم في مصنع البوتات
"""
        
        keyboard = InlineKeyboardMarkup()
        keyboard.row(
            InlineKeyboardButton("⚙️ الإعدادات", callback_data="settings"),
            InlineKeyboardButton("🔄 تحديث", callback_data="refresh_stats")
        )
        
        self.bot.reply_to(message, stats_text, reply_markup=keyboard, parse_mode='Markdown')
        self._update_stats(message)
    
    def _handle_settings(self, message: Message):
        """معالج إعدادات البوت (للمالك فقط)"""
        if message.from_user.id != self.owner_id:
            self.bot.reply_to(message, "❌ هذا الأمر للمالك فقط")
            return
        
        settings_text = """
⚙️ **إعدادات البوت**

يمكنك تخصيص سلوك البوت من هنا:
"""
        
        keyboard = InlineKeyboardMarkup()
        
        # إعدادات التفاعل
        react_status = "🟢 نشط" if self.settings['auto_react'] else "🔴 متوقف"
        keyboard.row(InlineKeyboardButton(f"تفاعل تلقائي: {react_status}", callback_data="toggle_react"))
        
        # إعدادات الترحيب
        welcome_status = "🟢 نشط" if self.settings['welcome_new_members'] else "🔴 متوقف"
        keyboard.row(InlineKeyboardButton(f"ترحيب الأعضاء: {welcome_status}", callback_data="toggle_welcome"))
        
        # إعدادات الإشعارات
        notif_status = "🟢 نشط" if self.settings['owner_notifications'] else "🔴 متوقف"
        keyboard.row(InlineKeyboardButton(f"إشعارات المالك: {notif_status}", callback_data="toggle_notifications"))
        
        keyboard.row(
            InlineKeyboardButton("📝 تعديل رسالة الترحيب", callback_data="edit_welcome"),
            InlineKeyboardButton("🎭 إعدادات التفاعل", callback_data="reaction_settings")
        )
        
        self.bot.reply_to(message, settings_text, reply_markup=keyboard, parse_mode='Markdown')
        self._update_stats(message)
    
    def _handle_new_member(self, message: Message):
        """ترحيب بالأعضاء الجدد"""
        if not self.settings['welcome_new_members']:
            return
        
        for new_member in message.new_chat_members:
            # تجنب الترحيب بالبوتات
            if new_member.is_bot:
                continue
            
            welcome_text = f"""
🎉 مرحباً {new_member.first_name}!

{self.settings['welcome_message']}

نتمنى لك وقتاً ممتعاً معنا! 🌟
"""
            
            keyboard = InlineKeyboardMarkup()
            keyboard.row(InlineKeyboardButton("📚 المساعدة", callback_data="help"))
            
            self.bot.reply_to(message, welcome_text, reply_markup=keyboard, parse_mode='Markdown')
        
        self._update_stats(message)
    
    def _handle_left_member(self, message: Message):
        """معالج مغادرة الأعضاء"""
        left_member = message.left_chat_member
        if left_member and not left_member.is_bot:
            goodbye_text = f"👋 وداعاً {left_member.first_name}، نتمنى أن نراك مرة أخرى!"
            self.bot.reply_to(message, goodbye_text)
        
        self._update_stats(message)
    
    def _handle_all_messages(self, message: Message):
        """معالج جميع الرسائل"""
        try:
            # تحديث الإحصائيات
            self._update_stats(message)
            
            # التفاعل التلقائي
            if self.settings['auto_react'] and random.random() < self.settings['reaction_probability']:
                self._react_to_message(message)
            
            # تسجيل النشاط
            logger.info(f"رسالة من {message.from_user.id} في {message.chat.id}")
            
            # إرسال تقرير دوري للمالك (كل 100 رسالة)
            if (self.settings['stats_reporting'] and 
                self.stats['messages_count'] % 100 == 0 and 
                self.owner_id):
                self._send_periodic_report()
                
        except Exception as e:
            logger.error(f"خطأ في معالجة الرسالة: {e}")
    
    def _handle_callback(self, call: CallbackQuery):
        """معالج أزرار التفاعل"""
        try:
            self.bot.answer_callback_query(call.id)
            
            if call.data == "help":
                self._show_help_callback(call)
            elif call.data == "about":
                self._show_about_callback(call)
            elif call.data == "settings" and call.from_user.id == self.owner_id:
                self._show_settings_callback(call)
            elif call.data.startswith("toggle_") and call.from_user.id == self.owner_id:
                self._handle_toggle_setting(call)
            elif call.data == "refresh_stats" and call.from_user.id == self.owner_id:
                self._refresh_stats_callback(call)
            
        except Exception as e:
            logger.error(f"خطأ في معالجة الزر: {e}")
    
    def _react_to_message(self, message: Message):
        """إضافة تفاعل للرسالة"""
        emoji = random.choice(self.reactions)
        
        try:
            # محاولة استخدام API التفاعل الجديد
            reaction_url = f"https://api.telegram.org/bot{self.token}/setMessageReaction"
            reaction_data = {
                'chat_id': message.chat.id,
                'message_id': message.message_id,
                'reaction': json.dumps([{'type': 'emoji', 'emoji': emoji}])
            }
            
            response = requests.post(reaction_url, data=reaction_data, timeout=5)
            
            if response.status_code != 200:
                # إذا فشل التفاعل، أرسل رد نصي
                self.bot.reply_to(message, emoji)
                
        except Exception as e:
            logger.debug(f"فشل التفاعل: {e}")
            try:
                # رد نصي كبديل
                self.bot.reply_to(message, emoji)
            except:
                pass  # تجاهل الأخطاء في الرد البديل
    
    def _update_stats(self, message: Message):
        """تحديث إحصائيات البوت"""
        self.stats['messages_count'] += 1
        
        # تتبع المستخدمين الفريدين
        self.user_cache.add(message.from_user.id)
        
        # تتبع المجموعات
        if message.chat.type in ['group', 'supergroup']:
            self.group_cache.add(message.chat.id)
    
    def _send_owner_notification(self, text: str):
        """إرسال إشعار للمالك"""
        if self.owner_id and self.settings['owner_notifications']:
            try:
                self.bot.send_message(self.owner_id, text, parse_mode='Markdown')
            except Exception as e:
                logger.error(f"فشل إرسال الإشعار للمالك: {e}")
    
    def _send_periodic_report(self):
        """إرسال تقرير دوري للمالك"""
        if not self.owner_id:
            return
        
        report = f"""
📊 **تقرير دوري - البوت {self.bot_id or 'غير محدد'}**

📈 **الإحصائيات الحالية:**
📨 الرسائل: {self.stats['messages_count']:,}
👥 المستخدمين: {len(self.user_cache)}
🏘️ المجموعات: {len(self.group_cache)}

⏰ **الوقت:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

🏭 مصنع البوتات
"""
        
        self._send_owner_notification(report)
    
    def _show_help_callback(self, call: CallbackQuery):
        """عرض المساعدة عبر الزر"""
        help_text = """
🤖 **دليل استخدام البوت**

🎯 **الميزات الرئيسية:**
• تفاعل ذكي مع الرسائل
• ترحيب تلقائي بالأعضاء الجدد  
• استجابة سريعة ومرنة
• إحصائيات مفصلة

📋 **الأوامر:**
/start - بدء البوت
/help - المساعدة

🏭 تم إنشاؤه بواسطة مصنع البوتات
"""
        
        keyboard = InlineKeyboardMarkup()
        keyboard.row(InlineKeyboardButton("ℹ️ حول البوت", callback_data="about"))
        
        self.bot.edit_message_text(
            help_text,
            call.message.chat.id,
            call.message.message_id,
            reply_markup=keyboard,
            parse_mode='Markdown'
        )
    
    def _show_about_callback(self, call: CallbackQuery):
        """عرض معلومات البوت"""
        about_text = f"""
ℹ️ **حول هذا البوت**

🤖 **معرف البوت:** {self.bot_id or 'غير محدد'}
⏰ **تاريخ الإنشاء:** {self.stats['start_time'].strftime('%Y-%m-%d')}
👑 **المالك:** {self.owner_id or 'غير محدد'}

🎯 **المهام:**
• تفاعل ذكي مع المستخدمين
• إدارة المجموعات
• تقديم الخدمات التفاعلية

🏭 **تم إنشاؤه بواسطة مصنع البوتات**
🔗 للمزيد من البوتات المخصصة

📊 **الإحصائيات:**
📨 {self.stats['messages_count']:,} رسالة معالجة
👥 {len(self.user_cache)} مستخدم فريد
"""
        
        keyboard = InlineKeyboardMarkup()
        keyboard.row(InlineKeyboardButton("📚 المساعدة", callback_data="help"))
        
        self.bot.edit_message_text(
            about_text,
            call.message.chat.id,
            call.message.message_id,
            reply_markup=keyboard,
            parse_mode='Markdown'
        )
    
    def run(self):
        """تشغيل البوت"""
        logger.info(f"🚀 بدء تشغيل البوت {self.bot_id or 'غير محدد'}...")
        
        try:
            self.bot.infinity_polling(
                timeout=10,
                long_polling_timeout=5,
                none_stop=True,
                interval=0
            )
        except Exception as e:
            logger.error(f"خطأ في تشغيل البوت: {e}")
            # إعادة المحاولة بعد 5 ثوانِ
            time.sleep(5)
            self.run()

def main():
    """الدالة الرئيسية"""
    # الحصول على التوكن من متغير البيئة
    token = os.getenv('BOT_TOKEN')
    if not token:
        logger.error("❌ متغير BOT_TOKEN غير موجود")
        return
    
    # إنشاء وتشغيل البوت
    try:
        bot_instance = EnhancedBot(token)
        bot_instance.run()
    except KeyboardInterrupt:
        logger.info("⏹️ تم إيقاف البوت بواسطة المستخدم")
    except Exception as e:
        logger.error(f"❌ خطأ فادح: {e}")

if __name__ == '__main__':
    main()
