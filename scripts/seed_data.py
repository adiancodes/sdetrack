"""Populate MongoDB with Striver SDE Sheet questions.

Usage:
    python scripts/seed_data.py --file app/static/data/striver_sde_sheet.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from dotenv import load_dotenv
from pymongo import MongoClient

# Ensure project root is on sys.path when running as a script (python scripts/seed_data.py)
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.config import get_settings


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Seed MongoDB with question data")
    parser.add_argument(
        "--file",
        type=Path,
        default=Path("app/static/data/striver_sde_sheet.json"),
        help="Path to the JSON file that contains the question list.",
    )
    parser.add_argument(
        "--preserve-status",
        action="store_true",
        help="Update metadata without resetting completion status.",
    )
    return parser.parse_args()


def load_questions(file_path: Path) -> list[dict]:
    if not file_path.exists():
        raise FileNotFoundError(f"Question file not found: {file_path}")
    with file_path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, list):
        raise ValueError("Expected a list of questions in the JSON file.")
    return data


def build_document(raw: dict, index: int, preserve_status: bool) -> dict:
    status = raw.get("status") if preserve_status else None
    return {
        "category": raw.get("category", "striver"),
        "day": raw.get("day", 0),
        "day_label": raw.get("day_label") or f"Day {raw.get('day', 0)}",
        "order": raw.get("order", index + 1),
        "title": raw.get("title"),
        "difficulty": raw.get("difficulty", "Medium"),
        "practice_link": raw.get("practice_link"),
        "editorial_link": raw.get("editorial_link"),
        "notes": raw.get("notes"),
        "status": status or {"user_one": False, "user_two": False},
    }


def main() -> None:
    # Load .env path relative to project root explicitly to avoid picking example or defaults
    env_path = PROJECT_ROOT / '.env'
    if env_path.exists():
        load_dotenv(env_path, override=True)
    else:
        load_dotenv(override=True)
    settings = get_settings()

    args = parse_args()
    questions = load_questions(args.file)

    mongo_client = MongoClient(settings.mongo_uri)
    collection = mongo_client[settings.mongo_db][settings.mongo_collection]

    # Build documents
    documents = [build_document(question, idx, args.preserve_status) for idx, question in enumerate(questions)]

    if not args.preserve_status:
        collection.delete_many({})
    for doc in documents:
        query = {"category": doc["category"], "day": doc["day"], "title": doc["title"]}
        collection.update_one(query, {"$set": doc}, upsert=True)

    print(f"Upserted {len(documents)} questions into {settings.mongo_collection} collection.")


if __name__ == "__main__":
    main()
