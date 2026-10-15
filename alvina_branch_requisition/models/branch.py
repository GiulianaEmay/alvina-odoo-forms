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
        # The supplied Alviña code represents branches as existing contacts.
        # An integration addon may extend this method for another verified model.
        # Never expose every model: a reference name is rendered for requesters.
        return [('res.partner', _('Contacto de sucursal existente'))]

    def _resource_is_available(self):
        """Recheck a configured contact that may have changed since assignment."""
        self.ensure_one()
        target = self.sudo().resource_ref
        allowed_models = {model for model, _label in self._reference_models()}
        return bool(
            target and target._name in allowed_models and target.exists()
            and ('active' not in target._fields or target.active)
            and ('company_id' not in target._fields or not target.company_id
                 or target.company_id == self.company_id)
        )

    @api.depends('resource_ref')
    def _compute_name(self):
        allowed_models = {model for model, _label in self._reference_models()}
        for rec in self:
            target = rec.sudo().resource_ref
            rec.name = target.display_name if target and target._name in allowed_models and target.exists() else _('Sucursal no disponible')

    @api.constrains('resource_ref', 'company_id', 'warehouse_id', 'user_ids')
    def _check_binding(self):
        for rec in self:
            target = rec.resource_ref
            if not target or not target.exists():
                raise ValidationError(_('Seleccione una sucursal existente.'))
            target.check_access('read')
            if 'active' in target._fields and not target.active:
                raise ValidationError(_('La sucursal vinculada está archivada.'))
            if 'company_id' in target._fields and target.company_id and target.company_id != rec.company_id:
                raise ValidationError(_('La sucursal pertenece a otra compañía.'))
            if any(rec.company_id not in user.company_ids for user in rec.user_ids):
                raise ValidationError(_('Los usuarios deben tener acceso a la compañía.'))

    def write(self, vals):
        if set(vals) & {'resource_ref', 'company_id', 'warehouse_id'}:
            if self.env['alvina.branch.request'].sudo().search_count([('branch_id', 'in', self.ids)]):
                raise ValidationError(_('Cambiar una sucursal o almacén con historial requiere una migración controlada.'))
        return super().write(vals)

class ProductTemplate(models.Model):
    _inherit = 'product.template'
    alvina_requisition_enabled = fields.Boolean(string='Habilitado para requerimientos Alviña', default=False, groups='alvina_branch_requisition.group_admin')
