from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional

from bson import ObjectId


DEFAULT_CATEGORY = "striver"


def _normalize_category(category: Optional[str]) -> str:
    return (category or DEFAULT_CATEGORY).lower()


def _build_category_filter(category: Optional[str], include_missing_default: bool = True) -> Dict:
    normalized = _normalize_category(category)
    if normalized == DEFAULT_CATEGORY:
        if include_missing_default:
            return {"$or": [{"category": DEFAULT_CATEGORY}, {"category": {"$exists": False}}]}
        return {"category": DEFAULT_CATEGORY}
    return {"category": normalized}


def get_all_questions(collection, category: Optional[str] = None) -> List[Dict]:
    """Fetch questions for a category ordered by section/pattern and declared order."""
    cursor = collection.find(
        _build_category_filter(category), sort=[("day", 1), ("order", 1), ("title", 1)]
    )
    questions = []
    for doc in cursor:
        doc["id"] = str(doc.pop("_id"))
        doc.setdefault("status", {"user_one": False, "user_two": False})
        if "category" not in doc:
            doc["category"] = DEFAULT_CATEGORY
        questions.append(doc)
    return questions


def group_questions_by_day(questions: List[Dict]) -> List[Dict]:
    grouped: Dict[int, Dict] = {}
    for question in questions:
        day_number = question.get("day", 0)
        day_label = question.get("day_label", f"Day {day_number}")
        if day_number not in grouped:
            grouped[day_number] = {
                "day": day_number,
                "label": day_label,
                "questions": [],
            }
        grouped[day_number]["questions"].append(question)
    ordered_days = sorted(grouped.values(), key=lambda d: d["day"])
    for entry in ordered_days:
        entry["questions"].sort(key=lambda q: q.get("order", 0))
    return ordered_days


def compute_progress_snapshot(collection, user_field: str, category: Optional[str] = None) -> Dict:
    """Return totals and per-difficulty stats for a given user field."""
    base_filter = _build_category_filter(category)
    completed_filter = dict(base_filter)
    completed_filter[f"status.{user_field}"] = True

    total_questions = collection.count_documents(base_filter)
    completed_total = collection.count_documents(completed_filter)

    pipeline = []
    if base_filter:
        pipeline.append({"$match": base_filter})
    pipeline.append(
        {
            "$group": {
                "_id": "$difficulty",
                "total": {"$sum": 1},
                "completed": {
                    "$sum": {
                        "$cond": [
                            {"$ifNull": [f"$status.{user_field}", False]},
                            1,
                            0,
                        ]
                    }
                },
            }
        }
    )
    difficulty_results = {
        "Easy": {"total": 0, "completed": 0},
        "Medium": {"total": 0, "completed": 0},
        "Hard": {"total": 0, "completed": 0},
    }
    for row in collection.aggregate(pipeline):
        difficulty = row.get("_id", "Unknown")
        difficulty_results.setdefault(difficulty, {"total": 0, "completed": 0})
        difficulty_results[difficulty]["total"] = row.get("total", 0)
        difficulty_results[difficulty]["completed"] = row.get("completed", 0)

    return {
        "total": total_questions,
        "completed": completed_total,
        "difficulty": difficulty_results,
    }


def build_dashboard_snapshot(
    collection,
    user_one_field: str,
    user_two_field: str,
    category: Optional[str] = None,
) -> Dict:
    """Produce a combined dashboard view for both users."""
    user_one_stats = compute_progress_snapshot(collection, user_one_field, category=category)
    user_two_stats = compute_progress_snapshot(collection, user_two_field, category=category)
    return {
        "user_one": user_one_stats,
        "user_two": user_two_stats,
    }


def toggle_question_status(collection, question_id: str, user_field: str, completed: bool) -> Dict:
    """Flip the completion flag for a single question and return the updated doc."""
    obj_id = ObjectId(question_id)
    collection.update_one({"_id": obj_id}, {"$set": {f"status.{user_field}": completed}})
    updated = collection.find_one({"_id": obj_id})
    if not updated:
        return {}
    updated["id"] = str(updated.pop("_id"))
    if "category" not in updated:
        updated["category"] = DEFAULT_CATEGORY
    return updated


def ensure_category_seeded(collection, category: str, data_path: Path) -> None:
    """Seed a category from a JSON file if it does not already exist in the collection."""
    normalized = _normalize_category(category)
    existing = collection.count_documents(_build_category_filter(normalized, include_missing_default=False))
    if existing:
        return

    path = Path(data_path)
    if not path.exists():
        raise FileNotFoundError(f"Seed file not found for category '{normalized}': {path}")

    with path.open("r", encoding="utf-8") as handle:
        records = json.load(handle)

    if not isinstance(records, list):
        raise ValueError(f"Seed file for category '{normalized}' must contain a list of questions.")

    for index, raw in enumerate(records):
        companies_raw = raw.get("companies") or []
        if isinstance(companies_raw, str):
            companies_processed = [item.strip() for item in companies_raw.split(",") if item.strip()]
        else:
            companies_processed = list(companies_raw)

        document = {
            "category": normalized,
            "day": raw.get("day", 0),
            "day_label": raw.get("day_label") or f"Pattern {raw.get('day', 0)}",
            "order": raw.get("order", index + 1),
            "title": raw.get("title"),
            "difficulty": raw.get("difficulty", "Medium"),
            "practice_link": raw.get("practice_link"),
            "editorial_link": raw.get("editorial_link"),
            "companies": companies_processed,
            "key_concept": raw.get("key_concept"),
            "notes": raw.get("notes"),
            "status": raw.get("status") or {"user_one": False, "user_two": False},
        }

        query = {
            "category": normalized,
            "day": document["day"],
            "title": document["title"],
        }
        collection.update_one(query, {"$set": document}, upsert=True)
