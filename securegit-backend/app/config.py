import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()


class BaseConfig:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-in-production")
    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "jwt-secret-change-in-production")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=15)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=7)
    JWT_TOKEN_LOCATION = ["cookies", "headers"]
    JWT_COOKIE_SECURE = True
    JWT_COOKIE_SAMESITE = "Lax"
    JWT_COOKIE_CSRF_PROTECT = True

    BCRYPT_LOG_ROUNDS = 12
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    GIT_REPOS_BASE = os.environ.get("GIT_REPOS_BASE", "/srv/git")
    GIT_USER = os.environ.get("GIT_USER", "git")
    AUTHORIZED_KEYS_PATH = os.environ.get(
        "AUTHORIZED_KEYS_PATH", "/home/git/.ssh/authorized_keys"
    )
    INTERNAL_DOMAIN = os.environ.get("INTERNAL_DOMAIN", "securegit.local")
    INTERNAL_HOOK_SECRET = os.environ.get("INTERNAL_HOOK_SECRET", "hook-secret-change")
    BACKUP_DEST_PATH = os.environ.get("BACKUP_DEST_PATH", "/mnt/backup")

    RATELIMIT_DEFAULT = "5000 per hour"
    RATELIMIT_STORAGE_URI = "memory://"


class DevelopmentConfig(BaseConfig):
    DEBUG = True
    TESTING = False
    # Use SQLite for local dev if DATABASE_URL not set
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        "sqlite:///securegit_dev.db"
    )
    JWT_COOKIE_SECURE = False   # allow HTTP in dev
    JWT_COOKIE_CSRF_PROTECT = False


class ProductionConfig(BaseConfig):
    DEBUG = False
    TESTING = False
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        "postgresql://securegit_app:CHANGEME@localhost:5432/securegit_db"
    )
    RATELIMIT_STORAGE_URI = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
    JWT_COOKIE_SECURE = os.environ.get("SECURE_COOKIES", "false").lower() == "true"
    JWT_COOKIE_SAMESITE = "Lax"
    JWT_COOKIE_CSRF_PROTECT = False  # CORS origin restrictions provide equivalent CSRF protection behind nginx proxy


class TestingConfig(BaseConfig):
    TESTING = True
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    JWT_COOKIE_SECURE = False
    JWT_COOKIE_CSRF_PROTECT = False
    BCRYPT_LOG_ROUNDS = 4   # Faster in tests
    WTF_CSRF_ENABLED = False


config = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
    "default": DevelopmentConfig,
}
