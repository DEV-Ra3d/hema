# Bot Factory (Telegram) - Inline Control via Factory Bot (Polling)

Features:
- Single factory bot (controls everything via inline buttons and messages).
- Local SQLite database `database.db` (lightweight).
- Owner ID: 7788181885 (set in code).
- Default per-user bot limit: 3 (owner can change per user and increase allowances).
- Users can add/delete only their own bots; owner can view/delete any bot.
- Broadcast (owner only) to factory users (sends message via factory bot).
- No payments; no webhooks (uses long polling).

Run locally:
1. Create a virtualenv and install dependencies:
   ```bash
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```
2. Set your factory bot token (the token of the controlling bot) in environment:
   ```bash
   export BOT_TOKEN="123456:ABC-DEF..."
   ```
3. Run:
   ```bash
   python bot_factory_main.py
   ```
4. Interact with the factory bot in Telegram. The owner (7788181885) will see extra admin buttons.

Deploy on Northflank:
- Push this repo to GitHub and configure a Northflank Deployment Service (use Dockerfile).
- Add BOT_TOKEN as Secret in Northflank Secret Group.

Notes:
- The DB `database.db` will be created automatically on first run.
- This is an MVP: you can later expand to store chat IDs from individual bots for message sending through them.
