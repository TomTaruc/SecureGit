import os
import tempfile
os.environ["TESTING"] = "1"
os.environ["GIT_REPOS_BASE"] = tempfile.gettempdir()
import pytest
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
    os.environ["GIT_REPOS_BASE"] = tempfile.gettempdir()

    app = create_app()
    app.config.update({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "JWT_ACCESS_TOKEN_EXPIRES": False,
        "RATELIMIT_ENABLED": False,
        "CELERY_TASK_ALWAYS_EAGER": True,
        "CELERY_TASK_EAGER_PROPAGATES": True,
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
    import subprocess
    temp_dir = tempfile.mkdtemp()
    subprocess.run(["git", "init", "--bare", temp_dir], check=True, capture_output=True)
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

@pytest.fixture(autouse=True)
def disable_async_post_receive(monkeypatch):
    def fake_delay(*args, **kwargs):
        pass

    # Patch at the task level and the service level just in case
    monkeypatch.setattr("app.tasks.async_post_receive_task.delay", fake_delay, raising=False)

@pytest.fixture(autouse=True)
def mock_webhook_network(monkeypatch):
    def fake_post(url, *args, **kwargs):
        import requests
        class DummyResponse:
            status_code = 200
            text = "ok"

        if "nonexistent" in url or "dns" in url:
            raise requests.exceptions.ConnectionError("Name or service not known")
        if "timeout" in url:
            raise requests.exceptions.ConnectTimeout("Timeout")
        if "refused" in url:
            raise requests.exceptions.ConnectionError("Connection refused")
        return DummyResponse()

    monkeypatch.setattr("app.services.webhook_service.requests.post", fake_post, raising=False)
