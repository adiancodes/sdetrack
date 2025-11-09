from flask import Flask
from flask_socketio import SocketIO
from pymongo import MongoClient

from .config import get_settings

socketio = SocketIO(async_mode="eventlet", cors_allowed_origins="*")


def create_app() -> Flask:
    """Factory that builds and configures the Flask application."""
    settings = get_settings()

    app = Flask(__name__)
    app.config.update(
        MONGO_URI=settings.mongo_uri,
        MONGO_DB_NAME=settings.mongo_db,
        MONGO_COLLECTION_NAME=settings.mongo_collection,
        USER_ONE_NAME=settings.user_one,
        USER_TWO_NAME=settings.user_two,
    )

    mongo_client = MongoClient(settings.mongo_uri)
    app.mongo_client = mongo_client
    app.tracker_collection = mongo_client[settings.mongo_db][settings.mongo_collection]

    from .routes import main_bp
    from .socket_events import register_socketio_events

    app.register_blueprint(main_bp)
    register_socketio_events(socketio)
    socketio.init_app(app)

    return app
