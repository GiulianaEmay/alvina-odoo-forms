"""Execute via Odoo shell ONLY against the dedicated disposable test database.
This intentionally commits fixtures and uninstalls the addon.
"""
if env.cr.dbname != 'alvina_requisition_test':
    raise RuntimeError('This destructive check only accepts alvina_requisition_test')
from uuid import uuid4
from odoo import Command, fields
# Local throwaway database only. Create real records before uninstalling.
company=env.company
user=env.ref('base.user_admin')
user.group_ids=[Command.link(env.ref('alvina_branch_requisition.group_requester').id)]
warehouse=env['stock.warehouse'].search([('company_id','=',company.id)],limit=1)
partner=env['res.partner'].create({'name':'Alvina uninstall sentinel'})
category=env['product.category'].create({'name':'Comerciales'})
product=env['product.product'].create({'name':'Alvina uninstall sentinel product','categ_id':category.id,'is_storable':True,'alvina_requisition_enabled':True})
env['stock.quant']._update_available_quantity(product,warehouse.lot_stock_id,7)
branch=env['alvina.branch.binding'].create({'resource_ref':f'res.partner,{partner.id}','company_id':company.id,'warehouse_id':warehouse.id,'user_ids':[Command.set(user.ids)]})
record=env['alvina.branch.request'].with_user(user).create({'branch_id':branch.id,'required_date':env['alvina.branch.request']._minimum_required_date(),'submission_key':str(uuid4()),'line_ids':[Command.create({'product_id':product.id,'product_qty':3})]})
partner_id,product_id,category_id=partner.id,product.id,category.id
purchase_ids=env['purchase.order'].search([]).ids
move_ids=env['stock.move'].search([]).ids
menu_rfq=env.ref('purchase.menu_purchase_rfq').id
menu_po=env.ref('purchase.menu_purchase_form_action').id
env.cr.commit()
module=env['ir.module.module'].search([('name','=','alvina_branch_requisition')])
module.button_immediate_uninstall()
env.cr.commit()
assert env['res.partner'].browse(partner_id).exists()
assert env['product.category'].browse(category_id).exists()
assert env['product.product'].browse(product_id).exists()
assert env['product.product'].browse(product_id).with_context(warehouse_id=warehouse.id).qty_available==7
assert env['purchase.order'].search([]).ids==purchase_ids
assert env['stock.move'].search([]).ids==move_ids
assert env.ref('purchase.menu_purchase_rfq').id==menu_rfq
assert env.ref('purchase.menu_purchase_form_action').id==menu_po
assert not env.ref('alvina_branch_requisition.menu_web',raise_if_not_found=False)
assert not env.ref('alvina_branch_requisition.menu_requests',raise_if_not_found=False)
assert not env.ref('alvina_branch_requisition.menu_consolidation',raise_if_not_found=False)
assert 'alvina_requisition_enabled' not in env['product.template']._fields
print('UNINSTALL_CHECK_PASSED: original entities, menus, stock and purchase/move counts preserved')
