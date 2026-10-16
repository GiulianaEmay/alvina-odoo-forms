from unittest.mock import patch
from uuid import uuid4
import runpy

from psycopg2 import IntegrityError
from odoo import Command, fields
from odoo.exceptions import AccessError, ValidationError, UserError
from odoo.tests import TransactionCase, tagged
from odoo.tools import file_path

from .test_supply_companies import SupplyCompanyFixture


@tagged('post_install', '-at_install')
class TestCommercialFlow(SupplyCompanyFixture, TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.supply_company.account_fiscal_country_id = cls.env.ref('base.pe')
        cls.keeper.group_ids = [Command.link(cls.env.ref('sales_team.group_sale_salesman').id)]
        cls.branch.resource_ref.company_id = False
        cls.supply_company.partner_id.company_id = False
        warehouse = cls.env['stock.warehouse'].search([('company_id', '=', cls.branch_company.id)], limit=1)
        if not warehouse:
            warehouse = cls.env['stock.warehouse'].create({
                'name': 'Commercial buyer receipt', 'code': 'CBUY', 'company_id': cls.branch_company.id})
        cls.branch.write({'branch_code': 'UPAO-COMMERCIAL',
                          'purchase_picking_type_id': warehouse.in_type_id.id})
        cls.shared_product.write({'list_price': 99, 'sale_ok': True, 'purchase_ok': True,
                                  'taxes_id': [Command.clear()], 'supplier_taxes_id': [Command.clear()]})
        cls.pricelist = cls.env['product.pricelist'].create({
            'name': 'Industry branches agreement', 'company_id': cls.supply_company.id,
            'currency_id': cls.supply_company.currency_id.id,
            'item_ids': [Command.create({'applied_on': '1_product',
                'product_tmpl_id': cls.shared_product.product_tmpl_id.id,
                'compute_price': 'fixed', 'fixed_price': 3.5})]})
        cls.configuration = cls.env['alvina.supply.configuration'].create({
            'company_id': cls.supply_company.id, 'sales_user_id': cls.keeper.id,
            'pricelist_id': cls.pricelist.id, 'enabled': True})

    def _flow(self, **values):
        return self._request(product=self.shared_product, quantity=20, **values)

    def test_uniform_documents_without_legacy_branch_opt_in(self):
        self.assertFalse(self.branch.generate_purchase_rfq)
        record = self._flow()
        sale, purchase = record.sudo().sale_order_id, record.sudo().purchase_order_id
        self.assertTrue(record.supply_flow)
        self.assertEqual(record.operation_mode, 'intercompany')
        self.assertEqual((sale.state, purchase.state), ('draft', 'draft'))
        self.assertEqual(sale.company_id, self.supply_company)
        self.assertEqual(purchase.company_id, self.branch_company)
        self.assertEqual(sale.partner_id, self.branch_company.partner_id)
        self.assertEqual(purchase.partner_id, self.supply_company.partner_id)
        self.assertEqual(sale.user_id, self.keeper)
        self.assertEqual(sale.warehouse_id, self.warehouse)
        self.assertEqual(sale.order_line.alvina_request_line_id, record.line_ids)
        self.assertEqual(purchase.order_line.alvina_request_line_id, record.line_ids)
        self.assertEqual(sale.alvina_purchase_order_id, purchase)
        self.assertEqual(purchase.alvina_sale_order_id, sale)
        self.assertFalse(sale.picking_ids | purchase.picking_ids)
        self.assertFalse(sale.invoice_ids | purchase.invoice_ids)

    def test_upgrade_refuses_the_alternative_branch_schema_without_mapping(self):
        migration = runpy.run_path(file_path(
            'alvina_branch_requisition/migrations/19.0.2.0.0/pre-migration.py'))['migrate']
        self.cr.execute('CREATE TABLE alvina_binding_keeper_rel (binding_id integer, user_id integer)')
        with self.assertRaisesRegex(RuntimeError, 'central-supply-multicompany'):
            migration(self.cr, '19.0.1.2.0')

    def test_branch_contact_stays_private_and_stock_transit_corresponds(self):
        self.branch.resource_ref.company_id = self.branch_company
        record = self._flow()
        sale, purchase = record.sudo().sale_order_id, record.sudo().purchase_order_id
        self.assertEqual(sale.partner_id, self.branch_company.partner_id)
        self.assertEqual(self.branch.resource_ref.company_id, self.branch_company)
        outgoing_destination = sale.partner_shipping_id.with_company(self.supply_company).property_stock_customer
        receipt_source = purchase.partner_id.with_company(self.branch_company).property_stock_supplier
        self.assertEqual(outgoing_destination, receipt_source)
        self.assertEqual(outgoing_destination.usage, 'transit')

    def test_pricelist_instead_of_public_price(self):
        record = self._flow()
        self.assertEqual(record.line_ids.price_unit, 3.5)
        self.assertEqual(record.sudo().sale_order_id.amount_total, 70)
        self.assertEqual(record.sudo().purchase_order_id.amount_total, 70)
        self.assertEqual(record.amount_total, 70)
        self.assertEqual(self.shared_product.list_price, 99)

    def test_standard_sale_taxes_are_calculated(self):
        tax = self.env['account.tax'].create({'name': 'Sale tax 18 test',
            'tax_group_id': self.env['account.tax.group'].create({'name': 'Commercial test taxes', 'company_id': self.supply_company.id}).id,
            'company_id': self.supply_company.id, 'type_tax_use': 'sale', 'amount': 18})
        self.shared_product.taxes_id = [Command.set(tax.ids)]
        record = self._flow()
        sale = record.sudo().sale_order_id
        self.assertEqual(sale.amount_untaxed, 70)
        self.assertEqual(sale.amount_tax, 12.6)
        self.assertEqual(sale.amount_total, 82.6)

    def test_tax_included_sale_maps_to_tax_excluded_purchase_without_double_tax(self):
        self.branch_company.account_fiscal_country_id = self.env.ref('base.pe')
        sale_tax = self.env['account.tax'].create({
            'name': 'Included 18 sale test', 'amount': 18, 'type_tax_use': 'sale',
            'company_id': self.supply_company.id, 'price_include_override': 'tax_included',
            'tax_group_id': self.env['account.tax.group'].create({
                'name': 'Industry VAT test', 'company_id': self.supply_company.id}).id})
        purchase_tax = self.env['account.tax'].with_company(self.branch_company).create({
            'name': 'Excluded 18 purchase test', 'amount': 18, 'type_tax_use': 'purchase',
            'company_id': self.branch_company.id,
            'tax_group_id': self.env['account.tax.group'].create({
                'name': 'Branch VAT test', 'company_id': self.branch_company.id}).id})
        self.shared_product.write({'taxes_id': [Command.set(sale_tax.ids)],
                                   'supplier_taxes_id': [Command.set(purchase_tax.ids)]})
        record = self._flow()
        sale, purchase = record.sudo().sale_order_id, record.sudo().purchase_order_id
        self.assertEqual(sale.amount_total, 70)
        self.assertEqual(purchase.amount_total, sale.amount_total)
        self.assertEqual(purchase.amount_untaxed, sale.amount_untaxed)

    def test_repeated_private_creation_does_not_duplicate_pairs(self):
        record = self._flow()
        counts = (self.env['sale.order'].search_count([]), self.env['purchase.order'].search_count([]))
        record._create_supply_documents()
        self.assertEqual(counts, (self.env['sale.order'].search_count([]), self.env['purchase.order'].search_count([])))

    def test_duplicate_token_keeps_one_pair(self):
        token = str(uuid4())
        first = self._flow(submission_key=token)
        with self.assertRaises(IntegrityError), self.cr.savepoint():
            self._flow(submission_key=token)
        self.assertEqual(self.env['sale.order'].search_count([('origin', '=', first.name)]), 1)
        self.assertEqual(self.env['purchase.order'].search_count([('origin', '=', first.name)]), 1)

    def test_failure_of_purchase_does_not_commit_a_partial_pair(self):
        counts = {model: self.env[model].search_count([]) for model in
                  ('alvina.branch.request', 'sale.order', 'purchase.order')}
        model_class = type(self.env['purchase.order'])
        with patch.object(model_class, 'create', side_effect=ValidationError('Controlled test failure')):
            with self.assertRaises(ValidationError), self.cr.savepoint():
                self._flow()
        for model, count in counts.items():
            self.assertEqual(self.env[model].search_count([]), count)

    def test_native_intercompany_guard_has_no_invented_bypass(self):
        Module = type(self.env['ir.module.module'])
        original = Module.search_count
        def installed(modules, domain, *args, **kwargs):
            if ('name', '=', 'account_inter_company_rules') in domain:
                return 1
            return original(modules, domain, *args, **kwargs)
        with patch.object(Module, 'search_count', installed):
            with self.assertRaises(ValidationError):
                self.configuration._assert_supported()
            with self.assertRaises(ValidationError), self.cr.savepoint():
                self._flow()

    def test_native_guard_covers_both_purchase_confirmation_paths(self):
        record = self._flow()
        purchase = record.sudo().purchase_order_id
        # Simulate enabling the native module after the pair was created. Do
        # not install an Enterprise placeholder or guess its confirmation hook.
        Module = type(self.env['ir.module.module'])
        original = Module.search_count

        def installed(modules, domain, *args, **kwargs):
            if ('name', '=', 'account_inter_company_rules') in domain:
                return 1
            return original(modules, domain, *args, **kwargs)

        with patch.object(Module, 'search_count', installed):
            with self.assertRaises(ValidationError), self.cr.savepoint():
                purchase.button_confirm()
            self.assertEqual(purchase.state, 'draft')
            purchase.state = 'to approve'
            with self.assertRaises(ValidationError), self.cr.savepoint():
                purchase.button_approve(force=True)
            self.assertEqual(purchase.state, 'to approve')
            self.assertFalse(purchase.picking_ids)
            with self.assertRaises(ValidationError), self.cr.savepoint():
                record.sudo().sale_order_id.action_confirm()
            self.assertFalse(record.sudo().sale_order_id.picking_ids)

    def test_sale_keeps_the_buyers_delivery_and_invoice_partner(self):
        record = self._flow()
        sale = record.sudo().sale_order_id
        third_party = self.env['res.partner'].create({'name': 'Unrelated destination'})
        for field in ('partner_shipping_id', 'partner_invoice_id'):
            with self.subTest(field=field):
                with self.assertRaises(ValidationError), self.cr.savepoint():
                    sale.write({field: third_party.id})
                self.assertEqual(sale[field], self.branch_company.partner_id)

    def test_purchase_cannot_redirect_the_branch_receipt(self):
        record = self._flow()
        purchase = record.sudo().purchase_order_id
        operation = self.env['stock.picking.type'].create({
            'name': 'Unrelated branch receipt', 'code': 'incoming',
            'company_id': self.branch_company.id,
            'sequence_code': 'OTHER-RECEIPT',
            'default_location_src_id': self.env.ref('stock.stock_location_suppliers').id,
            'default_location_dest_id': purchase.picking_type_id.default_location_dest_id.id,
        })
        with self.assertRaises(ValidationError), self.cr.savepoint():
            purchase.picking_type_id = operation
        self.assertEqual(purchase.picking_type_id, self.branch.purchase_picking_type_id)
        with self.assertRaises(ValidationError), self.cr.savepoint():
            self.branch.purchase_picking_type_id = operation
        self.assertEqual(purchase.picking_type_id, self.branch.purchase_picking_type_id)

    def test_identification_and_industry_are_mandatory(self):
        self.branch.branch_code = False
        with self.assertRaises(ValidationError), self.cr.savepoint():
            self._flow()
        self.branch.branch_code = 'RESTORED'
        self.branch.write({'supply_company_id': self.unrelated_company.id,
                           'user_ids': [Command.set(self.requester.ids)],
                           'warehouse_id': self.env['stock.warehouse'].search([
                               ('company_id', '=', self.unrelated_company.id)], limit=1).id})
        with self.assertRaises(ValidationError), self.cr.savepoint():
            self._flow()

    def test_client_cannot_choose_flow_or_companies(self):
        for values in ({'supply_flow': False}, {'operation_mode': 'internal'},
                       {'supply_config_id': self.configuration.id},
                       {'supply_company_id': self.unrelated_company.id}):
            with self.subTest(values=values):
                with self.assertRaises(AccessError), self.cr.savepoint():
                    self._flow(**values)

    def test_industry_sales_user_prints_without_buyer_company_or_request_role(self):
        record = self._flow()
        self.keeper.group_ids = [Command.set([
            self.env.ref('base.group_user').id, self.env.ref('sales_team.group_sale_salesman').id])]
        sale = self._as(record.sudo().sale_order_id, self.keeper)
        sale.check_access('read')
        self.assertEqual(self.keeper.company_ids, self.supply_company)
        values = self._as(self.env['report.alvina_branch_requisition.dispatch_sale'], self.keeper)._get_report_values(sale.ids)
        self.assertEqual(values['documents'][0]['totals']['requested']['total'], 70)
        with self.assertRaises(AccessError):
            self._as(record, self.keeper).check_access('read')

    def test_unassigned_sales_user_and_branch_user_cannot_read_sale(self):
        record = self._flow()
        self.other_keeper.group_ids = [Command.link(self.env.ref('sales_team.group_sale_salesman_all_leads').id)]
        for user in (self.requester, self.other_keeper):
            with self.assertRaises(AccessError):
                self._as(record.sudo().sale_order_id, user).check_access('read')
            with self.assertRaises(AccessError):
                self._as(record.sudo().sale_order_id.order_line, user).check_access('read')
        self.assertEqual(self.requester.company_ids, self.branch_company)

    def test_original_quantities_and_link_identity_are_immutable(self):
        record = self._flow()
        line = record.sudo().sale_order_id.order_line
        with self.assertRaises(ValidationError), self.cr.savepoint():
            line.product_uom_qty = 15
        self.assertEqual(record.line_ids.product_qty, 20)
        with self.assertRaises(AccessError):
            self._as(self.env['sale.order'], self.keeper).with_context(
                default_alvina_branch_request_id=record.id).create({'partner_id': self.vendor.id})
