from flask import current_app, request
from flask_socketio import SocketIO, emit, join_room

from .services.tracker_service import (
    build_dashboard_snapshot,
    toggle_question_status,
)


VALID_USER_FIELDS = {"user_one", "user_two"}


def register_socketio_events(socketio: SocketIO) -> None:
    """Attach Socket.IO event handlers for real-time updates."""

    def _resolve_category(raw_category):
        if not raw_category:
            return "striver"
        normalized = str(raw_category).lower()
        if normalized in {"striver", "binary_search"}:
            return normalized
        return "striver"

    def _build_dashboard_payload(category: str):
        collection = current_app.tracker_collection
        dashboard = build_dashboard_snapshot(
            collection,
            "user_one",
            "user_two",
            category=category,
        )
        return {
            "dashboard": dashboard,
            "user_one_name": current_app.config["USER_ONE_NAME"],
            "user_two_name": current_app.config["USER_TWO_NAME"],
            "category": category,
        }

    @socketio.on("connect")  # type: ignore[misc]
    def handle_connect():
        category = _resolve_category(request.args.get("category"))
        join_room(category)
        emit("dashboard_sync", _build_dashboard_payload(category))

    @socketio.on("request_dashboard")  # type: ignore[misc]
    def handle_dashboard_request(payload=None):
        payload = payload or {}
        category = _resolve_category(payload.get("category"))
        join_room(category)
        emit("dashboard_sync", _build_dashboard_payload(category), to=request.sid)

    @socketio.on("toggle_status")  # type: ignore[misc]
    def handle_toggle(payload):
        payload = payload or {}
        question_id = payload.get("question_id")
        user_field = payload.get("user_field")
        completed = bool(payload.get("completed", False))

        if not question_id or user_field not in VALID_USER_FIELDS:
            return

        collection = current_app.tracker_collection
        updated_question = toggle_question_status(collection, question_id, user_field, completed)
        if not updated_question:
            return

        category = _resolve_category(updated_question.get("category"))

        socketio.emit(
            "status_updated",
            {
                "question": updated_question,
                "user_field": user_field,
                "category": category,
            },
            room=category,
        )
        socketio.emit(
            "dashboard_sync",
            _build_dashboard_payload(category),
            room=category,
        )
