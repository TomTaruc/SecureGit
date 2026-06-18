from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager
from flask_bcrypt import Bcrypt
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_talisman import Talisman

import logging
import os

logger = logging.getLogger(__name__)

db = SQLAlchemy()
migrate = Migrate()
jwt = JWTManager()
bcrypt = Bcrypt()
cors = CORS()
limiter = Limiter(key_func=get_remote_address)
talisman = Talisman()


def _create_redis_client():
    """Create Redis client with graceful fallback if Redis is unavailable."""
    if os.environ.get("TESTING") == "1":
        try:
            import fakeredis
            return fakeredis.FakeRedis(decode_responses=True)
        except ImportError:
            logger.warning("fakeredis not installed; using stub Redis client for testing")
            return _StubRedis()

    import redis as _redis
    try:
        client = _redis.from_url(
            os.environ.get("REDIS_URL", "redis://localhost:6379/0")
        )
        client.ping()
        return client
    except Exception as e:
        logger.warning(
            "Redis unavailable (%s); JWT blocklist and caching disabled. "
            "Install and start Redis for full functionality.", e
        )
        return _StubRedis()


class _StubRedis:
    """No-op Redis stub so the app can start without a Redis server."""

    def get(self, *a, **kw):
        return None

    def set(self, *a, **kw):
        return True

    def setex(self, *a, **kw):
        return True

    def delete(self, *a, **kw):
        return 0

    def ping(self):
        return True


redis_client = _create_redis_client()
