# telegram-filter-bot
A powerful Telegram auto-filter bot for file channels and groups with admin settings, file indexing, smart search, and deployment options.

## 🚀 Features

- **Auto-indexing**: Files from specified Telegram channels are automatically indexed
- **Smart search**: Works in groups & private chat with fuzzy matching (handles typos/misspellings)
- **File interactions**: 
  - Stream & download links (placeholders - integrate with your streaming service)
  - Rename files, set custom captions/thumbnails
  - Set metadata: language, season, episode, quality, year
- **Admin controls** (via `/settings` menu):
  - Toggle all big features: clone bot creation, multiple DB support, premium plans, referrals, force subscribe, request to join approval, URL shortener, token verification, PM search, auto-delete in PM, stream/download links
- **Admin commands**:
  - `/stats` - Bot statistics
  - `/logs` - Recent logs
  - `/broadcast` - Send message to all users
  - `/users` / `/chats` - List users/chats
  - `/bans` - List banned users
  - `/filters` / `/globalfilters` - Manage filters
  - `/deletefile <query>` - Delete indexed files
  - `/premium` - Premium management
  - `/restart` - Restart bot

## 📁 File Structure

- `main.py` - Bot entry point
- `config.py` - Configuration (loads from `.env`)
- `database.py` - MongoDB async interface using Motor
- `handlers.py` - All bot logic and handlers
- `settings.py` - Placeholder
- `requirements.txt` - Python dependencies
- `Dockerfile` - Containerization
- `Procfile` - Heroku deployment
- `.env.example` - Environment template

## ⚙️ Setup

1. Clone the repo:
   ```bash
   git clone git@github.com:Therazerhub/razerfilterbot.git
   ```

2. Set up environment:
   ```bash
   cp .env.example .env
   # Edit .env with your values
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Run the bot:
   ```bash
   python main.py
   ```

## 🌐 Deployment Options

- **Docker**: 
  ```bash
  docker build -t filterbot .
  docker run -d --env-file .env filterbot
  ```
- **Heroku**: Push repo, set config vars, worker dyno runs via Procfile
- **Render/Koyeb/VPS**: Use Dockerfile or run directly with Python

## 🔑 Required Environment Variables

Create a `.env` file with:
```
BOT_TOKEN=your_telegram_bot_token
MONGO_URI=mongodb_connection_string
DB_NAME=telegram_filter_bot
ADMIN_IDS=123456789 987654321  # space-separated admin IDs
FILE_CHANNELS=-1001234567890 -1009876543210  # space-separated channel IDs
LOG_CHANNEL=-1001122334455  # optional, for logs
```

## 💻 Technologies

- Python 3.12+
- python-telegram-bot v21.4 (async)
- Motor (async MongoDB driver)
- MongoDB for storage

## 📝 License

MIT

---
Built with ❤️ by Hermes Agent