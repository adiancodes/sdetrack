from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional

from bson import ObjectId


DEFAULT_CATEGORY = "striver"
CONTEST_CATEGORY = "contest_tracker"
DEFAULT_CONTEST_PROBLEMS = 4


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


def ensure_contests_seeded(collection, data_path: Path) -> None:
    """Ensure contest tracker entries match the JSON seed file."""
    path = Path(data_path)
    if not path.exists():
        raise FileNotFoundError(f"Contest seed file not found: {path}")

    with path.open("r", encoding="utf-8") as handle:
        records = json.load(handle)

    if not isinstance(records, list):
        raise ValueError("Contest seed file must be a list of contest entries.")

    valid_titles = set()
    for index, raw in enumerate(records):
        title = raw.get("title")
        if not title:
            continue
        max_problems = int(raw.get("max_problems", DEFAULT_CONTEST_PROBLEMS) or DEFAULT_CONTEST_PROBLEMS)
        max_problems = max(max_problems, 0)
        status_raw = raw.get("status") or {}
        status_defaults = {
            "user_one": int(status_raw.get("user_one", 0) or 0),
            "user_two": int(status_raw.get("user_two", 0) or 0),
        }
        for key, value in status_defaults.items():
            status_defaults[key] = max(0, min(value, max_problems))

        query = {
            "category": CONTEST_CATEGORY,
            "title": title,
        }
        document = {
            "category": CONTEST_CATEGORY,
            "order": raw.get("order", index + 1),
            "title": title,
            "contest_link": raw.get("contest_link"),
            "max_problems": max_problems,
        }

        collection.update_one(
            query,
            {
                "$set": document,
                "$setOnInsert": {"status": status_defaults},
            },
            upsert=True,
        )
        valid_titles.add(title)

    if valid_titles:
        collection.delete_many({"category": CONTEST_CATEGORY, "title": {"$nin": list(valid_titles)}})


def get_contest_entries(collection) -> List[Dict]:
    """Return contest tracker entries ordered by their configured rank."""
    cursor = collection.find({"category": CONTEST_CATEGORY}, sort=[("order", 1), ("title", 1)])
    entries: List[Dict] = []
    for doc in cursor:
        doc_id = doc.pop("_id", None)
        if doc_id is not None:
            doc["id"] = str(doc_id)
        status = doc.setdefault("status", {"user_one": 0, "user_two": 0})
        max_problems = int(doc.get("max_problems", DEFAULT_CONTEST_PROBLEMS) or DEFAULT_CONTEST_PROBLEMS)
        max_problems = max(max_problems, 0)
        doc["max_problems"] = max_problems
        for key in ("user_one", "user_two"):
            value = int(status.get(key, 0) or 0)
            status[key] = max(0, min(value, max_problems))
        doc["category"] = CONTEST_CATEGORY
        entries.append(doc)
    return entries


def build_contest_dashboard(collection) -> Dict:
    """Aggregate contest progress for both users in dashboard format."""
    entries = get_contest_entries(collection)
    user_one_total = 0
    user_one_completed = 0
    user_two_total = 0
    user_two_completed = 0

    for entry in entries:
        max_problems = entry.get("max_problems", DEFAULT_CONTEST_PROBLEMS) or DEFAULT_CONTEST_PROBLEMS
        user_one_total += max_problems
        user_two_total += max_problems
        status = entry.get("status", {})
        user_one_completed += int(status.get("user_one", 0) or 0)
        user_two_completed += int(status.get("user_two", 0) or 0)

    return {
        "user_one": {
            "total": user_one_total,
            "completed": user_one_completed,
            "difficulty": {},
        },
        "user_two": {
            "total": user_two_total,
            "completed": user_two_completed,
            "difficulty": {},
        },
        "metadata": {
            "contest_count": len(entries),
        },
    }


def update_contest_solved(collection, contest_id: str, user_field: str, solved: int) -> Dict:
    """Persist solved count for a contest entry and return the updated document."""
    if user_field not in {"user_one", "user_two"}:
        return {}

    obj_id = ObjectId(contest_id)
    existing = collection.find_one({"_id": obj_id, "category": CONTEST_CATEGORY})
    if not existing:
        return {}

    max_problems = int(existing.get("max_problems", DEFAULT_CONTEST_PROBLEMS) or DEFAULT_CONTEST_PROBLEMS)
    max_problems = max(max_problems, 0)
    value = int(solved or 0)
    value = max(0, min(value, max_problems))

    collection.update_one({"_id": obj_id}, {"$set": {f"status.{user_field}": value}})
    updated = collection.find_one({"_id": obj_id})
    if not updated:
        return {}

    updated["id"] = str(updated.pop("_id"))
    status = updated.setdefault("status", {"user_one": 0, "user_two": 0})
    status[user_field] = value
    updated.setdefault("max_problems", max_problems)
    updated["category"] = CONTEST_CATEGORY
    return updated
