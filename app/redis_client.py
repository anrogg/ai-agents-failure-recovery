import os
import json
import redis.asyncio as redis
from typing import Optional, Dict, Any
import structlog

logger = structlog.get_logger(__name__)

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

redis_client: Optional[redis.Redis] = None


async def init_redis():
    global redis_client
    try:
        redis_client = redis.from_url(REDIS_URL, decode_responses=True)
        await redis_client.ping()
        logger.info("Redis connection established")
    except Exception as e:
        logger.error("Failed to connect to Redis", error=str(e))
        raise


async def close_redis():
    global redis_client
    if redis_client:
        await redis_client.close()
        logger.info("Redis connection closed")


class StateManager:
    def __init__(self):
        pass
    
    @property
    def redis(self):
        return redis_client
    
    async def save_state(self, session_id: str, state_data: Dict[str, Any], ttl: int = 3600):
        try:
            if not self.redis:
                logger.warning("Redis client not initialized", session_id=session_id)
                return
            key = f"agent_state:{session_id}"
            await self.redis.setex(key, ttl, json.dumps(state_data))
            logger.debug("Agent state saved", session_id=session_id)
        except Exception as e:
            logger.error("Failed to save agent state", session_id=session_id, error=str(e))
            raise
    
    async def load_state(self, session_id: str) -> Optional[Dict[str, Any]]:
        try:
            if not self.redis:
                logger.warning("Redis client not initialized", session_id=session_id)
                return None
            key = f"agent_state:{session_id}"
            state_json = await self.redis.get(key)
            if state_json:
                return json.loads(state_json)
            return None
        except Exception as e:
            logger.error("Failed to load agent state", session_id=session_id, error=str(e))
            return None
    
    async def delete_state(self, session_id: str):
        try:
            if not self.redis:
                logger.warning("Redis client not initialized", session_id=session_id)
                return
            key = f"agent_state:{session_id}"
            await self.redis.delete(key)
            logger.debug("Agent state deleted", session_id=session_id)
        except Exception as e:
            logger.error("Failed to delete agent state", session_id=session_id, error=str(e))
    
    async def create_checkpoint(self, session_id: str, checkpoint_name: str, state_data: Dict[str, Any]):
        try:
            if not self.redis:
                logger.warning("Redis client not initialized", session_id=session_id)
                return
            key = f"checkpoint:{session_id}:{checkpoint_name}"
            await self.redis.setex(key, 7200, json.dumps(state_data))  # 2 hour TTL for checkpoints
            logger.debug("Checkpoint created", session_id=session_id, checkpoint=checkpoint_name)
        except Exception as e:
            logger.error("Failed to create checkpoint", session_id=session_id, checkpoint=checkpoint_name, error=str(e))
    
    async def restore_checkpoint(self, session_id: str, checkpoint_name: str) -> Optional[Dict[str, Any]]:
        try:
            if not self.redis:
                logger.warning("Redis client not initialized", session_id=session_id)
                return None
            key = f"checkpoint:{session_id}:{checkpoint_name}"
            checkpoint_json = await self.redis.get(key)
            if checkpoint_json:
                return json.loads(checkpoint_json)
            return None
        except Exception as e:
            logger.error("Failed to restore checkpoint", session_id=session_id, checkpoint=checkpoint_name, error=str(e))
            return None
    
    async def track_failure_count(self, session_id: str) -> int:
        try:
            if not self.redis:
                logger.warning("Redis client not initialized", session_id=session_id)
                return 0
            key = f"failure_count:{session_id}"
            count = await self.redis.incr(key)
            await self.redis.expire(key, 3600)  # Reset count after 1 hour
            return count
        except Exception as e:
            logger.error("Failed to track failure count", session_id=session_id, error=str(e))
            return 0
    
    async def reset_failure_count(self, session_id: str):
        try:
            if not self.redis:
                logger.warning("Redis client not initialized", session_id=session_id)
                return
            key = f"failure_count:{session_id}"
            await self.redis.delete(key)
            logger.debug("Failure count reset", session_id=session_id)
        except Exception as e:
            logger.error("Failed to reset failure count", session_id=session_id, error=str(e))