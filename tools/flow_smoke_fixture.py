"""Synthetic Odoo shell scenario, only in the dedicated local disposable DB.

ALVINA_FLOW_SMOKE_PHASE=seed|deliver|receive odoo-bin shell ... < this_file
Requires alvina_logistics_http_test, /tmp/alvina-ci-pg and role odoo_test.
Commits synthetic data; never run against an operational database.
After seed, run check_flow_http.py submit before deliver and receive.
"""
import json
import os

from odoo import Command
from odoo.tools import config


if (env.cr.dbname != 'alvina_logistics_http_test'
        or config['db_host'] != '/tmp/alvina-ci-pg'
        or config['db_user'] != 'odoo_test'):
    raise RuntimeError('Only the dedicated local logistics HTTP test database is accepted')
env.cr.execute('SELECT current_database(), current_user')
assert env.cr.fetchone() == ('alvina_logistics_http_test', 'odoo_test')
phase = os.environ.get('ALVINA_FLOW_SMOKE_PHASE', 'seed')
if phase not in ('seed', 'deliver', 'receive'):
    raise RuntimeError('Only seed, deliver or receive phases are accepted')
key = 'alvina.flow.smoke.fixture'
parameters = env['ir.config_parameter'].sudo()


def stock_level(product, warehouse):
    return product.with_company(warehouse.company_id).with_context(
        allowed_company_ids=warehouse.company_id.ids,
        warehouse_id=warehouse.id).qty_available


def as_actor(records, user_id, company_id):
    return records.with_user(user_id).with_context(allowed_company_ids=[company_id])


if phase == 'seed':
    assert not parameters.get_param(key), 'Smoke fixture already exists; use a new disposable database'
    assert not env['alvina.supply.configuration'].search_count([]), 'Empty supply configuration required'
    peru = env.ref('base.pe')
    currency = env.ref('base.PEN')
    currency.active = True
    industry = env['res.company'].create({
        'name': 'Industria Alviña — DATOS DE PRUEBA', 'country_id': peru.id,
        'account_fiscal_country_id': peru.id, 'currency_id': currency.id,
    })
    buyer = env['res.company'].create({
        'name': 'Sucursal UPAO — DATOS DE PRUEBA', 'country_id': peru.id,
        'account_fiscal_country_id': peru.id, 'currency_id': currency.id,
    })
    # Only the commercial contacts created for these two synthetic companies
    # are shared. Never alter an existing operational partner.
    (industry.partner_id | buyer.partner_id).write({'company_id': False})
    source = env['stock.warehouse'].create({
        'name': 'Insumos — DATOS DE PRUEBA', 'code': 'HIND',
        'company_id': industry.id, 'delivery_steps': 'ship_only',
    })
    destination = env['stock.warehouse'].create({
        'name': 'Recepción UPAO — DATOS DE PRUEBA', 'code': 'HUPA',
        'company_id': buyer.id, 'reception_steps': 'one_step',
    })
    source.out_type_id.create_backorder = 'always'
    destination.in_type_id.create_backorder = 'always'
    requester = env['res.users'].create({
        'name': 'Sucursal UPAO — DATOS DE PRUEBA HTTP', 'login': 'alvina-flow-http',
        'password': 'flow-smoke-local-only', 'company_id': buyer.id,
        'company_ids': [Command.set(buyer.ids)], 'tz': 'America/Lima',
        'group_ids': [Command.set([
            env.ref('base.group_user').id,
            env.ref('purchase.group_purchase_user').id,
            env.ref('alvina_branch_requisition.group_requester').id,
        ])],
    })
    logistics = env['res.users'].create({
        'name': 'Logística — DATOS DE PRUEBA', 'login': 'alvina-logistics-http',
        'company_id': industry.id, 'company_ids': [Command.set(industry.ids)],
        'tz': 'America/Lima',
        'group_ids': [Command.set([
            env.ref('base.group_user').id,
            env.ref('alvina_branch_requisition.group_industry_logistics').id,
        ])],
    })
    # The supplier logistics role intentionally has no per-branch assignment.
    contact = env['res.partner'].create({
        'name': 'Sucursal UPAO — local de prueba', 'company_id': buyer.id,
    })
    binding = env['alvina.branch.binding'].create({
        'resource_ref': 'res.partner,%s' % contact.id, 'branch_code': 'HTTP-UPAO',
        'company_id': buyer.id, 'supply_company_id': industry.id,
        'warehouse_id': source.id, 'purchase_picking_type_id': destination.in_type_id.id,
        'user_ids': [Command.set(requester.ids)],
    })
    category = env['product.category'].search([('name', '=', 'Comerciales')], limit=1)
    category = category or env['product.category'].create({'name': 'Comerciales'})
    product = env['product.product'].create({
        'name': 'Útil de prueba para despacho', 'default_code': 'HTTP-001',
        'categ_id': category.id, 'company_id': False, 'is_storable': True,
        'list_price': 99, 'sale_ok': True, 'purchase_ok': True,
        'alvina_requisition_enabled': True, 'tracking': 'none',
        'taxes_id': [Command.clear()], 'supplier_taxes_id': [Command.clear()],
    })
    pricelist = env['product.pricelist'].create({
        'name': 'Acuerdo sucursales — DATOS DE PRUEBA', 'company_id': industry.id,
        'currency_id': currency.id,
        'item_ids': [Command.create({
            'applied_on': '1_product', 'product_tmpl_id': product.product_tmpl_id.id,
            'compute_price': 'fixed', 'fixed_price': 3.5,
        })],
    })
    env['alvina.supply.configuration'].create({
        'company_id': industry.id, 'sales_user_id': logistics.id,
        'pricelist_id': pricelist.id, 'enabled': True,
    })
    env['stock.quant']._update_available_quantity(product, source.lot_stock_id, 15)
    assert stock_level(product, source) == 15
    assert stock_level(product, destination) == 0
    assert not requester.has_group('stock.group_stock_user')
    data = {
        'scenario_version': 3, 'branch_id': binding.id, 'product_id': product.id,
        'requester_id': requester.id, 'logistics_id': logistics.id,
        'industry_id': industry.id, 'buyer_id': buyer.id,
        'source_warehouse_id': source.id, 'destination_warehouse_id': destination.id,
    }
    parameters.set_param(key, json.dumps(data))
    env.cr.commit()
    print('FLOW_SMOKE_FIXTURE_READY: synthetic Peru companies; requester has no Industry or Inventory access.')
else:
    raw = parameters.get_param(key)
    assert raw, 'Run the seed phase first'
    data = json.loads(raw)
    assert data['scenario_version'] == 3, 'This scenario requires the 19.0.3 fixture'
    requests = env['alvina.branch.request'].search([('branch_id', '=', data['branch_id'])])
    assert len(requests) == 1, 'Run the concurrent HTTP submit before processing this scenario'
    request = requests[0]
    assert request.company_id.id == data['buyer_id']
    assert request.supply_company_id.id == data['industry_id']
    assert request.sale_order_id.state == 'sale'
    assert request.purchase_order_id.state == 'purchase'
    assert len(request.line_ids) == 1 and request.line_ids.product_qty == 20
    product = env['product.product'].browse(data['product_id'])
    source = env['stock.warehouse'].browse(data['source_warehouse_id'])
    destination = env['stock.warehouse'].browse(data['destination_warehouse_id'])
    assert env['res.users'].browse(data['requester_id']).company_ids.ids == [data['buyer_id']]
    assert env['res.users'].browse(data['logistics_id']).company_ids.ids == [data['industry_id']]
    assert data['logistics_id'] not in request.branch_id.user_ids.ids

    if phase == 'deliver':
        assert not data.get('guide_id'), 'Delivery phase already completed'
        sale = as_actor(request.sale_order_id, data['logistics_id'], data['industry_id'])
        picking = sale.picking_ids.filtered(lambda item: item.picking_type_code == 'outgoing')
        assert len(picking) == 1 and picking.state not in ('done', 'cancel')
        assert stock_level(product, source) == 15
        picking.action_assign()
        picking.move_ids.write({'quantity': 15, 'picked': True})
        picking.write({
            'alvina_dispatch_note': 'MUESTRA — DATOS DE PRUEBA; no es un documento operativo de Alviña.',
            'alvina_shortage_note': 'Se envían 15 unidades; quedan 5 pendientes de despacho.',
        })
        picking.button_validate()
        assert picking.state == 'done'
        guide = picking.sudo().alvina_emitted_dispatch_ids
        assert len(guide) == 1 and guide.receipt_state == 'pending'
        assert guide.snapshot_json['lines'][0]['shipped'] == 15
        assert guide.snapshot_json['totals']['total'] == 52.5
        assert [(row['requested'], row['supplied'], row['pending'])
                for row in guide.snapshot_json['balances']] == [(20, 15, 5)]
        assert request.line_ids.qty_supplied == 15 and request.line_ids.qty_pending == 5
        assert request.line_ids.qty_received == 0
        assert len(picking.backorder_ids) == 1
        assert not request.purchase_order_id.picking_ids.filtered(lambda item: item.state == 'done')
        assert stock_level(product, source) == 0 and stock_level(product, destination) == 0
        data.update({'guide_id': guide.id, 'outgoing_id': picking.id,
                     'industry_stock_after_dispatch': stock_level(product, source)})
        parameters.set_param(key, json.dumps(data))
        message = 'FLOW_SMOKE_DELIVERY_PASSED: 20 requested, 15 dispatched, 5 pending; guide issued; buyer receipt still pending.'
    else:
        assert data.get('guide_id'), 'Run the delivery phase first'
        guide = as_actor(env['alvina.branch.dispatch'].browse(data['guide_id']),
                         data['requester_id'], data['buyer_id'])
        assert guide.receipt_state == 'pending', 'Receipt phase already completed'
        action = guide.action_open_receipt()
        wizard = as_actor(env['alvina.branch.dispatch.receipt'].browse(action['res_id']),
                          data['requester_id'], data['buyer_id'])
        assert len(wizard.line_ids) == 1 and wizard.line_ids.quantity == 0
        wizard.line_ids.quantity = 13
        wizard.note = 'MUESTRA — La sucursal recibió 13 de las 15 unidades de esta guía; faltan 2 por verificar.'
        wizard.action_confirm()
        guide = guide.sudo()
        assert guide.receipt_state == 'discrepancy'
        assert guide.confirmed_by.id == data['requester_id']
        assert [(row['shipped'], row['received'], row['difference'])
                for row in guide.receipt_confirmation_json['lines']] == [(15, 13, 2)]
        receipts = request.purchase_order_id.picking_ids.filtered(
            lambda item: item.alvina_dispatch_id == guide)
        assert len(receipts) == 1 and receipts.state == 'done'
        assert receipts.company_id.id == data['buyer_id']
        assert request.line_ids.qty_received == 13
        assert request.line_ids.qty_supplied == 15 and request.line_ids.qty_pending == 5
        assert request.line_ids.product_qty == 20
        assert stock_level(product, source) == data['industry_stock_after_dispatch'] == 0
        assert stock_level(product, destination) == 13
        assert not env['res.users'].browse(data['requester_id']).has_group('stock.group_stock_user')
        data['receipt_id'] = receipts.id
        parameters.set_param(key, json.dumps(data))
        message = 'FLOW_SMOKE_RECEIPT_PASSED: 13 received, discrepancy 2, dispatch pending 5; no second Industry stock deduction.'

    assert not request.sale_order_id.invoice_ids and not request.purchase_order_id.invoice_ids
    assert env['res.users'].browse(data['requester_id']).company_ids.ids == [data['buyer_id']]
    assert env['res.users'].browse(data['logistics_id']).company_ids.ids == [data['industry_id']]
    env.cr.commit()
    print(message)
