"""
ملف الإعدادات لمصنع البوتات
Configuration file for Bot Factory
"""
import os
from typing import Optional

class Config:
    # إعدادات البوت الرئيسي
    BOT_TOKEN: Optional[str] = os.getenv('BOT_TOKEN')
    OWNER_ID: Optional[int] = int(os.getenv('OWNER_ID', '0'))
    
    # إعدادات قاعدة البيانات
    DB_PATH: str = os.getenv('DB_PATH', 'database.db')
    
    # إعدادات النظام
    DEFAULT_LIMIT: int = int(os.getenv('DEFAULT_LIMIT', '3'))
    MAX_BOTS_PER_USER: int = int(os.getenv('MAX_BOTS_PER_USER', '10'))
    
    # إعدادات المراقبة
    MONITOR_INTERVAL: int = int(os.getenv('MONITOR_INTERVAL', '300'))  # 5 دقائق
    HEALTH_CHECK_TIMEOUT: int = int(os.getenv('HEALTH_CHECK_TIMEOUT', '10'))
    
    # إعدادات الإذاعة
    BROADCAST_DELAY: float = float(os.getenv('BROADCAST_DELAY', '0.1'))  # تأخير بين الرسائل
    MAX_BROADCAST_RETRIES: int = int(os.getenv('MAX_BROADCAST_RETRIES', '3'))
    
    # رسائل النظام
    WELCOME_MESSAGE: str = """
🤖 مرحباً بك في مصنع البوتات!

هنا يمكنك:
✅ إنشاء بوتات تيليجرام مخصصة
📊 مراقبة أداء بوتاتك
📢 إرسال إذاعات جماعية
🎛️ التحكم الكامل في بوتاتك

اختر من القائمة أدناه للبدء:
"""
    
    BOT_CREATED_MESSAGE: str = """
🎉 تم إنشاء البوت بنجاح!

✅ البوت جاهز للاستخدام
🔗 يمكنك الآن بدء محادثة مع البوت
📊 ستجد إحصائيات البوت في لوحة التحكم

نصائح مهمة:
• تأكد من إضافة البوت كمشرف في المجموعات
• يمكنك تخصيص رسائل الترحيب من الإعدادات
"""

    @classmethod
    def validate(cls) -> bool:
        """التحقق من صحة الإعدادات"""
        if not cls.BOT_TOKEN:
            print("❌ خطأ: BOT_TOKEN غير موجود في متغيرات البيئة")
            return False
        
        if not cls.OWNER_ID or cls.OWNER_ID == 0:
            print("❌ خطأ: OWNER_ID غير صحيح في متغيرات البيئة")
            return False
            
        return True

# إعدادات الرموز التعبيرية
EMOJIS = {
    'success': '✅',
    'error': '❌',
    'warning': '⚠️',
    'info': 'ℹ️',
    'bot': '🤖',
    'add': '➕',
    'delete': '🗑️',
    'edit': '✏️',
    'stats': '📊',
    'broadcast': '📢',
    'monitor': '👁️',
    'settings': '⚙️',
    'back': '🔙',
    'home': '🏠',
    'user': '👤',
    'admin': '👑',
    'active': '🟢',
    'inactive': '🔴',
    'loading': '⏳'
}

# قوالب الرسائل
MESSAGES = {
    'bot_limit_reached': lambda limit: f"⚠️ وصلت للحد المسموح: {limit} بوت\nاطلب من المالك زيادة الحد.",
    'invalid_token': "❌ التوكن غير صحيح أو منتهي الصلاحية",
    'bot_deleted': lambda bot_id: f"✅ تم حذف البوت {bot_id} بنجاح",
    'permission_denied': "❌ ليس لديك صلاحية لهذا الإجراء",
    'operation_cancelled': "❌ تم إلغاء العملية",
    'broadcast_sent': lambda count: f"📢 تم إرسال الإذاعة إلى {count} مستخدم",
    'no_bots_found': "ℹ️ لا توجد بوتات مسجلة"
}
