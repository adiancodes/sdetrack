import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    mongo_uri: str
    mongo_db: str
    mongo_collection: str
    user_one: str
    user_two: str


def get_settings() -> Settings:
    """Load configuration from environment variables with sensible defaults."""
    # Ensure .env values override any inherited environment variables
    load_dotenv(override=True)

    return Settings(
        mongo_uri=os.getenv("MONGO_URI", "mongodb://localhost:27017"),
        mongo_db=os.getenv("MONGO_DB_NAME", "sde_tracker"),
        mongo_collection=os.getenv("MONGO_COLLECTION_NAME", "questions"),
        user_one=os.getenv("USER_ONE_NAME", "You"),
        user_two=os.getenv("USER_TWO_NAME", "Friend"),
    )
