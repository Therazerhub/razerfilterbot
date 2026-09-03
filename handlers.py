# handlers.py
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile
from telegram.ext import ContextTypes
from typing import List
import os
import re
from difflib import SequenceMatcher

from config import Config
from database import Database

logger = logging.getLogger(__name__)

class Handlers:
    def __init__(self, db: Database):
        self.db = db

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        await self.db.add_user(user.id, {"joined_at": update.message.date, "last_seen": update.message.date})
        await update.message.reply_text(
            f"Hey {user.first_name}! I'm your auto-filter bot. I can index files from channels and let you search for them.\n"
            "Use /help to see what I can do."
        )

    async def help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        help_text = (
            "🔍 *How to use me:*\n"
            "1. Admins add channels as file sources using the bot's admin panel (or just forward files to me? Actually, we index automatically from set channels).\n"
            "2. Users send a search query in any group or private chat.\n"
            "3. I return matching files with options to stream/download.\n\n"
            "👨‍💻 *Admin Commands:*\n"
            "/stats - Bot statistics\n"
            "/logs - Recent logs\n"
            "/broadcast - Send a message to all users\n"
            "/users - List users\n"
            "/chats - List chats\n"
            "/bans - List banned users\n"
            "/filters - List chat-specific filters\n"
            "/globalfilters - List global filters\n"
            "/deletefile <query> - Delete files matching query\n"
            "/premium - Manage premium users\n"
            "/restart - Restart the bot\n\n"
            "🔧 *Features:*\n"
            "Use /settings to toggle features on/off (admin only).\n"
            "Features include: clone bot, multiple DB, premium plans, referrals, force subscribe, request to join, URL shortener, token verification, PM search, auto-delete in PM, stream/download links.\n\n"
            "💡 *Tips:*\n"
            "I support fuzzy search, so even if you misspell, I'll try to find close matches.\n"
            "You can set custom captions, thumbnails, and rename files when interacting with search results.\n"
            "For anime files, I can extract season, episode, quality, etc. if the filename follows common patterns."
        )
        await update.message.reply_text(help_text, parse_mode='Markdown')

    async def settings(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        if user_id not in Config.ADMIN_IDS:
            await update.message.reply_text("❌ This command is for admins only.")
            return

        settings = await self.db.get_settings()
        keyboard = []
        for feature, enabled in settings["features"].items():
            status = "✅ ON" if enabled else "❌ OFF"
            keyboard.append([InlineKeyboardButton(f"{feature}: {status}", callback_data=f"toggle_{feature}")])
        
        # Add a button to go back (though we don't have a back, just close)
        keyboard.append([InlineKeyboardButton("Close", callback_data="settings_close")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "⚙️ *Bot Settings* (Admin Only)\n"
            "Toggle features on or off:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

    async def button(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        data = query.data
        user_id = query.from_user.id

        if data.startswith("toggle_"):
            if user_id not in Config.ADMIN_IDS:
                await query.edit_message_text("❌ Admins only.")
                return
            feature = data.split("_", 1)[1]
            settings = await self.db.get_settings()
            new_status = not settings["features"].get(feature, False)
            await self.db.update_settings({"features." + feature: new_status})
            # Rebuild the keyboard
            keyboard = []
            for feat, enabled in settings["features"].items():
                if feat == feature:
                    enabled = new_status
                status = "✅ ON" if enabled else "❌ OFF"
                keyboard.append([InlineKeyboardButton(f"{feat}: {status}", callback_data=f"toggle_{feat}")])
            keyboard.append([InlineKeyboardButton("Close", callback_data="settings_close")])
            await query.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup(keyboard))
            await query.edit_message_text(f"✅ Feature `{feature}` set to {'ON' if new_status else 'OFF'}.", parse_mode='Markdown')

        elif data == "settings_close":
            await query.edit_message_text("Settings closed.")
        
        # File action buttons (from search results)
        elif data.startswith("file_"):
            # Example: file_<file_id>_<action>
            parts = data.split("_")
            if len(parts) < 3:
                return
            file_id = parts[1]
            action = parts[2]
            file_obj = await self.db.get_file({"_id": file_id})  # Assuming we stored _id as ObjectId, but we'll use string for simplicity
            if not file_obj:
                await query.edit_message_text("❌ File not found.")
                return

            if action == "stream":
                # Generate stream link (placeholder)
                stream_link = f"https://stream.example.com/{file_id}"
                await query.message.reply_text(f"📺 Stream link: {stream_link}")
            elif action == "download":
                # Generate download link (placeholder)
                download_link = f"https://download.example.com/{file_id}"
                await query.message.reply_text(f"💾 Download link: {download_link}")
            elif action == "rename":
                # Ask for new name
                await query.message.reply_text("Send me the new file name:")
                context.user_data['awaiting_rename'] = file_id
            elif action == "caption":
                await query.message.reply_text("Send me the new caption:")
                context.user_data['awaiting_caption'] = file_id
            elif action == "thumbnail":
                await query.message.reply_text("Send me the new thumbnail (as a photo):")
                context.user_data['awaiting_thumbnail'] = file_id
            elif action == "metadata":
                # Show metadata setting menu (season, episode, etc.)
                keyboard = [
                    [InlineKeyboardButton("Set Season", callback_data=f"meta_{file_id}_season")],
                    [InlineKeyboardButton("Set Episode", callback_data=f"meta_{file_id}_episode")],
                    [InlineKeyboardButton("Set Quality", callback_data=f"meta_{file_id}_quality")],
                    [InlineKeyboardButton("Set Year", callback_data=f"meta_{file_id}_year")],
                    [InlineKeyboardButton("Set Language", callback_data=f"meta_{file_id}_language")],
                    [InlineKeyboardButton("Back", callback_data=f"file_{file_id}_back")],
                ]
                await query.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup(keyboard))
            elif action == "back":
                # Go back to file actions
                keyboard = [
                    [InlineKeyboardButton("📺 Stream", callback_data=f"file_{file_id}_stream"),
                     InlineKeyboardButton("💾 Download", callback_data=f"file_{file_id}_download")],
                    [InlineKeyboardButton("✏️ Rename", callback_data=f"file_{file_id}_rename"),
                     InlineKeyboardButton("📝 Caption", callback_data=f"file_{file_id}_caption")],
                    [InlineKeyboardButton("🖼️ Thumbnail", callback_data=f"file_{file_id}_thumbnail"),
                     InlineKeyboardButton("🎬 Metadata", callback_data=f"file_{file_id}_metadata")],
                ]
                await query.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup(keyboard))
            
            # Handle metadata setting
            elif data.startswith("meta_"):
                # meta_<file_id>_<field>
                meta_parts = data.split("_")
                if len(meta_parts) < 4:
                    return
                meta_file_id = meta_parts[1]
                meta_field = meta_parts[2]
                await query.message.reply_text(f"Send me the value for {meta_field}:")
                context.user_data[f'awaiting_meta_{meta_field}'] = meta_file_id

        # Handle text input for rename, caption, etc.
        elif data.startswith("awaiting_"):
            # This is handled in the message handler, not in callback
            pass

    async def index_file(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        # Only index if the chat is in FILE_CHANNELS
        chat_id = update.effective_chat.id
        if chat_id not in Config.FILE_CHANNELS:
            return

        message = update.effective_message
        file_info = {}

        # Determine file type and get file_id
        if message.document:
            file_info["file_id"] = message.document.file_id
            file_info["file_name"] = message.document.file_name
            file_info["file_size"] = message.document.file_size
            file_info["mime_type"] = message.document.mime_type
        elif message.video:
            file_info["file_id"] = message.video.file_id
            file_info["file_name"] = message.video.file_name or "video.mp4"
            file_info["file_size"] = message.video.file_size
            file_info["mime_type"] = message.video.mime_type
        elif message.audio:
            file_info["file_id"] = message.audio.file_id
            file_info["file_name"] = message.audio.file_name or "audio.mp3"
            file_info["file_size"] = message.audio.file_size
            file_info["mime_type"] = message.audio.mime_type
        else:
            return  # Not a file we care about

        # Additional info
        file_info["caption"] = message.caption or ""
        file_info["chat_id"] = chat_id
        file_info["message_id"] = message.message_id
        file_info["date"] = message.date

        # Insert into DB
        file_id = await self.db.add_file(file_info)
        logger.info(f"Indexed file {file_info['file_name']} with ID {file_id}")

        # Log to log channel if set
        if Config.LOG_CHANNEL:
            log_text = (
                f"📥 New file indexed\n"
                f"Name: {file_info['file_name']}\n"
                f"Size: {file_info['file_size']} bytes\n"
                f"In channel: {chat_id}"
            )
            try:
                await context.bot.send_message(chat_id=Config.LOG_CHANNEL, text=log_text)
            except Exception as e:
                logger.error(f"Failed to send log: {e}")

    async def search(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        # Only search in groups and private if PM search is enabled
        chat_type = update.effective_chat.type
        if chat_type == "private":
            settings = await self.db.get_settings()
            if not settings.get("pm_search_enabled", True):
                return
        elif chat_type not in ["group", "supergroup"]:
            return

        query_text = update.effective_message.text.strip()
        if not query_text:
            return

        # Check if user is banned
        user_id = update.effective_user.id
        if await self.db.is_user_banned(user_id):
            await update.message.reply_text("❌ You are banned from using this bot.")
            return

        # Search in files collection
        # We'll do a regex search on file_name (case-insensitive) and also fuzzy match
        # First, try exact regex
        regex_query = {"file_name": {"$regex": re.escape(query_text), "$options": "i"}}
        files = await self.db.search_files(regex_query, limit=20)

        # If we don't have enough results, do fuzzy matching
        if len(files) < 5:
            # Get more files to fuzzy match against (limit to avoid too many)
            all_files = await self.db.search_files({}, limit=100)
            # Compute similarity
            scored_files = []
            for f in all_files:
                similarity = SequenceMatcher(None, query_text.lower(), f.get("file_name", "").lower()).ratio()
                if similarity > 0.4:  # Threshold
                    scored_files.append((similarity, f))
            # Sort by similarity descending
            scored_files.sort(key=lambda x: x[0], reverse=True)
            # Take top ones not already in files
            existing_ids = {str(f.get("_id")) for f in files}
            for similarity, f in scored_files:
                if str(f.get("_id")) not in existing_ids and len(files) < 20:
                    files.append(f)
                    existing_ids.add(str(f.get("_id")))

        if not files:
            await update.message.reply_text("❌ No files found matching your query.")
            return

        # Build results message
        result_text = f"🔍 Found {len(files)} results for '{query_text}':\n\n"
        keyboard = []
        for i, file_obj in enumerate(files[:10]):  # Limit to 10 results
            file_name = file_obj.get("file_name", "Unknown")
            # Truncate long names
            if len(file_name) > 50:
                file_name = file_name[:47] + "..."
            result_text += f"{i+1}. {file_name}\n"
            # Buttons for each file
            keyboard.append([
                InlineKeyboardButton("📺 Stream", callback_data=f"file_{file_obj.get('_id')}_stream"),
                InlineKeyboardButton("💾 Download", callback_data=f"file_{file_obj.get('_id')}_download")
            ])
            keyboard.append([
                InlineKeyboardButton("✏️ Rename", callback_data=f"file_{file_obj.get('_id')}_rename"),
                InlineKeyboardButton("📝 Caption", callback_data=f"file_{file_obj.get('_id')}_caption")
            ])
            keyboard.append([
                InlineKeyboardButton("🖼️ Thumbnail", callback_data=f"file_{file_obj.get('_id')}_thumbnail"),
                InlineKeyboardButton("🎬 Metadata", callback_data=f"file_{file_obj.get('_id')}_metadata")
            ])

        # Add a button for more results if we have more than 10
        if len(files) > 10:
            keyboard.append([InlineKeyboardButton("More Results", callback_data=f"more_{query_text}")])

        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(result_text, reply_markup=reply_markup, disable_web_page_preview=True)

    # Admin commands
    async def stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        if user_id not in Config.ADMIN_IDS:
            await update.message.reply_text("❌ Admins only.")
            return
        # Placeholder stats
        total_files = await self.db.files.count_documents({})
        total_users = await self.db.users.count_documents({})
        total_chats = await self.db.chats.count_documents({})
        await update.message.reply_text(
            f"📊 *Bot Statistics*\n"
            f"📁 Files indexed: {total_files}\n"
            f"👥 Users: {total_users}\n"
            f"💬 Chats: {total_chats}\n",
            parse_mode='Markdown'
        )

    async def logs(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        if user_id not in Config.ADMIN_IDS:
            await update.message.reply_text("❌ Admins only.")
            return
        # Get recent logs from DB
        logs = await self.db.logs.find({}).sort("_id", -1).limit(10).to_list(length=None)
        if not logs:
            await update.message.reply_text("No logs found.")
            return
        log_text = "📜 *Recent Logs*\n\n"
        for log in logs:
            log_text += f"• {log.get('message', 'No message')}\n"
        await update.message.reply_text(log_text, parse_mode='Markdown')

    async def broadcast(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        if user_id not in Config.ADMIN_IDS:
            await update.message.reply_text("❌ Admins only.")
            return
        # Check if there's text to broadcast
        if not update.message.reply_to_message:
            await update.message.reply_text("Please reply to a message to broadcast it.")
            return
        # Forward the message to all users
        users = await self.db.users.find({}).to_list(length=None)
        sent = 0
        for user in users:
            try:
                await update.message.reply_to_message.forward(chat_id=user["_id"])
                sent += 1
            except Exception as e:
                logger.error(f"Failed to broadcast to {user['_id']}: {e}")
        await update.message.reply_text(f"📢 Broadcast sent to {sent} users.")

    async def users(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        if user_id not in Config.ADMIN_IDS:
            await update.message.reply_text("❌ Admins only.")
            return
        users = await self.db.users.find({}).limit(20).to_list(length=None)
        if not users:
            await update.message.reply_text("No users found.")
            return
        user_list = "\n".join([f"• {u.get('_id')} ({(u.get('username') or 'No username')})" for u in users])
        await update.message.reply_text(f"👥 *Users* (first 20):\n{user_list}", parse_mode='Markdown')

    async def chats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        if user_id not in Config.ADMIN_IDS:
            await update.message.reply_text("❌ Admins only.")
            return
        chats = await self.db.chats.find({}).limit(20).to_list(length=None)
        if not chats:
            await update.message.reply_text("No chats found.")
            return
        chat_list = "\n".join([f"• {c.get('_id')} - {c.get('title', 'No title')}" for c in chats])
        await update.message.reply_text(f"💬 *Chats* (first 20):\n{chat_list}", parse_mode='Markdown')

    async def bans(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        if user_id not in Config.ADMIN_IDS:
            await update.message.reply_text("❌ Admins only.")
            return
        banned = await self.db.users.find({"is_banned": True}).to_list(length=None)
        if not banned:
            await update.message.reply_text("No banned users.")
            return
        ban_list = "\n".join([f"• {u.get('_id')} - {u.get('ban_reason', 'No reason')}" for u in banned])
        await update.message.reply_text(f"🚫 *Banned Users*:\n{ban_list}", parse_mode='Markdown')

    async def filters(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        if user_id not in Config.ADMIN_IDS:
            await update.message.reply_text("❌ Admins only.")
            return
        # This is for chat-specific filters, but we need to know which chat? 
        # We'll ask the user to specify a chat ID, or we can list all? For simplicity, we'll list global filters and note that chat-specific are per chat.
        # Actually, let's change: /filters <chat_id> to list filters for that chat.
        # But the problem says: admins need commands for filters, global filters.
        # We'll do: /filters lists global filters? No, we have /globalfilters for that.
        # Let's make /filters without argument list all chat-specific filters (maybe grouped by chat) - too heavy.
        # Instead, we'll make it so that /filters in a chat lists the filters for that chat (if admin).
        chat_id = update.effective_chat.id
        if chat_type := update.effective_chat.type:
            if chat_type not in ["group", "supergroup"]:
                await update.message.reply_text("Please use this command in a group to see its filters.")
                return
        filters_list = await self.db.get_filters(chat_id=chat_id)
        if not filters_list:
            await update.message.reply_text("No filters set for this chat.")
            return
        filter_list = "\n".join([f"• `{f.get('trigger')}` -> file ID: {f.get('file_id')}" for f in filters_list])
        await update.message.reply_text(f"🔎 *Filters for this chat*:\n{filter_list}", parse_mode='Markdown')

    async def global_filters(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        if user_id not in Config.ADMIN_IDS:
            await update.message.reply_text("❌ Admins only.")
            return
        gfilters = await self.db.get_global_filters()
        if not gfilters:
            await update.message.reply_text("No global filters set.")
            return
        gfilter_list = "\n".join([f"• `{g.get('trigger')}` -> file ID: {g.get('file_id')}" for g in gfilters])
        await update.message.reply_text(f"🌐 *Global Filters*:\n{gfilter_list}", parse_mode='Markdown')

    async def delete_file(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        if user_id not in Config.ADMIN_IDS:
            await update.message.reply_text("❌ Admins only.")
            return
        if not context.args:
            await update.message.reply_text("Usage: /deletefile <query>")
            return
        query_text = " ".join(context.args)
        # Delete files matching the query (by file_name regex)
        result = await self.db.files.delete_many({"file_name": {"$regex": re.escape(query_text), "$options": "i"}})
        await update.message.reply_text(f"🗑️ Deleted {result.deleted_count} files matching '{query_text}'.")

    async def premium(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        if user_id not in Config.ADMIN_IDS:
            await update.message.reply_text("❌ Admins only.")
            return
        # Placeholder for premium management
        await update.message.reply_text("💎 Premium management panel (not fully implemented).")

    async def restart(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        if user_id not in Config.ADMIN_IDS:
            await update.message.reply_text("❌ Admins only.")
            return
        await update.message.reply_text("🔄 Restarting bot...")
        # In a real deployment, we'd use a process manager to restart. Here we just exit.
        # But we can't exit from within the handler because it would stop the current update.
        # Instead, we'll send a signal to the process to restart via external means.
        # For simplicity, we'll just say we're restarting and let the user handle it.
        await update.message.reply_text("Please restart the bot manually (e.g., via your process manager).")

# We need to handle text input for awaiting states (rename, caption, etc.)
# We'll add a message handler for that in main.py, but we can also handle it here.
# Let's add a method to handle these inputs.
    async def handle_awaiting_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        text = update.effective_message.text.strip()

        # Check for awaiting rename
        if 'awaiting_rename' in context.user_data:
            file_id = context.user_data.pop('awaiting_rename')
            # Update the file's name in DB? Actually, we might want to store a custom name separately.
            # For simplicity, we'll just note it and maybe update the file_name field.
            # But note: the original file_name is from Telegram. We'll store a custom_name field.
            await self.db.files.update_one(
                {"_id": file_id},
                {"$set": {"custom_name": text}}
            )
            await update.message.reply_text(f"✅ File name updated to: {text}")
            return

        # Check for awaiting caption
        if 'awaiting_caption' in context.user_data:
            file_id = context.user_data.pop('awaiting_caption')
            await self.db.files.update_one(
                {"_id": file_id},
                {"$set": {"custom_caption": text}}
            )
            await update.message.reply_text(f"✅ Caption updated.")
            return

        # Check for awaiting thumbnail (we expect a photo, not text)
        # So we'll handle thumbnail in a separate message handler for photos.

        # Check for awaiting metadata fields
        for field in ['season', 'episode', 'quality', 'year', 'language']:
            key = f'awaiting_meta_{field}'
            if key in context.user_data:
                file_id = context.user_data.pop(key)
                # Store in a metadata field
                await self.db.files.update_one(
                    {"_id": file_id},
                    {"$set": {f"metadata.{field}": text}}
                )
                await update.message.reply_text(f"✅ {field.capitalize()} set to: {text}")
                return