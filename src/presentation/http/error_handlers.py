from __future__ import annotations

from flask import Flask, jsonify


def register_error_handlers(app: Flask) -> None:
    @app.errorhandler(404)
    def not_found(_: Exception):
        return jsonify({"error": "Not Found"}), 404

    @app.errorhandler(405)
    def method_not_allowed(_: Exception):
        return jsonify({"error": "Method Not Allowed"}), 405

    @app.errorhandler(500)
    def internal_error(_: Exception):
        return jsonify({"error": "Internal Server Error"}), 500

