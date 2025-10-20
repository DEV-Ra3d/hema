"""
مصنع البوتات المطور - البوت الرئيسي
Advanced Bot Factory - Main Bot
"""
import os
import asyncio
import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, ContextTypes, CommandHandler, 
    CallbackQueryHandler, MessageHandler, filters, ConversationHandler
)

# استيراد الوحدات المخصصة
from config import Config, EMOJIS, MESSAGES
from database_manager import db
from bot_monitor import monitor, BotAnalytics
from utils import (
    TokenValidator, MessageFormatter, BroadcastManager, 
    SecurityManager, FileManager
)

# إعداد التسجيل
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# حالات المحادثة
(ADD_TOKEN, CONFIRM_DELETE, BROADCAST_TEXT, BROADCAST_TARGET,
 SET_LIMIT_USER, SET_LIMIT_VALUE, INCREASE_USER_ID, INCREASE_AMOUNT,
 CUSTOM_WELCOME, BOT_SETTINGS) = range(10)

class BotFactory:
    def __init__(self):
        self.app = None
        
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالج أمر البدء"""
        user = update.effective_user
        
        # تسجيل المستخدم في قاعدة البيانات
        db.add_or_update_user(
            user_id=user.id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name
        )
        
        # تسجيل النشاط
        db.log_activity(user.id, 'start_command', 'بدء استخدام البوت')
        
        # إنشاء لوحة التحكم
        keyboard = self._create_main_keyboard(user.id)
        
        await update.message.reply_text(
            Config.WELCOME_MESSAGE,
            reply_markup=keyboard,
            parse_mode='Markdown'
        )
    
    def _create_main_keyboard(self, user_id: int) -> InlineKeyboardMarkup:
        """إنشاء لوحة التحكم الرئيسية"""
        keyboard = [
            [
                InlineKeyboardButton(f'{EMOJIS["add"]} إضافة بوت', callback_data='add_bot'),
                InlineKeyboardButton(f'{EMOJIS["bot"]} بوتاتي', callback_data='my_bots')
            ],
            [
                InlineKeyboardButton(f'{EMOJIS["stats"]} إحصائياتي', callback_data='my_stats'),
                InlineKeyboardButton(f'{EMOJIS["settings"]} الإعدادات', callback_data='settings')
            ]
        ]
        
        # إضافة أزرار المالك
        if SecurityManager.is_owner(user_id):
            keyboard.extend([
                [
                    InlineKeyboardButton(f'{EMOJIS["admin"]} لوحة المالك', callback_data='admin_panel'),
                    InlineKeyboardButton(f'{EMOJIS["monitor"]} المراقبة', callback_data='monitoring')
                ],
                [
                    InlineKeyboardButton(f'{EMOJIS["broadcast"]} إذاعة', callback_data='broadcast_menu'),
                    InlineKeyboardButton(f'{EMOJIS["stats"]} إحصائيات النظام', callback_data='system_stats')
                ]
            ])
        
        return InlineKeyboardMarkup(keyboard)
    
    async def callback_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالج الأزرار"""
        query = update.callback_query
        await query.answer()
        
        user = query.from_user
        data = query.data
        
        # تسجيل النشاط
        db.log_activity(user.id, 'button_click', data)
        
        # توجيه الطلبات حسب نوع الزر
        if data == 'main_menu':
            await self._show_main_menu(query)
        elif data == 'add_bot':
            return await self._handle_add_bot(query)
        elif data == 'my_bots':
            await self._show_my_bots(query)
        elif data == 'my_stats':
            await self._show_my_stats(query)
        elif data == 'settings':
            await self._show_settings(query)
        elif data.startswith('bot_'):
            await self._handle_bot_action(query, data)
        elif data.startswith('delete_'):
            await self._handle_delete_bot(query, data)
        elif data.startswith('confirm_delete_'):
            await self._confirm_delete_bot(query, data)
        
        # أزرار المالك
        elif SecurityManager.is_owner(user.id):
            if data == 'admin_panel':
                await self._show_admin_panel(query)
            elif data == 'monitoring':
                await self._show_monitoring(query)
            elif data == 'broadcast_menu':
                await self._show_broadcast_menu(query)
            elif data == 'system_stats':
                await self._show_system_stats(query)
            elif data.startswith('admin_'):
                await self._handle_admin_action(query, data)
    
    async def _show_main_menu(self, query):
        """عرض القائمة الرئيسية"""
        keyboard = self._create_main_keyboard(query.from_user.id)
        await query.edit_message_text(
            Config.WELCOME_MESSAGE,
            reply_markup=keyboard,
            parse_mode='Markdown'
        )
    
    async def _handle_add_bot(self, query):
        """معالج إضافة بوت جديد"""
        user_id = query.from_user.id
        
        # التحقق من الحد المسموح
        current_count = db.count_user_bots(user_id)
        limit = db.get_user_limit(user_id)
        
        if current_count >= limit:
            await query.edit_message_text(
                MESSAGES['bot_limit_reached'](limit),
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton(f'{EMOJIS["back"]} العودة', callback_data='main_menu')
                ]])
            )
            return ConversationHandler.END
        
        await query.edit_message_text(
            f"""
{EMOJIS['add']} **إضافة بوت جديد**

أرسل توكن البوت الآن:

💡 **نصائح:**
• احصل على التوكن من @BotFather
• تأكد من أن التوكن صحيح
• لا تشارك التوكن مع أحد

{EMOJIS['info']} البوتات المتاحة: {current_count}/{limit}
""",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton(f'{EMOJIS["back"]} إلغاء', callback_data='main_menu')
            ]]),
            parse_mode='Markdown'
        )
        return ADD_TOKEN
    
    async def _show_my_bots(self, query):
        """عرض بوتات المستخدم"""
        user_bots = db.get_user_bots(query.from_user.id)
        
        if not user_bots:
            await query.edit_message_text(
                f"{EMOJIS['info']} {MESSAGES['no_bots_found']}",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton(f'{EMOJIS["add"]} إضافة بوت', callback_data='add_bot'),
                    InlineKeyboardButton(f'{EMOJIS["back"]} العودة', callback_data='main_menu')
                ]])
            )
            return
        
        text = f"{EMOJIS['bot']} **بوتاتك ({len(user_bots)}):**\n\n"
        keyboard = []
        
        for bot in user_bots:
            bot_info = MessageFormatter.format_bot_info(bot, include_stats=False)
            text += bot_info + "\n"
            
            bot_name = bot.get('bot_username', '') or f"Bot {bot['id']}"
            keyboard.append([
                InlineKeyboardButton(f"⚙️ {bot_name}", callback_data=f'bot_{bot["id"]}'),
                InlineKeyboardButton(f'{EMOJIS["delete"]} حذف', callback_data=f'delete_{bot["id"]}')
            ])
        
        keyboard.append([
            InlineKeyboardButton(f'{EMOJIS["add"]} إضافة بوت', callback_data='add_bot'),
            InlineKeyboardButton(f'{EMOJIS["back"]} العودة', callback_data='main_menu')
        ])
        
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    
    async def _show_my_stats(self, query):
        """عرض إحصائيات المستخدم"""
        user_bots = db.get_user_bots(query.from_user.id)
        stats_text = MessageFormatter.format_user_stats(query.from_user.id, user_bots)
        
        await query.edit_message_text(
            stats_text,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton(f'{EMOJIS["back"]} العودة', callback_data='main_menu')
            ]]),
            parse_mode='Markdown'
        )
    
    async def _handle_bot_action(self, query, data):
        """معالج إجراءات البوت المحدد"""
        bot_id = int(data.split('_')[1])
        bot_info = db.get_bot_info(bot_id)
        
        if not bot_info or not SecurityManager.can_manage_bot(query.from_user.id, bot_info['owner_id']):
            await query.answer("❌ ليس لديك صلاحية لهذا البوت")
            return
        
        # الحصول على حالة البوت من نظام المراقبة
        bot_status = monitor.get_bot_status(bot_id)
        status_text = "غير محدد"
        if bot_status:
            status_emoji = EMOJIS['active'] if bot_status['status'] == 'online' else EMOJIS['inactive']
            status_text = f"{status_emoji} {bot_status['status']}"
        
        text = f"""
{EMOJIS['bot']} **تفاصيل البوت**

{MessageFormatter.format_bot_info(bot_info)}

🔍 **الحالة الحالية:** {status_text}

⚙️ **الإجراءات المتاحة:**
"""
        
        keyboard = [
            [
                InlineKeyboardButton('🔄 فحص الحالة', callback_data=f'check_{bot_id}'),
                InlineKeyboardButton('📊 الإحصائيات', callback_data=f'stats_{bot_id}')
            ],
            [
                InlineKeyboardButton('⚙️ الإعدادات', callback_data=f'settings_{bot_id}'),
                InlineKeyboardButton(f'{EMOJIS["delete"]} حذف', callback_data=f'delete_{bot_id}')
            ],
            [
                InlineKeyboardButton(f'{EMOJIS["back"]} العودة', callback_data='my_bots')
            ]
        ]
        
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    
    async def _handle_delete_bot(self, query, data):
        """معالج حذف البوت مع التأكيد"""
        bot_id = int(data.split('_')[1])
        bot_info = db.get_bot_info(bot_id)
        
        if not bot_info or not SecurityManager.can_manage_bot(query.from_user.id, bot_info['owner_id']):
            await query.answer("❌ ليس لديك صلاحية لهذا البوت")
            return
        
        bot_name = bot_info.get('bot_username', '') or f"Bot {bot_id}"
        
        text = f"""
{EMOJIS['warning']} **تأكيد الحذف**

هل أنت متأكد من حذف البوت؟

🤖 **البوت:** {bot_name}
🆔 **المعرف:** {bot_id}

⚠️ **تحذير:** سيتم حذف:
• البوت من قاعدة البيانات
• ملف البوت من الخادم
• جميع البيانات المرتبطة

هذا الإجراء لا يمكن التراجع عنه!
"""
        
        keyboard = [
            [
                InlineKeyboardButton('❌ نعم، احذف', callback_data=f'confirm_delete_{bot_id}'),
                InlineKeyboardButton('✅ لا، إلغاء', callback_data=f'bot_{bot_id}')
            ]
        ]
        
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    
    async def _confirm_delete_bot(self, query, data):
        """تأكيد حذف البوت"""
        bot_id = int(data.split('_')[2])
        bot_info = db.get_bot_info(bot_id)
        
        if not bot_info or not SecurityManager.can_manage_bot(query.from_user.id, bot_info['owner_id']):
            await query.answer("❌ ليس لديك صلاحية لهذا البوت")
            return
        
        # حذف البوت من قاعدة البيانات
        success = db.delete_bot(bot_id, query.from_user.id)
        
        if success:
            # حذف ملف البوت
            FileManager.delete_bot_file(bot_id)
            
            # تسجيل النشاط
            db.log_activity(
                query.from_user.id,
                'bot_deleted',
                f'تم حذف البوت {bot_id}'
            )
            
            await query.edit_message_text(
                f"{EMOJIS['success']} {MESSAGES['bot_deleted'](bot_id)}",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton(f'{EMOJIS["back"]} العودة للقائمة', callback_data='my_bots')
                ]])
            )
        else:
            await query.edit_message_text(
                f"{EMOJIS['error']} فشل في حذف البوت. حاول مرة أخرى.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton(f'{EMOJIS["back"]} العودة', callback_data=f'bot_{bot_id}')
                ]])
            )
    
    # معالجات المحادثة
    async def add_token_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالج إضافة التوكن"""
        token = update.message.text.strip()
        user = update.effective_user
        
        # التحقق من صيغة التوكن
        if not TokenValidator.validate_token_format(token):
            await update.message.reply_text(
                f"{EMOJIS['error']} صيغة التوكن غير صحيحة!\n\nالصيغة الصحيحة: `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`",
                parse_mode='Markdown'
            )
            return ADD_TOKEN
        
        # التحقق من صحة التوكن عبر API
        is_valid, bot_info = await TokenValidator.validate_token_api(token)
        
        if not is_valid:
            await update.message.reply_text(
                f"{EMOJIS['error']} {MESSAGES['invalid_token']}\n\nتأكد من:\n• صحة التوكن\n• أن البوت نشط\n• عدم استخدام التوكن مسبقاً"
            )
            return ADD_TOKEN
        
        # إضافة البوت لقاعدة البيانات
        bot_id = db.add_bot(user.id, token, bot_info)
        
        if bot_id:
            # إنشاء ملف البوت
            bot_code = FileManager.create_bot_file(bot_id, token)
            FileManager.save_bot_file(bot_id, bot_code)
            
            # تسجيل النشاط
            db.log_activity(
                user.id,
                'bot_created',
                f'تم إنشاء البوت {bot_info.get("username", bot_id)}'
            )
            
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton(f'{EMOJIS["bot"]} عرض البوت', callback_data=f'bot_{bot_id}')],
                [InlineKeyboardButton(f'{EMOJIS["home"]} القائمة الرئيسية', callback_data='main_menu')]
            ])
            
            await update.message.reply_text(
                f"{EMOJIS['success']} {Config.BOT_CREATED_MESSAGE}\n\n🤖 **اسم البوت:** {bot_info.get('first_name', 'غير محدد')}\n🔗 **المعرف:** @{bot_info.get('username', 'غير محدد')}",
                reply_markup=keyboard,
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(
                f"{EMOJIS['error']} فشل في إضافة البوت. حاول مرة أخرى."
            )
        
        return ConversationHandler.END
    
    # معالجات المالك
    async def _show_admin_panel(self, query):
        """لوحة تحكم المالك"""
        system_stats = db.get_system_stats()
        
        text = f"""
{EMOJIS['admin']} **لوحة تحكم المالك**

📊 **إحصائيات سريعة:**
• البوتات النشطة: {system_stats.get('total_bots', 0)}
• إجمالي المستخدمين: {system_stats.get('total_users', 0)}
• إجمالي الرسائل: {system_stats.get('total_messages', 0):,}

⚙️ **الإدارة:**
"""
        
        keyboard = [
            [
                InlineKeyboardButton('👥 إدارة المستخدمين', callback_data='admin_users'),
                InlineKeyboardButton('🤖 إدارة البوتات', callback_data='admin_bots')
            ],
            [
                InlineKeyboardButton('📊 التحليلات المتقدمة', callback_data='admin_analytics'),
                InlineKeyboardButton('🗂️ سجل الأنشطة', callback_data='admin_logs')
            ],
            [
                InlineKeyboardButton(f'{EMOJIS["back"]} العودة', callback_data='main_menu')
            ]
        ]
        
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    
    async def _show_monitoring(self, query):
        """عرض نظام المراقبة"""
        report = monitor.get_monitoring_report()
        
        keyboard = [
            [
                InlineKeyboardButton('🔄 تحديث', callback_data='monitoring'),
                InlineKeyboardButton('⚙️ إعدادات المراقبة', callback_data='monitor_settings')
            ],
            [
                InlineKeyboardButton(f'{EMOJIS["back"]} العودة', callback_data='admin_panel')
            ]
        ]
        
        await query.edit_message_text(
            report,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    
    async def _show_system_stats(self, query):
        """عرض إحصائيات النظام"""
        analytics_report = BotAnalytics.generate_analytics_report()
        
        keyboard = [
            [
                InlineKeyboardButton('🔄 تحديث', callback_data='system_stats'),
                InlineKeyboardButton('📈 تحليلات متقدمة', callback_data='admin_analytics')
            ],
            [
                InlineKeyboardButton(f'{EMOJIS["back"]} العودة', callback_data='admin_panel')
            ]
        ]
        
        await query.edit_message_text(
            analytics_report,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    
    async def _show_broadcast_menu(self, query):
        """قائمة الإذاعة"""
        text = f"""
{EMOJIS['broadcast']} **نظام الإذاعة المتقدم**

اختر نوع الإذاعة:

📢 **الإذاعة العادية:** عبر البوت الرئيسي
🤖 **الإذاعة الذكية:** عبر البوتات المصنوعة
👥 **إذاعة مخصصة:** لمجموعة محددة

💡 **مميزات الإذاعة الذكية:**
• توزيع الحمولة على البوتات
• معدل وصول أعلى
• تجنب حدود الإرسال
"""
        
        keyboard = [
            [
                InlineKeyboardButton('📢 إذاعة عادية', callback_data='broadcast_normal'),
                InlineKeyboardButton('🤖 إذاعة ذكية', callback_data='broadcast_smart')
            ],
            [
                InlineKeyboardButton('👥 إذاعة مخصصة', callback_data='broadcast_custom'),
                InlineKeyboardButton('📊 إحصائيات الإذاعة', callback_data='broadcast_stats')
            ],
            [
                InlineKeyboardButton(f'{EMOJIS["back"]} العودة', callback_data='admin_panel')
            ]
        ]
        
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    
    async def cancel_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالج الإلغاء"""
        await update.message.reply_text(
            f"{EMOJIS['info']} {MESSAGES['operation_cancelled']}",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton(f'{EMOJIS["home"]} القائمة الرئيسية', callback_data='main_menu')
            ]])
        )
        return ConversationHandler.END
    
    def setup_handlers(self):
        """إعداد معالجات البوت"""
        # معالج المحادثة الرئيسي
        conv_handler = ConversationHandler(
            entry_points=[CallbackQueryHandler(self.callback_handler)],
            states={
                ADD_TOKEN: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.add_token_handler)],
                BROADCAST_TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.broadcast_text_handler)],
                SET_LIMIT_USER: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.set_limit_user_handler)],
                SET_LIMIT_VALUE: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.set_limit_value_handler)],
                INCREASE_USER_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.increase_user_id_handler)],
                INCREASE_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.increase_amount_handler)],
            },
            fallbacks=[CommandHandler('cancel', self.cancel_handler)],
            per_chat=True,
            per_user=True,
            name='factory_conversation'
        )
        
        # إضافة المعالجات
        self.app.add_handler(CommandHandler('start', self.start_command))
        self.app.add_handler(conv_handler)
        self.app.add_handler(CallbackQueryHandler(self.callback_handler))
        
        logger.info("✅ تم إعداد معالجات البوت بنجاح")
    
    # معالجات الإذاعة والإدارة (يتم إضافتها لاحقاً)
    async def broadcast_text_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالج نص الإذاعة"""
        # سيتم تنفيذها لاحقاً
        pass
    
    async def set_limit_user_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالج تعديل حد المستخدم"""
        # سيتم تنفيذها لاحقاً
        pass
    
    async def set_limit_value_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالج قيمة الحد الجديد"""
        # سيتم تنفيذها لاحقاً
        pass
    
    async def increase_user_id_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالج زيادة حد المستخدم"""
        # سيتم تنفيذها لاحقاً
        pass
    
    async def increase_amount_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالج مقدار الزيادة"""
        # سيتم تنفيذها لاحقاً
        pass
    
    def run(self):
        """تشغيل البوت"""
        # التحقق من الإعدادات
        if not Config.validate():
            return
        
        # إنشاء التطبيق
        self.app = ApplicationBuilder().token(Config.BOT_TOKEN).build()
        
        # إعداد المعالجات
        self.setup_handlers()
        
        # بدء نظام المراقبة
        monitor.start_monitoring()
        
        logger.info("🚀 بدء تشغيل مصنع البوتات...")
        logger.info(f"👑 معرف المالك: {Config.OWNER_ID}")
        
        try:
            # تشغيل البوت
            self.app.run_polling(
                drop_pending_updates=True,
                allowed_updates=['message', 'callback_query']
            )
        except KeyboardInterrupt:
            logger.info("⏹️ تم إيقاف البوت بواسطة المستخدم")
        except Exception as e:
            logger.error(f"❌ خطأ في تشغيل البوت: {e}")
        finally:
            # إيقاف نظام المراقبة
            monitor.stop_monitoring()
            logger.info("👋 تم إغلاق مصنع البوتات")

def main():
    """الدالة الرئيسية"""
    try:
        factory = BotFactory()
        factory.run()
    except Exception as e:
        logger.error(f"❌ خطأ فادح: {e}")

if __name__ == '__main__':
    main()
