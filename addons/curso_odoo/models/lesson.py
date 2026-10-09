from odoo import fields, models


class Lesson(models.Model):
    _name = "lesson.odoo"
    _description = "Lesson"

    name = fields.Char(string="Lesson Name", required=True)
    description = fields.Char(string="Lesson Description")
    duration = fields.Selection(
        [
            ("one_minute", "1 min"),
            ("five_minutes", "5 min"),
            ("ten_minutes", "10 min"),
        ],
        required=True,
        default="ten_minutes",
        string="Duration",
    )
