import os
from flask import Flask, jsonify
from .config import config
from .extensions import db, migrate, jwt, bcrypt, cors, limiter, talisman


def create_app(config_name: str | None = None) -> Flask:
    """Application factory."""
    config_name = config_name or os.environ.get("FLASK_ENV", "development")
    app = Flask(__name__, instance_relative_config=False)
    app.config.from_object(config[config_name])

    from werkzeug.middleware.proxy_fix import ProxyFix
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

    # ---------------------------------------------------------------------------
    # Initialize extensions
    # ---------------------------------------------------------------------------
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    bcrypt.init_app(app)

    cors.init_app(
        app,
        resources={r"/api/*": {"origins": ["https://securegit.local", "http://localhost:5173"]}},
        supports_credentials=True,
    )

    limiter.init_app(app)

    if not app.debug:
        csp = {
            "default-src": "'self'",
            "script-src": "'self'",
            "style-src": ["'self'", "'unsafe-inline'", "https://fonts.googleapis.com"],
            "font-src": ["'self'", "https://fonts.gstatic.com"],
        }
        talisman.init_app(
            app,
            content_security_policy=csp,
            force_https=False,
            strict_transport_security=True,
        )

    # ---------------------------------------------------------------------------
    # Register blueprints
    # ---------------------------------------------------------------------------
    from .routes.auth import auth_bp
    from .routes.users import users_bp
    from .routes.projects import projects_bp
    from .routes.repositories import repos_bp
    from .routes.branches import branches_bp
    from .routes.commits import commits_bp
    from .routes.ssh_keys import ssh_keys_bp
    from .routes.dashboard import dashboard_bp
    from .routes.admin import admin_bp
    from .routes.internal import internal_bp
    from .routes.merge import merge_bp
    from .routes.tokens import tokens_bp
    from .routes.backups import backups_bp
    from .routes.metrics import metrics_bp
    from .routes.webhooks import webhooks_bp

    app.register_blueprint(auth_bp,      url_prefix="/api/auth")
    app.register_blueprint(users_bp,     url_prefix="/api/users")
    app.register_blueprint(projects_bp,  url_prefix="/api/projects")
    app.register_blueprint(repos_bp,     url_prefix="/api/repos")
    app.register_blueprint(branches_bp,  url_prefix="/api/branches")
    app.register_blueprint(commits_bp,   url_prefix="/api/commits")
    app.register_blueprint(ssh_keys_bp,  url_prefix="/api/ssh-keys")
    app.register_blueprint(dashboard_bp, url_prefix="/api/dashboard")
    app.register_blueprint(admin_bp,     url_prefix="/api/admin")
    app.register_blueprint(internal_bp,  url_prefix="/api/internal")
    app.register_blueprint(merge_bp,     url_prefix="/api/merge")
    app.register_blueprint(tokens_bp,    url_prefix="/api/tokens")
    app.register_blueprint(backups_bp,   url_prefix="/api/backups")
    app.register_blueprint(metrics_bp,   url_prefix="/api/admin/metrics")
    app.register_blueprint(webhooks_bp,  url_prefix="/api/webhooks")

    # ---------------------------------------------------------------------------
    # JWT error handlers & blocklist
    # ---------------------------------------------------------------------------
    @jwt.token_in_blocklist_loader
    def check_if_token_is_revoked(jwt_header, jwt_payload):
        from .extensions import redis_client
        jti = jwt_payload["jti"]
        token_in_redis = redis_client.get(jti)
        return token_in_redis is not None

    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        return jsonify({"error": "token_expired", "message": "Token has expired.", "status": 401}), 401

    @jwt.invalid_token_loader
    def invalid_token_callback(error):
        return jsonify({"error": "invalid_token", "message": "Signature verification failed.", "status": 401}), 401

    @jwt.unauthorized_loader
    def missing_token_callback(error):
        return jsonify({"error": "authorization_required", "message": "Request does not contain an access token.", "status": 401}), 401

    # ---------------------------------------------------------------------------
    # Generic error handlers
    # ---------------------------------------------------------------------------
    @app.errorhandler(400)
    def bad_request(e):
        return jsonify({"error": "bad_request", "message": str(e), "status": 400}), 400

    @app.errorhandler(403)
    def forbidden(e):
        return jsonify({"error": "forbidden", "message": "You do not have permission to perform this action.", "status": 403}), 403

    @app.errorhandler(404)
    def not_found(e):
        return jsonify({"error": "not_found", "message": str(e), "status": 404}), 404

    @app.errorhandler(409)
    def conflict(e):
        return jsonify({"error": "conflict", "message": str(e), "status": 409}), 409

    @app.errorhandler(422)
    def unprocessable(e):
        return jsonify({"error": "unprocessable_entity", "message": str(e), "status": 422}), 422

    @app.errorhandler(429)
    def ratelimit_handler(e):
        return jsonify({"error": "rate_limit_exceeded", "message": str(e.description), "status": 429}), 429

    @app.errorhandler(500)
    def internal_error(e):
        return jsonify({"error": "internal_server_error", "message": "An internal error occurred.", "status": 500}), 500

    # ---------------------------------------------------------------------------
    # Health check (unauthenticated)
    # ---------------------------------------------------------------------------
    @app.route("/health")
    def health():
        return jsonify({"status": "ok"}), 200

    return app
