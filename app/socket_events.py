from flask import current_app
from flask_socketio import SocketIO, emit

from .services.tracker_service import (
    build_dashboard_snapshot,
    toggle_question_status,
)


VALID_USER_FIELDS = {"user_one", "user_two"}


def register_socketio_events(socketio: SocketIO) -> None:
    """Attach Socket.IO event handlers for real-time updates."""

    def _build_dashboard_payload():
        collection = current_app.tracker_collection
        dashboard = build_dashboard_snapshot(collection, "user_one", "user_two")
        return {
            "dashboard": dashboard,
            "user_one_name": current_app.config["USER_ONE_NAME"],
            "user_two_name": current_app.config["USER_TWO_NAME"],
        }

    @socketio.on("connect")  # type: ignore[misc]
    def handle_connect():
        emit("dashboard_sync", _build_dashboard_payload())

    @socketio.on("request_dashboard")  # type: ignore[misc]
    def handle_dashboard_request():
        emit("dashboard_sync", _build_dashboard_payload())

    @socketio.on("toggle_status")  # type: ignore[misc]
    def handle_toggle(payload):
        question_id = payload.get("question_id")
        user_field = payload.get("user_field")
        completed = bool(payload.get("completed", False))

        if not question_id or user_field not in VALID_USER_FIELDS:
            return

        collection = current_app.tracker_collection
        updated_question = toggle_question_status(collection, question_id, user_field, completed)
        if not updated_question:
            return

        socketio.emit(
            "status_updated",
            {
                "question": updated_question,
                "user_field": user_field,
            },
            broadcast=True,
        )
        socketio.emit(
            "dashboard_sync",
            _build_dashboard_payload(),
            broadcast=True,
        )
