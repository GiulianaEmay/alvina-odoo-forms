"""Odoo shell fixture, limited to the dedicated local disposable smoke DB.

ALVINA_FLOW_SMOKE_PHASE=seed|deliver odoo-bin shell ... < this_file
This fixture commits only synthetic documents in alvina_flow_smoke_test.
"""
import json
import os
from odoo import Command
from odoo.tools import config

if env.cr.dbname != 'alvina_flow_smoke_test' or config['db_host'] != '/tmp/alvina-test-pg':
    raise RuntimeError('Only the dedicated local smoke database is accepted')
phase = os.environ.get('ALVINA_FLOW_SMOKE_PHASE', 'seed')
key = 'alvina.flow.smoke.fixture'
parameters = env['ir.config_parameter'].sudo()
if phase == 'seed':
    assert not parameters.get_param(key), 'Smoke fixture already exists'
    assert not env['alvina.supply.configuration'].search_count([])
    industry = env['res.company'].create({'name': 'Industria Alviña — DATOS DE PRUEBA'})
    buyer = env['res.company'].create({'name': 'Sucursal UPAO — DATOS DE PRUEBA'})
    source = env['stock.warehouse'].create({'name': 'Insumos prueba', 'code': 'HIND', 'company_id': industry.id})
    receipt = env['stock.warehouse'].create({'name': 'Recepción UPAO prueba', 'code': 'HUPA', 'company_id': buyer.id})
    source.out_type_id.create_backorder = 'always'
    requester = env['res.users'].create({
        'name': 'Sucursal UPAO prueba HTTP', 'login': 'alvina-flow-http',
        'password': 'flow-smoke-local-only', 'company_id': buyer.id,
        'company_ids': [Command.set(buyer.ids)],
        'group_ids': [Command.set([env.ref('base.group_portal').id,
                                   env.ref('alvina_branch_requisition.group_requester').id])]})
    rolly = env['res.users'].create({
        'name': 'Rolly — usuario de prueba', 'login': 'alvina-rolly-http',
        'company_id': industry.id, 'company_ids': [Command.set(industry.ids)],
        'group_ids': [Command.set([env.ref('base.group_user').id,
                                   env.ref('sales_team.group_sale_salesman').id,
                                   env.ref('alvina_branch_requisition.group_keeper').id])]})
    contact = env['res.partner'].create({'name': 'Sucursal UPAO — cliente de prueba'})
    binding = env['alvina.branch.binding'].create({
        'resource_ref': 'res.partner,%s' % contact.id, 'branch_code': 'HTTP-UPAO',
        'company_id': buyer.id, 'supply_company_id': industry.id, 'warehouse_id': source.id,
        'purchase_picking_type_id': receipt.in_type_id.id,
        'user_ids': [Command.set((requester | rolly).ids)]})
    category = env['product.category'].search([('name', '=', 'Comerciales')], limit=1)
    category = category or env['product.category'].create({'name': 'Comerciales'})
    product = env['product.product'].create({
        'name': 'Útil de prueba para despacho', 'default_code': 'HTTP-001',
        'categ_id': category.id, 'is_storable': True, 'list_price': 99,
        'sale_ok': True, 'purchase_ok': True, 'alvina_requisition_enabled': True,
        'taxes_id': [Command.clear()], 'supplier_taxes_id': [Command.clear()]})
    pricelist = env['product.pricelist'].create({
        'name': 'Acuerdo sucursales de prueba', 'company_id': industry.id,
        'currency_id': industry.currency_id.id,
        'item_ids': [Command.create({'applied_on': '1_product',
             'product_tmpl_id': product.product_tmpl_id.id, 'compute_price': 'fixed', 'fixed_price': 3.5})]})
    env['alvina.supply.configuration'].create({'company_id': industry.id,
        'sales_user_id': rolly.id, 'pricelist_id': pricelist.id, 'enabled': True})
    env['stock.quant']._update_available_quantity(product, source.lot_stock_id, 15)
    parameters.set_param(key, json.dumps({'branch_id': binding.id, 'product_id': product.id,
        'requester_id': requester.id, 'rolly_id': rolly.id, 'industry_id': industry.id, 'buyer_id': buyer.id}))
    env.cr.commit()
    print('FLOW_SMOKE_FIXTURE_READY')
elif phase == 'deliver':
    data = json.loads(parameters.get_param(key))
    requests = env['alvina.branch.request'].search([('branch_id', '=', data['branch_id'])])
    assert len(requests) == 1
    request = requests[0]
    sale = request.sale_order_id.with_user(data['rolly_id']).with_context(allowed_company_ids=[data['industry_id']])
    assert sale.state == 'draft' and request.purchase_order_id.state == 'draft'
    sale.action_confirm()
    picking = sale.picking_ids
    picking.action_assign()
    picking.move_ids.write({'quantity': 15, 'picked': True})
    picking.button_validate()
    assert picking.state == 'done'
    assert request.line_ids.qty_supplied == 15 and request.line_ids.qty_pending == 5
    assert request.line_ids.qty_received == 0
    assert len(picking.backorder_ids) == 1
    assert not sale.invoice_ids and not request.purchase_order_id.invoice_ids
    env.cr.commit()
    print('FLOW_SMOKE_DELIVERY_PASSED: 20 requested, 15 done, 5 backordered; receipt unvalidated; no invoice.')
else:
    raise RuntimeError('Only seed or deliver phases are accepted')
