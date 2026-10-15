"""Probe a real 19.0.1.0.1 -> 19.0.1.1.0 upgrade in a disposable Odoo database.

Execute with ``odoo-bin shell`` and stdin redirection. Use
``ALVINA_SUPPLY_UPGRADE_PHASE=prepare`` with the old addon installed, then
upgrade the addon normally and rerun with ``ALVINA_SUPPLY_UPGRADE_PHASE=verify``.
Both phases commit fixtures or probe results. Only the dedicated local database
and Unix socket below are accepted; never run against an operational database.
"""

import json
import os
import runpy
from uuid import uuid4

from odoo import Command, fields
from odoo.tools import config, file_path


if (env.cr.dbname != 'alvina_supply_upgrade_test'
        or config['db_host'] != '/tmp/alvina-test-pg'):
    raise RuntimeError(
        'This probe only accepts alvina_supply_upgrade_test on /tmp/alvina-test-pg'
    )

phase = os.environ.get('ALVINA_SUPPLY_UPGRADE_PHASE', 'verify')
snapshot_key = 'alvina.supply_upgrade.fixture'
parameters = env['ir.config_parameter'].sudo()
module = env['ir.module.module'].search([('name', '=', 'alvina_branch_requisition')])


def snapshot_requests(records):
    return [{
        'id': request.id,
        'name': request.name,
        'branch_id': request.branch_id.id,
        'company_id': request.company_id.id,
        'user_id': request.user_id.id,
        'request_date': fields.Datetime.to_string(request.request_date),
        'required_date': fields.Date.to_string(request.required_date),
        'note': request.note,
        'state': request.state,
        'submission_key': request.submission_key,
        'lines': [{
            'id': line.id,
            'product_id': line.product_id.id,
            'company_id': line.company_id.id,
            'product_uom_id': line.product_uom_id.id,
            'product_qty': line.product_qty,
            'qty_supplied': line.qty_supplied,
            'qty_pending': line.qty_pending,
        } for line in request.line_ids.sorted('id')],
    } for request in records.sorted('id')]


if phase == 'prepare':
    assert module.installed_version == '19.0.1.0.1', module.installed_version
    assert 'supply_company_id' not in env['alvina.branch.binding']._fields
    assert not parameters.get_param(snapshot_key), 'Fixture already exists'
    companies = env['res.company'].create([
        {'name': 'Upgrade fixture branch A'},
        {'name': 'Upgrade fixture branch B'},
    ])
    category = env['product.category'].search([('name', '=', 'Comerciales')], limit=1)
    if not category:
        category = env['product.category'].create({'name': 'Comerciales'})
    product = env['product.product'].create({
        'name': 'Upgrade fixture shared product',
        'categ_id': category.id,
        'is_storable': True,
        'alvina_requisition_enabled': True,
    })
    bindings = env['alvina.branch.binding']
    requests = env['alvina.branch.request']
    binding_snapshots = []
    for index, company in enumerate(companies, 1):
        warehouse = env['stock.warehouse'].search([('company_id', '=', company.id)], limit=1)
        if not warehouse:
            warehouse = env['stock.warehouse'].create({
                'name': 'Upgrade fixture warehouse %s' % index,
                'code': 'UPG%s' % index,
                'company_id': company.id,
            })
        user = env['res.users'].create({
            'name': 'Upgrade fixture requester %s' % index,
            'login': 'alvina-upgrade-%s-%s' % (index, uuid4()),
            'company_id': company.id,
            'company_ids': [Command.set(company.ids)],
            'group_ids': [Command.set([
                env.ref('base.group_user').id,
                env.ref('alvina_branch_requisition.group_requester').id,
            ])],
        })
        partner = env['res.partner'].create({
            'name': 'Upgrade fixture branch contact %s' % index,
            'company_id': company.id,
        })
        binding = env['alvina.branch.binding'].with_company(company).create({
            'resource_ref': 'res.partner,%s' % partner.id,
            'company_id': company.id,
            'warehouse_id': warehouse.id,
            'user_ids': [Command.set(user.ids)],
        })
        request = env['alvina.branch.request'].with_user(user).with_company(company).create({
            'branch_id': binding.id,
            'required_date': fields.Date.today(),
            'note': 'Historical upgrade fixture %s' % index,
            'submission_key': str(uuid4()),
            'line_ids': [Command.create({'product_id': product.id, 'product_qty': index + 2})],
        })
        # Exercise both active and archived historical assignments.
        if index == 2:
            binding.active = False
        bindings |= binding
        requests |= request.sudo()
        binding_snapshots.append({
            'id': binding.id,
            'company_id': company.id,
            'warehouse_id': warehouse.id,
            'expected_supply_company_id': warehouse.company_id.id,
            'resource_ref': 'res.partner,%s' % partner.id,
            'active': binding.active,
            'user_ids': sorted(user.ids),
            'user_company_ids': sorted(user.company_ids.ids),
            'user_default_company_id': user.company_id.id,
        })
    snapshot = {
        'bindings': binding_snapshots,
        'requests': snapshot_requests(requests),
        'purchase_ids': env['purchase.order'].search([]).ids,
        'stock_move_ids': env['stock.move'].search([]).ids,
        'upgrade_default_company_id': env.company.id,
    }
    # All fixtures intentionally differ from the administrator's default company.
    assert all(item['company_id'] != env.company.id for item in binding_snapshots)
    parameters.set_param(snapshot_key, json.dumps(snapshot, sort_keys=True))
    env.cr.commit()
    print('SUPPLY_UPGRADE_PREPARED: 2 companies, 2 bindings, 2 historical requests; '
          'one archived binding; no supplier access granted to requesters')
elif phase == 'verify':
    assert module.installed_version == '19.0.1.1.0', module.installed_version
    raw_snapshot = parameters.get_param(snapshot_key)
    assert raw_snapshot, 'Run prepare on the baseline addon before upgrading'
    snapshot = json.loads(raw_snapshot)
    for item in snapshot['bindings']:
        binding = env['alvina.branch.binding'].browse(item['id']).exists()
        assert binding, item
        assert binding.company_id.id == item['company_id']
        assert binding.supply_company_id.id == item['expected_supply_company_id']
        assert binding.supply_company_id == binding.warehouse_id.company_id
        assert binding.warehouse_id.id == item['warehouse_id']
        assert binding.resource_ref._name + ',' + str(binding.resource_ref.id) == item['resource_ref']
        assert binding.active == item['active']
        assert sorted(binding.user_ids.ids) == item['user_ids']
        for user in binding.user_ids:
            assert sorted(user.company_ids.ids) == item['user_company_ids']
            assert user.company_id.id == item['user_default_company_id']
    requests = env['alvina.branch.request'].browse([item['id'] for item in snapshot['requests']])
    assert snapshot_requests(requests) == snapshot['requests']
    for request in requests:
        assert request.supply_company_id == request.branch_id.supply_company_id
        assert request.warehouse_id == request.branch_id.warehouse_id
        assert request.line_ids.mapped('supply_company_id') == request.supply_company_id
        assert request.line_ids.mapped('warehouse_id') == request.warehouse_id
    migration = runpy.run_path(file_path(
        'alvina_branch_requisition/migrations/19.0.1.1.0/pre-migration.py'
    ))['migrate']
    post_migration = runpy.run_path(file_path(
        'alvina_branch_requisition/migrations/19.0.1.1.0/post-migration.py'
    ))['migrate']
    for _attempt in range(2):
        migration(env.cr, '19.0.1.0.1')
        post_migration(env.cr, '19.0.1.0.1')
    env.cr.execute('SELECT id, supply_company_id FROM alvina_branch_binding ORDER BY id')
    supplier_snapshot = dict(env.cr.fetchall())
    for item in snapshot['bindings']:
        assert supplier_snapshot[item['id']] == item['expected_supply_company_id']
    assert snapshot_requests(requests) == snapshot['requests']
    assert env['purchase.order'].search([]).ids == snapshot['purchase_ids']
    assert env['stock.move'].search([]).ids == snapshot['stock_move_ids']
    env.cr.commit()
    print('SUPPLY_UPGRADE_PASSED: supplier backfill follows each warehouse; '
          'requester companies, users, history, purchase orders and stock moves preserved; '
          'migration rerun twice without changes')
else:
    raise RuntimeError('Use ALVINA_SUPPLY_UPGRADE_PHASE=prepare or verify')
