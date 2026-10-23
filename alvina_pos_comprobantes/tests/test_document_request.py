"""Requires a real Odoo 19 test database. No live provider calls or SUNAT calls."""
from unittest.mock import patch

from odoo import Command, fields
from odoo.exceptions import AccessError, UserError
from odoo.tests import tagged
from odoo.tests.common import new_test_user
from odoo.addons.point_of_sale.tests.common import CommonPosTest


@tagged("post_install", "-at_install", "alvina")
class TestAlvinaDocumentRequest(CommonPosTest):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company.country_id = cls.env.ref("base.pe")
        cls.company.account_fiscal_country_id = cls.env.ref("base.pe")
        cls.company.alvina_emission_mode = "pending"
        cls.config = cls.pos_config_usd
        cls.session = cls.env["pos.session"].create({"config_id": cls.config.id, "user_id": cls.env.uid})
        cls.dni_partner = cls.env["res.partner"].create({
            "name": "Cliente prueba ALVIÑA", "vat": "12345678", "country_id": cls.env.ref("base.pe").id,
            "l10n_latam_identification_type_id": cls.env.ref("l10n_pe.it_DNI").id,
        })
        cls.cashier = new_test_user(cls.env, login="alvina_cashier_test", groups="point_of_sale.group_pos_user")

    def make_order(self):
        fiscal = self.env["account.fiscal.position"].with_company(self.company)._get_fiscal_position(self.dni_partner)
        return self.env["pos.order"].create({
            "session_id": self.session.id, "company_id": self.company.id, "state": "paid",
            "amount_total": 118, "amount_tax": 18, "amount_paid": 118, "amount_return": 0,
            "fiscal_position_id": fiscal.id,
        })

    def preview(self, order):
        return order.alvina_lookup_identity("boleta", self.dni_partner.vat)["identity_id"]

    def test_local_partner_does_not_call_provider(self):
        order = self.make_order()
        with patch.object(type(self.company), "_alvina_lookup_external", side_effect=AssertionError("No network expected")):
            result = order.alvina_lookup_identity("boleta", self.dni_partner.vat)
        self.assertEqual(result["name"], self.dni_partner.name)
        self.assertNotIn("token", result)

    def test_duplicate_submit_keeps_original_order_and_no_new_payments(self):
        order = self.make_order()
        preview = self.preview(order)
        before_orders = self.env["pos.order"].search_count([])
        before_payments = self.env["pos.payment"].search_count([])
        first = order.alvina_submit_document(preview)
        second = order.alvina_submit_document(preview)
        self.assertEqual(first, second)
        self.assertEqual(first["state"], "pending")
        self.assertEqual(order.partner_id, self.dni_partner)
        self.assertFalse(order.account_move)
        self.assertEqual(self.env["pos.order"].search_count([]), before_orders)
        self.assertEqual(self.env["pos.payment"].search_count([]), before_payments)
        self.assertEqual(self.env["alvina.pos.document.request"].search_count([("order_id", "=", order.id)]), 1)

    def test_foreign_order_preview_is_rejected(self):
        order, other = self.make_order(), self.make_order()
        preview = self.preview(order)
        with self.assertRaises(UserError):
            other.alvina_submit_document(preview)

    def test_expired_preview(self):
        from datetime import timedelta
        order = self.make_order()
        preview = self.env["alvina.pos.identity"].sudo().browse(self.preview(order))
        # Odoo 19 ignores writes to create_date even under sudo. Advance the
        # service clock instead of weakening the identity model's ACL.
        with patch.object(fields.Datetime, "now", return_value=preview.create_date + timedelta(hours=2)), \
                self.assertRaises(UserError):
            order.alvina_submit_document(preview.id)

    def test_invalid_document(self):
        with self.assertRaises(UserError):
            self.make_order().alvina_lookup_identity("factura", "20100070971")

    def test_other_session_user_is_denied(self):
        order = self.make_order()
        with self.assertRaises(AccessError):
            order.with_user(self.cashier).alvina_lookup_identity("boleta", "12345678")

    def test_request_is_not_writable_by_cashier(self):
        order = self.make_order()
        order.alvina_submit_document(self.preview(order))
        request = order._alvina_request()
        with self.assertRaises(AccessError):
            request.with_user(self.cashier).write({"state": "processed"})

    def test_processing_failure_is_persistent_and_not_retried_silently(self):
        order = self.make_order()
        order.alvina_submit_document(self.preview(order))
        request = order._alvina_request()
        with patch.object(type(request), "_validate_for_invoice", side_effect=UserError("Diario de prueba inválido")):
            request._process_pending()
        self.assertEqual(request.state, "failed")
        self.assertIn("Diario", request.error_message)
        self.assertEqual(request.attempts, 1)
        self.assertFalse(order.account_move)
        request._process_pending()
        self.assertEqual(request.attempts, 1)

    def test_pending_cannot_print(self):
        order = self.make_order()
        order.alvina_submit_document(self.preview(order))
        with self.assertRaises(UserError):
            order.alvina_print_document()

    def test_official_invoice_values_use_type_03(self):
        order = self.make_order()
        order.config_id.invoice_journal_id.l10n_latam_use_documents = True
        order.alvina_submit_document(self.preview(order))
        values = order._prepare_invoice_vals()
        self.assertEqual(values["l10n_latam_document_type_id"], self.env.ref("l10n_pe.document_type02").id)
        self.assertEqual(values["journal_id"], order.config_id.invoice_journal_id.id)
        self.assertEqual(values["pos_order_ids"], order.ids)

    def test_official_invoice_values_use_type_01(self):
        order = self.make_order()
        order.config_id.invoice_journal_id.l10n_latam_use_documents = True
        self.env["res.partner"].create({
            "name": "Empresa prueba", "vat": "20100070970", "street": "Dirección fiscal de prueba",
            "country_id": self.env.ref("base.pe").id,
            "l10n_latam_identification_type_id": self.env.ref("l10n_pe.it_RUC").id,
        })
        preview = order.alvina_lookup_identity("factura", "20100070970")["identity_id"]
        order.alvina_submit_document(preview)
        values = order._prepare_invoice_vals()
        self.assertEqual(values["l10n_latam_document_type_id"], self.env.ref("l10n_pe.document_type01").id)

    def test_failed_invoice_attempt_rolls_back_its_changes(self):
        order = self.make_order()
        order.alvina_submit_document(self.preview(order))
        request = order._alvina_request()
        before_name = order.name

        def fail_after_write(records):
            records.write({"name": "Must be rolled back"})
            raise UserError("Simulated posting failure")

        with patch.object(type(request), "_validate_for_invoice", return_value=self.env.ref("l10n_pe.document_type02")), \
             patch.object(type(order), "action_pos_order_invoice", fail_after_write):
            request._process_pending()
        self.assertEqual(order.name, before_name)
        self.assertFalse(order.account_move)
        self.assertEqual(request.state, "failed")

    def test_configured_boleta_journal_is_used_and_accepted(self):
        order = self.make_order()
        order.config_id.invoice_journal_id.l10n_latam_use_documents = True
        ballot = order.config_id.invoice_journal_id.copy({"name": "Separate boleta journal", "code": "BALT"})
        order.alvina_submit_document(self.preview(order))
        # Exact selection contract in the supplied alvinha_point_of_sale:
        # config._get_journal(partner, refunded_order_id).
        def select(config, partner, refunded):
            self.assertEqual(partner, self.dni_partner)
            self.assertFalse(refunded)
            return ballot
        with patch.object(type(order.config_id), "_get_journal", select, create=True):
            values = order._prepare_invoice_vals()
            self.assertEqual(values["journal_id"], ballot.id)

    def make_paid_order(self, partner=None):
        partner = partner or self.dni_partner
        product = self.env["product.product"].create({
            "name": "Receipt integration service", "type": "service", "available_in_pos": True,
            "list_price": 118, "taxes_id": [Command.clear()],
            "property_account_income_id": self.company_data["default_account_revenue"].id,
        })
        self.config.invoice_journal_id.l10n_latam_use_documents = True
        self.config.journal_id = self.env["account.journal"].create({
            "name": "POS payment entries", "code": "PPAY", "type": "general",
            "company_id": self.company.id,
        })
        order = self.env["pos.order"].create({
            "session_id": self.session.id, "company_id": self.company.id,
            "amount_total": 118, "amount_tax": 0, "amount_paid": 118, "amount_return": 0,
            "fiscal_position_id": self.env["account.fiscal.position"].with_company(
                self.company)._get_fiscal_position(partner).id,
            "lines": [Command.create({"product_id": product.id, "qty": 1, "price_unit": 118,
                "price_subtotal": 118, "price_subtotal_incl": 118, "tax_ids": [Command.clear()]})],
            "payment_ids": [Command.create({"payment_method_id": self.cash_payment_method.id,
                "amount": 118, "payment_date": fields.Datetime.now()})],
        })
        order.action_pos_order_paid()
        self.assertEqual(order.state, "paid")
        return order

    def test_real_paid_sale_processes_once_without_creating_another_order_or_payment(self):
        order = self.make_paid_order()
        ballot = self.config.invoice_journal_id.copy({"name": "Real boleta journal", "code": "REALB"})
        order.alvina_submit_document(self.preview(order))
        request = order._alvina_request()
        counts = [self.env[model].search_count([]) for model in ("pos.order", "pos.payment", "account.move")]
        with patch.object(type(order.config_id), "_get_journal", return_value=ballot, create=True):
            result = request._process_pending()
        self.assertEqual(order.account_move.journal_id, ballot)
        self.assertEqual(result["state"], "processed", result)
        self.assertTrue(result["can_print"])
        self.assertEqual(order.account_move.state, "posted")
        self.assertEqual(order.account_move.amount_total, 118)
        self.assertEqual(order.account_move.l10n_latam_document_type_id, self.env.ref("l10n_pe.document_type02"))
        request._process_pending()
        self.assertEqual(request.attempts, 1)
        self.assertEqual(self.env["pos.order"].search_count([]), counts[0])
        self.assertEqual(self.env["pos.payment"].search_count([]), counts[1])
        self.assertEqual(self.env["account.move"].search_count([]), counts[2] + 2)

    def test_immediate_real_factura_has_type_01_and_download_action(self):
        partner = self.env["res.partner"].create({
            "name": "Real invoice fixture", "vat": "20100070970", "street": "Fiscal fixture address",
            "country_id": self.env.ref("base.pe").id,
            "l10n_latam_identification_type_id": self.env.ref("l10n_pe.it_RUC").id,
        })
        order = self.make_paid_order(partner)
        self.company.sudo().alvina_emission_mode = "immediate"
        preview = order.alvina_lookup_identity("factura", partner.vat)["identity_id"]
        result = order.alvina_submit_document(preview)
        self.assertEqual(result["state"], "processed", result)
        self.assertEqual(order.account_move.state, "posted")
        self.assertEqual(order.account_move.amount_total, 118)
        self.assertEqual(order.account_move.l10n_latam_document_type_id, self.env.ref("l10n_pe.document_type01"))
        action = order.alvina_print_document()
        self.assertEqual(action["type"], "ir.actions.act_url")
        self.assertIn(str(order.account_move.id), action["url"])
        self.assertEqual(order.alvina_submit_document(preview), result)

    def test_synced_ticket_is_not_auto_invoiced_before_receipt_choice_or_selected_at_night(self):
        order = self.make_paid_order()
        self.company.sudo().alvina_emission_mode = "immediate"
        order.to_invoice = True  # The existing fast-payment addon sets this flag.
        order._process_saved_order(False)
        self.assertEqual(order.state, "paid")
        self.assertFalse(order.to_invoice)
        self.assertFalse(order.account_move)
        self.assertFalse(order._alvina_request())
        # These are both mandatory conditions of the supplied nightly domain.
        nightly = [("id", "=", order.id), ("to_invoice", "=", True), ("account_move", "=", False)]
        self.assertFalse(self.env["pos.order"].search(nightly))
        result = order.alvina_submit_document(self.preview(order))
        self.assertEqual(result["state"], "processed", result)
        self.assertTrue(order.account_move)
        self.assertFalse(self.env["pos.order"].search(nightly))

    def test_resync_does_not_change_the_invoice_flag_on_an_existing_ordinary_invoice(self):
        order = self.make_paid_order()
        order.partner_id = self.dni_partner
        order.with_context(generate_pdf=False).action_pos_order_invoice()
        self.assertTrue(order.account_move)
        self.assertFalse(order._alvina_request())
        self.assertTrue(order.to_invoice)
        self.company.sudo().alvina_emission_mode = "immediate"
        order._process_saved_order(True)
        self.assertTrue(order.to_invoice)
