# database.py
import motor.motor_asyncio
from config import Config
import logging

logger = logging.getLogger(__name__)

class Database:
    def __init__(self, mongo_uri, db_name):
        self.client = motor.motor_asyncio.AsyncIOMotorClient(mongo_uri)
        self.db = self.client[db_name]
        # Collections
        self.files = self.db.files
        self.settings = self.db.settings
        self.users = self.db.users
        self.chats = self.db.chats
        self.bans = self.db.bans
        self.logs = self.db.logs
        self.premium = self.db.premium
        self.referrals = self.db.referrals
        self.filters = self.db.filters
        self.global_filters = self.db.global_filters

    async def connect(self):
        # Test connection
        try:
            await self.client.admin.command('ping')
            logger.info("Connected to MongoDB")
        except Exception as e:
            logger.error(f"Could not connect to MongoDB: {e}")
            raise

    # File indexing methods
    async def add_file(self, file_info):
        # file_info should be a dict with: file_id, file_name, file_size, mime_type, caption, etc.
        result = await self.files.insert_one(file_info)
        return result.inserted_id

    async def get_file(self, query):
        return await self.files.find_one(query)

    async def search_files(self, query, limit=10):
        cursor = self.files.find(query).limit(limit)
        return await cursor.to_list(length=limit)

    async def delete_file(self, query):
        result = await self.files.delete_one(query)
        return result.deleted_count

    # Settings methods
    async def get_settings(self):
        settings = await self.settings.find_one({"_id": "global"})
        if not settings:
            # Insert default settings
            default_settings = {
                "_id": "global",
                "features": Config.FEATURES.copy(),
                "force_subscribe_channels": [],
                "request_to_join_chats": [],
                "url_shortener_service": None,
                "token_verification_enabled": False,
                "pm_search_enabled": True,
                "auto_delete_pm": False,
                "stream_links": True,
                "download_links": True,
                "premium_plans": {},
                "referrals": {}
            }
            await self.settings.insert_one(default_settings)
            return default_settings
        return settings

    async def update_settings(self, update_dict):
        await self.settings.update_one({"_id": "global"}, {"$set": update_dict}, upsert=True)

    # User methods
    async def add_user(self, user_id, user_data):
        await self.users.update_one(
            {"_id": user_id},
            {"$setOnInsert": {"_id": user_id, "joined_at": user_data.get("joined_at")},
             "$set": {"last_seen": user_data.get("last_seen"), "is_banned": False}},
            upsert=True
        )

    async def is_user_banned(self, user_id):
        user = await self.users.find_one({"_id": user_id})
        return user.get("is_banned", False) if user else False

    async def ban_user(self, user_id, reason=None):
        await self.users.update_one(
            {"_id": user_id},
            {"$set": {"is_banned": True, "ban_reason": reason, "banned_at": logger}},
            upsert=True
        )

    # Chat methods
    async def add_chat(self, chat_id, chat_data):
        await self.chats.update_one(
            {"_id": chat_id},
            {"$setOnInsert": {"_id": chat_id, "type": chat_data.get("type"), "title": chat_data.get("title")},
             "$set": {"last_active": chat_data.get("last_active")}},
            upsert=True
        )

    # Log methods
    async def add_log(self, log_entry):
        await self.logs.insert_one(log_entry)

    # Premium methods
    async def is_premium(self, user_id):
        premium = await self.premium.find_one({"user_id": user_id})
        return premium is not None

    async def add_premium(self, user_id, plan_id, expires_at):
        await self.premium.update_one(
            {"user_id": user_id},
            {"$set": {"plan_id": plan_id, "expires_at": expires_at, "activated_at": logger}},
            upsert=True
        )

    # Referral methods
    async def add_referral(self, referrer_id, referred_id):
        await self.referrals.update_one(
            {"referrer_id": referrer_id},
            {"$push": {"referred_ids": referred_id}, "$setOnInsert": {"referrer_id": referrer_id, "referred_ids": []}},
            upsert=True
        )

    # Filter methods
    async def add_filter(self, trigger, file_id, chat_id=None):
        filter_doc = {"trigger": trigger.lower(), "file_id": file_id}
        if chat_id is not None:
            filter_doc["chat_id"] = chat_id
        await self.filters.insert_one(filter_doc)

    async def get_filters(self, chat_id=None):
        query = {}
        if chat_id is not None:
            query["chat_id"] = chat_id
        cursor = self.filters.find(query)
        return await cursor.to_list(length=None)

    async def delete_filter(self, trigger, chat_id=None):
        query = {"trigger": trigger.lower()}
        if chat_id is not None:
            query["chat_id"] = chat_id
        result = await self.filters.delete_one(query)
        return result.deleted_count

    # Global filter methods
    async def add_global_filter(self, trigger, file_id):
        await self.global_filters.insert_one({"trigger": trigger.lower(), "file_id": file_id})

    async def get_global_filters(self):
        cursor = self.global_filters.find({})
        return await cursor.to_list(length=None)

    async def delete_global_filter(self, trigger):
        result = await self.global_filters.delete_one({"trigger": trigger.lower()})
        return result.deleted_count