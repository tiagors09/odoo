import logging
from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class LessonsAPI(http.Controller):
    """API Controller to manage lessons (CRUD operations)."""

    @http.route("/lessons/list", type="json", auth="public", methods=["POST"], csrf=False)
    def list_lessons(self, **kw):
        """Retrieve a list of all available lessons.
        
        Returns:
            dict: Status, response code, and list of lessons.
        """
        try:
            lessons = request.env["lesson.odoo"].sudo().search([])
            lessons_list = []

            for lesson in lessons:
                lessons_list.append({
                    "id": lesson.id,
                    "name": lesson.name,
                    "desc": lesson.desc,
                    "duration": lesson.duration,
                })
            
            return {
                "status": "success", 
                "code": "LESSONS_FETCHED",
                "lessons": lessons_list
            }
        except Exception as e:
            _logger.error("Error listing lessons: %s", str(e))
            return {
                "status": "error", 
                "code": "INTERNAL_SERVER_ERROR",
                "message": str(e)
            }

    @http.route("/lessons/create", type="json", auth="public", methods=["POST"], csrf=False)
    def create_lesson(self, **kw):
        """Create a new lesson record.
        
        Expected JSON params:
            - name (str): Required lesson name.
            - desc (str): Optional lesson description.
            - duration (str): Optional duration ('one_minute', 'five_minutes', 'ten_minutes').
            
        Returns:
            dict: Status, response code, and created lesson details.
        """
        try:
            params = request.params or kw
            
            name = params.get("name")
            desc = params.get("desc")
            duration = params.get("duration", "ten_minutes")

            if not name:
                return {
                    "status": "error", 
                    "code": "MISSING_REQUIRED_FIELD",
                    "field": "name"
                }

            new_lesson = request.env["lesson.odoo"].sudo().create({
                "name": name,
                "desc": desc,
                "duration": duration,
            })

            _logger.info("Lesson created successfully with ID: %s", new_lesson.id)

            return {
                "status": "success",
                "code": "LESSON_CREATED",
                "lesson": {
                    "id": new_lesson.id,
                    "name": new_lesson.name,
                    "desc": new_lesson.desc,
                    "duration": new_lesson.duration,
                }
            }
        except Exception as e:
            _logger.error("Error creating lesson: %s", str(e))
            return {
                "status": "error", 
                "code": "DATABASE_ERROR",
                "message": str(e)
            }

    @http.route("/lessons/update", type="json", auth="public", methods=["POST"], csrf=False)
    def update_lesson(self, **kw):
        """Update an existing lesson record.
        
        Expected JSON params:
            - id (int): Required lesson ID to identify the record.
            - name (str): New name (optional).
            - desc (str): New description (optional).
            - duration (str): New duration (optional).
            
        Returns:
            dict: Status, response code, and updated lesson details.
        """
        try:
            params = request.params or kw
            lesson_id = params.get("id")

            if not lesson_id:
                return {
                    "status": "error",
                    "code": "MISSING_REQUIRED_FIELD",
                    "field": "id"
                }

            lesson = request.env["lesson.odoo"].sudo().browse(lesson_id)
            if not lesson.exists():
                return {
                    "status": "error",
                    "code": "LESSON_NOT_FOUND",
                    "message": f"Lesson with ID {lesson_id} does not exist."
                }

            values_to_update = {}
            if "name" in params:
                values_to_update["name"] = params.get("name")
            if "desc" in params:
                values_to_update["desc"] = params.get("desc")
            if "duration" in params:
                values_to_update["duration"] = params.get("duration")

            if values_to_update:
                lesson.write(values_to_update)
                _logger.info("Lesson updated successfully with ID: %s", lesson.id)

            return {
                "status": "success",
                "code": "LESSON_UPDATED",
                "lesson": {
                    "id": lesson.id,
                    "name": lesson.name,
                    "desc": lesson.desc,
                    "duration": lesson.duration,
                }
            }
        except Exception as e:
            _logger.error("Error updating lesson: %s", str(e))
            return {
                "status": "error",
                "code": "DATABASE_ERROR",
                "message": str(e)
            }

    @http.route("/lessons/delete", type="json", auth="public", methods=["POST"], csrf=False)
    def delete_lesson(self, **kw):
        """Delete an existing lesson record.
        
        Expected JSON params:
            - id (int): Required lesson ID to identify the record.
            
        Returns:
            dict: Status and response code confirming deletion.
        """
        try:
            params = request.params or kw
            lesson_id = params.get("id")

            if not lesson_id:
                return {
                    "status": "error",
                    "code": "MISSING_REQUIRED_FIELD",
                    "field": "id"
                }

            lesson = request.env["lesson.odoo"].sudo().browse(lesson_id)
            if not lesson.exists():
                return {
                    "status": "error",
                    "code": "LESSON_NOT_FOUND",
                    "message": f"Lesson with ID {lesson_id} does not exist."
                }

            lesson.unlink()
            _logger.info("Lesson deleted successfully with ID: %s", lesson_id)

            return {
                "status": "success",
                "code": "LESSON_DELETED",
                "id": lesson_id
            }
        except Exception as e:
            _logger.error("Error deleting lesson: %s", str(e))
            return {
                "status": "error",
                "code": "DATABASE_ERROR",
                "message": str(e)
            }
