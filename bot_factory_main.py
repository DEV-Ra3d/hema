import os, asyncio, logging, sqlite3, datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ConversationHandler

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

# === CONFIG ===
OWNER_ID = 7788181885  # owner id provided
DB_PATH = 'database.db'
DEFAULT_LIMIT = 3

# Conversation states
ADD_TOKEN, CONFIRM_DELETE, BROADCAST_TEXT, SET_LIMIT_USER, SET_LIMIT_VALUE, INCREASE_USER_ID, INCREASE_AMOUNT = range(7)

# DB helpers
def init_db():
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS bots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            owner_id INTEGER NOT NULL,
            token TEXT NOT NULL,
            date_created TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'active'
        )
    ''')
    cur.execute('''
        CREATE TABLE IF NOT EXISTS user_limits (
            user_id INTEGER PRIMARY KEY,
            allow_count INTEGER NOT NULL
        )
    ''')
    con.commit()
    con.close()

def get_user_limit(user_id):
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute('SELECT allow_count FROM user_limits WHERE user_id=?', (user_id,))
    r = cur.fetchone()
    con.close()
    if r:
        return r[0]
    return DEFAULT_LIMIT

def set_user_limit(user_id, count):
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute('INSERT INTO user_limits(user_id, allow_count) VALUES(?,?) ON CONFLICT(user_id) DO UPDATE SET allow_count=excluded.allow_count', (user_id, count))
    con.commit(); con.close()

def count_user_bots(user_id):
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute('SELECT COUNT(*) FROM bots WHERE owner_id=? AND status="active"', (user_id,))
    r = cur.fetchone()[0]
    con.close()
    return r

def add_bot_record(owner_id, token):
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute('INSERT INTO bots(owner_id, token, date_created, status) VALUES(?,?,?,?)', (owner_id, token, datetime.datetime.utcnow().isoformat(), 'active'))
    con.commit()
    con.close()

def delete_bot_record(bot_id):
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute('UPDATE bots SET status="deleted" WHERE id=?', (bot_id,))
    con.commit()
    con.close()

def get_user_bots(user_id):
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute('SELECT id, token, date_created FROM bots WHERE owner_id=? AND status="active"', (user_id,))
    rows = cur.fetchall()
    con.close()
    return rows

def get_all_bots():
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute('SELECT id, owner_id, token, date_created, status FROM bots')
    rows = cur.fetchall()
    con.close()
    return rows

# === Bot logic ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    kb = [
        [InlineKeyboardButton('➕ إضافة بوت', callback_data='add_bot'), InlineKeyboardButton('📋 عرض بوتاتي', callback_data='my_bots')],
        [InlineKeyboardButton('🗑️ حذف بوت', callback_data='del_bot')]
    ]
    if user.id == OWNER_ID:
        kb.append([InlineKeyboardButton('👁️ عرض كل البوتات', callback_data='all_bots')])
        kb.append([InlineKeyboardButton('📢 إذاعة', callback_data='broadcast'), InlineKeyboardButton('🔧 تعديل حد لمستخدم', callback_data='set_limit')])
        kb.append([InlineKeyboardButton('➕ زيادة حد لمستخدم', callback_data='increase_limit')])
    reply_markup = InlineKeyboardMarkup(kb)
    await update.message.reply_text('أهلاً! هذه لوحة مصنع البوتات. اختر عملية:', reply_markup=reply_markup)

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user = query.from_user
    if data == 'add_bot':
        await query.message.reply_text('أرسل توكن البوت الذي تريد إضافته الآن:')
        return ADD_TOKEN
    if data == 'my_bots':
        rows = get_user_bots(user.id)
        if not rows:
            await query.message.reply_text('لا توجد بوتات مسجلة لديك.')
            return
        text = 'بوتاتك:\n'
        kb = []
        for r in rows:
            bid, token, created = r
            text += f'ID: {bid} — created: {created}\n'
            kb.append([InlineKeyboardButton(f'حذف بوت {bid}', callback_data=f'del_{bid}')])
        await query.message.reply_text(text, reply_markup=InlineKeyboardMarkup(kb))
        return
    if data.startswith('del_'):
        bid = int(data.split('_')[1])
        # ensure owner
        con = sqlite3.connect(DB_PATH)
        cur = con.cursor()
        cur.execute('SELECT owner_id FROM bots WHERE id=? AND status="active"', (bid,))
        row = cur.fetchone()
        con.close()
        if not row:
            await query.message.reply_text('البوت مش موجود أو بالفعل محذوف.')
            return
        owner_id = row[0]
        if user.id != owner_id and user.id != OWNER_ID:
            await query.message.reply_text('ما تقدرش تحذف بوت مش بتاعك.')
            return
        delete_bot_record(bid)
        await query.message.reply_text(f'تم حذف البوت {bid}.')
        return
    if data == 'all_bots':
        if user.id != OWNER_ID:
            await query.message.reply_text('فقط للمالك.')
            return
        rows = get_all_bots()
        text = 'كل البوتات (شملت المحذوفة):\n'
        for r in rows:
            bid, owner_id, token, created, status = r
            text += f'ID:{bid} owner:{owner_id} status:{status} created:{created}\n'
        await query.message.reply_text(text)
        return
    if data == 'broadcast':
        if user.id != OWNER_ID:
            await query.message.reply_text('فقط للمالك.')
            return
        await query.message.reply_text('مرر الرسالة التي تريد إذاعتها الآن:')
        return BROADCAST_TEXT
    if data == 'set_limit':
        if user.id != OWNER_ID:
            await query.message.reply_text('فقط للمالك.')
            return
        await query.message.reply_text('أرسل آي دي المستخدم الذي تريد تعديل الحد له:')
        return SET_LIMIT_USER
    if data == 'increase_limit':
        if user.id != OWNER_ID:
            await query.message.reply_text('فقط للمالك.')
            return
        await query.message.reply_text('أرسل آي دي المستخدم الذي تريد زيادة الحد له:')
        return INCREASE_USER_ID
    return

async def add_token_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    user = update.effective_user
    # check limit
    limit = get_user_limit(user.id)
    current = count_user_bots(user.id)
    if current >= limit:
        await update.message.reply_text(f'وصلت للحد المسموح: {limit} بوت. اطلب من المالك زيادة الحد.')
        return ConversationHandler.END
    # store token
    add_bot_record(user.id, text)
    await update.message.reply_text('تمت الإضافة بنجاح.')
    return ConversationHandler.END

async def broadcast_text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    # broadcast to all distinct owners in bots table
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute('SELECT DISTINCT owner_id FROM bots WHERE status="active"')
    rows = cur.fetchall()
    con.close()
    sent = 0
    for r in rows:
        uid = r[0]
        try:
            await context.bot.send_message(chat_id=uid, text=f'📢 Broadcast from factory:\n\n{text}')
            sent += 1
        except Exception as e:
            log.exception('failed send to %s', uid)
    await update.message.reply_text(f'تم الإرسال إلى {sent} مستخدم.')
    return ConversationHandler.END

async def set_limit_user_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if not text.isdigit():
        await update.message.reply_text('الآي دي لازم رقم. أرسل آي دي المستخدم.')
        return SET_LIMIT_USER
    context.user_data['limit_set_target'] = int(text)
    await update.message.reply_text('الآن أرسل القيمة الجديدة للحد (مثلاً 3):')
    return SET_LIMIT_VALUE

async def set_limit_value_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if not text.isdigit():
        await update.message.reply_text('قيمة غير صحيحة. أرسل رقم.')
        return SET_LIMIT_VALUE
    uid = context.user_data.get('limit_set_target')
    count = int(text)
    set_user_limit(uid, count)
    await update.message.reply_text(f'تم وضع حد {count} للمستخدم {uid}.')
    return ConversationHandler.END

async def increase_user_id_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if not text.isdigit():
        await update.message.reply_text('الآي دي لازم رقم. أرسل آي دي المستخدم.')
        return INCREASE_USER_ID
    context.user_data['inc_target'] = int(text)
    await update.message.reply_text('الآن أرسل عدد البوتات الذي تريد إضافته (مثلاً 1):')
    return INCREASE_AMOUNT

async def increase_amount_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if not text.isdigit():
        await update.message.reply_text('أرسل رقم صحيح.')
        return INCREASE_AMOUNT
    target = context.user_data.get('inc_target')
    add = int(text)
    cur = get_user_limit(target)
    new = cur + add
    set_user_limit(target, new)
    await update.message.reply_text(f'تمت زيادة حد المستخدم {target} من {cur} إلى {new}.')
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('تم الإلغاء.')
    return ConversationHandler.END

def main():
    init_db()
    token = os.getenv('BOT_TOKEN')
    if not token:
        print('ERROR: BOT_TOKEN env var required')
        return
    app = ApplicationBuilder().token(token).build()

    conv = ConversationHandler(
    entry_points=[CallbackQueryHandler(callback_handler)],
    states={
        ADD_TOKEN: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_token_handler)],
        BROADCAST_TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, broadcast_text_handler)],
        SET_LIMIT_USER: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_limit_user_handler)],
        SET_LIMIT_VALUE: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_limit_value_handler)],
        INCREASE_USER_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, increase_user_id_handler)],
        INCREASE_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, increase_amount_handler)],
    },
    fallbacks=[CommandHandler('cancel', cancel)],
    per_chat=True,
    per_user=True,
    per_message=True,   # << هنا أضف السطر
    name='factory_conv'
)


    app.add_handler(CommandHandler('start', start))
    app.add_handler(conv)
    app.add_handler(CallbackQueryHandler(callback_handler))

    print('Bot factory is running (polling)...')
    app.run_polling()

if __name__ == '__main__':
    main()
