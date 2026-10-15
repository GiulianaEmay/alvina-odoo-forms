"""Central supply without extending requesters' standard Odoo permissions."""
from uuid import uuid4

from odoo import Command, fields
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestCentralSupply(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.industria = cls.env.company
        cls.upao = cls.env['res.company'].create({'name': 'UPAO test'})
        cls.other_company = cls.env['res.company'].create({'name': 'Other requester test'})
        cls.warehouse = cls.env['stock.warehouse'].search([
            ('company_id', '=', cls.industria.id)], limit=1)
        cls.other_warehouse = cls.env['stock.warehouse'].create({
            'name': 'Other central warehouse', 'code': 'OTCTR', 'company_id': cls.industria.id})
        requester = cls.env.ref('alvina_branch_requisition.group_requester')
        keeper = cls.env.ref('alvina_branch_requisition.group_keeper')
        internal = cls.env.ref('base.group_user')

        def user(login, company, group):
            return cls.env['res.users'].create({
                'name': login, 'login': login, 'company_id': company.id,
                'company_ids': [Command.set(company.ids)],
                'group_ids': [Command.set((internal | group).ids)],
            })

        cls.requester = user('central-upao-requester', cls.upao, requester)
        cls.other_requester = user('central-other-requester', cls.other_company, requester)
        cls.keeper = user('central-industria-keeper', cls.industria, keeper)
        cls.outsider = user('central-unassigned-keeper', cls.industria, keeper)
        category = cls.env['product.category'].create({'name': 'Comerciales'})
        cls.product = cls.env['product.product'].create({
            'name': 'Shared central product', 'is_storable': True,
            'categ_id': category.id, 'alvina_requisition_enabled': True})
        cls.branch = cls._binding(cls.upao, cls.requester, 'UPAO existing branch')
        cls.second_branch = cls._binding(cls.other_company, cls.other_requester, 'Other existing branch')

    @classmethod
    def _binding(cls, company, requester, name, warehouse=None):
        partner = cls.env['res.partner'].create({'name': name, 'company_id': company.id})
        return cls.env['alvina.branch.binding'].create({
            'resource_ref': f'res.partner,{partner.id}', 'company_id': company.id,
            'warehouse_id': (warehouse or cls.warehouse).id,
            'user_ids': [Command.set(requester.ids)],
            'keeper_ids': [Command.set(cls.keeper.ids)],
        })

    def _request(self, branch=None, user=None, qty=10, **extra):
        vals = {
            'branch_id': (branch or self.branch).id, 'required_date': fields.Date.today(),
            'submission_key': str(uuid4()),
            'line_ids': [Command.create({'product_id': self.product.id, 'product_qty': qty})],
        }
        vals.update(extra)
        return self.env['alvina.branch.request'].with_user(user or self.requester).create(vals)

    def _wizard(self, user=None, **context):
        return self.env['alvina.branch.consolidation'].with_user(user or self.keeper).with_context(
            **context).create({})

    def test_upao_can_request_without_industria_membership_or_standard_access(self):
        moves = self.env['stock.move'].search_count([])
        orders = self.env['purchase.order'].search_count([])
        rec = self._request()
        self.assertEqual(rec.company_id, self.upao)
        self.assertEqual(rec.supply_company_id, self.industria)
        self.assertEqual(rec.warehouse_id, self.warehouse)
        self.assertEqual(rec.line_ids.company_id, self.upao)
        self.assertEqual(rec.line_ids.supply_company_id, self.industria)
        self.assertEqual(rec.line_ids.warehouse_id, self.warehouse)
        self.assertNotIn(self.industria, self.requester.company_ids)
        for model in ('stock.move', 'purchase.order'):
            with self.subTest(model=model), self.assertRaises(AccessError):
                self.env[model].with_user(self.requester).check_access('read')
        self.env['stock.quant']._update_available_quantity(self.product, self.warehouse.lot_stock_id, 1)
        quant = self.env['stock.quant'].search([('product_id', '=', self.product.id),
                                               ('location_id', '=', self.warehouse.lot_stock_id.id)])
        for records in (quant, self.warehouse):
            with self.subTest(model=records._name), self.assertRaises(AccessError):
                records.with_user(self.requester).check_access('read')
        with self.assertRaises(AccessError):
            self.env['stock.quant'].with_user(self.requester).with_context(
                allowed_company_ids=self.industria.ids).search([])
        self.assertEqual(self.env['stock.move'].search_count([]), moves)
        self.assertEqual(self.env['purchase.order'].search_count([]), orders)

    def test_industria_keeper_manages_only_assigned_branches(self):
        rec = self._request()
        own = rec.with_user(self.keeper)
        self.assertEqual(own.read(['name', 'company_id', 'supply_company_id', 'warehouse_id'])[0]['id'], rec.id)
        own.action_review()
        self.assertEqual(rec.state, 'review')
        for records in (rec, rec.line_ids, self.branch):
            with self.subTest(model=records._name), self.assertRaises(AccessError):
                records.with_user(self.outsider).check_access('read')
        for action in ('action_review', 'action_cancel'):
            with self.subTest(action=action), self.assertRaises(AccessError):
                getattr(rec.with_user(self.outsider), action)()
        self.assertFalse(self.env['alvina.branch.request'].with_user(self.outsider).search([]))
        self.branch.keeper_ids = [Command.clear()]
        with self.assertRaises(AccessError):
            own.action_cancel()
        wizard = self._wizard()
        wizard.action_refresh()
        self.assertFalse(wizard.line_ids)

    def test_keeper_assignment_does_not_allow_submission_or_forge_company_context(self):
        with self.assertRaises(AccessError):
            self._request(user=self.keeper)
        with self.assertRaises(AccessError):
            self.env['alvina.branch.request'].with_user(self.keeper).with_context(
                allowed_company_ids=self.upao.ids).search([])
        with self.assertRaises(AccessError):
            self._request(branch=self.second_branch)

    def test_supply_snapshots_cannot_be_forged_or_changed(self):
        for name, value in (('supply_company_id', self.upao.id),
                            ('warehouse_id', self.other_warehouse.id), ('company_id', self.industria.id)):
            with self.subTest(field=name), self.assertRaises(AccessError), self.cr.savepoint():
                self._request(**{name: value})
        rec = self.env['alvina.branch.request'].with_user(self.requester).with_context(
            default_supply_company_id=self.upao.id, default_warehouse_id=self.other_warehouse.id).create({
                'branch_id': self.branch.id, 'required_date': fields.Date.today(),
                'submission_key': str(uuid4()), 'line_ids': [Command.create({
                    'product_id': self.product.id, 'product_qty': 3})]})
        self.assertEqual(rec.warehouse_id, self.warehouse)
        self.assertEqual(rec.supply_company_id, self.industria)
        with self.assertRaises(AccessError):
            rec.write({'warehouse_id': self.other_warehouse.id})
        with self.assertRaises(AccessError):
            rec.line_ids.write({'warehouse_id': self.other_warehouse.id})
        with self.assertRaises(ValidationError):
            self.branch.write({'warehouse_id': self.other_warehouse.id})

    def test_private_products_are_rejected_without_expanding_catalog_access(self):
        for company in (self.upao, self.industria, self.other_company):
            product = self.product.copy({'name': 'Private central product', 'company_id': company.id})
            with self.subTest(company=company.name), self.assertRaises(UserError), self.cr.savepoint():
                self._request(line_ids=[Command.create({'product_id': product.id, 'product_qty': 1})])

    def test_sum_across_requesting_companies_then_subtract_central_stock_once(self):
        first = self._request(qty=12)
        second = self._request(self.second_branch, self.other_requester, qty=8)
        self.env['stock.quant']._update_available_quantity(self.product, self.warehouse.lot_stock_id, 10)
        self.env['stock.quant']._update_reserved_quantity(self.product, self.warehouse.lot_stock_id, 2)
        self.env['stock.quant']._update_available_quantity(self.product, self.other_warehouse.lot_stock_id, 100)
        move = self.env['stock.move'].create({
            'product_id': self.product.id, 'product_uom_qty': 3, 'product_uom': self.product.uom_id.id,
            'location_id': self.env.ref('stock.stock_location_suppliers').id,
            'location_dest_id': self.warehouse.lot_stock_id.id,
            'picking_type_id': self.warehouse.in_type_id.id, 'company_id': self.industria.id})
        move._action_confirm()
        moves, orders = self.env['stock.move'].search_count([]), self.env['purchase.order'].search_count([])
        wizard = self._wizard(location=self.other_warehouse.lot_stock_id.id, to_date='2000-01-01')
        wizard.action_refresh()
        row = wizard.line_ids
        self.assertEqual(len(row), 1)
        self.assertEqual(row.company_id, self.industria)
        self.assertEqual(row.warehouse_id, self.warehouse)
        self.assertEqual(row.product_qty, 20)
        self.assertEqual(row.free_qty, 8)
        self.assertEqual(row.incoming_qty, 3)
        self.assertEqual(row.suggested_qty, 9)
        self.assertEqual(set(row.source_line_ids.ids), set((first | second).line_ids.ids))
        wizard.action_refresh()
        self.assertEqual(wizard.line_ids.suggested_qty, 9)
        second.with_user(self.keeper).action_cancel()
        wizard.action_refresh()
        self.assertEqual(wizard.line_ids.product_qty, 12)
        self.assertEqual(wizard.line_ids.suggested_qty, 1)
        self.assertEqual(self.env['stock.move'].search_count([]), moves)
        self.assertEqual(self.env['purchase.order'].search_count([]), orders)

    def test_consolidation_never_reads_unassigned_demand(self):
        self._request(qty=12)
        self._request(self.second_branch, self.other_requester, qty=80)
        self.second_branch.keeper_ids = [Command.clear()]
        wizard = self._wizard()
        wizard.action_refresh()
        self.assertEqual(wizard.line_ids.product_qty, 12)
        outsider = self._wizard(self.outsider)
        outsider.action_refresh()
        self.assertFalse(outsider.line_ids)
        with self.assertRaises(AccessError):
            wizard.with_user(self.outsider).action_refresh()
        with self.assertRaises(AccessError):
            wizard.line_ids.with_user(self.outsider).read(['product_qty', 'free_qty'])

    def test_distinct_supply_warehouses_stay_separate(self):
        self._request(qty=12)
        branch = self._binding(self.upao, self.requester, 'UPAO second supply', self.other_warehouse)
        self._request(branch, qty=8)
        self.env['stock.quant']._update_available_quantity(self.product, self.warehouse.lot_stock_id, 5)
        self.env['stock.quant']._update_available_quantity(self.product, self.other_warehouse.lot_stock_id, 2)
        wizard = self._wizard()
        wizard.action_refresh()
        self.assertEqual(len(wizard.line_ids), 2)
        self.assertEqual(sorted(wizard.line_ids.mapped('suggested_qty')), [6, 7])

    def test_assignments_require_keeper_group_and_supply_company_membership(self):
        with self.assertRaises(ValidationError), self.cr.savepoint():
            self.branch.keeper_ids = [Command.set(self.requester.ids)]

    def test_requesting_company_keeper_cannot_read_inactive_supply_stock(self):
        self._request()
        self.requester.group_ids = [Command.link(self.env.ref('alvina_branch_requisition.group_keeper').id)]
        wizard = self._wizard(self.requester)
        with self.assertRaises(AccessError):
            wizard.action_refresh()
