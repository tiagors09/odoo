from odoo import models, fields

class AulasOdoo(models.Model):
    _name: str = 'aula.odoo'
    _description: str = 'modelo aula'

    nome_aula: Any = fields.Char()
