from odoo import api, fields, models, _
from odoo.exceptions import AccessError, ValidationError
from contextvars import ContextVar
_CREATING = ContextVar("alvina_creating", default=False)

from .validation import CATEGORIES, pending, quantity

class BranchRequest(models.Model):
    _name = 'alvina.branch.request'
    _description = 'Requerimiento de sucursal'
    _order = 'request_date desc, id desc'
    _check_company_auto = True

    name = fields.Char(default='Nuevo', readonly=True, copy=False)
    user_id = fields.Many2one('res.users', required=True, default=lambda self: self.env.user, readonly=True)
    branch_id = fields.Many2one('alvina.branch.binding', required=True, check_company=True, ondelete='restrict')
    company_id = fields.Many2one(related='branch_id.company_id', store=True)
    request_date = fields.Datetime(default=fields.Datetime.now, required=True, readonly=True)
    required_date = fields.Date(required=True)
    note = fields.Text()
    state = fields.Selection([('pending', 'Pendiente'), ('review', 'En revisión'),
        ('partial', 'Parcialmente atendido'), ('done', 'Atendido'), ('cancel', 'Cancelado')], default='pending', required=True, readonly=True)
    line_ids = fields.One2many('alvina.branch.request.line', 'request_id', copy=False)
    submission_key = fields.Char(required=True, readonly=True, copy=False)
    _submission_unique = models.Constraint('UNIQUE(submission_key)', 'Este formulario ya fue enviado.')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            branch = self.env['alvina.branch.binding'].browse(vals.get('branch_id')).exists()
            if not branch or not branch.active or self.env.user not in branch.user_ids or branch.company_id not in self.env.companies:
                raise AccessError(_('Sucursal no autorizada.'))
            if not branch._resource_is_available():
                raise ValidationError(_('La sucursal vinculada ya no está disponible en esta compañía.'))
            if vals.get('state', 'pending') != 'pending' or vals.get('user_id', self.env.uid) != self.env.uid:
                raise AccessError(_('Datos de solicitud no autorizados.'))
            if not vals.get('line_ids'):
                raise ValidationError(_('Ingrese al menos un producto.'))
            vals.update(user_id=self.env.uid, request_date=fields.Datetime.now(),
                        name=self.env['ir.sequence'].sudo().next_by_code('alvina.branch.request'))
        token = _CREATING.set(True)
        try:
            records = super().create(vals_list)
            if any(not rec.line_ids for rec in records):
                raise ValidationError(_('Ingrese al menos un producto.'))
            return records
        finally:
            _CREATING.reset(token)

    @api.constrains('required_date')
    def _check_date(self):
        for rec in self:
            if rec.required_date < fields.Date.context_today(rec):
                raise ValidationError(_('La fecha requerida no puede ser anterior a hoy.'))

    def write(self, vals):
        raise AccessError(_('Los requerimientos enviados son inmutables; use las acciones autorizadas.'))

    def unlink(self):
        raise AccessError(_('Archive la sucursal o cancele el requerimiento; no elimine su historial.'))

    def _manager(self):
        self.check_access('write')
        if not self.env.user.has_group('alvina_branch_requisition.group_keeper'):
            raise AccessError(_('Acción reservada al almacenero.'))

    def action_review(self):
        self._manager()
        if any(r.state != 'pending' for r in self):
            raise ValidationError(_('Solo puede revisar solicitudes pendientes.'))
        return super().write({'state': 'review'})

    def action_cancel(self):
        self._manager()
        if any(r.state not in ('pending', 'review') or any(r.line_ids.mapped('qty_supplied')) for r in self):
            raise ValidationError(_('No se puede cancelar una solicitud atendida.'))
        return super().write({'state': 'cancel'})

class RequestLine(models.Model):
    _name = 'alvina.branch.request.line'
    _description = 'Detalle de requerimiento'
    _check_company_auto = True

    request_id = fields.Many2one('alvina.branch.request', required=True, ondelete='cascade', check_company=True)
    branch_id = fields.Many2one(related='request_id.branch_id', store=True)
    company_id = fields.Many2one(related='request_id.company_id', store=True)
    product_id = fields.Many2one('product.product', required=True, check_company=True)
    product_uom_id = fields.Many2one('uom.uom', required=True, readonly=True, ondelete='restrict')
    product_qty = fields.Float(required=True, digits='Product Unit')
    qty_supplied = fields.Float(default=0, readonly=True, digits='Product Unit')
    qty_pending = fields.Float(compute='_compute_pending', store=True, digits='Product Unit')
    _product_unique = models.Constraint('UNIQUE(request_id, product_id)', 'No repita productos.')
    _positive = models.Constraint('CHECK(product_qty > 0 AND qty_supplied >= 0 AND qty_supplied <= product_qty)', 'Cantidades inválidas.')

    @api.depends('product_qty', 'qty_supplied')
    def _compute_pending(self):
        for line in self:
            line.qty_pending = pending(line.product_qty, line.qty_supplied)

    @api.model_create_multi
    def create(self, vals_list):
        if not _CREATING.get():
            raise AccessError(_('Agregue líneas únicamente al enviar un requerimiento nuevo.'))
        for vals in vals_list:
            if set(vals) - {'request_id', 'product_id', 'product_qty'}:
                raise AccessError(_('Campos de detalle no autorizados.'))
            product = self.env['product.product'].sudo().browse(vals.get('product_id')).exists()
            if not product:
                raise ValidationError(_('Producto inexistente.'))
            try:
                q = quantity(vals.get('product_qty'), product.uom_id.rounding)
                if not q:
                    raise ValueError('La cantidad debe ser positiva')
            except ValueError as exc:
                raise ValidationError(str(exc)) from exc
            vals['product_uom_id'] = product.uom_id.id
            request = self.env['alvina.branch.request'].browse(vals.get('request_id'))
            if request.user_id != self.env.user or request.state != 'pending':
                raise AccessError(_('Requerimiento no autorizado.'))
        return super().create(vals_list)

    @api.constrains('product_id', 'product_qty', 'request_id')
    def _validate_product(self):
        for line in self:
            p = line.product_id.sudo()
            if not p.active or not p.product_tmpl_id.active or not p.alvina_requisition_enabled or p.categ_id.name not in CATEGORIES:
                raise ValidationError(_('Producto no habilitado o categoría no permitida.'))
            try:
                quantity(line.product_qty, p.uom_id.rounding)
            except ValueError as exc:
                raise ValidationError(str(exc)) from exc

    def write(self, vals):
        raise AccessError(_('El detalle enviado es inmutable.'))

    def unlink(self):
        raise AccessError(_('El detalle enviado es inmutable.'))
