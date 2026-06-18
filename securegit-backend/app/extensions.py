from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager
from flask_bcrypt import Bcrypt
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_talisman import Talisman

import redis
import os

db = SQLAlchemy()
migrate = Migrate()
jwt = JWTManager()
bcrypt = Bcrypt()
cors = CORS()
limiter = Limiter(key_func=get_remote_address)
talisman = Talisman()

if os.environ.get("TESTING") == "1":
    import fakeredis
    redis_client = fakeredis.FakeRedis(decode_responses=True)
else:
    redis_client = redis.from_url(os.environ.get("REDIS_URL", "redis://localhost:6379/0"))
