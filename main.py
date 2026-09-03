# main.py
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
import os
from config import Config
from database import Database
from handlers import Handlers
from settings import Settings

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

async def main():
    # Initialize database
    db = Database(Config.MONGO_URI, Config.DB_NAME)
    await db.connect()
    
    # Initialize handlers and settings
    handlers = Handlers(db)
    settings = Settings(db)
    
    # Build the application
    application = Application.builder().token(Config.BOT_TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", handlers.start))
    application.add_handler(CommandHandler("help", handlers.help))
    application.add_handler(CommandHandler("settings", handlers.settings))
    application.add_handler(CallbackQueryHandler(handlers.button))
    
    # Add message handler for awaiting input (text) in private chat - must come before search handler
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND) & filters.ChatType.PRIVATE, handlers.handle_awaiting_input))
    # Add message handler for awaiting thumbnail (photo) in private chat
    application.add_handler(MessageHandler(filters.PHOTO & filters.ChatType.PRIVATE, handlers.handle_awaiting_input))
    
    # Add message handler for file indexing (only in file channels)
    application.add_handler(MessageHandler(filters.ChatType.CHANNEL & (filters.Document.ALL | filters.VIDEO | filters.AUDIO), handlers.index_file))
    
    # Add message handler for search in groups and private (this will be skipped if awaiting input handler handled the message)
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND) & (filters.ChatType.GROUP | filters.ChatType.PRIVATE), handlers.search))
    
    # Admin commands
    application.add_handler(CommandHandler("stats", handlers.stats))
    application.add_handler(CommandHandler("logs", handlers.logs))
    application.add_handler(CommandHandler("broadcast", handlers.broadcast))
    application.add_handler(CommandHandler("users", handlers.users))
    application.add_handler(CommandHandler("chats", handlers.chats))
    application.add_handler(CommandHandler("bans", handlers.bans))
    application.add_handler(CommandHandler("filters", handlers.filters))
    application.add_handler(CommandHandler("globalfilters", handlers.global_filters))
    application.add_handler(CommandHandler("deletefile", handlers.delete_file))
    application.add_handler(CommandHandler("premium", handlers.premium))
    application.add_handler(CommandHandler("restart", handlers.restart))
    
    # Start the bot
    await application.run_polling()

if __name__ == '__main__':
    import asyncio
    asyncio.run(main())