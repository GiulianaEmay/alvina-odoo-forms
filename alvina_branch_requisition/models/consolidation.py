from odoo import Command, api, fields, models, _
from odoo.exceptions import AccessError, ValidationError
from .validation import suggested

class Consolidation(models.TransientModel):
    _name = 'alvina.branch.consolidation'
    _description = 'Consolidado de insumos'
    line_ids = fields.One2many('alvina.branch.consolidation.line', 'wizard_id',
                               string='Necesidades por producto', readonly=True)

    @api.depends_context('lang')
    def _compute_display_name(self):
        for wizard in self:
            wizard.display_name = _('Consolidado de insumos')

    def action_branch_detail(self):
        self.ensure_one()
        self.check_access('read')
        if not self.env.user.has_group('alvina_branch_requisition.group_keeper'):
            raise AccessError(_('Acción reservada al almacenero.'))
        return {'type': 'ir.actions.act_window', 'name': _('Pendientes por sucursal'),
                'res_model': 'alvina.branch.request.line', 'view_mode': 'list',
                'domain': [('request_id.state', 'in', ['pending', 'review', 'partial']),
                           ('qty_pending', '>', 0)],
                'context': {'group_by': ['company_id', 'branch_id', 'product_id', 'product_uom_id'],
                            'create': False, 'edit': False, 'delete': False}}

    def action_refresh(self):
        self.ensure_one()
        if not self.env.user.has_group('alvina_branch_requisition.group_keeper'):
            raise AccessError(_('Acción reservada al almacenero.'))
        self.check_access('write')
        self.line_ids.unlink()
        lines = self.env['alvina.branch.request.line'].search([
            ('request_id.state', 'in', ['pending', 'review', 'partial']), ('qty_pending', '>', 0)])
        groups = {}
        for line in lines:
            if line.product_uom_id != line.product_id.uom_id:
                raise ValidationError(_('La unidad de un producto cambió después del requerimiento. Revise sus solicitudes antes de consolidar.'))
            if line.supply_company_id not in self.env.companies:
                raise AccessError(_('Active la compañía abastecedora autorizada para consultar su stock.'))
            key = (line.product_id, line.warehouse_id, line.supply_company_id)
            groups.setdefault(key, self.env['alvina.branch.request.line'])
            groups[key] |= line
        for (product, warehouse, company), detail in groups.items():
            # Keep normal stock ACLs and record rules in the supplying company.
            # Ignore caller-provided location/date filters for this live summary.
            stock = product.with_company(company).with_context(
                allowed_company_ids=[company.id], warehouse_id=warehouse.id,
                location=False, search_location=False, search_warehouse=False, lot_id=False, owner_id=False, package_id=False,
                from_date=False, to_date=False)
            demand = sum(detail.mapped('qty_pending'))
            free, incoming = stock.free_qty, stock.incoming_qty
            unit_cost = stock.standard_price
            self.env['alvina.branch.consolidation.line'].create({
                'wizard_id': self.id, 'product_id': product.id, 'warehouse_id': warehouse.id,
                'company_id': company.id, 'product_qty': demand, 'free_qty': free,
                'incoming_qty': incoming, 'suggested_qty': suggested(demand, free, incoming),
                'unit_cost': unit_cost, 'estimated_value': demand * unit_cost,
                'detail_ids': [Command.create({
                    'request_line_id': source.id, 'product_qty': source.qty_pending,
                    'estimated_value': source.qty_pending * unit_cost,
                }) for source in detail],
                'source_line_ids': [(6, 0, detail.ids)]})
        return {'type': 'ir.actions.act_window', 'name': _('Consolidado de insumos'),
                'res_model': self._name, 'res_id': self.id,
                'view_mode': 'form', 'target': 'current'}

class ConsolidationLine(models.TransientModel):
    _name = 'alvina.branch.consolidation.line'
    _description = 'Necesidad por producto y almacén'
    wizard_id = fields.Many2one('alvina.branch.consolidation', string='Consolidado',
                                required=True, ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Producto', readonly=True)
    product_uom_id = fields.Many2one(related='product_id.uom_id', string='Unidad de medida')
    warehouse_id = fields.Many2one('stock.warehouse', string='Almacén abastecedor', readonly=True)
    company_id = fields.Many2one('res.company', string='Compañía abastecedora', readonly=True)
    product_qty = fields.Float(string='Pendiente', readonly=True, digits='Product Unit')
    free_qty = fields.Float(string='Stock libre', readonly=True, digits='Product Unit')
    incoming_qty = fields.Float(string='Entradas confirmadas', readonly=True, digits='Product Unit')
    suggested_qty = fields.Float(string='Compra orientativa', readonly=True, digits='Product Unit')
    unit_cost = fields.Float(string='Costo unitario actual', readonly=True, digits='Product Price')
    currency_id = fields.Many2one(related='company_id.currency_id', string='Moneda')
    estimated_value = fields.Monetary(string='Valor estimado pendiente', readonly=True,
                                      currency_field='currency_id')
    detail_ids = fields.One2many('alvina.branch.consolidation.detail', 'consolidation_line_id',
                                 string='Valorización pendiente por sucursal', readonly=True)
    source_line_ids = fields.Many2many('alvina.branch.request.line',
                                      string='Desglose de requerimientos', readonly=True)


class ConsolidationDetail(models.TransientModel):
    _name = 'alvina.branch.consolidation.detail'
    _description = 'Valorización pendiente por sucursal'

    consolidation_line_id = fields.Many2one(
        'alvina.branch.consolidation.line', string='Línea del consolidado',
        required=True, ondelete='cascade', readonly=True)
    request_line_id = fields.Many2one(
        'alvina.branch.request.line', string='Línea del requerimiento',
        required=True, ondelete='cascade', readonly=True)
    request_id = fields.Many2one(related='request_line_id.request_id',
                                 string='Requerimiento', readonly=True, compute_sudo=False)
    branch_id = fields.Many2one(related='request_line_id.branch_id',
                                string='Sucursal', readonly=True, compute_sudo=False)
    company_id = fields.Many2one(related='request_line_id.company_id',
                                 string='Compañía solicitante', readonly=True, compute_sudo=False)
    user_id = fields.Many2one(related='request_line_id.request_id.user_id',
                              string='Solicitante', readonly=True, compute_sudo=False)
    product_qty = fields.Float(string='Cantidad pendiente', readonly=True, digits='Product Unit')
    product_uom_id = fields.Many2one(related='consolidation_line_id.product_uom_id',
                                     string='Unidad de medida', readonly=True, compute_sudo=False)
    unit_cost = fields.Float(related='consolidation_line_id.unit_cost',
                             string='Costo unitario actual', readonly=True, compute_sudo=False)
    currency_id = fields.Many2one(related='consolidation_line_id.currency_id',
                                  string='Moneda', readonly=True, compute_sudo=False)
    estimated_value = fields.Monetary(string='Valor estimado pendiente', readonly=True,
                                      currency_field='currency_id')
