import asyncio
from typing import List, Dict, Any

from pymongo import MongoClient, DESCENDING

from config import MONGO_URI

mongo_client = None
db = None
documents_collection = None
messages_collection = None
metrics_collection = None


async def initialize_database():
    global mongo_client, db, documents_collection, messages_collection, metrics_collection

    try:
        mongo_client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=10000)
        mongo_client.admin.command('ismaster')
        db = mongo_client['ai_assistant_telegram_db']

        documents_collection = db['documents']
        messages_collection = db['messages']
        metrics_collection = db['rag_metrics']

        messages_collection.create_index([("user_id", 1), ("timestamp", DESCENDING)])
        documents_collection.create_index([("upload_time", DESCENDING)])
        metrics_collection.create_index([("message_id", 1)], unique=True)
        metrics_collection.create_index([("user_id", 1), ("created_at", DESCENDING)])

        return True
    except Exception as e:
        print(f"Error initializing MongoDB: {e}")
        return False


async def close_database():
    if mongo_client:
        try:
            mongo_client.close()
        except Exception as e:
            print(f"Error closing MongoDB connection: {e}")


async def list_knowledge_base_documents() -> List[Dict[str, Any]]:
    if documents_collection is None:
        return []
    try:
        cursor = documents_collection.find({'status': 'active'},
            {'filename': 1, 'upload_time': 1, 'chunk_count': 1}).sort("upload_time", DESCENDING)

        docs = await asyncio.to_thread(list, cursor)

        for doc in docs:
            doc['_id'] = str(doc['_id'])
            doc['upload_time_str'] = doc['upload_time'].strftime('%Y-%m-%d %H:%M:%S UTC')
        return docs
    except Exception as e:
        print(f"Error listing documents from MongoDB: {e}")
        return []


async def clear_user_history(user_id: int) -> tuple[bool, str]:
    if messages_collection is None:
        return False, "Database connection not available."
    try:
        delete_result = await asyncio.to_thread(messages_collection.delete_many, {"user_id": user_id})

        deleted_count = delete_result.deleted_count
        return True, f"История сообщений ({deleted_count} сообщений) была очищена."
    except Exception as e:
        print(f"Error clearing history for user_id {user_id}: {e}")
        return False, "An error occurred while clearing your history."


async def get_chat_history_with_metrics() -> List[Dict[str, Any]]:
    if messages_collection is None or metrics_collection is None:
        print("MongoDB collections not initialized")
        return []

    try:
        messages_cursor = messages_collection.find().sort([("user_id", 1), ("timestamp", 1)])
        messages = await asyncio.to_thread(list, messages_cursor)

        metrics_cursor = metrics_collection.find()
        metrics = await asyncio.to_thread(list, metrics_cursor)

        metrics_dict = {m["message_id"]: m["metrics"] for m in metrics}

        chats = {}
        for msg in messages:
            user_id = msg["user_id"]
            if user_id not in chats:
                chats[user_id] = {"user_id": user_id, "messages": [], "total_messages": 0,
                    "first_message_time": msg["timestamp"], "last_message_time": msg["timestamp"]}

            if msg["role"] == "assistant":
                msg["metrics"] = metrics_dict.get(msg["_id"], {})

            chats[user_id]["messages"].append(msg)
            chats[user_id]["total_messages"] += 1
            chats[user_id]["last_message_time"] = msg["timestamp"]

        result = list(chats.values())
        result.sort(key=lambda x: x["last_message_time"], reverse=True)

        return result

    except Exception as e:
        print(f"Error getting chat history with metrics: {e}")
        return []
