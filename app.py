from datetime import datetime
import json
from pathlib import Path

from flask import Flask, jsonify, request


app = Flask(__name__)

# Store courses.json in the same folder as app.py
DATA_FILE = Path(__file__).parent / "courses.json"

VALID_STATUSES = [
    "Not Started",
    "In Progress",
    "Completed",
]

REQUIRED_FIELDS = [
    "name",
    "description",
    "target_date",
    "status",
]


def ensure_data_file():
    """Create courses.json if it does not exist."""
    if not DATA_FILE.exists():
        DATA_FILE.write_text("[]", encoding="utf-8")


def load_courses():
    """Read courses from courses.json."""
    ensure_data_file()

    try:
        with DATA_FILE.open("r", encoding="utf-8") as file:
            courses = json.load(file)

        if not isinstance(courses, list):
            raise ValueError("courses.json must contain a JSON list.")

        return courses

    except json.JSONDecodeError as error:
        raise ValueError("courses.json contains invalid JSON.") from error

    except OSError as error:
        raise OSError("Unable to read courses.json.") from error


def save_courses(courses):
    """Save courses to courses.json."""
    try:
        with DATA_FILE.open("w", encoding="utf-8") as file:
            json.dump(courses, file, indent=2)

    except OSError as error:
        raise OSError("Unable to save courses.json.") from error


def get_next_id(courses):
    """Return the next available numeric course ID."""
    if not courses:
        return 1

    return max(course.get("id", 0) for course in courses) + 1


def validate_course_data(data):
    """
    Validate the data sent by the client.

    Returns an error message if the data is invalid.
    Returns None when the data is valid.
    """
    if not isinstance(data, dict):
        return "Request body must be a JSON object."

    missing_fields = [
        field for field in REQUIRED_FIELDS
        if field not in data
    ]

    if missing_fields:
        return (
            "Missing required field(s): "
            + ", ".join(missing_fields)
        )

    for field in REQUIRED_FIELDS:
        if not isinstance(data[field], str) or not data[field].strip():
            return f"{field} must be a non-empty string."

    if data["status"] not in VALID_STATUSES:
        return (
            "Invalid status. Status must be one of: "
            + ", ".join(VALID_STATUSES)
        )

    try:
        datetime.strptime(data["target_date"], "%Y-%m-%d")
    except ValueError:
        return "target_date must use YYYY-MM-DD format."

    return None


def find_course(courses, course_id):
    """Find a course by ID."""
    return next(
        (course for course in courses if course.get("id") == course_id),
        None,
    )


@app.route("/", methods=["GET"])
def home():
    """Display basic API information."""
    return jsonify({
        "name": "CodeCraftHub",
        "message": "Course tracking REST API",
        "available_endpoints": {
            "create": "POST /api/courses",
            "list": "GET /api/courses",
            "stats": "GET /api/courses/stats",
            "get_one": "GET /api/courses/<id>",
            "update": "PUT /api/courses/<id>",
            "delete": "DELETE /api/courses/<id>",
        },
    }), 200


@app.route("/api/courses", methods=["POST"])
@app.route("/api/courses/", methods=["POST"])
def create_course():
    """Create a new course."""
    data = request.get_json(silent=True)
    validation_error = validate_course_data(data)

    if validation_error:
        return jsonify({"error": validation_error}), 400

    try:
        courses = load_courses()

        new_course = {
            "id": get_next_id(courses),
            "name": data["name"].strip(),
            "description": data["description"].strip(),
            "target_date": data["target_date"].strip(),
            "status": data["status"].strip(),
            "created_at": datetime.utcnow().isoformat() + "Z",
        }

        courses.append(new_course)
        save_courses(courses)

        return jsonify(new_course), 201

    except (ValueError, OSError) as error:
        return jsonify({"error": str(error)}), 500


@app.route("/api/courses", methods=["GET"])
@app.route("/api/courses/", methods=["GET"])
def get_courses():
    """Return all courses."""
    try:
        courses = load_courses()
        return jsonify(courses), 200

    except (ValueError, OSError) as error:
        return jsonify({"error": str(error)}), 500


@app.route("/api/courses/stats", methods=["GET"])
@app.route("/api/courses/stats/", methods=["GET"])
def get_course_stats():
    """
    Return statistics about courses.

    Example response:
    {
        "total_courses": 3,
        "courses_by_status": {
            "Not Started": 1,
            "In Progress": 1,
            "Completed": 1
        }
    }
    """
    try:
        courses = load_courses()

        courses_by_status = {
            "Not Started": 0,
            "In Progress": 0,
            "Completed": 0,
        }

        for course in courses:
            status = course.get("status")

            if status in courses_by_status:
                courses_by_status[status] += 1

        statistics = {
            "total_courses": len(courses),
            "courses_by_status": courses_by_status,
        }

        return jsonify(statistics), 200

    except (ValueError, OSError) as error:
        return jsonify({"error": str(error)}), 500


@app.route("/api/courses/<int:course_id>", methods=["GET"])
@app.route("/api/courses/<int:course_id>/", methods=["GET"])
def get_course(course_id):
    """Return one course by ID."""
    try:
        courses = load_courses()
        course = find_course(courses, course_id)

        if course is None:
            return jsonify({
                "error": f"Course with id {course_id} was not found."
            }), 404

        return jsonify(course), 200

    except (ValueError, OSError) as error:
        return jsonify({"error": str(error)}), 500


@app.route("/api/courses/<int:course_id>", methods=["PUT"])
@app.route("/api/courses/<int:course_id>/", methods=["PUT"])
def update_course(course_id):
    """Replace an existing course."""
    data = request.get_json(silent=True)
    validation_error = validate_course_data(data)

    if validation_error:
        return jsonify({"error": validation_error}), 400

    try:
        courses = load_courses()
        course = find_course(courses, course_id)

        if course is None:
            return jsonify({
                "error": f"Course with id {course_id} was not found."
            }), 404

        course["name"] = data["name"].strip()
        course["description"] = data["description"].strip()
        course["target_date"] = data["target_date"].strip()
        course["status"] = data["status"].strip()

        save_courses(courses)

        return jsonify(course), 200

    except (ValueError, OSError) as error:
        return jsonify({"error": str(error)}), 500


@app.route("/api/courses/<int:course_id>", methods=["DELETE"])
@app.route("/api/courses/<int:course_id>/", methods=["DELETE"])
def delete_course(course_id):
    """Delete a course by ID."""
    try:
        courses = load_courses()
        course = find_course(courses, course_id)

        if course is None:
            return jsonify({
                "error": f"Course with id {course_id} was not found."
            }), 404

        courses.remove(course)
        save_courses(courses)

        return jsonify({
            "message": f"Course with id {course_id} was deleted."
        }), 200

    except (ValueError, OSError) as error:
        return jsonify({"error": str(error)}), 500


@app.errorhandler(404)
def handle_404(error):
    """Return JSON for unknown routes."""
    return jsonify({
        "error": "The requested endpoint was not found."
    }), 404


@app.errorhandler(405)
def handle_405(error):
    """Return JSON for unsupported HTTP methods."""
    return jsonify({
        "error": "The HTTP method is not allowed for this endpoint."
    }), 405


if __name__ == "__main__":
    ensure_data_file()
    app.run(debug=True)