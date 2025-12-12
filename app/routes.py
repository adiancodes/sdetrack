from pathlib import Path

from flask import Blueprint, current_app, render_template

from .services.tracker_service import (
    build_dashboard_snapshot,
    build_contest_dashboard,
    ensure_category_seeded,
    ensure_contests_seeded,
    get_all_questions,
    get_contest_entries,
    group_questions_by_day,
)

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def index():
    collection = current_app.tracker_collection
    category = "striver"
    questions = get_all_questions(collection, category=category)
    grouped_questions = group_questions_by_day(questions)

    user_one_field = "user_one"
    user_two_field = "user_two"

    dashboard = build_dashboard_snapshot(
        collection=collection,
        user_one_field=user_one_field,
        user_two_field=user_two_field,
        category=category,
    )

    return render_template(
        "index.html",
        grouped_questions=grouped_questions,
        dashboard=dashboard,
        user_one_name=current_app.config["USER_ONE_NAME"],
        user_two_name=current_app.config["USER_TWO_NAME"],
        category=category,
        active_page="striver",
    )


@main_bp.route("/binary-search")
def binary_search():
    collection = current_app.tracker_collection
    category = "binary_search"

    data_path = Path(current_app.root_path) / "static" / "data" / "binary_search_questions.json"
    ensure_category_seeded(collection, category, data_path)

    questions = get_all_questions(collection, category=category)
    grouped_questions = group_questions_by_day(questions)

    dashboard = build_dashboard_snapshot(
        collection=collection,
        user_one_field="user_one",
        user_two_field="user_two",
        category=category,
    )

    return render_template(
        "binary_search.html",
        grouped_questions=grouped_questions,
        dashboard=dashboard,
        user_one_name=current_app.config["USER_ONE_NAME"],
        user_two_name=current_app.config["USER_TWO_NAME"],
        category=category,
        active_page="binary_search",
    )


@main_bp.route("/contest-tracker")
def contest_tracker():
    collection = current_app.tracker_collection
    category = "contest_tracker"

    data_path = Path(current_app.root_path) / "static" / "data" / "contest_tracker.json"
    ensure_contests_seeded(collection, data_path)

    entries = get_contest_entries(collection)
    dashboard = build_contest_dashboard(collection)

    return render_template(
        "contest_tracker.html",
        contests=entries,
        dashboard=dashboard,
        user_one_name=current_app.config["USER_ONE_NAME"],
        user_two_name=current_app.config["USER_TWO_NAME"],
        category=category,
        active_page="contest_tracker",
    )
