import os
os.environ["TESTING"] = "1"
import pytest
import tempfile
import shutil
from flask_jwt_extended import create_access_token
from app import create_app
from app.extensions import db, bcrypt
import fakeredis

@pytest.fixture(autouse=True)
def mock_redis(monkeypatch):
    fake_redis = fakeredis.FakeRedis()
    monkeypatch.setattr("app.extensions.redis_client", fake_redis)

@pytest.fixture(scope="session")
def app():
    """Create and configure a new app instance for the entire test session."""
    os.environ["FLASK_ENV"] = "testing"
    os.environ["SECRET_KEY"] = "test-secret"
    os.environ["JWT_SECRET_KEY"] = "test-jwt-secret"
    os.environ["INTERNAL_HOOK_SECRET"] = "test-hook-secret"
    os.environ["DATABASE_URL"] = "sqlite:///:memory:"

    app = create_app()
    app.config.update({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "JWT_ACCESS_TOKEN_EXPIRES": False,
        "RATELIMIT_ENABLED": False,
    })

    with app.app_context():
        yield app

@pytest.fixture
def client(app):
    """A test client for the app."""
    return app.test_client()

@pytest.fixture
def runner(app):
    """A test runner for the app's click commands."""
    return app.test_cli_runner()

@pytest.fixture
def db_session(app):
    """Provides an isolated database session for each test."""
    with app.app_context():
        db.create_all()
        yield db.session
        db.session.remove()
        db.drop_all()

@pytest.fixture
def admin_user(db_session):
    from app.models.user import User
    pw_hash = bcrypt.generate_password_hash("password").decode("utf-8")
    user = User(
        username="admin_user",
        email="admin@example.com",
        password_hash=pw_hash,
        role="admin"
    )
    db_session.add(user)
    db_session.commit()
    return user

@pytest.fixture
def normal_user(db_session):
    from app.models.user import User
    pw_hash = bcrypt.generate_password_hash("password").decode("utf-8")
    user = User(
        username="test_user",
        email="test@example.com",
        password_hash=pw_hash,
        role="user"
    )
    db_session.add(user)
    db_session.commit()
    return user

@pytest.fixture
def another_user(db_session):
    from app.models.user import User
    pw_hash = bcrypt.generate_password_hash("password").decode("utf-8")
    user = User(
        username="another_user",
        email="another@example.com",
        password_hash=pw_hash,
        role="user"
    )
    db_session.add(user)
    db_session.commit()
    return user

@pytest.fixture
def auth_headers(app, normal_user):
    with app.app_context():
        token = create_access_token(identity=str(normal_user.user_id))
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture
def admin_headers(app, admin_user):
    with app.app_context():
        token = create_access_token(identity=str(admin_user.user_id))
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture
def mock_repo_dir():
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)

@pytest.fixture
def project(db_session, normal_user, mock_repo_dir):
    from app.models.project import Project
    from app.models.repository import Repository
    p = Project(owner_user_id=normal_user.user_id, project_name="test-repo")
    db_session.add(p)
    db_session.flush()
    r = Repository(project_id=p.project_id, repo_path=mock_repo_dir, clone_url="ssh://git@localhost/test-repo.git")
    db_session.add(r)
    db_session.commit()
    return p
