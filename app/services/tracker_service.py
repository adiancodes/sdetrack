from __future__ import annotations

from collections import defaultdict
from typing import Dict, List, Tuple

from bson import ObjectId


def get_all_questions(collection) -> List[Dict]:
    """Fetch every question from Mongo ordered by day and original index."""
    cursor = collection.find({}, sort=[("day", 1), ("order", 1)])
    questions = []
    for doc in cursor:
        doc["id"] = str(doc.pop("_id"))
        doc.setdefault("status", {"user_one": False, "user_two": False})
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


def compute_progress_snapshot(collection, user_field: str) -> Dict:
    """Return totals and per-difficulty stats for a given user field."""
    total_questions = collection.count_documents({})
    completed_total = collection.count_documents({f"status.{user_field}": True})

    pipeline = [
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
    ]
    difficulty_results = {"Easy": {"total": 0, "completed": 0}, "Medium": {"total": 0, "completed": 0}, "Hard": {"total": 0, "completed": 0}}
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


def build_dashboard_snapshot(collection, user_one_field: str, user_two_field: str) -> Dict:
    """Produce a combined dashboard view for both users."""
    user_one_stats = compute_progress_snapshot(collection, user_one_field)
    user_two_stats = compute_progress_snapshot(collection, user_two_field)
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
    return updated
