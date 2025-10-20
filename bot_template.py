"""Bot template script — this is the script each installed bot will run.
Usage: set environment variable BOT_TOKEN to the bot's token (do NOT commit tokens into git).
The script reacts with a random emoji to incoming messages and replies "i react with {emoji}".
"""
import os, json, random, logging, requests
from telebot import TeleBot
from telebot.types import Message

logging.basicConfig(level=logging.INFO)
log = logging.getLogger('bot_template')

API_TOKEN = os.getenv('BOT_TOKEN')
if not API_TOKEN:
    raise RuntimeError('Set BOT_TOKEN environment variable for the bot.')

bot = TeleBot(API_TOKEN)

REACTIONS = ["\uD83D\uDE00", "\u2764\uFE0F", "\uD83D\uDE0E", "\uD83D\uDE09", "\uD83D\uDE48", "\uD83D\uDE0A"]

def send_message_react(chat_id, message_id, emoji):
    """Attempt to call setMessageReaction endpoint; fallback to replying with text if not available."""
    url = f"https://api.telegram.org/bot{API_TOKEN}/setMessageReaction"
    # fixed malformed braces and ensure valid JSON payload for 'reaction'
    payload = {
        'chat_id': chat_id,
        'message_id': message_id,
        'reaction': json.dumps([{'type': 'emoji', 'emoji': emoji}])
    }
    try:
        r = requests.post(url, data=payload, timeout=10)
        if r.status_code == 200:
            return r.json()
    except Exception as e:
        log.debug('reaction endpoint failed: %s', e)

    # Fallback: reply with a text message indicating the reaction
    try:
        # prefer using TeleBot instance if available
        if 'bot' in globals() and hasattr(bot, 'send_message'):
            bot.send_message(chat_id, f'i react with {emoji}', reply_to_message_id=message_id)
        else:
            # fallback to HTTP sendMessage endpoint
            fallback_url = f"https://api.telegram.org/bot{API_TOKEN}/sendMessage"
            requests.post(fallback_url, data={
                'chat_id': chat_id,
                'text': f'i react with {emoji}',
                'reply_to_message_id': message_id
            }, timeout=10)
    except Exception:
        log.exception('failed fallback reply')
    return None

@bot.message_handler(func=lambda m: True)
def handle_all(message: Message):
    emoji = random.choice(REACTIONS)
    try:
        send_message_react(message.chat.id, message.message_id, emoji)
    except Exception:
        log.exception('error sending reaction')

if __name__ == '__main__':
    log.info('Starting bot template (polling)...')
    bot.infinity_polling()