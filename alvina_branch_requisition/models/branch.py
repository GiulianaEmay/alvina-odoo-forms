from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

class BranchBinding(models.Model):
    _name = 'alvina.branch.binding'
    _description = 'Vínculo con sucursal existente (no crea sucursales)'
    _rec_name = 'name'

    name = fields.Char(compute='_compute_name')
    active = fields.Boolean(default=True)
    resource_ref = fields.Reference(selection='_reference_models', required=True, string='Sucursal existente')
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company)
    warehouse_id = fields.Many2one('stock.warehouse', required=True, check_company=True)
    user_ids = fields.Many2many('res.users', string='Usuarios autorizados')
    _check_company_auto = True
    _unique_resource = models.Constraint('UNIQUE(resource_ref)', 'La sucursal ya está vinculada.')

    @api.model
    def _reference_models(self):
        return [(m.model, m.name) for m in self.env['ir.model'].sudo().search([('transient', '=', False)])]

    @api.depends('resource_ref')
    def _compute_name(self):
        for rec in self:
            rec.name = rec.sudo().resource_ref.display_name if rec.sudo().resource_ref and rec.sudo().resource_ref.exists() else _('Sucursal no disponible')

    @api.constrains('resource_ref', 'company_id', 'warehouse_id', 'user_ids')
    def _check_binding(self):
        for rec in self:
            target = rec.resource_ref
            if not target or not target.exists():
                raise ValidationError(_('Seleccione una sucursal existente.'))
            if 'company_id' in target._fields and target.company_id and target.company_id != rec.company_id:
                raise ValidationError(_('La sucursal pertenece a otra compañía.'))
            if any(rec.company_id not in user.company_ids for user in rec.user_ids):
                raise ValidationError(_('Los usuarios deben tener acceso a la compañía.'))

    def write(self, vals):
        if set(vals) & {'resource_ref', 'company_id', 'warehouse_id'}:
            if self.env['alvina.branch.request'].sudo().search_count([('branch_id', 'in', self.ids)]):
                raise ValidationError(_('No cambie vínculos con historial; archive y configure otro vínculo.'))
        return super().write(vals)

class ProductTemplate(models.Model):
    _inherit = 'product.template'
    alvina_requisition_enabled = fields.Boolean(string='Habilitado para requerimientos Alviña', default=False, groups='alvina_branch_requisition.group_admin')
