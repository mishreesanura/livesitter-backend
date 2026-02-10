"""
Overlay Routes
RESTful API endpoints for overlay CRUD operations

Endpoints:
    POST   /overlays      - Create a new overlay
    GET    /overlays      - Retrieve all overlays
    GET    /overlays/:id  - Retrieve a specific overlay
    PUT    /overlays/:id  - Update an overlay (full update)
    PATCH  /overlays/:id  - Partial update an overlay
    DELETE /overlays/:id  - Remove an overlay
"""

from flask import Blueprint, request, jsonify
from models.overlay import Overlay
from config.database import db_config

# Blueprint with /overlays prefix (accessible at both /overlays and /api/overlays)
overlay_bp = Blueprint("overlay", __name__)


def register_overlay_routes(app):
    """Register overlay routes with both /overlays and /api/overlays prefixes"""
    app.register_blueprint(overlay_bp, url_prefix="/overlays")
    app.register_blueprint(overlay_bp, url_prefix="/api/overlays", name="overlay_api")


def get_overlay_model():
    """Get the Overlay model instance with current database connection"""
    db = db_config.get_db()
    return Overlay(db)


@overlay_bp.route("", methods=["GET"])
def get_all_overlays():
    """
    GET /api/overlays
    Retrieve all overlay documents.
    Optional query param: rtsp_url
    """
    try:
        overlay_model = get_overlay_model()

        rtsp_url = request.args.get("rtsp_url")
        query = {}
        if rtsp_url:
            query["rtsp_url"] = rtsp_url

        overlays = overlay_model.find_all(query)
        return jsonify({"success": True, "data": overlays, "count": len(overlays)}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@overlay_bp.route("/batch", methods=["POST"])
def save_overlays_batch():
    """
    POST /api/overlays/batch
    Save a batch of overlays for a specific RTSP URL.
    Replaces all existing overlays for that URL.

    Request Body:
    {
        "rtsp_url": "string",
        "overlays": [ ... list of overlay objects ... ]
    }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "error": "No data provided"}), 400

        rtsp_url = data.get("rtsp_url")
        overlays = data.get("overlays", [])

        if not rtsp_url:
            return jsonify({"success": False, "error": "rtsp_url is required"}), 400

        overlay_model = get_overlay_model()

        # 1. Delete existing overlays for this URL
        overlay_model.delete_by_rtsp_url(rtsp_url)

        # 2. Add rtsp_url to all overlays and insert
        if overlays:
            for overlay in overlays:
                overlay["rtsp_url"] = rtsp_url

            count = overlay_model.insert_many(overlays)
        else:
            count = 0

        return (
            jsonify(
                {
                    "success": True,
                    "message": f"Saved {count} overlays for {rtsp_url}",
                    "count": count,
                }
            ),
            200,
        )

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@overlay_bp.route("/<overlay_id>", methods=["GET"])
def get_overlay(overlay_id):
    """
    GET /api/overlays/:id
    Retrieve a specific overlay by ID
    """
    try:
        overlay_model = get_overlay_model()
        overlay = overlay_model.find_by_id(overlay_id)

        if overlay:
            return jsonify({"success": True, "data": overlay}), 200
        else:
            return jsonify({"success": False, "error": "Overlay not found"}), 404
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@overlay_bp.route("", methods=["POST"])
def create_overlay():
    """
    POST /api/overlays
    Create a new overlay

    Request Body:
    {
        "content": "string (text or image URL)",
        "type": "text" | "image",
        "position": { "x": number, "y": number },
        "size": { "width": number, "height": number }
    }
    """
    try:
        data = request.get_json()

        if not data:
            return jsonify({"success": False, "error": "No data provided"}), 400

        overlay_model = get_overlay_model()
        overlay = overlay_model.create(data)

        return (
            jsonify(
                {
                    "success": True,
                    "data": overlay,
                    "message": "Overlay created successfully",
                }
            ),
            201,
        )
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@overlay_bp.route("/<overlay_id>", methods=["PUT"])
def update_overlay(overlay_id):
    """
    PUT /api/overlays/:id
    Update an existing overlay

    Request Body (all fields optional):
    {
        "content": "string (text or image URL)",
        "type": "text" | "image",
        "position": { "x": number, "y": number },
        "size": { "width": number, "height": number }
    }
    """
    try:
        data = request.get_json()

        if not data:
            return jsonify({"success": False, "error": "No data provided"}), 400

        overlay_model = get_overlay_model()
        overlay = overlay_model.update(overlay_id, data)

        if overlay:
            return (
                jsonify(
                    {
                        "success": True,
                        "data": overlay,
                        "message": "Overlay updated successfully",
                    }
                ),
                200,
            )
        else:
            return jsonify({"success": False, "error": "Overlay not found"}), 404
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@overlay_bp.route("/<overlay_id>", methods=["PATCH"])
def patch_overlay(overlay_id):
    """
    PATCH /overlays/:id
    Partial update an existing overlay (position, size, or content)

    Request Body (all fields optional):
    {
        "content": "string (text or image URL)",
        "type": "text" | "image",
        "position": { "x": number, "y": number },
        "size": { "width": number, "height": number }
    }
    """
    try:
        data = request.get_json()

        if not data:
            return jsonify({"success": False, "error": "No data provided"}), 400

        overlay_model = get_overlay_model()
        overlay = overlay_model.update(overlay_id, data)

        if overlay:
            return (
                jsonify(
                    {
                        "success": True,
                        "data": overlay,
                        "message": "Overlay patched successfully",
                    }
                ),
                200,
            )
        else:
            return jsonify({"success": False, "error": "Overlay not found"}), 404
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@overlay_bp.route("/<overlay_id>", methods=["DELETE"])
def delete_overlay(overlay_id):
    """
    DELETE /overlays/:id
    Delete an overlay by ID
    """
    try:
        overlay_model = get_overlay_model()
        deleted = overlay_model.delete(overlay_id)

        if deleted:
            return (
                jsonify({"success": True, "message": "Overlay deleted successfully"}),
                200,
            )
        else:
            return jsonify({"success": False, "error": "Overlay not found"}), 404
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
