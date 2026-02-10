"""
LiveSitter Backend Application
RTSP Livestream Overlay Web Application - Flask Backend
"""

import os
from flask import Flask, jsonify
from flask_cors import CORS

from config.settings import config
from config.database import db_config
from routes.overlay_routes import overlay_bp, register_overlay_routes
from routes.video_routes import video_bp


def create_app(config_name=None):
    """
    Application Factory Pattern
    Creates and configures the Flask application

    Args:
        config_name: Configuration environment name (development, production, testing)

    Returns:
        Configured Flask application instance
    """
    # Create Flask app
    app = Flask(__name__)

    # Load configuration
    config_name = config_name or os.getenv("FLASK_ENV", "development")
    app.config.from_object(config[config_name])

    # Enable CORS for React frontend
    CORS(
        app,
        origins=app.config.get("CORS_ORIGINS", ["http://localhost:3000"]),
        methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization"],
        supports_credentials=True,
    )

    # Initialize database
    with app.app_context():
        db_config.init_db(app)

    # Register overlay routes (available at both /overlays and /api/overlays)
    register_overlay_routes(app)

    # Register video streaming routes
    app.register_blueprint(video_bp)

    # Health check endpoint
    @app.route("/api/health", methods=["GET"])
    def health_check():
        """Health check endpoint to verify the API is running"""
        return (
            jsonify(
                {
                    "status": "healthy",
                    "message": "LiveSitter API is running",
                    "version": "1.0.0",
                }
            ),
            200,
        )

    # Root endpoint
    @app.route("/", methods=["GET"])
    def root():
        """Root endpoint with API information"""
        return (
            jsonify(
                {
                    "name": "LiveSitter Backend API",
                    "version": "1.0.0",
                    "description": "RTSP Livestream Overlay Web Application API",
                    "endpoints": {
                        "health": "/api/health",
                        "video_feed": "GET /video_feed?rtsp_url=<url>",
                        "overlays": {
                            "list": "GET /overlays",
                            "create": "POST /overlays",
                            "get": "GET /overlays/<id>",
                            "update": "PUT /overlays/<id>",
                            "patch": "PATCH /overlays/<id>",
                            "delete": "DELETE /overlays/<id>",
                        },
                    },
                }
            ),
            200,
        )

    # Error handlers
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({"success": False, "error": "Resource not found"}), 404

    @app.errorhandler(500)
    def internal_error(error):
        return jsonify({"success": False, "error": "Internal server error"}), 500

    return app


# Create the application instance
app = create_app()


if __name__ == "__main__":
    # Run the development server
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
