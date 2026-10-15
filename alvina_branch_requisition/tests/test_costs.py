"""Pending supply is valued with the supplier's existing cost and permissions."""
from uuid import uuid4

from odoo import Command, fields
from odoo.exceptions import AccessError
from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestRequisitionCosts(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.supplier = cls.env.company
        cls.request_company = cls.env['res.company'].create({
            'name': 'UPAO cost test', 'currency_id': cls.env.ref('base.EUR').id})
        cls.requester = cls.env['res.users'].create({
            'name': 'Cost requester', 'login': 'alvina-cost-requester',
            'company_id': cls.request_company.id, 'company_ids': [Command.set(cls.request_company.ids)],
            'group_ids': [Command.set([cls.env.ref('base.group_portal').id,
                cls.env.ref('alvina_branch_requisition.group_requester').id])]})
        cls.keeper = cls.env['res.users'].create({
            'name': 'Cost keeper', 'login': 'alvina-cost-keeper',
            'company_id': cls.supplier.id, 'company_ids': [Command.set(cls.supplier.ids)],
            'group_ids': [Command.set([cls.env.ref('base.group_user').id,
                cls.env.ref('alvina_branch_requisition.group_keeper').id])]})
        cls.outsider = cls.keeper.copy({'name': 'Other cost keeper', 'login': 'alvina-cost-outsider'})
        partner = cls.env['res.partner'].create({'name': 'Existing UPAO cost branch',
                                                'company_id': cls.request_company.id})
        cls.warehouse = cls.env['stock.warehouse'].search([('company_id', '=', cls.supplier.id)], limit=1)
        cls.branch = cls.env['alvina.branch.binding'].create({
            'resource_ref': f'res.partner,{partner.id}', 'company_id': cls.request_company.id,
            'warehouse_id': cls.warehouse.id, 'user_ids': [Command.set(cls.requester.ids)],
            'keeper_ids': [Command.set(cls.keeper.ids)]})
        category = cls.env['product.category'].create({'name': 'Abarrotes'})
        cls.product = cls.env['product.product'].create({'name': 'Shared supply with cost',
            'categ_id': category.id, 'alvina_requisition_enabled': True, 'is_storable': True})
        cls.product.with_company(cls.request_company).standard_price = 99
        cls.product.with_company(cls.supplier).standard_price = 2.5

    def _request(self, qty=4):
        return self.env['alvina.branch.request'].with_user(self.requester).create({
            'branch_id': self.branch.id, 'required_date': fields.Date.today(),
            'submission_key': str(uuid4()), 'line_ids': [Command.create({
                'product_id': self.product.id, 'product_qty': qty})]})

    def _consolidate(self):
        wizard = self.env['alvina.branch.consolidation'].with_user(self.keeper).create({})
        wizard.action_refresh()
        return wizard

    def test_pending_value_uses_supplier_cost_currency_and_current_pending_quantity(self):
        self._request(qty=4)
        self._request(qty=6)
        self.env['stock.quant']._update_available_quantity(self.product, self.warehouse.lot_stock_id, 3)
        row = self._consolidate().line_ids
        self.assertEqual(len(row), 1)
        self.assertEqual(row.product_qty, 10)
        self.assertEqual(row.suggested_qty, 7)
        self.assertEqual(row.unit_cost, 2.5)
        self.assertEqual(row.currency_id, self.supplier.currency_id)
        self.assertEqual(row.estimated_value, 25)
        self.assertEqual(sum(row.detail_ids.mapped('product_qty')), 10)
        self.assertEqual(sum(row.detail_ids.mapped('estimated_value')), 25)
        self.assertEqual(set(row.detail_ids.request_line_id.ids), set(row.source_line_ids.ids))

    def test_recalculate_uses_current_cost_and_excludes_cancelled_requests(self):
        self._request(qty=4)
        second = self._request(qty=6)
        wizard = self._consolidate()
        self.product.with_company(self.supplier).standard_price = 5
        second.with_user(self.keeper).action_cancel()
        wizard.action_refresh()
        self.assertEqual(wizard.line_ids.product_qty, 4)
        self.assertEqual(wizard.line_ids.unit_cost, 5)
        self.assertEqual(wizard.line_ids.estimated_value, 20)
        self.assertEqual(len(wizard.line_ids.detail_ids), 1)
        self.assertEqual(wizard.line_ids.detail_ids.estimated_value, 20)

    def test_estimates_and_branch_breakdown_are_private_to_the_keeper_owner(self):
        self._request()
        wizard = self._consolidate()
        for user in (self.requester, self.outsider):
            for records in (wizard, wizard.line_ids, wizard.line_ids.detail_ids):
                with self.subTest(user=user.login, model=records._name), self.assertRaises(AccessError):
                    records.with_user(user).read()
        # An ordinary request line never stores or publishes the supplier's cost.
        self.assertNotIn('unit_cost', self.env['alvina.branch.request.line']._fields)

    def test_keeper_in_requesting_company_cannot_calculate_supplier_cost(self):
        self._request()
        self.requester.write({'group_ids': [Command.set([self.env.ref('base.group_user').id,
            self.env.ref('alvina_branch_requisition.group_keeper').id])]})
        wizard = self.env['alvina.branch.consolidation'].with_user(self.requester).create({})
        with self.assertRaises(AccessError):
            wizard.action_refresh()

    def test_zero_cost_is_preserved_without_inventing_a_price(self):
        self.product.with_company(self.supplier).standard_price = 0
        self._request()
        row = self._consolidate().line_ids
        self.assertEqual(row.unit_cost, 0)
        self.assertEqual(row.estimated_value, 0)
        self.assertEqual(row.detail_ids.estimated_value, 0)
