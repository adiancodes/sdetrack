from flask import Blueprint, current_app, render_template

from .services.tracker_service import (
    build_dashboard_snapshot,
    get_all_questions,
    group_questions_by_day,
)

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def index():
    collection = current_app.tracker_collection
    questions = get_all_questions(collection)
    grouped_questions = group_questions_by_day(questions)

    user_one_field = "user_one"
    user_two_field = "user_two"

    dashboard = build_dashboard_snapshot(
        collection=collection,
        user_one_field=user_one_field,
        user_two_field=user_two_field,
    )

    return render_template(
        "index.html",
        grouped_questions=grouped_questions,
        dashboard=dashboard,
        user_one_name=current_app.config["USER_ONE_NAME"],
        user_two_name=current_app.config["USER_TWO_NAME"],
    )
