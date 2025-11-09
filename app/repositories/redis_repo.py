import json
from typing import List, Dict, Any
import redis.asyncio as redis

class ChatHistory:
    def __init__(self, client: redis.Redis, ttl_seconds: int = 3600 * 24 * 7): # 7-day TTL
        self.client = client
        self.ttl = ttl_seconds

    async def get_messages(self, conversation_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Gets the last N messages from a conversation."""
        key = f"chat:{conversation_id}"
        try:
            raw_messages = await self.client.lrange(key, 0, -1)
            messages = [json.loads(m) for m in raw_messages]
            return messages[-limit:]
        except (redis.RedisError, IndexError):
            return []

    async def add_message(self, conversation_id: str, role: str, content: str):
        """Adds a new message to the conversation history."""
        key = f"chat:{conversation_id}"
        message = {"role": role, "content": content}
        await self.client.rpush(key, json.dumps(message))
        await self.client.expire(key, self.ttl)