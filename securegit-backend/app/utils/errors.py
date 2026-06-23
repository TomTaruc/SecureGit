from flask import jsonify

def api_error(code: str, message: str, status: int = 400, details: dict | None = None):
    """Centralized API error helper."""
    response = {
        "error": code,
        "message": message,
        "status": status
    }
    if details:
        response["details"] = details
    return jsonify(response), status
